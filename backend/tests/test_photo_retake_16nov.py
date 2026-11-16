"""
Photo marking when too little of a sheet can be marked (16 Nov, MPT101, photo_analysis_2.png): three Progressor sheets had the SAME different numbers on
5 of 6 sums (most likely an earlier version of the worksheet: the shared plan had been made again). Each child was "scored" on one sum, got NA, and the
group got "0%" and "Teach again". Now:
  * a child is given a level only when at least half of the sheet's required points could be marked (copied-wrongly sums cannot be); otherwise
    "photograph again" and NOTHING is saved (no evidence row, no status);
  * several sheets with the same different numbers on the same questions are reported as not matching today's worksheet;
  * a short reading or writing sheet is never cut down (only plain sums can be "copied wrongly"), so it is always scored.
A scratch class in the lab database; no AI (the vision answers are given here).

    cd backend && AUTH_MODE=off python tests/test_photo_retake_16nov.py --env-file .env
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import asyncio
import os
import sys
from datetime import date

os.environ.setdefault("AUTH_MODE", "off")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "prompts"))
import _scratch
import vision_analysis as V

failures = []
TODAY = date.today()


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


# today's worksheet (the key) and the numbers the three children actually wrote (the screenshot's sheets)
KEY = [{"number": 1, "problem_hi": "36 + 28"}, {"number": 2, "problem_hi": "47 + 25"}, {"number": 3, "problem_hi": "58 + 34"},
       {"number": 4, "problem_hi": "29 + 46"}, {"number": 5, "problem_hi": "38 + 27"}, {"number": 6, "problem_hi": "45 + 37"}]
WRITTEN = {1: "36 + 27", 2: "48 + 25", 3: "54 + 36", 5: "28 + 39", 6: "45 + 29"}


def other_sheet(roll, answers):
    """A sheet from another version of the worksheet: sums 1, 2, 3, 5, 6 differ from today's key; sum 4 is today's (answered wrongly)."""
    probs = []
    for n in range(1, 7):
        written = WRITTEN.get(n, KEY[n - 1]["problem_hi"])
        probs.append({"number": n, "problem_as_written": written, "extracted_answer": str(answers[n - 1]), "is_correct": False, "confidence": "high"})
    return {"roll_number": roll, "problems": probs, "summary": {}}


def todays_sheet(roll, right, slip_at=None):
    """A sheet from today's worksheet: `right` sums right in order; one sum copied wrongly at slip_at (a genuine slip)."""
    probs = []
    for i, kp in enumerate(KEY):
        a, b = map(int, kp["problem_hi"].split(" + "))
        written = kp["problem_hi"]
        if slip_at == kp["number"]:
            written, ans, ok = f"{a + 1} + {b}", a + 1 + b, False
        else:
            ok = i < right
            ans = a + b if ok else a + b - 10
        probs.append({"number": kp["number"], "problem_as_written": written, "extracted_answer": str(ans), "is_correct": ok, "confidence": "high"})
    return {"roll_number": roll, "problems": probs, "summary": {}}


