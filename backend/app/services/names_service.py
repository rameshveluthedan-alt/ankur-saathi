"""
Children's names. TEACHER-ONLY: shown on the teacher's own screens and in her own class report.

THE RULE: nothing that builds a request to the AI may import this module or read the child_names table. That covers
plan_service, the prompts, the baseline code and the worksheet renderer. backend/tests/test_names_static_guard.py fails
if one does, and backend/tests/test_names_never_reach_ai.py checks the real requests for a canary name.

The one AI-adjacent use is the opposite direction: after the AI answers about a photo, scrub_names removes any class
member's name the AI may have copied from the notebook page, before anything is stored.
"""

import re
import unicodedata

MAX_NAME = 80
# control characters and invisible marks; NOT the zero-width joiners (U+200C / U+200D), which Hindi conjuncts need
_STRIP = re.compile("[\u0000-\u001f\u007f-\u009f\u200b\u200e\u200f\u202a-\u202e\u2060\ufeff]")
PLACEHOLDER = "[नाम हटाया]"


def clean_name(raw) -> str:
    s = unicodedata.normalize("NFC", str(raw if raw is not None else ""))
    return re.sub(r"\s+", " ", _STRIP.sub("", s)).strip()


async def table_exists(db) -> bool:
    return bool(await db.fetchval("SELECT to_regclass('public.child_names') IS NOT NULL"))


async def names_for_teacher(db, teacher_id) -> dict:
    """{class number: name} for the teacher's own screens. Empty when no names were entered (or the table is not loaded yet)."""
    if not await table_exists(db):
        return {}
    rows = await db.fetch("""SELECT c.roll_number, cn.name FROM children c JOIN child_names cn ON cn.child_id = c.id
                             WHERE c.teacher_id = $1 AND c.is_active = TRUE""", teacher_id)
    return {r["roll_number"]: r["name"] for r in rows}


async def save_name(db, child_id, name: str):
    await db.execute("""INSERT INTO child_names (child_id, name) VALUES ($1, $2)
                        ON CONFLICT (child_id) DO UPDATE SET name = $2, updated_at = now()""", child_id, name)


def scrub_names(obj, names: dict) -> int:
    """
    Replace any class member's name found in the text of `obj` (a dict / list / string tree, changed in place) and return how
    many were replaced. Used on what the AI said about a photo: a name written in a notebook must not be kept.
    Slightly over-eager by design (a name part inside a longer Hindi word may be replaced): privacy first.
    """
    # the full name AND each part of it (people say "Asha", not "Asha Kumari"); parts shorter than 3 letters are left alone
    words = set()
    for n in names.values():
        n = (n or "").strip()
        if len(n) >= 2:
            words.add(n)
            words.update(t for t in n.split() if len(t) >= 3)
    words = sorted(words, key=len, reverse=True)
    if not words:
        return 0
    pattern = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(w) for w in words) + r")(?!\w)", re.IGNORECASE | re.UNICODE)
    count = 0

    def walk(x):
        nonlocal count
        if isinstance(x, dict):
            for k, v in x.items():
                if isinstance(v, str):
                    new, n = pattern.subn(PLACEHOLDER, v)
                    if n:
                        x[k], count = new, count + n
                else:
                    walk(v)
        elif isinstance(x, list):
            for i, v in enumerate(x):
                if isinstance(v, str):
                    new, n = pattern.subn(PLACEHOLDER, v)
                    if n:
                        x[i], count = new, count + n
                else:
                    walk(v)

    walk(obj)
    return count
