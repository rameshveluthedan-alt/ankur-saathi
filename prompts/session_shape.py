"""
The shape of a session: how its minutes are shared out (anchor, setup, a separate re-teach block, transitions, the three teach blocks),
the pace inside each teach block, and how many show-me questions each block keeps. ONE place, so the prompt, the plan checks and the
screen cannot disagree (docs/drafts/PROMPT_V2_REBUILD_PLAN.md, D1).

Plain Python: no database, no model. Step 1 of the prompt v2 rebuild: the numbers are TODAY's (v1) layout, unchanged, so the prompt the
model receives does not change yet. Step 3 changes the anchor and the short-block rules.
"""
import math

# The pace the teachers called realistic (Vaishnavi, 23 Oct): 2 + 6 + 7 + 4 + 8 = 27 minutes. The SAME table as the screen's
# pwa/src/services/reteachInfo.js (PACE), so the minutes in the prompt are the minutes the teacher sees.
PACE = (("recall", 2), ("i_do", 6), ("we_do", 7), ("show_me", 4), ("you_do", 8))
PACE_BASE_TOTAL = sum(m for _, m in PACE)
PACE_MIN_BLOCK = 10              # under 10 minutes the screen shows no pace: the parts would be too small to mean anything

ANCHOR_MINUTES = 10
SETUP_MINUTES = 2
TRANSITION_MINUTES = 2           # each; two transitions between the three teach blocks
SEPARATE_RETEACH_MINUTES = 5     # only the old kind of re-teach (no teacher decision recorded): a separate block before the rotation
PRIORITY_SHARE = 0.4             # the first teach block gets about 40% of the teaching time ...
PRIORITY_MIN = 15                # ... and at least 15 minutes
CFU_PER_BLOCK = 2                # show-me questions the app keeps in each teach block


def pace_plan(duration):
    """The pace scaled to a block's length, in whole minutes that add up to exactly the block's duration (largest remainder, each part at
    least 1): {part: minutes}, or None under PACE_MIN_BLOCK. A port of pacePlan() in pwa/src/services/reteachInfo.js; the tests pin both to
    the same numbers."""
    try:
        d = int(round(float(duration)))
    except (TypeError, ValueError):
        return None
    if d < PACE_MIN_BLOCK:
        return None
    raw = [m * d / PACE_BASE_TOTAL for _, m in PACE]
    mins = [max(1, math.floor(r)) for r in raw]
    left = d - sum(mins)
    # the JavaScript sort is stable: equal remainders keep their order
    order = [i for _, i in sorted(((r - math.floor(r), i) for i, r in enumerate(raw)), key=lambda x: -x[0])]
    k = 0
    while left > 0:
        mins[order[k]] += 1
        left -= 1
        k = (k + 1) % len(order)
    k = len(order) - 1
    while left < 0:
        if mins[order[k]] > 1:
            mins[order[k]] -= 1
            left += 1
        k = (k - 1) % len(order)
    return {name: m for (name, _), m in zip(PACE, mins)}


def session_shape(minutes: int, separate_reteach: bool = False) -> dict:
    """How a session of `minutes` is laid out. separate_reteach: the old kind of re-teach (a separate 5-minute block; when the teacher
    decided at the review, the re-teach is a group's own teach block and takes no extra time).
    Returns {total, anchor, setup, reteach, transitions, transition_total, teaching, blocks: [first, second, third], unassigned,
    pace: [per block, or None], cfu: [per block]}. `blocks` are in rotation order: the first is the priority block."""
    total = int(minutes)
    reteach = SEPARATE_RETEACH_MINUTES if separate_reteach else 0
    transitions = 2
    transition_total = transitions * TRANSITION_MINUTES
    teaching = total - ANCHOR_MINUTES - SETUP_MINUTES - reteach - transition_total
    first = max(teaching * 4 // 10, PRIORITY_MIN)            # integer arithmetic, exactly as v1 (orchestrate.py) computed it
    other = (teaching - first) // 2
    blocks = [first, other, other]
    return {
        "total": total, "anchor": ANCHOR_MINUTES, "setup": SETUP_MINUTES, "reteach": reteach,
        "transitions": transitions, "transition_total": transition_total, "teaching": teaching,
        "blocks": blocks, "unassigned": teaching - sum(blocks),
        "pace": [pace_plan(b) for b in blocks], "cfu": [CFU_PER_BLOCK for _ in blocks],
    }
