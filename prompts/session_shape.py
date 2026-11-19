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

# The 3 + N worksheet (prompt v2, step 5; docs/drafts/PROMPT_DRAFT_3N_WORKSHEET.md): 3 CORE problems every child does (the signal), then N
# EXTRAS for children who finish early, N by the session's length. PROVISIONAL until the education lead confirms (rebuild plan, F3).
CORE_PROBLEMS = 3
EXTRAS_BY_MINUTES = {45: 1, 60: 2, 90: 3}


def worksheet_extras(minutes) -> int:
    """The extras for a session of this length: the nearest length in EXTRAS_BY_MINUTES (ties go to the shorter)."""
    try:
        m = int(minutes)
    except (TypeError, ValueError):
        m = 90
    return EXTRAS_BY_MINUTES[min(sorted(EXTRAS_BY_MINUTES), key=lambda k: abs(k - m))]


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


# A session length with its own reviewed layout, used EXACTLY (prompt v2, step 3). 45 minutes: the team's split of 19 Nov 2026
# ("45-minute-session - Sheet1.csv"): anchor 5, no setup, transitions 2 + 1, and the teach slots 16 / 14 / 7, each with its own pace (no recall
# part: a one-sentence recall goes inside the I Do). The slots go to the groups by level (Beginners the longest), except that a group being
# RE-TAUGHT takes the longest slot, and the others keep their order of need for the rest (decided 19 Nov).
# Each slot: (minutes, pace, a note for the model). show_me: the show-me questions kept per block.
FIXED_LAYOUTS = {
    45: {"anchor": 5, "setup": 0, "transitions": [2, 1], "show_me": 1,
         "slots": [(16, {"i_do": 4, "we_do": 5, "show_me": 2, "you_do": 5}, ""),
                   (14, {"i_do": 3, "we_do": 4, "show_me": 2, "you_do": 5}, ""),
                   (7, {"i_do": 2, "show_me": 2, "you_do": 3}, "a short block: the I Do is a quick model or framing, no We Do, and the You Do is a stretch task or a peer check")]},
}
LEVELS = ("beginner", "progressor", "proficient")       # order of need: the furthest behind first


PACE_LABELS = {"recall": "recall", "i_do": "I Do", "we_do": "We Do", "show_me": "the show-me questions", "you_do": "You Do"}


def pace_text(pace) -> str:
    """'recall 2, I Do 6, We Do 7, the show-me questions 4, You Do 8': the parts with minutes, in teaching order; a part at 0 or absent is
    left out. A block too short for a pace says so."""
    if not pace:
        return "too short for separate parts: one short model, then the group works"
    return ", ".join(f"{PACE_LABELS[k]} {pace[k]}" for k, _ in PACE if pace.get(k))


def session_shape(minutes: int, separate_reteach: bool = False) -> dict:
    """How a session of `minutes` is laid out. separate_reteach: the old kind of re-teach (a separate 5-minute block; when the teacher
    decided at the review, the re-teach is a group's own teach block and takes no extra time). A length in FIXED_LAYOUTS uses its table.
    Returns {total, anchor, setup, reteach, transitions, transition_list, transition_total, teaching, blocks: [first, second, third],
    unassigned, pace: [per block], cfu: [per block], fixed, notes, core, extras, sheet_total}. `blocks` are slot lengths, longest (the
    priority block) first; group_slots() says which group gets which."""
    total = int(minutes)
    fixed = FIXED_LAYOUTS.get(total)
    if fixed:
        slots = fixed["slots"]
        blocks = [m for m, _, _ in slots]
        tl = list(fixed["transitions"])
        return {
            "total": total, "anchor": fixed["anchor"], "setup": fixed["setup"], "reteach": 0,
            "transitions": len(tl), "transition_list": tl, "transition_total": sum(tl),
            "teaching": total - fixed["anchor"] - fixed["setup"] - sum(tl), "blocks": blocks,
            "unassigned": total - fixed["anchor"] - fixed["setup"] - sum(tl) - sum(blocks),
            "pace": [dict(p) for _, p, _ in slots], "cfu": [fixed["show_me"]] * len(slots), "notes": [n for _, _, n in slots], "fixed": True,
            "core": CORE_PROBLEMS, "extras": worksheet_extras(total), "sheet_total": CORE_PROBLEMS + worksheet_extras(total),
        }
    reteach = SEPARATE_RETEACH_MINUTES if separate_reteach else 0
    transitions = 2
    transition_total = transitions * TRANSITION_MINUTES
    teaching = total - ANCHOR_MINUTES - SETUP_MINUTES - reteach - transition_total
    first = max(teaching * 4 // 10, PRIORITY_MIN)            # integer arithmetic, as v1 (orchestrate.py) computed it ...
    other = (teaching - first) // 2
    first += teaching - first - 2 * other                    # ... but the minute v1 left to no block goes to the first (60: 18, 13, 13)
    blocks = [first, other, other]
    return {
        "total": total, "anchor": ANCHOR_MINUTES, "setup": SETUP_MINUTES, "reteach": reteach,
        "transitions": transitions, "transition_list": [TRANSITION_MINUTES] * transitions, "transition_total": transition_total, "teaching": teaching,
        "blocks": blocks, "unassigned": teaching - sum(blocks),
        "pace": [pace_plan(b) for b in blocks], "cfu": [CFU_PER_BLOCK for _ in blocks], "notes": ["" for _ in blocks], "fixed": False,
        "core": CORE_PROBLEMS, "extras": worksheet_extras(total), "sheet_total": CORE_PROBLEMS + worksheet_extras(total),
    }


def group_slots(shape: dict, rotation_order, reteach_groups=None) -> dict:
    """{group: slot index} for the three groups. A computed layout: the rotation's first group takes the first (longest) slot, as v1 did.
    A fixed layout (45 minutes): slots by order of need, except that the groups being re-taught take the longest slots first."""
    order = list(rotation_order)
    if not shape.get("fixed"):
        return {g: (0 if i == 0 else i) for i, g in enumerate(order)}
    rt = [g for g in order if g in (reteach_groups or [])]
    rest = [g for g in LEVELS if g in order and g not in rt]
    return {g: i for i, g in enumerate(rt + rest)}
