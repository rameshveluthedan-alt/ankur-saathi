"""
A two-digit skill never reaches 100, and the other prompt rules of the second round of real blocks.
Found on the second real block: worksheet problem 6 was 79 + 21 = 100. The knowledge base says max 99 for N2.3.2 and the model read it as a limit on the numbers ADDED, not on the TOTAL; the code that
replaces worksheet problems had no check for it (and no tests at all). Three-digit numbers are the Proficients' skill.

    cd backend && AUTH_MODE=off python tests/test_two_digit_limit.py --env-file .env
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import copy
import os
import random
import sys

os.environ.setdefault("AUTH_MODE", "off")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "..", "prompts"), os.path.join(HERE, "..")]
import _scratch  # noqa: F401
import cfu_prompt
import orchestrate
from app.services import cfu, plan_service

failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


def sheet(level, sums, required=6):
    """A plan with ONE worksheet of plain additions (problem_hi 'a + b = ___', answer, layout fields)."""
    return {"worksheets": {level: {"required_count": required, "problems": [{"number": i + 1, "problem_hi": f"{a} + {b} = ___", "answer": str(a + b), "row_type": "plain"} for i, (a, b) in enumerate(sums)]}},
            "rotation_schedule": {"blocks": []}, "explainability": {"items": []}}


SIX = [(38, 25), (57, 18), (49, 33), (56, 28), (39, 27)]
pa = lambda p: plan_service._plain_addition(p)


print("the skill rule: only a TWO-DIGIT ADDITION skill has a cap")
r = cfu.skill_rules
check("N2.3.2 and N2.3.1 (two-digit addition, with and without regrouping): the cap is 99", r("Adds two 2-digit numbers with regrouping (carry-over)")["max_result"] == 99 and r("Adds two 2-digit numbers without regrouping")["max_result"] == 99)
check("3-digit addition, subtraction, multiplication and a counting skill: no cap (their numbers and totals are bigger or not sums)", all(r(n)["max_result"] is None for n in ("Adds 3-digit numbers with regrouping", "Subtracts 2-digit numbers with borrowing (regrouping)", "Multiplies a 2-digit number by a 1-digit number", "Counts up to 20 objects", None, "")))
check("the two older rules are untouched", r("Adds two 2-digit numbers without regrouping")["no_carry"] is True and r("Subtracts 2-digit numbers without borrowing")["no_borrow"] is True)

print("\nthe show-me questions")
RULES = r("Adds two 2-digit numbers with regrouping (carry-over)")
ck = lambda item, rules=RULES: cfu.check_item(item, valid_ids={"N2.3.2-M1", "N2.3.2-M2"}, avoid=set(), rules=rules, strict=True, compare=True, lesson_results=frozenset())
lf = [{"misconception_id": "N2.3.2-M1", "wrong_answer_hi": "x"}]
check("a sum that reaches 100 is dropped, and the reason is given (79 + 21)", any("is over 99" in p for p in ck({"kind": "compute", "question_hi": "79 + 21 कितना होगा?", "expected_hi": "100", "listen_for": lf})), ck({"kind": "compute", "question_hi": "79 + 21 कितना होगा?", "expected_hi": "100", "listen_for": lf}))
check("a sum of 99 is fine (the limit is 'over 99')", ck({"kind": "compute", "question_hi": "56 + 43 कितना होगा?", "expected_hi": "99", "listen_for": lf}) == [])
check("an ordinary two-digit carry question is fine", ck({"kind": "compute", "question_hi": "56 + 28 कितना होगा?", "expected_hi": "84", "listen_for": lf}) == [])
check("a worked line to judge may show a WRONG result over 99 on purpose (56 + 28 = 714): only REAL results count", ck({"kind": "spot_error", "question_hi": "56 + 28 = 714। क्या यह सही है या गलत?", "expected_hi": "गलत, 84", "listen_for": lf}) == [])
check("...but a worked line whose REAL result reaches 100 is dropped (79 + 21 = 90)", any("is over 99" in p for p in ck({"kind": "spot_error", "question_hi": "79 + 21 = 90। क्या यह सही है या गलत?", "expected_hi": "गलत, 100", "listen_for": lf})))
check("a 'choose' question is held to it too", any("is over 99" in p for p in ck({"kind": "choose", "question_hi": "85 + 38: उत्तर 123 है या 113?", "expected_hi": "123", "listen_for": lf})))
check("a skill with no cap lets 3-digit totals through (N3.3.1)", ck({"kind": "compute", "question_hi": "167 + 245 कितना होगा?", "expected_hi": "412", "listen_for": lf}, r("Adds 3-digit numbers with regrouping")) == [])

print("\nthe worksheet repair (it had no tests at all)")
p = sheet("progressor", SIX + [(79, 21)])
log = plan_service.repair_worksheet_numbers(p)
pr = p["worksheets"]["progressor"]["problems"]
rep = pr[5]
check("the 6th problem, 79 + 21 = 100, is replaced, and the log says why", rep["problem_hi"] != "79 + 21 = ___" and any("problem 6" in l and "total is 100" in l for l in log), log)
a, b, _ = pa(rep)
check("the replacement is a TWO-digit sum with a carry and a total of 99 or less, its answer is right and its '= ___' is kept", a < 100 and b < 100 and a + b <= 99 and a % 10 + b % 10 >= 10 and rep["answer"] == str(a + b) and rep["problem_hi"].endswith("= ___"), rep)
check("the layout field and the problem number are kept", rep["row_type"] == "plain" and rep["number"] == 6)
others = [(x["problem_hi"], x["answer"]) for x in pr[:5]]
check("the five other problems are untouched", others == [(f"{x} + {y} = ___", str(x + y)) for x, y in SIX], others)
check("the new answer is not an answer already on the sheet", sum(1 for x in pr if x["answer"] == rep["answer"]) == 1)

rng = random.Random(24)
many, bad = 0, []
for _ in range(400):
    a, b = rng.randint(50, 99), rng.randint(50, 99)
    pl = sheet("progressor", SIX[:4] + [(a, b)], required=5)
    plan_service.repair_worksheet_numbers(pl)
    rep = pl["worksheets"]["progressor"]["problems"][4]
    x, y, _ = pa(rep)
    many += 1
    if not (x < 100 and y < 100 and x + y <= 99 and x % 10 + y % 10 >= 10 and rep["answer"] == str(x + y)):
        bad.append((a, b, rep))
check(f"{many} random two-digit sums that reach 100 or more (50-99 + 50-99): every replacement is two-digit, needs a carry and has the right answer", not bad, bad[:3])

pb = sheet("beginner", [(21, 14), (32, 25), (85, 27)], required=3)
plan_service.repair_worksheet_numbers(pb)
x, y, _ = pa(pb["worksheets"]["beginner"]["problems"][2])
check("a BEGINNER sheet is held to it too, and the replacement needs NO carry (their skill)", x + y <= 99 and x % 10 + y % 10 <= 9 and (x // 10 + y // 10) <= 9, pb["worksheets"]["beginner"]["problems"][2])

pp = sheet("proficient", [(167, 245), (85, 38), (356, 128)], required=3)
before = copy.deepcopy(pp)
plan_service.repair_worksheet_numbers(pp)
check("a PROFICIENT sheet is NOT touched: 3-digit sums are their skill (and a 2-digit sum over 99 there is left as the model wrote it)", pp["worksheets"] == before["worksheets"])
q3 = sheet("progressor", [(167, 245), (38, 25)], required=2)
b3 = copy.deepcopy(q3)
plan_service.repair_worksheet_numbers(q3)
check("a progressor problem with a THREE-digit addend is left alone (it is not a two-digit sum that overflowed)", q3["worksheets"] == b3["worksheets"])
word = sheet("progressor", SIX[:3], required=3)
word["worksheets"]["progressor"]["problems"].append({"number": 4, "problem_hi": "रानी के पास 79 रुपये थे और 21 रुपये और मिले। कुल कितने रुपये हुए?", "answer": "100", "row_type": None})
bw = copy.deepcopy(word)
plan_service.repair_worksheet_numbers(word)
check("a word problem is never touched (the repair only reads plain 'a + b' problems)", word["worksheets"] == bw["worksheets"])
fine = sheet("progressor", SIX[:5], required=5)
bf = copy.deepcopy(fine)
check("a sheet with nothing wrong comes back unchanged with an empty log", plan_service.repair_worksheet_numbers(fine) == [] and fine["worksheets"] == bf["worksheets"])

print("\nthe warning about the lesson's own results (the board), log only")
KB = {"progressor": {"competency_id": "N2.3.2", "name_en": "Adds two 2-digit numbers with regrouping (carry-over)", "name_hi": "x", "criteria_type": "computation",
                     "mistakes": [{"id": f"N2.3.2-M{i}", "name_hi": f"गलती {i}", "diagnostic_indicator": "d"} for i in (1, 2, 3, 4)]}}
Q1 = {"kind": "compute", "question_hi": "बोर्ड पर देखो: 47 + 35। इसका उत्तर लिखो।", "expected_hi": "82", "listen_for": [{"misconception_id": "N2.3.2-M1", "wrong_answer_hi": "72"}, {"misconception_id": "N2.3.2-M3", "wrong_answer_hi": "92"}]}
Q2 = {"kind": "spot_error", "question_hi": "बोर्ड पर देखो: 56 + 27 = 73 लिखा है। सही या गलत?", "expected_hi": "गलत, 83", "listen_for": [{"misconception_id": "N2.3.2-M1", "wrong_answer_hi": "सही"}]}
pl = {"rotation_schedule": {"blocks": [{"type": "teach", "teach_group": "progressor", "cfu": [copy.deepcopy(Q1), copy.deepcopy(Q2)],
                                       "talking_points": {"i_do_hi": "बोर्ड पर 57 + 26 लिखें: उत्तर 83।", "we_do_hi": "नया उदाहरण 68 + 24 = 92 साथ में करें।"}}]}}
lines, _ = cfu.clean_plan_cfu(pl, KB)
kept = pl["rotation_schedule"]["blocks"][0]["cfu"]
check("both questions are KEPT (a warning, not a drop: a drop would cost an extra model call)", len(kept) == 2, kept)
check("question 2's right answer 83 is the I Do's result: a warning", any("question 2: warning: its right answer 83 is already a result in the lesson" in l for l in lines), lines)
check("question 1's listed wrong answer 92 is the We Do's result: a warning (and 72 is not)", any("question 1: warning: the listed wrong answer 92" in l for l in lines) and not any("wrong answer 72" in l for l in lines), lines)
pl2 = {"rotation_schedule": {"blocks": [{"type": "teach", "teach_group": "progressor", "cfu": [copy.deepcopy(Q1), copy.deepcopy(Q2)], "talking_points": {"i_do_hi": "बोर्ड पर 46 + 38 लिखें: उत्तर 84।"}}]}}
lines2, _ = cfu.clean_plan_cfu(pl2, KB)
check("with no collision there is no warning", not any("warning" in l for l in lines2), lines2)

print("\nthe prompts")
check("the number-range note: a two-digit skill (max 99) says every number and the TOTAL stay within 99, and that 79 + 21 = 100 is not allowed", all(w in orchestrate.range_note({"max": 99, "min": 10}) for w in ("at most 99", "never reaches 100", "79 + 21 = 100 is NOT allowed")))
check("...a three-digit skill (max 999) is told the limit too, without the two-digit sentence", "at most 999" in orchestrate.range_note({"max": 999, "min": 100}) and "never reaches 100" not in orchestrate.range_note({"max": 999}))
check("...and a skill with no maximum, or a broken range, gets nothing (never an error)", orchestrate.range_note(None) == "" and orchestrate.range_note({}) == "" and orchestrate.range_note({"max": "x"}) == "" and orchestrate.range_note("junk") == "")
rules = orchestrate.RETEACH_MAIN_RULES
check("I Do: the wrong and the right working are of the SAME sum, and that is the one exception to 'never repeat a sum'", "do the SAME sum again correctly" in rules and "the right working is of the SAME sum as the wrong working" in rules and "47 + 36 and 36 + 47 are the SAME sum" in rules)
check("everything the earlier tests pin is still in the re-teach rules", all(w in rules for w in ("show the mistake FIRST", "FIND AND FIX", "Name no child", "कल हमने क्या सीखा था", "NEW numbers", "ERASE it", "recall 2, I Do 6, We Do 7", "quietly", "never call out", "more than a quarter", "do NOT write problems of your own", "वर्कशीट के सवाल")))
check("the show-me rules: not a result already on the board", "must not be a result the lesson has already written on the board" in cfu_prompt.CFU_RULES and "DIFFERENT right answers" in cfu_prompt.CFU_RULES)
text = " ".join(v for v in vars(orchestrate).values() if isinstance(v, str))
check("the plan prompt: the other groups' practice is NAMED (two or three example problems), and a worksheet's total stays within 99 in a skill whose range ends there", "NAME the actual practice" in text and "also stays at 99 or less" in text)

if failures:
    print(f"\nFAILED ({len(failures)})")
    sys.exit(1)
print("\nOK: a two-digit skill never reaches 100 (worksheet, show-me, prompt), the repair has its first tests, and the three prompt changes are in")
