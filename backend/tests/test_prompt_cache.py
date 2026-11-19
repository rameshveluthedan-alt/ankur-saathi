"""
Prompt v2, step 2: the fixed rules travel in a CACHED system block, the per-plan facts in the user message, and the meter counts the cached
tokens (docs/drafts/PROMPT_V2_REBUILD_PLAN.md, D2 and D3). The AI is a fake: no paid call.

    python backend/tests/test_prompt_cache.py --env-file backend/.env
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
from app.services import ai_budget, plan_service
import orchestrate
from cfu_prompt import CFU_RULES
from orchestrate import RETEACH_MAIN_RULES, HINDI_STYLE_SECTION, build_system_prompt, build_system_blocks

TODAY = date.today()
SAMPLE = json.load(open(os.path.join(HERE, "..", "..", "db", "seeds", "sample_plans", "N2.3.2.json"), encoding="utf-8"))
failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


print("the system prompt")
num, lit, num_off = build_system_prompt("numeracy", cfu=True), build_system_prompt("r1_literacy", cfu=True), build_system_prompt("numeracy", cfu=False)
check("it carries the role, the Hindi style, the show-me rules, the re-teach rules and the output format",
      all(x in num for x in (orchestrate._SYSTEM_ROLE, HINDI_STYLE_SECTION, CFU_RULES, RETEACH_MAIN_RULES, orchestrate._SCHEMA_COMMON, orchestrate._SCHEMA_WORKSHEET_NUMERACY)))
check("the literacy one has the literacy worksheet format, not the numeracy one", orchestrate._SCHEMA_WORKSHEET_LITERACY in lit and orchestrate._SCHEMA_WORKSHEET_NUMERACY not in lit)
check("with the show-me questions switched off, no show-me rules", CFU_RULES not in num_off and HINDI_STYLE_SECTION in num_off)
check("the November rules are in it word for word: polite instructions, no gendered 'मैं', mark names, the pace of every block",
      all(w in num for w in ("'बोर्ड पर लिखें: ...'", "Never the teacher's first person", "Never call ै or े a बिंदी", "Pace of EVERY teach block")))
check("it is the same text every time (a cache is read only by an identical prefix)", build_system_prompt("numeracy", cfu=True) == num)
check("nothing per-plan in it: no date, no roll number, no skill code", str(TODAY) not in num and "Roll:" not in num and "N2.3.2" not in num)
blocks = build_system_blocks("numeracy", cfu=True)
check("the server sends it as ONE text block marked for caching", len(blocks) == 1 and blocks[0]["type"] == "text" and blocks[0]["cache_control"] == {"type": "ephemeral"} and blocks[0]["text"] == num)
check("without a subject: the role only, as v1 (the preview and old callers)", build_system_prompt() == orchestrate._SYSTEM_ROLE)

print("the meter")
s = get_settings()
check("cache reads and writes have their own prices", (s.ai_price_cache_read_per_mtok, s.ai_price_cache_write_per_mtok) == (0.10, 2.5))
check("a call without caching costs what it did", ai_budget.cost_usd(1_000_000, 100_000) == 2.0 + 1.0)
check("cached tokens are priced: 1M read = $0.10, 1M written = $2.50", abs(ai_budget.cost_usd(0, 0, 1_000_000, 1_000_000) - 2.6) < 1e-9)
check("the SDK's usage fields are read, and a usage without them counts zero",
      ai_budget.cache_tokens_of(SimpleNamespace(cache_read_input_tokens=7, cache_creation_input_tokens=3)) == (7, 3) and ai_budget.cache_tokens_of(SimpleNamespace(input_tokens=1)) == (0, 0)
      and ai_budget.cache_tokens_of({"cache_read_input_tokens": 5}) == (5, 0) and ai_budget.cache_tokens_of(None) == (0, 0))


class Fake:
    def __init__(self, usages):
        self.calls, self.usages = [], list(usages)

    async def create(self, **kw):
        self.calls.append(kw)
        u = self.usages.pop(0) if self.usages else SimpleNamespace(input_tokens=100, output_tokens=100)
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(copy.deepcopy(SAMPLE), ensure_ascii=False))], stop_reason="end_turn", usage=u)


async def main():
    db = await _scratch.connect()
    teacher_id, school = await _scratch.make_class(db, {1: ("beginner", "beginner"), 2: ("progressor", "progressor"), 3: ("proficient", "proficient")}, grade="grade_2")
    real = anthropic.AsyncAnthropic
    try:
        print("\nthe request, with a stand-in model (two plans on two days, the second reads the cache)")
        fake = Fake([SimpleNamespace(input_tokens=4000, output_tokens=9000, cache_read_input_tokens=0, cache_creation_input_tokens=12000),
                     SimpleNamespace(input_tokens=4100, output_tokens=9100, cache_read_input_tokens=12000, cache_creation_input_tokens=0)])
        anthropic.AsyncAnthropic = lambda **kw: SimpleNamespace(messages=fake)
        with contextlib.redirect_stdout(io.StringIO()):
            await plan_service.generate_dainik_yojana(db, teacher_id, "N2.3.2", "numeracy", TODAY, session_minutes=90)
            await plan_service.generate_dainik_yojana(db, teacher_id, "N2.3.2", "numeracy", date.fromordinal(TODAY.toordinal() + 1), session_minutes=60)
        main_calls = [c for c in fake.calls if isinstance(c.get("system"), list)]
        check("both plan calls send the system as cached blocks", len(main_calls) == 2, [type(c.get("system")).__name__ for c in fake.calls])
        if len(main_calls) == 2:
            a, b = main_calls
            check("...byte-identical between the two plans, though the date and the minutes differ", a["system"] == b["system"])
            user = a["messages"][0]["content"]
            check("the user message keeps the per-plan facts (the time, PART C, the groups, the skill)",
                  all(w in user for w in ("**Available teaching time:** 90 minutes", "PART C: ROTATION SCHEDULE (90 min total)", "## THREE GROUPS", "N2.3.2")))
            check("...and no longer repeats the fixed rules", CFU_RULES not in user and HINDI_STYLE_SECTION not in user and orchestrate._SCHEMA_COMMON not in user and RETEACH_MAIN_RULES not in user)
            check("...and it points at the rules in the system instructions", "OUTPUT FORMAT given in the system instructions" in user)
            check("the show-me list per group is still in the user message (it is per plan)", "MISTAKES PER GROUP" in user)
        rows = await db.fetch("""SELECT input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, est_cost_usd FROM ai_usage
                                 WHERE school_id = (SELECT id FROM schools WHERE school_code = $1) AND kind = 'plan' ORDER BY id""", school)
        check("the meter stored both calls with their cached tokens", [(r["cache_read_tokens"], r["cache_write_tokens"]) for r in rows] == [(0, 12000), (12000, 0)], [dict(r) for r in rows])
        if len(rows) == 2:
            want = [round(ai_budget.cost_usd(4000, 9000, 0, 12000), 4), round(ai_budget.cost_usd(4100, 9100, 12000, 0), 4)]
            check("...and priced them (the cache write costs more than the read)", [float(r["est_cost_usd"]) for r in rows] == want and want[0] > want[1], ([float(r["est_cost_usd"]) for r in rows], want))
            spent = await ai_budget._spent(db, "school_id = (SELECT id FROM schools WHERE school_code = $1)", school)
            check("the caps add the cached tokens too", abs(spent - sum(want)) < 0.001, (spent, want))
    finally:
        anthropic.AsyncAnthropic = real
        await _scratch.remove_class(db, teacher_id, school)
        await db.close()


asyncio.run(main())
if failures:
    print(f"\nFAILED ({len(failures)})")
    sys.exit(1)
print("\nOK: the fixed rules are cached, the per-plan facts stay in the user message, and the meter counts the cached tokens")
