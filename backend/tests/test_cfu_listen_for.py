"""
The listen-for answers of the check-for-understanding questions are checked by CODE: what a child with a recorded mistake would write must be what that mistake really gives.
Found on the first real re-teach block: for 54 + 29 the model listed 613 for "writes the whole ones sum" (a child writes 713; the 613 was copied from the I Do's 46 + 27).

    cd backend && AUTH_MODE=off python tests/test_cfu_listen_for.py --env-file .env
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import asyncio
import copy
import os
import sys

os.environ.setdefault("AUTH_MODE", "off")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "..", "prompts"), os.path.join(HERE, "..")]
import _scratch
from app.services import cfu
from app.services.cfu import IMPOSSIBLE

failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


# ---- a child doing the sum column by column: written SEPARATELY from the code's formulas, so that the two can disagree ----
def digits(n):
    return [int(c) for c in str(n)][::-1]


def child_drops_the_carry(a, b):                                   # writes the ones digit, forgets the carry
    da, db = digits(a), digits(b)
    out, needs = [], False
    for i in range(max(len(da), len(db))):
        s = (da[i] if i < len(da) else 0) + (db[i] if i < len(db) else 0)
        needs |= s >= 10
        out.append(s % 10 if i == 0 else s)                        # the tens column: its sum is written as it is (11 is written 11)
    return (int("".join(str(x) for x in out[::-1])) if needs else None)


def child_writes_whole_ones(a, b):
    da, db = digits(a), digits(b)
    o = da[0] + db[0]
    return int(str(da[1] + db[1]) + str(o)) if o >= 10 else None


def child_carries_the_ones_digit(a, b):
    da, db = digits(a), digits(b)
    o = da[0] + db[0]
    if o < 10:
        return None
    carry = o % 10                                                 # the ONES digit of the sum, not the tens digit
    return int(str(da[1] + db[1] + carry) + str(o % 10))


def child_forgets_the_second_carry(a, b):                          # 3 digits: ones to tens carried, tens to hundreds forgotten
    da, db = digits(a), digits(b)
    o = da[0] + db[0]
    t = da[1] + db[1] + o // 10
    if t < 10:
        return None
    return int(str(da[2] + db[2]) + str(t % 10) + str(o % 10))


def child_subtracts_smaller_from_larger(a, b):
    da, db = digits(a), digits(b)
    if da[0] >= db[0]:
        return None
    return int(str(da[1] - db[1]) + str(abs(da[0] - db[0])))


def child_forgets_to_reduce_the_tens(a, b):
    da, db = digits(a), digits(b)
    if da[0] >= db[0]:
        return None
    return int(str(da[1] - db[1]) + str(da[0] + 10 - db[0]))


async def main():
    db = await _scratch.connect()
    print("the patterns reproduce the knowledge base's OWN recorded wrong answers")
    recorded = {"N2.3.2-M1": (34, "+", 28, 52), "N2.3.2-M2": (34, "+", 28, 512), "N2.3.2-M3": (34, "+", 28, 72), "N3.3.1-M1": (167, "+", 245, 312),
                "N2.3.4-M1": (42, "-", 17, 35), "N2.3.4-M2": (42, "-", 17, 35), "N3.3.4-M1": (23, "*", 4, 812), "N3.3.5-M1": (24, "/", 6, 18)}
    for mid, (a, op, b, ans) in recorded.items():
        text = await db.fetchval("SELECT example_incorrect FROM misconceptions WHERE id = $1", mid)
        check(f"{mid}: {a} {op} {b} gives {ans}, and the knowledge base's own example says so ({(text or '')[:44]!r})", cfu.wrong_answer_for(mid, a, op, b) == ans and str(ans) in (text or ""), (cfu.wrong_answer_for(mid, a, op, b), text))
    check("every registered pattern is one of those the knowledge base records (none invented)", set(cfu.LISTEN_PATTERNS) == set(recorded))
    await db.close()

    print("\nthe code against a child doing the sum column by column (every pair of two-digit numbers)")
    pairs = [(a, b) for a in range(10, 100) for b in range(10, 100)]
    for mid, child in (("N2.3.2-M1", child_drops_the_carry), ("N2.3.2-M2", child_writes_whole_ones), ("N2.3.2-M3", child_carries_the_ones_digit)):
        bad = [(a, b, cfu.wrong_answer_for(mid, a, "+", b), child(a, b)) for a, b in pairs
               if (child(a, b) is None and cfu.wrong_answer_for(mid, a, "+", b) != IMPOSSIBLE) or (child(a, b) is not None and cfu.wrong_answer_for(mid, a, "+", b) not in (child(a, b), IMPOSSIBLE))]
        check(f"{mid}: all {len(pairs)} sums agree (no carry needed = the mistake cannot happen)", not bad, bad[:3])
    both = [(a, b) for a, b in pairs if (a % 10 + b % 10) >= 10 and a + b < 100 + 0]
    check("a sum that needs a carry never has its mistake equal the right answer", all(cfu.wrong_answer_for("N2.3.2-M1", a, "+", b) not in (a + b,) for a, b in pairs if (a % 10 + b % 10) >= 10))
    three = [(a, b) for a in range(100, 1000, 7) for b in range(100, 1000, 11)]
    bad = [(a, b, cfu.wrong_answer_for("N3.3.1-M1", a, "+", b), child_forgets_the_second_carry(a, b)) for a, b in three
           if (child_forgets_the_second_carry(a, b) is None) != (cfu.wrong_answer_for("N3.3.1-M1", a, "+", b) == IMPOSSIBLE) or (child_forgets_the_second_carry(a, b) not in (None, cfu.wrong_answer_for("N3.3.1-M1", a, "+", b)))]
    check(f"N3.3.1-M1: {len(three)} three-digit sums agree (the second carry must exist for the mistake to happen)", not bad, bad[:3])
    subs = [(a, b) for a in range(10, 100) for b in range(10, a + 1)]
    for mid, child in (("N2.3.4-M1", child_subtracts_smaller_from_larger), ("N2.3.4-M2", child_forgets_to_reduce_the_tens)):
        bad = [(a, b, cfu.wrong_answer_for(mid, a, "-", b), child(a, b)) for a, b in subs
               if (child(a, b) is None) != (cfu.wrong_answer_for(mid, a, "-", b) == IMPOSSIBLE) or (child(a, b) is not None and cfu.wrong_answer_for(mid, a, "-", b) != child(a, b))]
        check(f"{mid}: all {len(subs)} subtractions agree (no borrow needed = the mistake cannot happen)", not bad, bad[:3])
    check("the two subtraction mistakes are NOT the same answer in general (61 - 29: 48 against 42), so each is computed by itself", cfu.wrong_answer_for("N2.3.4-M1", 61, "-", 29) == 48 and cfu.wrong_answer_for("N2.3.4-M2", 61, "-", 29) == 42)

    print("\nwhere the patterns do not apply, the code says nothing")
    check("another operation, other sizes, or a mistake with no pattern: None (left as the model wrote it)", cfu.wrong_answer_for("N2.3.2-M1", 54, "-", 29) is None and cfu.wrong_answer_for("N2.3.2-M1", 5, "+", 7) is None
          and cfu.wrong_answer_for("N2.3.2-M4", 54, "+", 29) is None and cfu.wrong_answer_for("N9.9.9-M1", 54, "+", 29) is None and cfu.wrong_answer_for(None, 54, "+", 29) is None)
    check("the times and divide signs written as Hindi books write them are read as the same operations", cfu.wrong_answer_for("N3.3.4-M1", 23, "×", 4) == 812 and cfu.wrong_answer_for("N3.3.5-M1", 24, "÷", 6) == 18 and cfu.wrong_answer_for("N2.3.4-M1", 42, "−", 17) == 35)

    print("\nthe question from the real block")
    q1 = {"kind": "compute", "question_hi": "54 + 29 को हल करें। उत्तर लिखें।", "expected_hi": "83", "listen_for": [{"misconception_id": "N2.3.2-M1", "wrong_answer_hi": "73"}, {"misconception_id": "N2.3.2-M2", "wrong_answer_hi": "613"}]}
    new, notes = cfu.verified_listen(q1)
    check("613 for 'writes the whole ones sum' is corrected to 713, and the right 73 for the dropped carry is left alone", [x["wrong_answer_hi"] for x in new["listen_for"]] == ["73", "713"], new["listen_for"])
    check("the correction is reported (a log line for the plan)", len(notes) == 1 and "613" in notes[0] and "713" in notes[0], notes)
    check("the original item is not changed (a copy is returned)", q1["listen_for"][1]["wrong_answer_hi"] == "613")
    same, none_ = cfu.verified_listen({**q1, "listen_for": [{"misconception_id": "N2.3.2-M1", "wrong_answer_hi": "73"}, {"misconception_id": "N2.3.2-M2", "wrong_answer_hi": "713"}]})
    check("an item that is already right comes back untouched, with no notes", none_ == [] and same["listen_for"][1]["wrong_answer_hi"] == "713")

    print("\nwhat is corrected, removed, and left alone")
    one = lambda mid, w, q="54 + 29 कितना होगा?", kind="compute": {"kind": kind, "question_hi": q, "expected_hi": "83", "listen_for": [{"misconception_id": mid, "wrong_answer_hi": w}]}
    out = lambda item: [x["wrong_answer_hi"] for x in cfu.verified_listen(item)[0]["listen_for"]]
    check("a wrong number with words after it is corrected in place ('613 लिखेगा' -> '713 लिखेगा')", out(one("N2.3.2-M2", "613 लिखेगा")) == ["713 लिखेगा"])
    check("several numbers and none right: the entry becomes the right number alone ('613 (पूरा 13 लिखा)' -> '713')", out(one("N2.3.2-M2", "613 (पूरा 13 लिखा)")) == ["713"] and out(one("N2.3.2-M2", "61 या 63")) == ["713"])
    check("several numbers with the right one among them: left alone ('613 या 713')", out(one("N2.3.2-M2", "613 या 713")) == ["613 या 713"])
    check("a behaviour in words ('कोई उत्तर नहीं लिखा') is left alone", out(one("N2.3.2-M2", "कोई उत्तर नहीं लिखा")) == ["कोई उत्तर नहीं लिखा"])
    check("Devanagari digits are read ('६१३' is corrected to 713)", out(one("N2.3.2-M2", "६१३")) == ["713"])
    check("a mistake that CANNOT happen on these numbers is removed: dropping a carry on 23 + 14 (there is none)", out(one("N2.3.2-M1", "27", "23 + 14 कितना होगा?")) == [])
    check("a mistake with no pattern (N2.3.2-M4, left to right) is left exactly as written", out(one("N2.3.2-M4", "512")) == ["512"])
    check("only a 'compute' question is checked: a spot-the-error answer ('सही है') and a 'choose' question are untouched", out(one("N2.3.2-M1", "सही है", "36 + 45 = 71 सही या गलत?", "spot_error")) == ["सही है"] and out(one("N2.3.2-M2", "613", "54 + 29: 613 या 713?", "choose")) == ["613"])
    check("a question with two sums, or a chain, is not checked (which one the child answers is not clear)", out(one("N2.3.2-M2", "613", "54 + 29 और 36 + 45 का योग?")) == ["613"] and out(one("N2.3.2-M2", "613", "54 + 29 + 10 कितना?")) == ["613"])
    check("a question with no sum at all is untouched", out(one("N2.3.2-M2", "613", "हासिल क्या होता है?")) == ["613"])
    check("not a list, not an object: returned as it is, never an error", cfu.verified_listen("x") == ("x", []) and cfu.verified_listen({"kind": "compute", "listen_for": None}) == ({"kind": "compute", "listen_for": None}, []))

    print("\nthrough the whole cleaning pipeline (the real block's two questions, and two that cannot be right)")
    kb = {"progressor": {"competency_id": "N2.3.2", "name_en": "Adds two 2-digit numbers with regrouping (carry-over)", "name_hi": "हासिल के साथ दो अंकों का जोड़", "criteria_type": "computation",
                         "mistakes": [{"id": f"N2.3.2-M{i}", "name_hi": f"गलती {i}", "diagnostic_indicator": "d"} for i in (1, 2, 3, 4)]}}
    q2 = {"kind": "spot_error", "question_hi": "बोर्ड पर देखें: 36 + 45 = 71। क्या यह सही है या गलत?", "expected_hi": "गलत, 81", "listen_for": [{"misconception_id": "N2.3.2-M1", "wrong_answer_hi": "सही है"}]}
    q3 = {"kind": "compute", "question_hi": "23 + 14 कितना होगा?", "expected_hi": "37", "listen_for": [{"misconception_id": "N2.3.2-M1", "wrong_answer_hi": "27"}]}
    q4 = {**copy.deepcopy(q3), "question_hi": "32 + 15 कितना होगा?", "expected_hi": "47", "shows_hi": "बच्चा इकाई और दहाई अलग-अलग जोड़ता है", "listen_for": [{"misconception_id": "N2.3.2-M1", "wrong_answer_hi": "37"}]}
    pl = {"rotation_schedule": {"blocks": [{"type": "teach", "teach_group": "progressor", "talking_points": {}, "cfu": [copy.deepcopy(q1), copy.deepcopy(q2)]}]}}
    lines, stats = cfu.clean_plan_cfu(pl, kb)
    kept = pl["rotation_schedule"]["blocks"][0]["cfu"]
    check("the real block's two questions both survive, both grounded in a recorded mistake", [k["question_hi"][:8] for k in kept] == ["54 + 29 ", "बोर्ड पर"] and [k["grounded"] for k in kept] == [True, True], [(k["question_hi"][:10], k["grounded"]) for k in kept])
    check("the card a teacher sees now says 713 (and still 73)", [x["wrong_answer_hi"] for x in kept[0]["listen_for"]] == ["73", "713"], kept[0]["listen_for"])
    check("the spot-the-error answer ('सही है') is unchanged", kept[1]["listen_for"][0]["wrong_answer_hi"] == "सही है")
    check("the log tells what was done to which question", any("question 1: listen-for N2.3.2-M2" in l and "713" in l for l in lines), lines)
    # two questions on sums with no carry, given a mistake that needs one: the first has nothing else to say and is dropped (the top-up would ask again), the second says what a right answer shows and stays, ungrounded
    pl3 = {"rotation_schedule": {"blocks": [{"type": "teach", "teach_group": "progressor", "talking_points": {}, "cfu": [q3, q4]}]}}
    lines3, _ = cfu.clean_plan_cfu(pl3, kb)
    kept3 = pl3["rotation_schedule"]["blocks"][0]["cfu"]
    check("a 'dropped carry' entry on 23 + 14 is removed, and the question with nothing else to listen for or show is DROPPED; the one that says what a right answer shows is kept, ungrounded",
          [k["question_hi"][:8] for k in kept3] == ["32 + 15 "] and kept3[0]["grounded"] is False and kept3[0]["listen_for"] == [], kept3)
    check("the log says so", any("question 1: listen-for removed N2.3.2-M1" in l for l in lines3) and any("question 1 dropped" in l for l in lines3), lines3)
    # the cap of two per block: a third valid question is left out, as before
    pl4 = {"rotation_schedule": {"blocks": [{"type": "teach", "teach_group": "progressor", "talking_points": {}, "cfu": [copy.deepcopy(q1), copy.deepcopy(q2), q4]}]}}
    cfu.clean_plan_cfu(pl4, kb)
    check("two questions per block is still the limit (the first two that pass)", [k["question_hi"][:8] for k in pl4["rotation_schedule"]["blocks"][0]["cfu"]] == ["54 + 29 ", "बोर्ड पर"])
    kb_lit = {"progressor": {**kb["progressor"], "criteria_type": "literacy"}}
    pl2 = {"rotation_schedule": {"blocks": [{"type": "teach", "teach_group": "progressor", "talking_points": {}, "cfu": [copy.deepcopy(q1)]}]}}
    cfu.clean_plan_cfu(pl2, kb_lit)
    check("a LITERACY skill is not checked this way (its numbers are labels, not quantities)", [x["wrong_answer_hi"] for x in (pl2["rotation_schedule"]["blocks"][0]["cfu"] or [{"listen_for": []}])[0]["listen_for"]] in (["73", "613"], []))

    if failures:
        print(f"\nFAILED ({len(failures)})")
        sys.exit(1)
    print("\nOK: the wrong answers a teacher listens for are computed by the code for the mistakes the knowledge base records, and a wrong one is corrected or removed before the question is used")


if __name__ == "__main__":
    asyncio.run(main())
