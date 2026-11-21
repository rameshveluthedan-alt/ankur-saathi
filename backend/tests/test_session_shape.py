"""
The shape of a session (prompts/session_shape.py): one function for how the minutes are shared out, the pace inside each teach block and the
show-me count. Step 1 of the prompt v2 rebuild: the numbers must be EXACTLY v1's (the prompt does not change yet), and the pace must be the
screen's (pwa/src/services/reteachInfo.js pacePlan). No database needed.

    python backend/tests/test_session_shape.py
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path[:0] = [os.path.join(ROOT, "prompts")]
from session_shape import pace_plan, session_shape, group_slots, pace_text, PACE, FIXED_LAYOUTS

failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


def v1_layout(minutes, reteach):
    """v1's arithmetic, copied from orchestrate.py before the shape function replaced it."""
    teaching = minutes - 10 - 2 - reteach - 4
    first = max(teaching * 4 // 10, 15)
    other = (teaching - first) // 2
    return teaching, first, other


print("a computed layout is v1's, except that the minute v1 left to no block goes to the first (step 3)")
same = True
for minutes in [m for m in range(40, 121) if m not in FIXED_LAYOUTS]:
    for sep in (False, True):
        s = session_shape(minutes, separate_reteach=sep)
        teaching, first, other = v1_layout(minutes, 5 if sep else 0)
        first += teaching - first - 2 * other
        if (s["teaching"], s["blocks"], s["unassigned"]) != (teaching, [first, other, other], 0) or (s["anchor"], s["setup"], s["transition_total"]) != (10, 2, 4):
            same = False
            print("   differs at", minutes, sep, s)
check("40 to 120 minutes (not 45), with and without a separate re-teach block: every minute assigned", same)
s45, s60, s90 = session_shape(45), session_shape(60), session_shape(90)
check("60 minutes: 18, 13, 13 (v1 gave 17 and lost a minute)", s60["blocks"] == [18, 13, 13] and s60["unassigned"] == 0, s60)
check("90 minutes: 30, 22, 22 (v1 gave 29 and lost a minute)", s90["blocks"] == [30, 22, 22] and s90["unassigned"] == 0, s90["blocks"])
check("a separate re-teach block takes 5 minutes", session_shape(90, separate_reteach=True)["reteach"] == 5 and s90["reteach"] == 0)
check("two show-me questions kept in every block at 60 and 90", all(s["cfu"] == [2, 2, 2] for s in (s60, s90)))
check("every session adds up: anchor + setup + re-teach + blocks + transitions",
      all(s["anchor"] + s["setup"] + s["reteach"] + sum(s["blocks"]) + s["transition_total"] == s["total"] for s in (session_shape(m, sep) for m in (45, 60, 90) for sep in (False, True))))

print("45 minutes: the team's table (19 Nov), used exactly")
check("anchor 5, no setup, transitions 2 + 1, slots 16 / 14 / 7: 45 in all",
      (s45["anchor"], s45["setup"], s45["transition_list"], s45["blocks"], s45["unassigned"]) == (5, 0, [2, 1], [16, 14, 7], 0), s45)
check("the slots' pace: 4/5/2/5, 3/4/2/5, and 2 + 2 + 3 with no We Do; no recall part",
      s45["pace"] == [{"i_do": 4, "we_do": 5, "show_me": 2, "you_do": 5}, {"i_do": 3, "we_do": 4, "show_me": 2, "you_do": 5}, {"i_do": 2, "show_me": 2, "you_do": 3}])
check("each slot's pace adds up to the slot", all(sum(p.values()) == m for p, m in zip(s45["pace"], s45["blocks"])))
check("one show-me question per block; the 7-minute slot says what it is", s45["cfu"] == [1, 1, 1] and "stretch task or a peer check" in s45["notes"][2])
check("a separate re-teach block is not added at 45 (no time for it)", session_shape(45, separate_reteach=True)["reteach"] == 0)
ROT = ["progressor", "beginner", "proficient"]
check("slots go by need: Beginners 16, Progressors 14, Proficients 7, whatever the rotation", group_slots(s45, ROT) == {"beginner": 0, "progressor": 1, "proficient": 2})
check("a re-taught group takes the longest: re-teach the Proficients -> 16, then Beginners 14, Progressors 7",
      group_slots(s45, ["proficient", "beginner", "progressor"], ["proficient"]) == {"proficient": 0, "beginner": 1, "progressor": 2})
check("two re-taught groups take the two longest, in rotation order",
      group_slots(s45, ["progressor", "proficient", "beginner"], ["progressor", "proficient"]) == {"progressor": 0, "proficient": 1, "beginner": 2})
check("a computed layout (90): the rotation's first group gets the long block, as v1", group_slots(s90, ROT) == {"progressor": 0, "beginner": 1, "proficient": 2})
check("the pace in words for the prompt", pace_text(s45["pace"][2]) == "I Do 2, the show-me questions 2, You Do 3" and pace_text(None).startswith("too short"))

print("the pace is the screen's")
# pacePlan() in pwa/src/services/reteachInfo.js, run with node on 19 Nov 2026 for these durations
SCREEN = {7: None, 9: None, 10: [2, 2, 2, 1, 3], 12: [2, 2, 3, 2, 3], 15: [1, 3, 4, 2, 5], 17: [1, 4, 4, 3, 5], 18: [1, 4, 5, 3, 5],
          22: [2, 5, 6, 3, 6], 23: [2, 5, 6, 3, 7], 27: [2, 6, 7, 4, 8], 29: [2, 6, 8, 4, 9], 31: [2, 7, 8, 5, 9], 36: [3, 8, 9, 5, 11]}
for d, want in SCREEN.items():
    got = pace_plan(d)
    got = [got[k] for k, _ in PACE] if got else None
    check(f"{d} minutes: {want}", got == want, got)
check("every pace adds up to its block", all(sum(pace_plan(d).values()) == d for d in range(10, 61)))
check("every part is at least one minute", all(min(pace_plan(d).values()) >= 1 for d in range(10, 61)))
check("nonsense gives no pace rather than an error", pace_plan(None) is None and pace_plan("x") is None)
check("a computed shape carries each block's scaled pace", s90["pace"][0] == pace_plan(30) and s90["pace"][1] == pace_plan(22))

print("the Plan screen's line under 'Today's time' says what the server will lay out")
import re as _re
js = open(os.path.join(ROOT, "pwa", "src", "services", "sessionShapes.js"), encoding="utf-8").read()
screen = {int(m.group(1)): (int(m.group(2)), [int(x) for x in m.group(3).split(",")], int(m.group(4)))
          for m in _re.finditer(r"(\d+): \{ anchor: (\d+), blocks: \[([\d, ]+)\], extras: (\d+) \}", js)}
check("the screen's table has the three lengths", sorted(screen) == [45, 60, 90], screen)
for m, (anchor, blocks, extras) in sorted(screen.items()):
    s = session_shape(m)
    check(f"{m} minutes: the screen says anchor {anchor}, blocks {blocks}, 3 + {extras}: the same as the server",
          (anchor, sorted(blocks, reverse=True), extras) == (s["anchor"], sorted(s["blocks"], reverse=True), s["extras"]), (s["anchor"], s["blocks"], s["extras"]))

print("the prompt uses it")
src = open(os.path.join(ROOT, "prompts", "orchestrate.py"), encoding="utf-8").read()
check("build_user_prompt takes the minutes from session_shape, not its own arithmetic", "session_shape(ctx.available_minutes" in src and "teaching_time * 4 // 10" not in src)

if failures:
    print(f"\nFAILED ({len(failures)})")
    sys.exit(1)
print("\nOK: one session shape, v1's numbers, the screen's pace")
