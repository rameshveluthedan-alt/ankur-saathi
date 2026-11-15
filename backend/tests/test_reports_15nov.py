"""
The reports before the 18 Nov demo (15 Nov): the CSVs readable (a report date, "Grade 1", "Beginner") with each subject's latest checked skill and
its result; the class summary with where each child is on the skills taught (A / PA / NA); the mentor report with results by skill (counts only).
A scratch class in the lab database; no AI.

    cd backend && AUTH_MODE=off python tests/test_reports_15nov.py --env-file .env
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import asyncio
import csv
import io
import json
import os
import sys
from datetime import date, timedelta

os.environ.setdefault("AUTH_MODE", "off")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "prompts"))
import _scratch
from app.services import progress_service as P

failures = []
TODAY = date.today()


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


def unit():
    print("the readable values")
    check("'grade_1' -> 'Grade 1', 'balvatika' -> 'Balvatika'", P._grade("grade_1") == "Grade 1" and P._grade("balvatika") == "Balvatika")
    check("levels in words, results as A / PA / NA", P.LEVEL_EN["progressor"] == "Progressor" and P.RESULT_CODE["partially_achieved"] == "PA")
    res = {"N2.3.1": {"status": "achieved", "date": "2026-11-10", "domain": "numeracy"}, "N2.3.2": {"status": "not_achieved", "date": "2026-11-12", "domain": "numeracy"},
           "L2.7.2": {"status": "partially_achieved", "date": "2026-11-14", "domain": "r1_literacy"}}
    check("a child's newest result in a subject: the latest date wins, per subject", P._latest_in(res, "numeracy") == ("N2.3.2", "not_achieved", "2026-11-12")
          and P._latest_in(res, "r1_literacy") == ("L2.7.2", "partially_achieved", "2026-11-14") and P._latest_in({}, "numeracy") is None)


async def flow():
    print("\na scratch class with plans and results")
    db = await _scratch.connect()
    levels = {1: ("beginner", "beginner"), 2: ("beginner", "beginner"), 3: ("progressor", "progressor"), 4: ("progressor", "progressor"), 5: ("proficient", "proficient")}
    teacher_id, school = await _scratch.make_class(db, levels, grade="grade_2")
    try:
        kids = {r["roll_number"]: r["id"] for r in await db.fetch("SELECT id, roll_number FROM children WHERE teacher_id = $1", teacher_id)}
        d1, d2 = TODAY - timedelta(days=3), TODAY - timedelta(days=1)
        snap = {"beginner": {"target": "N2.3.1", "rolls": [1, 2]}, "progressor": {"target": "N2.3.2", "rolls": [3, 4]}, "proficient": {"target": "N3.3.1", "rolls": [5]}}
        for d in (d1, d2):
            await db.execute("""INSERT INTO daily_plans (teacher_id, plan_date, domain_id, selected_competency_id, plan_content, groups_snapshot, explainability)
                                VALUES ($1, $2, 'numeracy', 'N2.3.2', '{}'::jsonb, $3::jsonb, '{}'::jsonb)""", teacher_id, d, json.dumps(snap))
        ev = [(1, "N2.3.1", "not_achieved", d1), (1, "N2.3.1", "achieved", d2), (2, "N2.3.1", "partially_achieved", d2), (3, "N2.3.2", "not_achieved", d2)]
        for roll, k, st, d in ev:
            await db.execute("""INSERT INTO assessment_evidence (child_id, competency_id, teacher_id, channel, status, evidence_data, session_date)
                                VALUES ($1, $2, $3, 'observed', $4, '{}'::jsonb, $5)""", kids[roll], k, teacher_id, st, d)

        cs = await P.get_class_summary(db, teacher_id, TODAY)
        ch = cs["subjects"]["numeracy"]["children"]
        rows = {r["roll"]: r["results"] for r in ch["rows"]}
        check("the class summary: the skills taught, in group order", ch["skills"] == ["N2.3.1", "N2.3.2", "N3.3.1"], ch["skills"])
        check("...each child's NEWEST result on each (roll 1: NA then A -> A), and nothing where not checked",
              rows[1]["N2.3.1"] == "a" and rows[2]["N2.3.1"] == "pa" and rows[3]["N2.3.2"] == "na" and rows[4]["N2.3.2"] == "" and rows[5]["N3.3.1"] == "", rows)
        check("...a row for every child of the class, roll numbers only", sorted(rows) == [1, 2, 3, 4, 5] and all(set(r) == {"roll", "results"} for r in ch["rows"]))     # each row: a roll number and results, no child's name

        ms = await P.get_mentor_summary(db, teacher_id, TODAY)
        sr = {x["skill_id"]: x for x in ms["progress"]["skill_results"]}
        check("the mentor report: results by skill as counts, and who it was taught to without a result yet",
              (sr["N2.3.1"]["a"], sr["N2.3.1"]["pa"], sr["N2.3.1"]["na"], sr["N2.3.1"]["not_checked"]) == (1, 1, 0, 0)
              and (sr["N2.3.2"]["na"], sr["N2.3.2"]["not_checked"]) == (1, 1) and sr["N3.3.1"]["not_checked"] == 1, sr)

        mlo = list(csv.reader(io.StringIO(await P.export_mlo_report_csv(db, teacher_id))))
        head, first = mlo[0], {r[4]: r for r in mlo[1:]}
        check("the officer CSV: a report date, readable grade and group, and the latest checked skill with its result and date",
              head[:6] == ["Report Date", "School Code", "Block", "District", "Roll No", "Grade"] and first["1"][0] == TODAY.isoformat() and first["1"][5] == "Grade 2"
              and first["1"][6] == "Beginner" and first["1"][8:11] == ["N2.3.1", "A", d2.isoformat()], first.get("1"))
        check("...a child with no result: those three columns empty", first["5"][8:11] == ["", "", ""], first.get("5"))
        check("...and no Name column (roll numbers only)", "Name" not in head)
        klass = list(csv.reader(io.StringIO(await P.export_class_report_csv(db, teacher_id))))
        check("the class CSV: the same tidy columns, with the name column", klass[0][:5] == ["Report Date", "Class No", "Grade", "School Roll", "Name"]
              and "Numeracy Latest Result (A/PA/NA)" in klass[0])
    finally:
        await db.execute("DELETE FROM assessment_evidence WHERE teacher_id = $1", teacher_id)
        await db.execute("DELETE FROM daily_plans WHERE teacher_id = $1", teacher_id)
        await _scratch.remove_class(db, teacher_id, school)
        await db.close()


if __name__ == "__main__":
    unit()
    asyncio.run(flow())
    print(f"\n{'ALL OK' if not failures else str(len(failures)) + ' FAILED'}")
    sys.exit(1 if failures else 0)
