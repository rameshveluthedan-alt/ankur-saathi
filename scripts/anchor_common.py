"""
Ankur Saathi — shared definitions for the anchor-bank spreadsheet tools.

The template builder and the importer both read COLUMNS, so the spreadsheet and the
loader can never drift apart. Change a column here and re-run build_anchor_template.py.
"""

import argparse
import os
from pathlib import Path

# ── Sheet layout ─────────────────────────────────────────────────────────────
SHEET_ANCHORS = "Anchors"
BAND_ROW = 1          # coloured group labels
HEADER_ROW = 2        # column headers (the importer matches on these exact labels)
EXAMPLE_ROW = 3       # one worked example; the importer skips it
FIRST_INPUT_ROW = 4
LAST_INPUT_ROW = 103  # 100 rows to fill in

# ── Option lists (shown as dropdowns) ────────────────────────────────────────
SUBJECTS = {"Numeracy": "numeracy", "Literacy": "r1_literacy"}
THEMES = ["market", "kitchen", "farm", "festival", "school", "travel",
          "home", "nature", "animals", "other"]
SETTINGS = ["universal", "rural", "urban"]
GRADES = [("gr_balvatika", "Balvatika", "balvatika"),
          ("gr_1", "Grade 1", "grade_1"),
          ("gr_2", "Grade 2", "grade_2"),
          ("gr_3", "Grade 3", "grade_3")]
GRADE_LABEL = {code: label for _, label, code in GRADES}

# ── Columns of the "Anchors" sheet, in order ─────────────────────────────────
# kind: text | longtext | subject | theme | setting | grade | number | competency | yn | tlm
def _c(key, label, group, width, kind="text", required=False):
    return dict(key=key, label=label, group=group, width=width, kind=kind, required=required)

G_ABOUT = "ABOUT THE ACTIVITY"
G_GRADES = "GRADES — mark Y where children can do it"
G_SKILLS = "WHAT IT TEACHES — pick skill IDs from the list"
G_TEXT = "THE ACTIVITY — write in Hindi"
G_MAT = "MATERIALS"
G_SRC = "SOURCE AND REVIEW"

COLUMNS = (
    [_c("anchor_id", "Anchor ID (leave blank for a new anchor)", G_ABOUT, 16),
     _c("subject", "Subject", G_ABOUT, 12, "subject", True),
     _c("title_en", "Title (English)", G_ABOUT, 24, "text", True),
     _c("title_hi", "शीर्षक — Title (Hindi)", G_ABOUT, 24, "text", True),
     _c("description_en", "What children do and learn (1-2 sentences, English)", G_ABOUT, 38, "longtext", True),
     _c("theme", "Story theme", G_ABOUT, 11, "theme", True),
     _c("setting", "Setting", G_ABOUT, 11, "setting"),
     _c("duration", "Minutes", G_ABOUT, 8, "number")]
    + [_c(k, lab, G_GRADES, 9, "grade") for k, lab, _ in GRADES]
    + [_c(f"primary_{i}", f"Main skill {i}" + (" (required)" if i == 1 else ""), G_SKILLS, 12, "competency", i == 1)
       for i in (1, 2, 3)]
    + [_c(f"secondary_{i}", f"Also practises {i}", G_SKILLS, 12, "competency") for i in (1, 2, 3, 4)]
    + [_c("setup_hi", "Story or situation the teacher tells", G_TEXT, 42, "longtext", True),
       _c("whole_class_hi", "Whole-class moment: what the teacher shows or asks everyone", G_TEXT, 42, "longtext"),
       _c("beginner_hi", "Beginner task", G_TEXT, 42, "longtext", True),
       _c("progressor_hi", "Progressor task", G_TEXT, 42, "longtext", True),
       _c("proficient_hi", "Proficient task", G_TEXT, 42, "longtext", True),
       _c("closing_hi", "Closing question for everyone", G_TEXT, 36, "longtext", True)]
    + [_c("needs_print", "Needs a printout? (Y/N)", G_MAT, 11, "yn"),
       _c("tlm_1", "Material 1 (TLM)", G_MAT, 11, "tlm"),
       _c("tlm_2", "Material 2 (TLM)", G_MAT, 11, "tlm")]
    + [_c("source", "Source (original / adapted from … / permission obtained)", G_SRC, 28),
       _c("validated_by", "Skill tags checked by (name)", G_SRC, 20)]
)
KEYS = [c["key"] for c in COLUMNS]
LABEL_TO_KEY = {c["label"]: c["key"] for c in COLUMNS}


def col_index(key: str) -> int:
    """1-based column number of a key on the Anchors sheet."""
    return KEYS.index(key) + 1


# ── Database helpers (explicit parameters: URL parsing is unreliable on some Windows setups) ──
def parse_env_file(path: str) -> dict:
    out = {}
    p = Path(path)
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def add_db_args(parser: argparse.ArgumentParser):
    parser.add_argument("--env-file", default=None,
                        help="read DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME from this file "
                             "(e.g. backend/.env)")
    for name, default in (("host", "127.0.0.1"), ("port", "5432"), ("user", "postgres"),
                          ("password", ""), ("name", "ankur_saathi")):
        parser.add_argument(f"--db-{name}", default=None, help=f"default {default or '(empty)'}")


def db_params(args) -> dict:
    env = parse_env_file(args.env_file) if args.env_file else {}
    def pick(opt, key, default):
        return getattr(args, f"db_{opt}") or env.get(key) or os.environ.get(key) or default
    return dict(host=pick("host", "DB_HOST", "127.0.0.1"), port=int(pick("port", "DB_PORT", "5432")),
                user=pick("user", "DB_USER", "postgres"), password=pick("password", "DB_PASSWORD", ""),
                database=pick("name", "DB_NAME", "ankur_saathi"), ssl=False)


async def connect(args):
    import asyncpg
    return await asyncpg.connect(**db_params(args))
