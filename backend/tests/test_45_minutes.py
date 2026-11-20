"""
Prompt v2, step 3: a 45-minute session follows the team's table (19 Nov 2026): anchor 5, no setup, blocks 16 / 14 / 7 by need (a re-taught group
takes the longest), each block with its own pace, one show-me question per block, transitions 2 + 1. The prompt says it, the show-me check keeps
one, and the plan carries each block's pace for the screen. The AI is a fake: no paid call.

    python backend/tests/test_45_minutes.py --env-file backend/.env
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

TODAY = date.today()
SAMPLE = json.load(open(os.path.join(HERE, "..", "..", "db", "seeds", "sample_plans", "N2.3.2.json"), encoding="utf-8"))
failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


def reply_45(minutes_by_group):
    """The recorded N2.3.2 plan with its blocks laid out for 45 minutes, and three show-me questions per block (the app keeps one)."""
    plan = copy.deepcopy(SAMPLE)
    blocks = [b for b in plan["rotation_schedule"]["blocks"] if b.get("type") == "teach"]
    for b in blocks:
        b["duration_minutes"] = minutes_by_group[b["teach_group"]]
    plan["rotation_schedule"]["blocks"] = [{"type": "anchor", "duration_minutes": 5, "time_start": "0:00"}] + blocks
    return plan


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
        print("a normal day, 45 minutes")
        fake = Fake(reply_45({"beginner": 16, "progressor": 14, "proficient": 7}))
        anthropic.AsyncAnthropic = lambda **kw: SimpleNamespace(messages=fake)
        with contextlib.redirect_stdout(io.StringIO()):
            await plan_service.generate_dainik_yojana(db, teacher_id, "N2.3.2", "numeracy", TODAY, session_minutes=45)
        pc_ = fake.prompts[0].split("### PART C")[1].split("### PART D")[0]
        check("anchor 5, no setup block, transitions 2 then 1", "- Anchor: 5 min" in pc_ and "No setup block today" in pc_ and "- Transitions: 2 min, then 1 min" in pc_, pc_)
        check("the blocks by need: Beginners 16, Progressors 14, Proficients 7",
              "TEACH beginner (16 min)" in pc_ and "TEACH progressor (14 min)" in pc_ and "TEACH proficient (7 min)" in pc_, pc_)
        check("each block's own pace, one show-me question each",
              'pace: I Do 4, We Do 5, the show-me questions 2, You Do 5; write 3 show-me questions in the block\'s "cfu" list (the app keeps 1)' in pc_
              and 'pace: I Do 2, the show-me questions 2, You Do 3; write 3 show-me questions in the block\'s "cfu" list (the app keeps 1); a short block' in pc_, pc_)
        check("the worksheets are 3 + 1", "3 core + 1 extra = 4 problems" in fake.prompts[0])
        row = await db.fetchrow("SELECT plan_content FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2", teacher_id, TODAY)
        pc = json.loads(row["plan_content"]) if isinstance(row["plan_content"], str) else row["plan_content"]
        teach = {b["teach_group"]: b for b in pc["rotation_schedule"]["blocks"] if b.get("type") == "teach"}
        w = plan_service.validate_plan_shape(pc, "numeracy")
        check("the 7-minute block without a We Do is not warned about (found in the real 45-minute run)", not any("we_do_hi missing" in x for x in w), w)
        check("the show-me check keeps ONE question per block", all(len(teach[g].get("cfu") or []) <= 1 for g in teach), {g: len(teach[g].get("cfu") or []) for g in teach})
        check("each block carries its pace for the screen: the Proficients' 2 + 2 + 3, no We Do",
              teach["proficient"].get("pace") == [{"key": "i_do", "min": 2}, {"key": "show_me", "min": 2}, {"key": "you_do", "min": 3}]
              and teach["beginner"].get("pace") == [{"key": "i_do", "min": 4}, {"key": "we_do", "min": 5}, {"key": "show_me", "min": 2}, {"key": "you_do", "min": 5}], teach["proficient"].get("pace"))

        print("\na re-teach day: the teacher re-teaches the Proficients")
        fake2 = Fake(reply_45({"beginner": 14, "progressor": 7, "proficient": 16}))
        anthropic.AsyncAnthropic = lambda **kw: SimpleNamespace(messages=fake2)
        with contextlib.redirect_stdout(io.StringIO()):
            await plan_service.generate_dainik_yojana(db, teacher_id, "N2.3.2", "numeracy", TODAY + timedelta(days=1), reteach_groups=["proficient"], session_minutes=45)
        pc2 = fake2.prompts[0].split("### PART C")[1].split("### PART D")[0]
        check("the re-taught Proficients take the longest block, first; then Beginners 14, Progressors 7",
              "Block 1: TEACH proficient (16 min)" in pc2 and "TEACH beginner (14 min)" in pc2 and "TEACH progressor (7 min)" in pc2, pc2)

        print("\n60 minutes: every minute assigned")
        fake3 = Fake(copy.deepcopy(SAMPLE))
        anthropic.AsyncAnthropic = lambda **kw: SimpleNamespace(messages=fake3)
        with contextlib.redirect_stdout(io.StringIO()):
            await plan_service.generate_dainik_yojana(db, teacher_id, "N2.3.2", "numeracy", TODAY + timedelta(days=2), session_minutes=60)
        pc3 = fake3.prompts[0].split("### PART C")[1].split("### PART D")[0]
        check("anchor 10, setup 2, blocks 18 / 13 / 13, transitions 2 each, with the scaled pace and 2 show-me questions",
              "- Setup: 2 min" in pc3 and "(18 min)" in pc3 and pc3.count("(13 min)") == 2 and "- Transitions: 2 min each" in pc3 and "(the app keeps 2)" in pc3, pc3)
    finally:
        anthropic.AsyncAnthropic = real
        await _scratch.remove_class(db, teacher_id, school)
        await db.close()


asyncio.run(main())
if failures:
    print(f"\nFAILED ({len(failures)})")
    sys.exit(1)
print("\nOK: 45 minutes follows the team's table, a re-taught group takes the longest block, and 60 minutes loses no minute")
