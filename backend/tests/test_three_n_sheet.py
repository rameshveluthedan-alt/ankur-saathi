"""
Prompt v2, step 5: the 3 + N worksheet for maths and reading sheets (docs/drafts/PROMPT_DRAFT_3N_WORKSHEET.md): 3 core problems every child does
(the signal), then 1, 2 or 3 extras by the session's length. Writing, fluency and observed sheets keep their own November rules. The count is
per plan, so it is stated in PART B (the user message); the cached system rules never carry it. The AI is a fake: no paid call.

    python backend/tests/test_three_n_sheet.py --env-file backend/.env
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
from datetime import date, timedelta
from types import SimpleNamespace

os.environ.setdefault("AUTH_MODE", "off")
HERE = os.path.dirname(os.path.abspath(__file__))
import _scratch
import anthropic
from app.services import plan_service
from orchestrate import build_system_prompt, RETEACH_MAIN_RULES
from session_shape import session_shape, worksheet_extras

TODAY = date.today()
SEEDS = os.path.join(HERE, "..", "..", "db", "seeds", "sample_plans")
failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


print("the extras by length (provisional: 1 / 2 / 3)")
check("45 -> 1, 60 -> 2, 90 -> 3", [worksheet_extras(m) for m in (45, 60, 90)] == [1, 2, 3])
check("another length takes the nearest; a tie goes to the shorter; nonsense is treated as 90", (worksheet_extras(50), worksheet_extras(75), worksheet_extras(120), worksheet_extras(None)) == (1, 2, 3, 3))
check("the session shape carries it", (session_shape(60)["core"], session_shape(60)["extras"], session_shape(60)["sheet_total"]) == (3, 2, 5))

print("the rules (cached system prompt)")
num, lit = build_system_prompt("numeracy", cfu=True), build_system_prompt("r1_literacy", cfu=True)
check("the 3 + N sheet: 3 core, the extras PART B gives, required_count 3", all(w in num for w in ("THE 3 + N SHEET", "exactly 3 CORE problems", "the number of EXTRA problems that PART B gives", '"required_count" is 3')))
check("the core is the signal: 1 plainest, 2 and 3 reveal the listed mistakes, no diagnostic on an extra", "problem 1, the skill in its plainest form" in num and "NO extra problem does" in num)
check("the old counts are gone (5 / 6 required, '8-10 problems')", "required_count 5" not in num and "required_count 6" not in num and "problems 1-5 first" not in num)
check("the You Do says 1 to 3", "'पहले वर्कशीट के सवाल 1 से 3 हल करें" in num and "वर्कशीट के सवाल 1 से 3 पहले हल करें" in RETEACH_MAIN_RULES)
check("writing, fluency and observed sheets follow their own section", "follows that section instead" in num)
check("a reading sheet is 3 + N, and bank questions are its core", "A READING sheet is a 3 + N sheet" in lit and "they ARE the core" in lit)
check("no per-plan number in the cached rules (the count is in PART B)", "3 core + 1" not in num and "3 core + 3" not in num)

print("the plan checks")
def sheet(n, rc, diag_at=()):
    return {"required_count": rc, "problems": [{"number": i, "problem_hi": f"{10 + i} + {20 + i}", "answer": str(30 + 2 * i),
                                                 "diagnostic_for_misconception": ("X-M1" if i in diag_at else None)} for i in range(1, n + 1)]}
def warn(ws, extras=2, kinds=None):
    plan = {"worksheets": {"beginner": ws, "progressor": sheet(5, 3, (2, 3)), "proficient": sheet(5, 3, (2,))}}
    return [w for w in plan_service.validate_plan_shape(plan, "numeracy", extras=extras, sheet_kinds=kinds) if "worksheets.beginner" in w]
check("a 3 + 2 sheet with its diagnostics in the core: no warning", warn(sheet(5, 3, (2, 3))) == [], warn(sheet(5, 3, (2, 3))))
check("required_count 5: warned", any("not 3" in w for w in warn(sheet(5, 5))))
check("the wrong number of problems: warned", any("not 3 core + 2 extra" in w for w in warn(sheet(8, 3))))
check("a diagnostic on an extra: warned", any("is an extra (only the core 1-3 may)" in w for w in warn(sheet(5, 3, (4,)))))
check("a composition sheet is not held to 3 + N", warn(sheet(2, 2), kinds={"beginner": "composition"}) == [])
check("a recorded plan (extras unknown) keeps the old rules", warn(sheet(8, 5), extras=None) == [])


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
    real = anthropic.AsyncAnthropic
    try:
        print("\nPART B, with a stand-in model")
        seen = {}
        for i, m in enumerate((45, 60, 90)):
            fake = Fake(json.load(open(os.path.join(SEEDS, "N2.3.2.json"), encoding="utf-8")))
            anthropic.AsyncAnthropic = lambda **kw: SimpleNamespace(messages=fake)
            with contextlib.redirect_stdout(io.StringIO()):
                await plan_service.generate_dainik_yojana(db, teacher_id, "N2.3.2", "numeracy", TODAY + timedelta(days=i), session_minutes=m)
            seen[m] = fake.prompts[-1].split("### PART B")[1].split("### PART C")[0]
        check("maths, 45 / 60 / 90 minutes: 3 core + 1 / 2 / 3 extra in PART B",
              all(f"3 core + {e} extra = {3 + e} problems" in seen[m] for m, e in ((45, 1), (60, 2), (90, 3))), seen[45][:200])
        check("...on each group's line, with its own mistakes in the core", sum(1 for l in seen[90].splitlines() if l.startswith("- ") and "3 core + 3 extra" in l and "core problem 2 reveals this group's OWN mistake" in l) == 3, seen[90])

        fake = Fake(json.load(open(os.path.join(SEEDS, "L2.7.2.json"), encoding="utf-8")))
        anthropic.AsyncAnthropic = lambda **kw: SimpleNamespace(messages=fake)
        with contextlib.redirect_stdout(io.StringIO()):
            await plan_service.generate_dainik_yojana(db, teacher_id, "L2.7.2", "r1_literacy", TODAY + timedelta(days=5), session_minutes=60)
        pb = fake.prompts[-1].split("### PART B")[1].split("### PART C")[0]
        lines = {l.split(":")[0].strip("- "): l for l in pb.splitlines() if l.startswith("- ")}
        prog = [l for l in seen[90].splitlines() if l.startswith("- प्रगतिशील")][0]
        check("two mistakes for two core problems: the top two, in order (2 then 3)", "core problem 2 reveals this group's OWN mistake N2.3.2-M1, core problem 3 reveals N2.3.2-M2" in prog and "M4" not in prog, prog)
        beg = [l for l in seen[90].splitlines() if l.startswith("- शुरुआती")][0]
        check("a skill with one recorded mistake: problem 3 is the hardest case", "core problem 3 is the hardest case the skill allows" in beg, beg)
        check("Hindi writing (L2.7.2): the writing groups follow their own section, not 3 + N", "COMPOSITION sheet: follow its own section" in pb, pb)
        check("...and a reading group (if any) gets 3 + 2", all(("3 core + 2 extra" in l) or ("follow its own section" in l) for l in lines.values()), lines)
    finally:
        anthropic.AsyncAnthropic = real
        await _scratch.remove_class(db, teacher_id, school)
        await db.close()


asyncio.run(main())
if failures:
    print(f"\nFAILED ({len(failures)})")
    sys.exit(1)
print("\nOK: 3 core + 1 / 2 / 3 extra for maths and reading sheets; the other sheets keep their own rules")