def unit():
    print("the sheet's points and how many could be marked")
    c = other_sheet(14, [81, 91, 80, 64, 67, 64])
    V.apply_copy_checks(c, KEY)
    s = V.rescore(c, 6)
    check("the screenshot's sheet: 6 points, 1 could be marked (5 copied wrongly)", (s["sheet_points"], s["marked_points"], s["total_problems"]) == (6, 1, 1), s)
    t = todays_sheet(3, 5, slip_at=6)
    V.apply_copy_checks(t, KEY)
    s2 = V.rescore(t, 6)
    check("one genuine slip: 5 of 6 marked, scored as before", (s2["marked_points"], s2["total_problems"]) == (5, 5), s2)
    reading = {"roll_number": 1, "problems": [{"number": 1, "problem_hi": "रामू कहाँ गया?", "extracted_answer": "खेत", "is_correct": True},
                                              {"number": 2, "problem_hi": "क्यों?", "extracted_answer": "बारिश", "is_correct": False}]}
    V.apply_copy_checks(reading, [{"number": 1, "problem_hi": "रामू कहाँ गया?"}, {"number": 2, "problem_hi": "क्यों?"}])
    s3 = V.rescore(reading, 2)
    check("a reading sheet with 2 questions: never cut down (only plain sums can be copied wrongly), 2 of 2 marked", (s3["sheet_points"], s3["marked_points"]) == (2, 2), s3)
    writing = {"roll_number": 1, "problems": [{"number": 1, "extracted_answer": "मेरा स्कूल बड़ा है। ...", "checklist_met": [True, True, False, True]}]}
    s4 = V.rescore(writing, 1)
    check("a one-paragraph writing sheet: its 4 checklist items are its points, all marked", (s4["sheet_points"], s4["marked_points"]) == (4, 4), s4)

    print("\na mistake written as an object, not a code (17 Nov, live: \"unhashable type: 'dict'\" when kept sheets were counted)")
    odd = {"problems": [{"number": 1, "diagnosed_misconception": {"id": "N2.3.2-M1", "name": "drops the carry"}, "confidence": "high"},
                        {"number": 2, "diagnosed_misconception": [{"misconception_id": "N2.3.2-M1"}]},
                        {"number": 3, "diagnosed_misconception": "N2.3.2-M2"}, {"number": 4, "diagnosed_misconception": None}]}
    got = V.recompute_misconceptions(odd)
    check("an object {id: ...}, a list of objects and a plain code are all counted by their code", {m["misconception_id"]: m["occurrences"] for m in got} == {"N2.3.2-M1": 2, "N2.3.2-M2": 1}, got)
    only_summary = {"problems": [{"number": 1}], "summary": {"detected_misconceptions": [{"misconception_id": {"id": "N2.3.2-M1"}, "occurrences": 2}, "N2.3.2-M2", {"id": "N2.3.2-M3"}]}}
    got2 = V.recompute_misconceptions(only_summary)
    check("...and in the AI's own summary list (an object id, a bare code, an 'id' key)", [m["misconception_id"] for m in got2] == ["N2.3.2-M1", "N2.3.2-M2", "N2.3.2-M3"], got2)

    print("\nthe wrong-worksheet signal")
    per = [{"roll_number": r, "copy_errors": [{"problem": n, "written": w} for n, w in WRITTEN.items()]} for r in (6, 14, 16)]
    m = V.sheet_mismatch(per)
    check("three sheets with the same different numbers on 5 questions: reported, with the rolls and questions", m == {"problems": [1, 2, 3, 5, 6], "rolls": [6, 14, 16]}, m)
    check("one child's own slips (different on each sheet) are not a mismatch",
          V.sheet_mismatch([{"roll_number": 1, "copy_errors": [{"problem": 2, "written": "48 + 25"}]}, {"roll_number": 2, "copy_errors": [{"problem": 3, "written": "57 + 34"}]}]) is None)
    check("the same slip on ONE question of two sheets is not enough (it takes two questions)",
          V.sheet_mismatch([{"roll_number": r, "copy_errors": [{"problem": 2, "written": "48 + 25"}]} for r in (1, 2)]) is None)


