"""
The Hindi style rules inside the real plan pipeline: a plan the model writes with the old wording, and a recorded plan replayed when the AI
limit is reached, both come out softened and still valid.

    cd backend && AUTH_MODE=off python tests/test_hindi_style_pipeline.py --env-file .env
"""

import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):          # a pipe on Windows uses a legacy code page that cannot print Hindi
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")
import asyncio
import contextlib
import io
import json
import os
import re
import sys
from datetime import date
from types import SimpleNamespace

os.environ.setdefault("AUTH_MODE", "off")
import _scratch
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "prompts"))
import hindi_style as hs
import anthropic
from app.core.config import get_settings
from app.services import ai_budget as b, plan_service

S = get_settings()
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
OLD_STYLE = json.load(open(os.path.join(ROOT, "db", "seeds", "sample_plans", "N2.3.2.json"), encoding="utf-8"))     # contains फालतू, चुपचाप, खाना, आओ ...
failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


class FakeMessages:
    async def create(self, **kw):
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(OLD_STYLE, ensure_ascii=False))], stop_reason="end_turn",
                               usage=SimpleNamespace(input_tokens=6000, output_tokens=9000))


class FakeClient:
    def __init__(self, **kw):
        self.messages = FakeMessages()


def stored_text(row):
    pc = json.loads(row["plan_content"]) if isinstance(row["plan_content"], str) else row["plan_content"]
    return pc, json.dumps(pc, ensure_ascii=False)


def whole(word, text):
    return re.search(r"(?<![\u0900-\u0963\u0966-\u097F])" + word + r"(?![\u0900-\u0963\u0966-\u097F])", text) is not None


async def main():
    db = await _scratch.connect()
    levels = {r: ("beginner", "progressor", "proficient")[r % 3] for r in range(1, 19)}
    A, school = await _scratch.make_class(db, {r: (l, l) for r, l in levels.items()}, grade="grade_2")
    real = anthropic.AsyncAnthropic
    anthropic.AsyncAnthropic = FakeClient
    saved = (S.ai_cap_teacher_daily_usd, S.ai_cap_shared_demo_daily_usd)
    try:
        with contextlib.redirect_stdout(io.StringIO()) as out:
            r1 = await plan_service.generate_dainik_yojana(db, A, "N2.3.2", "numeracy", date(2031, 11, 1))
        log = out.getvalue()
        row = await db.fetchrow("SELECT plan_content FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2", A, date(2031, 11, 1))
        pc, text = stored_text(row)
        scripts = " ".join((blk.get("script_hi") or "") for blk in pc["rotation_schedule"]["blocks"])
        print("1. the model writes the OLD wording; the stored plan is softened")
        check("it was served from the AI", r1["served_from"] == "ai")
        check("the log says how many wording changes were made", "Hindi style:" in log, log[-200:])
        check("no फालतू or चुपचाप in what the teacher reads", not whole("फालतू", text) and not whole("चुपचाप", text))
        check("the transition scripts are respectful (आएँ, रोक दें, दें, जाएँ)", all(w in scripts for w in ("आएँ", "रोक दें", "दें", "जाएँ")) and "आओ" not in scripts and "बंद करो" not in scripts)
        check(f"the frame is called {hs.FRAME_WORD}, never खाना/खाने", not whole("खाना", text) and not whole("खाने", text) and f"दहाई-इकाई का {hs.FRAME_WORD}" in text)
        check("'कितनी दहाई और कितनी इकाई' (gender) is in the anchor", "कितनी दहाई और कितनी इकाई" in pc["anchor"]["beginner_participation_hi"])
        check("the plan is still complete (groups, worksheets, rotation)", len(r1["groups"]) == 3 and bool(pc["worksheets"]) and len(pc["rotation_schedule"]["blocks"]) >= 6)

        print("2. the AI limit is reached: the recorded plan is replayed, and softened the same way")
        S.ai_cap_teacher_daily_usd = S.ai_cap_shared_demo_daily_usd = 0.0
        with contextlib.redirect_stdout(io.StringIO()):
            r2 = await plan_service.generate_dainik_yojana(db, A, "N2.3.2", "numeracy", date(2031, 11, 2))
        row = await db.fetchrow("SELECT plan_content FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2", A, date(2031, 11, 2))
        pc2, text2 = stored_text(row)
        check("it was a recorded plan", r2["served_from"] == "sample")
        check("and it too has no old wording", not any(whole(w, text2) for w in ("फालतू", "चुपचाप", "खाना", "खाने")) and "आओ" not in text2)
    finally:
        S.ai_cap_teacher_daily_usd, S.ai_cap_shared_demo_daily_usd = saved
        anthropic.AsyncAnthropic = real
        await db.execute("DELETE FROM ai_usage WHERE school_id IN (SELECT id FROM schools WHERE school_code = $1)", school)
        await _scratch.remove_class(db, A, school)
        await db.close()
    if failures:
        print(f"\nFAILED ({len(failures)})")
        sys.exit(1)
    print("\nOK: a generated plan and a replayed plan both come out in the new Hindi style")


if __name__ == "__main__":
    asyncio.run(main())
