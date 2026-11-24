"""
The session's minutes are the code's, not the model's (handover item 6). A plan from any model (Haiku wrote 46-47 minutes at 45, and added
transitions) leaves the plan service with every block's minutes from the layout, stray transitions removed, and the clock times and total
written again. The content of the blocks is never touched. No database, no model.

    python backend/tests/test_block_minutes.py
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")
import copy
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "prompts")]
os.environ.setdefault("ANTHROPIC_API_KEY", "dummy")
from app.services import plan_service
from session_shape import session_shape, group_slots

failures = []


def check(name, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f"   {detail}"))
    if not ok:
        failures.append(name)


ORDER = ["beginner", "progressor", "proficient"]       # at 45 minutes the slots go by level: Beginners 16, Progressors 14, Proficients 7


def layout(minutes, separate_reteach=False):
    shape = session_shape(minutes, separate_reteach=separate_reteach)
    slot_of = group_slots(shape, ORDER, None)
    lay = {g: {"minutes": shape["blocks"][i], "pace": shape["pace"][i], "cfu": shape["cfu"][i], "note": shape["notes"][i]} for g, i in slot_of.items()}
    return shape, lay


def blk(kind, mins, g=None, text=None):
    b = {"type": kind, "time_start": "9:99", "duration_minutes": mins}
    if g:
        b["teach_group"] = g
        b["talking_points"] = {"i_do_hi": text or f"{g} I Do", "we_do_hi": "we", "you_do_hi": "you"}
    if kind in ("setup", "transition"):
        b["script_hi"] = text or f"{kind} script"
    return b


def plan_of(blocks):
    return {"rotation_schedule": {"total_minutes": 45, "blocks": blocks}}


def mins(plan):
    return [(b["type"], b.get("teach_group"), b["duration_minutes"]) for b in plan["rotation_schedule"]["blocks"]]


print("45 minutes (the team's table: anchor 5, no setup, transitions 2 + 1, teach 16 / 14 / 7)")
shape, lay = layout(45)
# Haiku-like: a setup block, anchor 10, three transitions, the blocks add up to 47
plan = plan_of([blk("anchor", 10), blk("setup", 2), blk("teach", 15, "progressor"), blk("transition", 2), blk("teach", 14, "beginner"),
                blk("transition", 2), blk("teach", 7, "proficient"), blk("transition", 2)])
log = plan_service.fix_block_minutes(plan, shape, lay)
got = mins(plan)
check("the anchor, the teach blocks and the two transitions get the table's minutes",
      got == [("anchor", None, 5), ("teach", "progressor", 14), ("transition", None, 2), ("teach", "beginner", 16), ("transition", None, 1), ("teach", "proficient", 7)], got)
check("the setup the layout does not have, and the transition after the last block, are removed", not any(t == "setup" for t, _, _ in got) and got[-1][0] == "teach")
check("the blocks now add up to 45 and the total says 45", sum(m for _, _, m in got) == 45 and plan["rotation_schedule"]["total_minutes"] == 45)
check("the clock times are written again from the minutes", [b["time_start"] for b in plan["rotation_schedule"]["blocks"]] == ["0:00", "0:05", "0:19", "0:21", "0:37", "0:38"],
      [b["time_start"] for b in plan["rotation_schedule"]["blocks"]])
check("what was changed is logged", any("setup" in l for l in log) and any("stray transition" in l for l in log) and any("anchor" in l for l in log), log)
tp = [b["talking_points"]["i_do_hi"] for b in plan["rotation_schedule"]["blocks"] if b["type"] == "teach"]
check("the teaching text is untouched", tp == ["progressor I Do", "beginner I Do", "proficient I Do"], tp)

print("a plan that is already right")
plan = plan_of([blk("anchor", 5), blk("teach", 14, "progressor"), blk("transition", 2), blk("teach", 16, "beginner"), blk("transition", 1), blk("teach", 7, "proficient")])
before = copy.deepcopy(plan)
log = plan_service.fix_block_minutes(plan, shape, lay)
check("nothing is logged but the clock times are set", log == [] and plan["rotation_schedule"]["blocks"][1]["time_start"] == "0:05", log)
plan2 = copy.deepcopy(plan)
check("running it twice changes nothing more", plan_service.fix_block_minutes(plan2, shape, lay) == [] and plan2 == plan)

print("60 and 90 minutes (computed layouts: anchor 10, setup 2, transitions 2 + 2)")
for total in (60, 90):
    shape, lay = layout(total)
    plan = plan_of([blk("anchor", 8), blk("setup", 3), blk("teach", 20, "progressor"), blk("transition", 3), blk("teach", 20, "beginner"), blk("transition", 3),
                    blk("teach", 20, "proficient")])
    plan_service.fix_block_minutes(plan, shape, lay)
    got = mins(plan)
    teach = {g: m for t, g, m in got if t == "teach"}
    check(f"{total}: the blocks add up to the session", sum(m for _, _, m in got) == total and plan["rotation_schedule"]["total_minutes"] == total, got)
    check(f"{total}: each group has its slot's length and the setup has 2", teach == {g: lay[g]["minutes"] for g in lay} and ("setup", None, 2) in got, got)

print("a re-teach group at 45 minutes takes the longest slot")
shape = session_shape(45)
slot_of = group_slots(shape, ["beginner", "progressor", "proficient"], ["proficient"])
lay = {g: {"minutes": shape["blocks"][i]} for g, i in slot_of.items()}
plan = plan_of([blk("anchor", 5), blk("teach", 10, "beginner"), blk("transition", 2), blk("teach", 10, "progressor"), blk("transition", 1), blk("teach", 10, "proficient")])
plan_service.fix_block_minutes(plan, shape, lay)
got = {g: m for t, g, m in mins(plan) if t == "teach"}
check("the group being re-taught has 16", got["proficient"] == 16 and sorted(got.values()) == [7, 14, 16], got)

print("two transitions in the same gap, and a second anchor")
shape, lay = layout(60)
plan = plan_of([blk("anchor", 10), blk("anchor", 3), blk("setup", 2), blk("teach", 18, "progressor"), blk("transition", 2), blk("transition", 2), blk("teach", 13, "beginner"),
                blk("transition", 2), blk("teach", 13, "proficient")])
plan_service.fix_block_minutes(plan, shape, lay)
got = mins(plan)
check("only one anchor and one transition in each gap",
      [t for t, _, _ in got] == ["anchor", "setup", "teach", "transition", "teach", "transition", "teach"], got)

print("a missing block is not invented, but the sum says so")
shape, lay = layout(60)
plan = plan_of([blk("anchor", 10), blk("setup", 2), blk("teach", 18, "progressor"), blk("teach", 13, "beginner"), blk("transition", 2), blk("teach", 13, "proficient")])
log = plan_service.fix_block_minutes(plan, shape, lay)
check("no block added; a line says the blocks do not add up", len(plan["rotation_schedule"]["blocks"]) == 6 and any("add up" in l for l in log), log)

print("a separate re-teach block (the old kind)")
shape, lay = layout(90, separate_reteach=True)
plan = plan_of([blk("anchor", 10), blk("setup", 2), blk("reteach", 7), blk("teach", 30, "progressor"), blk("transition", 2), blk("teach", 20, "beginner"), blk("transition", 2),
                blk("teach", 20, "proficient")])
plan_service.fix_block_minutes(plan, shape, lay)
got = mins(plan)
check("the re-teach block has the layout's 5 minutes and everything adds up to 90", ("reteach", None, 5) in got and sum(m for _, _, m in got) == 90, got)

print("odd plans do nothing and do not crash")
shape, lay = layout(60)
check("no plan, no rotation, no blocks, a block that is not an object",
      plan_service.fix_block_minutes({}, shape, lay) == [] and plan_service.fix_block_minutes(None, shape, lay) == []
      and plan_service.fix_block_minutes({"rotation_schedule": {"blocks": []}}, shape, lay) == [] and plan_service.fix_block_minutes(plan_of(["x", blk("anchor", 3)]), shape, lay) is not None)
plan = plan_of([blk("anchor", "ten"), blk("teach", None, "progressor")])
check("minutes written as text or missing are read as 0 and replaced", plan_service.fix_block_minutes(plan, shape, lay) is not None and plan["rotation_schedule"]["blocks"][0]["duration_minutes"] == 10)

print()
if failures:
    print(f"{len(failures)} FAILED: {failures}")
    sys.exit(1)
print("ALL PASSED")
