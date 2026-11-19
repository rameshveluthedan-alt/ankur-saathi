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
from session_shape import pace_plan, session_shape, PACE

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


print("the layout is v1's, for every length and both kinds of re-teach")
same = True
for minutes in range(40, 121):
    for sep in (False, True):
        s = session_shape(minutes, separate_reteach=sep)
        teaching, first, other = v1_layout(minutes, 5 if sep else 0)
        if (s["teaching"], s["blocks"]) != (teaching, [first, other, other]) or (s["anchor"], s["setup"], s["transition_total"]) != (10, 2, 4):
            same = False
            print("   differs at", minutes, sep, s)
check("40 to 120 minutes, with and without a separate re-teach block", same)
s45, s60, s90 = session_shape(45), session_shape(60), session_shape(90)
check("45 minutes: 15, 7, 7 (the known short blocks)", s45["blocks"] == [15, 7, 7], s45["blocks"])
check("60 minutes: 17, 13, 13 and one minute nobody gets (v1's rounding, fixed in step 3)", s60["blocks"] == [17, 13, 13] and s60["unassigned"] == 1, s60)
check("90 minutes: 29, 22, 22", s90["blocks"] == [29, 22, 22], s90["blocks"])
check("a separate re-teach block takes 5 minutes", session_shape(90, separate_reteach=True)["reteach"] == 5 and s90["reteach"] == 0)
check("two show-me questions kept in every block (v1)", all(s["cfu"] == [2, 2, 2] for s in (s45, s60, s90)))

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
check("the shape carries each block's pace (none for a 7-minute block)", s45["pace"][1] is None and s90["pace"][0] == pace_plan(29))

print("the prompt uses it")
src = open(os.path.join(ROOT, "prompts", "orchestrate.py"), encoding="utf-8").read()
check("build_user_prompt takes the minutes from session_shape, not its own arithmetic", "session_shape(ctx.available_minutes" in src and "teaching_time * 4 // 10" not in src)

if failures:
    print(f"\nFAILED ({len(failures)})")
    sys.exit(1)
print("\nOK: one session shape, v1's numbers, the screen's pace")
