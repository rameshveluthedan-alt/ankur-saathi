"""
When a talking point builds an example with more sticks than the kit holds, the repair swaps it. The swap must not be refused because of examples that were
ALREADY in the text. (In the cloud a Beginner We Do kept "41 + 26", 67 sticks, in a lesson whose pair kit holds 49: the model's first worksheet had copied the
unchanged "32 + 15" from the We Do, the worksheet is repaired only afterwards, and the fix was refused for 'using an example already used elsewhere'.)

    python backend/tests/test_stick_repair.py
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):          # a pipe on Windows uses a legacy code page that cannot print Hindi
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import asyncio
import copy
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."), os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "prompts")]
from app.services import plan_service as ps

failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


WE_DO = ("हर जोड़ी अपने किट और दहाई-इकाई के बॉक्स पर 32 + 15 बनाए। पूछें: इकाई में कितनी खुली छड़ियाँ हैं? दहाई में कितने बंडल? पहले इकाई जोड़ें, फिर दहाई। "
         "उत्तर कॉपी में लिखें। फिर 41 + 26 इसी तरह करें, कुल 49 से अधिक छड़ियाँ न लगें।")


def plan_with(worksheet):
    return {"rotation_schedule": {"blocks": [{"type": "teach", "teach_group": "beginner", "talking_points": {
        "i_do_hi": "बोर्ड पर 23 + 14 लिखें। शिक्षक किट से 2 बंडल और 3 खुली, फिर 1 बंडल और 4 खुली दिखाएँ।", "we_do_hi": WE_DO, "you_do_hi": "पहले दो सवाल छड़ियों से हल करें।"}}]},
        "worksheets": {"beginner": {"problems": [{"problem_hi": p} for p in worksheet]}}}


class Down:
    class messages:
        @staticmethod
        async def create(**kw):
            raise RuntimeError("the model is unavailable")


def repair(worksheet):
    new, log = asyncio.run(ps.repair_stick_overflows(Down(), "m", plan_with(worksheet)))
    we_do = next(b for b in new["rotation_schedule"]["blocks"])["talking_points"]["we_do_hi"]
    return we_do, log, ps.find_stick_overflows(new)


print("the repair, with the model unavailable (the swap is made in code)")
for label, ws in {"a worksheet with no copies of the lesson": ("11 + 26", "22 + 25", "73 + 21", "52 + 17", "34 + 45"),
                  "the model's ORIGINAL worksheet that copied the unchanged 32 + 15 (repaired only later)": ("32 + 15", "22 + 25", "73 + 21", "52 + 17", "34 + 45"),
                  "a worksheet that copied BOTH the unchanged and the oversized example": ("32 + 15", "41 + 26", "73 + 21", "52 + 17", "34 + 45")}.items():
    we_do, log, left = repair(ws)
    check(f"{label}: the oversized example is replaced and nothing overflows", "41 + 26" not in we_do and not left and "replaced in code" in " ".join(log), (log, left))
    check("   ...the unchanged first example is kept, and the sentence about the kit is untouched", "32 + 15" in we_do and "कुल 49 से अधिक छड़ियाँ न लगें" in we_do)
we_do, _, _ = repair(("11 + 26", "22 + 25", "73 + 21", "52 + 17", "34 + 45"))
import re
new_pair = [tuple(map(int, m)) for m in re.findall(r"(\d+) \+ (\d+)", we_do)][1]
check("the new example fits the pair kit (49 sticks) and needs no carry (a Beginner skill)", sum(new_pair) <= 49 and (new_pair[0] % 10 + new_pair[1] % 10) < 10, new_pair)

print("what a rewrite is judged on (the model's own rewrite goes through the same check)")
old = WE_DO
avoid = {(15, 32), (22, 25)}                                     # pairs used elsewhere in the lesson (unordered, sorted)
ok, why = ps._fix_is_acceptable("beginner", "we_do_hi", old, old.replace("41 + 26", "21 + 13"), avoid)
check("a rewrite that keeps the old 32 + 15 (also in the worksheet) and adds a FRESH example is accepted", ok, why)
ok, why = ps._fix_is_acceptable("beginner", "we_do_hi", old, old.replace("41 + 26", "22 + 25"), avoid)
check("a rewrite that INTRODUCES an example already used elsewhere is still refused", not ok and "already used elsewhere" in why, (ok, why))
ok, why = ps._fix_is_acceptable("beginner", "we_do_hi", old, old.replace("41 + 26", "41 + 27"), set())
check("a rewrite that is still too big for the kit is refused", not ok and "more than 49" in why, why)
ok, why = ps._fix_is_acceptable("beginner", "we_do_hi", old, old.replace("41 + 26", "26 + 17"), set())
check("a rewrite that needs a carry (a Beginner example must not) is refused", not ok and "carry" in why, why)
ok, why = ps._fix_is_acceptable("beginner", "we_do_hi", old, old.replace("41 + 26", "21 + 13 = 35"), set())
check("a rewrite with a wrong stated sum is refused", not ok and "stated sum is wrong" in why, why)

if failures:
    print(f"\nFAILED ({len(failures)})")
    sys.exit(1)
print("\nOK: an oversized stick example is always replaced, and the replacement is checked only on what it introduces")
