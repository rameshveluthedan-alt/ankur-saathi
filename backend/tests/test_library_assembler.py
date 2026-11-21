"""
Plans built by code from the recorded-block library, with no AI call (app/services/library_assembler.py): any skill and session length, a
teacher's own group skills, a re-teach of the group's commonest mistake; then the app's own pipeline runs its checks, and the plan is stored as
'library'. Uses the REAL library in db/seeds/library and a scratch class. No AI.

    python backend/tests/test_library_assembler.py --env-file backend/.env
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import asyncio
import contextlib
import io
import json
import os
import sys
from datetime import date, timedelta
from types import SimpleNamespace

os.environ.setdefault("AUTH_MODE", "off")
import _scratch
os.environ["LIBRARY_FALLBACK"] = "1"            # this test is about the library (the helper turns it off for the others)
import anthropic
from app.services import library_assembler as la, plan_service, writing_sheets

TODAY = date.today()
failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


def ctx_for(skills, minutes, domain="numeracy", reteach_groups=None, reteach_items=None):
    return SimpleNamespace(group_skill_ids=skills, available_minutes=minutes, reteach_groups=reteach_groups, reteach_competencies=reteach_items or [],
                           domain_id=domain, sheet_kinds=writing_sheets.group_kinds(skills, domain))


print("the assembler on its own")
check("the library is there", la.available())
check("slot lengths map to the three lengths", [la.nominal_length(m) for m in (7, 13, 14, 16, 18, 22, 30)] == ["short", "medium", "medium", "medium", "long", "long", "long"])
N232 = {"beginner": "N2.3.1", "progressor": "N2.3.2", "proficient": "N3.3.1"}
for minutes in (45, 60, 90):
    p = la.assemble(ctx_for(N232, minutes), TODAY)
    blocks = p["rotation_schedule"]["blocks"]
    teach = {b["teach_group"]: b for b in blocks if b["type"] == "teach"}
    check(f"{minutes} minutes: every block, adding up to the session", sum(b["duration_minutes"] for b in blocks) == minutes and len(teach) == 3,
          [(b["type"], b["duration_minutes"]) for b in blocks])
    if minutes == 45:
        check("...45: the team's table (anchor 5, no setup, Beginners 16, Progressors 14, Proficients 7)",
              blocks[0]["duration_minutes"] == 5 and not any(b["type"] == "setup" for b in blocks)
              and [teach[g]["duration_minutes"] for g in ("beginner", "progressor", "proficient")] == [16, 14, 7])
        check("...the 7-minute block is the short piece: no We Do", teach["proficient"]["talking_points"]["we_do_hi"] == "")
    check(f"...{minutes}: each group has talking points, show-me questions and a worksheet", all(teach[g]["talking_points"]["i_do_hi"] and teach[g]["cfu"] and p["worksheets"][g].get("problems") for g in teach))
    ext = {45: 1, 60: 2, 90: 3}[minutes]
    check(f"...{minutes}: the maths sheets are 3 + {ext}", all(len(p["worksheets"][g]["problems"]) == 3 + ext and p["worksheets"][g]["required_count"] == 3 for g in teach),
          [len(p["worksheets"][g]["problems"]) for g in teach])
check("the anchor: a setting, and each group's own task in it", p["library"]["setting"] and all(p["anchor"][f"{g}_participation_hi"] for g in N232) and p["anchor"]["narration_hi"])
check("'meanwhile' names the two other groups' own activities", all(sum(lbl in teach[g]["other_groups_hi"] for lbl in ("शुरुआती समूह", "प्रगतिशील समूह", "दक्ष समूह")) == 2 for g in teach))
check("the plan says how it was made (code, AI-drafted pieces, not yet reviewed)", p["explainability"]["items"][0]["id"] == "library" and "not yet reviewed" in p["explainability"]["items"][0]["body_en"])
p2 = la.assemble(ctx_for(N232, 60), TODAY, avoid_setting=p["library"]["setting"])
check("yesterday's setting is not used again when another fits as well", p2["library"]["setting"] != p["library"]["setting"], p2["library"]["setting"])
own = la.assemble(ctx_for({"beginner": "N2.2.1", "progressor": "N2.3.2", "proficient": "N2.3.3"}, 60), TODAY)
check("a teacher's own group skills (any skills) are served", own is not None and own["library"]["pieces"][0].startswith("N2.2.1"), own and own["library"]["pieces"][:3])
rt = la.assemble(ctx_for(N232, 60, reteach_groups=["proficient"],
                         reteach_items=[{"competency_id": "N3.3.1", "misconception_id": "N3.3.1-M1", "affected_by_group": {"proficient": 4}}]), TODAY)
check("a re-teach: the group's commonest mistake's re-teach piece", rt["library"]["reteach"] == {"proficient": "N3.3.1-M1"} and any(k.startswith("N3.3.1-M1__") for k in rt["library"]["pieces"]), rt["library"])
lit = la.assemble(ctx_for({"beginner": "L1.7.3", "progressor": "L2.7.2", "proficient": "L3.7.1"}, 60, "r1_literacy"), TODAY)
check("Hindi writing (L2.7.2): the writing sheets keep their own shape", lit is not None and lit["worksheets"]["progressor"].get("sheet_kind") == "composition", lit and lit["worksheets"]["progressor"].get("sheet_kind"))
check("an unknown skill: no plan (the caller falls back)", la.assemble(ctx_for({"beginner": "X9.9.9", "progressor": "N2.3.2", "proficient": "N3.3.1"}, 60), TODAY) is None)


class NoAI:
    def __init__(self):
        self.calls = 0
        self.messages = self

    async def create(self, **kw):
        self.calls += 1
        raise AssertionError("no AI call may be made")


async def main():
    db = await _scratch.connect()
    levels = {r: ("beginner" if r <= 8 else ("progressor" if r <= 20 else "proficient"),) * 2 for r in range(1, 31)}
    teacher_id, school = await _scratch.make_class(db, levels, grade="grade_2")
    real = anthropic.AsyncAnthropic
    fake = NoAI()
    anthropic.AsyncAnthropic = lambda **kw: SimpleNamespace(messages=fake)
    os.environ["PLAN_SOURCE"] = "library"
    try:
        print("\nthrough the app's pipeline (PLAN_SOURCE=library: no AI)")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            reply = await plan_service.generate_dainik_yojana(db, teacher_id, "N2.3.2", "numeracy", TODAY, session_minutes=45)
        row = await db.fetchrow("SELECT plan_content, claude_model FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2", teacher_id, TODAY)
        pc = json.loads(row["plan_content"]) if isinstance(row["plan_content"], str) else row["plan_content"]
        check("served from the library, with no AI call", pc["served_from"] == "library" and fake.calls == 0 and row["claude_model"] == "library", (pc.get("served_from"), fake.calls))
        check("the plan keeps the teacher's 45 minutes", pc["session_minutes"] == 45)
        teach = [b for b in pc["rotation_schedule"]["blocks"] if b["type"] == "teach"]
        check("each block carries its pace from the layout (for the screen)", all(b.get("pace") for b in teach), [b.get("pace") for b in teach])
        check("the show-me questions went through the app's check (one kept per block at 45)", all(len(b.get("cfu") or []) == 1 for b in teach), [len(b.get("cfu") or []) for b in teach])
        check("the 'Why this plan?' panel has the library note and the resources item", {"library", "resources"} <= {i.get("id") for i in pc["explainability"]["items"]})
        warn = reply.get("validation_warnings") or []
        check("no shape warning about the worksheets or the blocks", not any(("required_count" in w or "problems" in w or "blocks[" in w) for w in warn), warn)
        os.environ.pop("PLAN_SOURCE")
        os.environ["LIBRARY_FALLBACK"] = "0"
        from app.services import ai_budget
        settings = __import__("app.core.config", fromlist=["get_settings"]).get_settings()
        settings.ai_enabled = False
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                await plan_service.generate_dainik_yojana(db, teacher_id, "N2.3.2", "numeracy", TODAY + timedelta(days=1), session_minutes=90)
            pc2 = json.loads((await db.fetchval("SELECT plan_content FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2", teacher_id, TODAY + timedelta(days=1))))
            check("the library switched off (LIBRARY_FALLBACK=0) and no AI: the recorded plan, as before", pc2["served_from"] == "sample")
            os.environ["LIBRARY_FALLBACK"] = "1"
            with contextlib.redirect_stdout(io.StringIO()):
                await plan_service.generate_dainik_yojana(db, teacher_id, "N2.3.2", "numeracy", TODAY + timedelta(days=2), session_minutes=60)
            pc3 = json.loads((await db.fetchval("SELECT plan_content FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2", teacher_id, TODAY + timedelta(days=2))))
            check("the AI switched off (AI_ENABLED=false): the library plan comes first", pc3["served_from"] == "library" and pc3["session_minutes"] == 60)
        finally:
            settings.ai_enabled = True
    finally:
        os.environ.pop("PLAN_SOURCE", None)
        os.environ.pop("LIBRARY_FALLBACK", None)
        anthropic.AsyncAnthropic = real
        await _scratch.remove_class(db, teacher_id, school)
        await db.close()


asyncio.run(main())
if failures:
    print(f"\nFAILED ({len(failures)})")
    sys.exit(1)
print("\nOK: plans from the library for any skill, length and choice, through the app's own checks, with no AI call")