async def flow():
    print("\nthe screenshot's three sheets, through the photo marking (a scratch class, no AI)")
    db = await _scratch.connect()
    levels = {r: ("progressor", "progressor") for r in (3, 6, 14, 16, 19)}
    teacher_id, school = await _scratch.make_class(db, levels, grade="grade_2")
    try:
        sheets = [other_sheet(14, [81, 91, 80, 64, 67, 64]), other_sheet(16, [63, 63, 90, 64, 67, 74]), other_sheet(6, [53, 910, 810, 64, 57, 64])]
        r = await V.process_vision_results(db, teacher_id, TODAY, "N2.3.2", sheets, None, required_count=6, problems=KEY, expected_rolls=[3, 6, 14, 16, 19])
        check("no child is given a level: all three 'photograph again', with 1 of 6 marked", r["children_scored"] == 0 and sorted(r["retake"]) == [6, 14, 16]
              and all(c["reason"] == "too_few_marked" and (c["marked_points"], c["sheet_points"]) == (1, 6) for c in r["per_child"]), r["per_child"])
        check("...so no group score and no suggestion (before: 0% and Teach again)", r["group_accuracy"] is None and r["ai_recommendation"] is None, (r["group_accuracy"], r["ai_recommendation"]))
        check("...and the sheets are reported as not today's worksheet", r["sheet_mismatch"] == {"problems": [1, 2, 3, 5, 6], "rolls": [6, 14, 16]}, r["sheet_mismatch"])
        saved = await db.fetchval("SELECT COUNT(*) FROM assessment_evidence WHERE teacher_id = $1 AND session_date = $2", teacher_id, TODAY)
        status = await db.fetchval("""SELECT COUNT(*) FROM child_competency_status s JOIN children c ON c.id = s.child_id WHERE c.teacher_id = $1""", teacher_id)
        check("...and NOTHING is saved for them: no evidence, no status (before: three NA in the records)", saved == 0 and status == 0, (saved, status))

        print("\na mixed batch: one sheet from today's worksheet with a genuine slip, one from the other version")
        r2 = await V.process_vision_results(db, teacher_id, TODAY, "N2.3.2", [todays_sheet(3, 5, slip_at=6), other_sheet(19, [81, 91, 80, 64, 67, 64])],
                                            None, required_count=6, problems=KEY, expected_rolls=[3, 6, 14, 16, 19])
        c3 = next(c for c in r2["per_child"] if c["roll_number"] == 3)
        check("roll 3 is scored on its 5 marked sums (5 right): a level and a group score", c3["accuracy"] == 1.0 and c3["assessed_problems"] == 5 and r2["children_scored"] == 1
              and r2["group_accuracy"] == 1.0 and r2["ai_recommendation"] == "advance", (c3, r2["group_accuracy"]))
        check("roll 19 'photograph again'; one other-version sheet alone is not a mismatch", r2["retake"] == [19] and r2["sheet_mismatch"] is None, (r2["retake"], r2["sheet_mismatch"]))
        saved2 = {x["roll_number"] for x in await db.fetch("""SELECT c.roll_number FROM assessment_evidence e JOIN children c ON c.id = e.child_id
                                                              WHERE e.teacher_id = $1 AND e.session_date = $2""", teacher_id, TODAY)}
        check("...only roll 3 is saved", saved2 == {3}, saved2)

        print("\nreplacing children already marked today, several at once, with NO new AI call (16 Nov: each replacement sent all photos again)")
        from app.services import review_service as RS
        await db.execute("DELETE FROM assessment_evidence WHERE teacher_id = $1", teacher_id)
        await db.execute("DELETE FROM child_competency_status WHERE child_id IN (SELECT id FROM children WHERE teacher_id = $1)", teacher_id)
        await db.execute("""INSERT INTO daily_plans (teacher_id, plan_date, domain_id, selected_competency_id, plan_content, groups_snapshot, explainability)
                            VALUES ($1, $2, 'numeracy', 'N2.3.2', $3::jsonb, '{}'::jsonb, '{}'::jsonb)""", teacher_id, TODAY,
                         __import__("json").dumps({"worksheets": {"progressor": {"problems": KEY, "required_count": 6}}}))
        first = await V.process_vision_results(db, teacher_id, TODAY, "N2.3.2", [todays_sheet(r, 2) for r in (3, 6, 14)], None, required_count=6, problems=KEY)
        newer = [todays_sheet(r, 6) for r in (3, 6, 14, 16, 19)]
        for sheet in newer[:3]:                    # the kept readings carry a mistake written as an object (what broke on live, 17 Nov)
            sheet["problems"][0]["diagnosed_misconception"] = {"id": "N2.3.2-M1", "name": "drops the carry"}
        second = await V.process_vision_results(db, teacher_id, TODAY, "N2.3.2", newer, None, required_count=6, problems=KEY)
        check("round 1: three children at 2 of 6; round 2: the two new ones marked, the three repeats skipped AND their new readings kept",
              first["children_scored"] == 3 and second["children_scored"] == 2 and sorted(int(k) for k in second["pending"]) == [3, 6, 14], (second["children_scored"], list(second["pending"])))
        aid = await RS.save_analysis(db, teacher_id, TODAY, "numeracy", "progressor", "N2.3.2", second)
        out = await RS.replace_from_saved(db, teacher_id, aid, [3, 6, 14])
        acc = {x["roll_number"]: x["evidence_data"] for x in await db.fetch("""SELECT c.roll_number, e.evidence_data FROM assessment_evidence e JOIN children c ON c.id = e.child_id
                                                                               WHERE e.teacher_id = $1 AND e.session_date = $2""", teacher_id, TODAY)}
        import json as _j
        new_acc = {r: (_j.loads(v) if isinstance(v, str) else v)["scoring"]["accuracy"] for r, v in acc.items()}
        check("all three replaced in one go: their new sheets (6 of 6) now count, one result each", out["children_scored"] == 3 and all(new_acc[r] == 1.0 for r in (3, 6, 14))
              and len(acc) == 5, new_acc)
        check("the result shows the WHOLE group today: 5 children, all right (before: '1 child'); the object-shaped mistake on 3 replaced sheets is COUNTED "
              "(3 times: the rule suggests teaching again), not a crash", out["today_group"]["children"] == 5 and out["today_group"]["group_accuracy"] == 1.0
              and out["today_group"]["ai_recommendation"] == "reteach" and out["today_group"]["rolls"] == [3, 6, 14, 16, 19], out["today_group"])
        left = await db.fetchval("SELECT result FROM review_analyses WHERE id = $1", aid)
        left = _j.loads(left) if isinstance(left, str) else left
        check("the earlier round stops offering them (no pending, no 'already checked')", not left.get("pending") and not left.get("skipped_duplicates"), (left.get("pending"), left.get("skipped_duplicates")))
        try:
            await RS.replace_from_saved(db, teacher_id, aid, [3])
            check("replacing again with nothing kept says so", False)
        except LookupError as e:
            check("replacing again with nothing kept says so", "no longer available" in str(e))
        await db.execute("DELETE FROM review_analyses WHERE teacher_id = $1", teacher_id)
        await db.execute("DELETE FROM daily_plans WHERE teacher_id = $1", teacher_id)
    finally:
        await db.execute("DELETE FROM child_competency_status WHERE child_id IN (SELECT id FROM children WHERE teacher_id = $1)", teacher_id)
        await db.execute("DELETE FROM assessment_evidence WHERE teacher_id = $1", teacher_id)
        await _scratch.remove_class(db, teacher_id, school)
        await db.close()


if __name__ == "__main__":
    unit()
    asyncio.run(flow())
    print(f"\n{'ALL OK' if not failures else str(len(failures)) + ' FAILED'}")
    sys.exit(1 if failures else 0)
