"""
How many questions a child must get right, and what counts. The thresholds come from each skill's own criteria in the knowledge base; the score is
computed IN CODE from the per-problem results (rescore), then the status IN CODE (derive_status). No database, no AI.

  * required problems are always scored (a blank one counts as wrong); an extra counts only if attempted;
  * a problem the child copied wrongly is left out; an answer the app cannot read counts as not correct;
  * EXTRAS CAN ONLY HELP (decided 21 Oct): a wrong extra never lowers the result, a right one can raise it.

    python backend/tests/test_scoring.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "prompts"))
from vision_analysis import derive_status, rescore

failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


# the criteria exactly as the knowledge base stores them for the three skills of the N2.3.2 lesson
BEGINNER = {"type": "computation", "achieved": {"min_accuracy": 0.85, "sessions_required": 2, "no_persistent_misconception": True}, "not_achieved": {"max_accuracy": 0.5, "or_cannot_attempt": True}}
PROGRESSOR = {"type": "computation", "achieved": {"min_accuracy": 0.8, "sessions_required": 2, "no_persistent_misconception": True}, "not_achieved": {"max_accuracy": 0.4, "or_cannot_attempt": True}}
PROFICIENT = PROGRESSOR


def child(required, right, wrong_extras=0, right_extras=0, blank_extras=0, copy_error_at=(), unreadable_at=(), blank_required_at=()):
    """right = how many of the REQUIRED problems are correct, in order; the rest of the required ones are wrong."""
    probs = []
    for i in range(required):
        p = {"number": i + 1, "extracted_answer": "1", "is_correct": i < right}
        if (i + 1) in copy_error_at: p["copy_error"] = True
        if (i + 1) in unreadable_at: p.update(is_correct=None, extracted_answer="6?", confidence="needs_verification")
        if (i + 1) in blank_required_at: p.update(is_correct=None, extracted_answer=None, attempted=False)
        probs.append(p)
    n = required
    for _ in range(right_extras): n += 1; probs.append({"number": n, "extracted_answer": "1", "is_correct": True})
    for _ in range(wrong_extras): n += 1; probs.append({"number": n, "extracted_answer": "1", "is_correct": False})
    for _ in range(blank_extras): n += 1; probs.append({"number": n, "extracted_answer": None, "attempted": False})
    return {"problems": probs, "summary": {}}


def status(crit, required, right, **kw):
    s = rescore(child(required, right, **kw), required)
    return derive_status(s, crit, []), s


print("how many REQUIRED problems must be right (the thresholds of the three skills in the N2.3.2 lesson)")
for name, crit, req, expect in (("Beginner N2.3.1, of 5", BEGINNER, 5, {"achieved": [5], "partially_achieved": [3, 4], "not_achieved": [0, 1, 2]}),
                                ("Progressor N2.3.2, of 6", PROGRESSOR, 6, {"achieved": [5, 6], "partially_achieved": [3, 4], "not_achieved": [0, 1, 2]}),
                                ("Proficient N3.3.1, of 8", PROFICIENT, 8, {"achieved": [7, 8], "partially_achieved": [4, 5, 6], "not_achieved": [0, 1, 2, 3]})):
    got = {}
    for right in range(req + 1):
        got.setdefault(status(crit, req, right)[0], []).append(right)
    check(f"{name}: achieved {expect['achieved']}, partly {expect['partially_achieved']}, not achieved {expect['not_achieved']}", got == expect, got)
check("the Beginner rule is strict: 4 of 5 is 80%, below 85%, so only partly achieved", status(BEGINNER, 5, 4)[0] == "partially_achieved")

print("extras can only help")
for name, crit, req in (("Progressor", PROGRESSOR, 6), ("Beginner", BEGINNER, 5)):
    st, s = status(crit, req, req, wrong_extras=2)
    check(f"{name}: everything required right and 2 extras attempted WRONG is still achieved (it used to be 'partly')", st == "achieved" and s["accuracy"] == 1.0 and s["score_basis"] == "required", (st, s))
    st, s = status(crit, req, req, right_extras=2)
    check(f"{name}: everything required right and 2 extras right is achieved", st == "achieved")
    st, s = status(crit, req, req, blank_extras=2)
    check(f"{name}: 2 extras left blank is not an error", st == "achieved" and s["total_problems"] == req and s["extras_attempted"] == 0)
st, s = status(BEGINNER, 5, 4, right_extras=3)
check("a right extra CAN raise the result: Beginner 4 of 5 (80%, partly) plus 3 extras right = 7 of 8 (87.5%) is achieved", st == "achieved" and s["score_basis"] == "required+extras" and (s["correct"], s["total_problems"]) == (7, 8), (st, s))
st, s = status(BEGINNER, 5, 4, wrong_extras=3)
check("...but the same child with 3 extras WRONG stays at 4 of 5, partly: never lower than without the extras", st == "partially_achieved" and (s["correct"], s["total_problems"]) == (4, 5), (st, s))
st, s = status(PROGRESSOR, 6, 4, right_extras=1, wrong_extras=1)
check("one right and one wrong extra: the better basis is used (4 of 6 beats 5 of 8)", (s["correct"], s["total_problems"]) == (4, 6) and s["score_basis"] == "required", s)
st, s = status(PROGRESSOR, 6, 3, right_extras=2)
check("a tie goes to the required problems alone, and the numbers always agree with each other", all(abs(x["accuracy"] - x["correct"] / x["total_problems"]) < 0.001 for x in (status(PROGRESSOR, 6, r, wrong_extras=w, right_extras=e)[1] for r in range(7) for w in range(3) for e in range(3) if w + e <= 2)))
worst = min(status(PROGRESSOR, 6, r, wrong_extras=w, right_extras=e)[1]["accuracy"] - status(PROGRESSOR, 6, r)[1]["accuracy"] for r in range(7) for w in range(3) for e in range(3) if w + e <= 2)
check("over every combination of 0 to 6 required right and up to 2 extras, an extra never lowers the accuracy", worst >= 0, worst)

print("what counts")
st, s = status(PROGRESSOR, 6, 4, copy_error_at=(6,))
check("a problem copied wrongly is left out: 4 right, 1 wrong, 1 miscopied is 4 of 5 = 80% = achieved", (s["correct"], s["total_problems"], s["copy_excluded"]) == (4, 5, 1) and st == "achieved", s)
st, s = status(PROGRESSOR, 6, 5, unreadable_at=(6,))
check("an answer the app cannot read counts as not correct (5 of 6)", (s["correct"], s["total_problems"]) == (5, 6), s)
st, s = status(PROGRESSOR, 6, 4, blank_required_at=(5, 6))
check("a required problem left blank counts as wrong (4 of 6)", (s["correct"], s["total_problems"]) == (4, 6), s)
s = rescore({"problems": [{"number": i, "extracted_answer": "1", "is_correct": True, "copy_error": True} for i in range(1, 4)], "summary": {}}, 3)
check("all required problems miscopied: nothing to score, and no crash (accuracy is None)", s["total_problems"] == 0 and s["accuracy"] is None, s)
keep = {"summary": {"accuracy": 0.5, "correct": 3, "total_problems": 6}, "problems": [{"number": 1}]}
check("without a required_count the model's own summary is kept", rescore(keep, None) == keep["summary"])

print("the status rule itself")
check("exactly at the achieved line is achieved; exactly at the not-achieved line is not achieved", derive_status({"accuracy": 0.8}, PROGRESSOR, []) == "achieved" and derive_status({"accuracy": 0.4}, PROGRESSOR, []) == "not_achieved")
check("between the lines is partly achieved", derive_status({"accuracy": 0.6}, PROGRESSOR, []) == "partially_achieved")
check("the same mistake twice or more stops 'achieved' even on a high score (when the skill says so)", derive_status({"accuracy": 0.95}, PROGRESSOR, [{"occurrences": 2}]) == "partially_achieved" and derive_status({"accuracy": 0.95}, PROGRESSOR, [{"occurrences": 1}]) == "achieved")
check("a skill with no numeric rule (observational) has no calculated status: the caller falls back to the model's label",
      derive_status({"accuracy": 1.0}, {"type": "observational", "achieved": {"description": "x"}, "not_achieved": {"description": "y"}}, []) is None)
check("a skill with no accuracy to judge has no calculated status", derive_status({}, PROGRESSOR, []) is None)

if failures:
    print(f"\nFAILED ({len(failures)})")
    sys.exit(1)
print("\nOK: the scoring rules are pinned down, and an extra can only help a child")
