"""
Prompt v2, step 4: each group's OWN mistakes, in ONE list, for the show-me questions AND the worksheets. Before, the worksheets saw only the
Progressors' mistakes (the MISCONCEPTION TAXONOMY), so the Beginner and Proficient sheets borrowed them and photo marking was told the wrong
mistakes for those groups (docs/KNOWN_ISSUES.md). The code now also clears a diagnostic ID that is not the group's own. The AI is a fake.

    python backend/tests/test_group_mistakes.py --env-file backend/.env
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import asyncio
import contextlib
import copy
import io
import json
import os
import sys
from datetime import date
from types import SimpleNamespace

os.environ.setdefault("AUTH_MODE", "off")
HERE = os.path.dirname(os.path.abspath(__file__))
import _scratch
import anthropic
from app.core.config import get_settings
from app.services import plan_service

TODAY = date.today()
SAMPLE = json.load(open(os.path.join(HERE, "..", "..", "db", "seeds", "sample_plans", "N2.3.2.json"), encoding="utf-8"))
failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


print("the code check on the worksheet labels")
kb = {"beginner": {"competency_id": "B1", "mistakes": [{"id": "B1-M1"}]}, "progressor": {"competency_id": "P1", "mistakes": [{"id": "P1-M1"}, {"id": "P1-M2"}]}}
plan = {"worksheets": {
    "beginner": {"problems": [{"number": 1, "diagnostic_for_misconception": "B1-M1"}, {"number": 2, "diagnostic_for_misconception": "P1-M1"}, {"number": 3}]},
    "progressor": {"problems": [{"number": 1, "diagnostic_for_misconception": "P1-M2"}, {"number": 2, "diagnostic_for_misconception": {"id": "P1-M1"}}]},
    "proficient": {"problems": [{"number": 1, "diagnostic_for_misconception": "X-M9"}]}}}
log = plan_service.clean_worksheet_diagnostics(plan, kb)
w = plan["worksheets"]
check("a group's own mistake stays", w["beginner"]["problems"][0]["diagnostic_for_misconception"] == "B1-M1" and w["progressor"]["problems"][0]["diagnostic_for_misconception"] == "P1-M2")
check("another group's mistake on a sheet is cleared, the problem kept", w["beginner"]["problems"][1]["diagnostic_for_misconception"] is None and len(w["beginner"]["problems"]) == 3)
check("a label that is not even an ID (an object) is cleared, without an error", w["progressor"]["problems"][1]["diagnostic_for_misconception"] is None)
check("a group with nothing to check against is left alone", w["proficient"]["problems"][0]["diagnostic_for_misconception"] == "X-M9")
check("each clearing is logged, naming the group's skill", len(log) == 2 and "P1-M1 is not a mistake of B1" in log[0], log)
check("an empty or odd plan does nothing", plan_service.clean_worksheet_diagnostics({}, kb) == [] and plan_service.clean_worksheet_diagnostics(None, None) == [])


class Fake:
    def __init__(self, plan):
        self.prompts, self.plan = [], plan

    async def create(self, **kw):
        self.prompts.append(kw["messages"][0]["content"])
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(self.plan, ensure_ascii=False))], stop_reason="end_turn",
                               usage=SimpleNamespace(input_tokens=100, output_tokens=100))


async def main():
    db = await _scratch.connect()
    teacher_id, school = await _scratch.make_class(db, {1: ("beginner", "beginner"), 2: ("progressor", "progressor"), 3: ("proficient", "proficient")}, grade="grade_2")
    real, settings = anthropic.AsyncAnthropic, get_settings()
    try:
        ids = {c: [r["id"] for r in await db.fetch("SELECT id FROM misconceptions WHERE competency_id = $1 ORDER BY sort_order", c)] for c in ("N2.3.1", "N2.3.2", "N3.3.1")}
        print("\nthe prompt, with a stand-in model (N2.3.2: Beginner N2.3.1, Progressor N2.3.2, Proficient N3.3.1)")
        check("the knowledge base has mistakes for all three skills", all(ids.values()), ids)
        reply = copy.deepcopy(SAMPLE)
        # the model labels a Beginner problem with a PROGRESSOR mistake: the old prompt's typical slip
        reply["worksheets"]["beginner"]["problems"][0]["diagnostic_for_misconception"] = ids["N2.3.2"][0]
        reply["worksheets"]["progressor"]["problems"][0]["diagnostic_for_misconception"] = ids["N2.3.2"][0]
        fake = Fake(reply)
        anthropic.AsyncAnthropic = lambda **kw: SimpleNamespace(messages=fake)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            await plan_service.generate_dainik_yojana(db, teacher_id, "N2.3.2", "numeracy", TODAY, session_minutes=90)
        user = fake.prompts[-1]
        check("no Progressors-only MISCONCEPTION TAXONOMY any more", "MISCONCEPTION TAXONOMY" not in user)
        check("ONE list, MISTAKES PER GROUP, said to be for the show-me questions AND the worksheets", user.count("MISTAKES PER GROUP (from L1") == 1 and "worksheet's diagnostic_for_misconception" in user)
        sect = user.split("MISTAKES PER GROUP (from L1")[1]
        check("each group appears with its own skill and its own mistake IDs",
              all(s in sect for s in ("GROUP BEGINNER", "N2.3.1", "GROUP PROGRESSOR", "GROUP PROFICIENT", "N3.3.1")) and ids["N2.3.1"][0] in sect and ids["N3.3.1"][0] in sect)
        partb = user.split("### PART B")[1].split("### PART C")[0]
        beg, pro = [l for l in partb.splitlines() if l.startswith("- शुरुआती")][0], [l for l in partb.splitlines() if l.startswith("- दक्ष")][0]
        check("PART B names the Beginners' own mistakes on the Beginner line, not the Progressors'", ids["N2.3.1"][0] in beg and ids["N2.3.2"][0] not in beg, beg)
        check("...and the Proficients' own on theirs", ids["N3.3.1"][0] in pro and ids["N2.3.2"][0] not in pro, pro)
        row = await db.fetchrow("SELECT plan_content FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2", teacher_id, TODAY)
        pc = json.loads(row["plan_content"]) if isinstance(row["plan_content"], str) else row["plan_content"]
        check("the borrowed Progressor ID on the Beginner sheet is cleared in the saved plan", pc["worksheets"]["beginner"]["problems"][0].get("diagnostic_for_misconception") is None)
        check("...the Progressors keep theirs", pc["worksheets"]["progressor"]["problems"][0].get("diagnostic_for_misconception") == ids["N2.3.2"][0])
        check("...and the log says so", f"{ids['N2.3.2'][0]} is not a mistake of N2.3.1" in buf.getvalue())

        print("\nwith the show-me questions switched off, the list stays (the worksheets need it)")
        settings.cfu_enabled = False
        try:
            fake2 = Fake(copy.deepcopy(SAMPLE))
            anthropic.AsyncAnthropic = lambda **kw: SimpleNamespace(messages=fake2)
            with contextlib.redirect_stdout(io.StringIO()):
                await plan_service.generate_dainik_yojana(db, teacher_id, "N2.3.2", "numeracy", date.fromordinal(TODAY.toordinal() + 1), session_minutes=90)
            check("MISTAKES PER GROUP is there, with the Beginners' own IDs", "MISTAKES PER GROUP" in fake2.prompts[-1] and ids["N2.3.1"][0] in fake2.prompts[-1])
        finally:
            settings.cfu_enabled = True
    finally:
        anthropic.AsyncAnthropic = real
        await _scratch.remove_class(db, teacher_id, school)
        await db.close()


asyncio.run(main())
if failures:
    print(f"\nFAILED ({len(failures)})")
    sys.exit(1)
print("\nOK: each group's own mistakes, one list, and no borrowed label survives")
