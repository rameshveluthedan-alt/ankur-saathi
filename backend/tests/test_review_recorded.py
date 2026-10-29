"""
The Review shows what was recorded, not only who: an observed save says per child whether the result is new, changed or the same as before (and which
roll numbers are not in the class, never counted as saved), and the coverage reply carries each child's recorded result today (the newest; for reading
aloud with the two numbers entered), so the screen can show the teacher's own choices after a save and when she comes back. No AI call.

    cd backend && AUTH_MODE=off python tests/test_review_recorded.py --env-file .env
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import asyncio
import json
import os
import sys
from datetime import date, timedelta

os.environ.setdefault("AUTH_MODE", "off")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "prompts"))
import _scratch
from fastapi.testclient import TestClient
from app.main import app

TODAY = date.today()
failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


async def main():
    db = await _scratch.connect()
    levels = {1: "beginner", 2: "beginner", 3: "progressor", 4: "progressor", 5: "progressor", 6: "proficient"}
    teacher_id, school = await _scratch.make_class(db, {r: (lv, lv) for r, lv in levels.items()}, grade="grade_2")
    snapshot = {"beginner": {"count": 2, "rolls": [1, 2], "target": "N2.3.1"}, "progressor": {"count": 3, "rolls": [3, 4, 5], "target": "N2.3.2"},
                "proficient": {"count": 1, "rolls": [6], "target": "N3.3.1"}}
    lit = {"beginner": {"count": 2, "rolls": [1, 2], "target": "L2.5.1"}, "progressor": {"count": 3, "rolls": [3, 4, 5], "target": "L2.5.1"}, "proficient": {"count": 1, "rolls": [6], "target": "L2.5.1"}}
    for dom, snap, content in (("numeracy", snapshot, {}), ("r1_literacy", lit, {"passages_used": {"progressor": "RP-004"}})):       # the Hindi plan read RP-004 in class today
        await db.execute("""INSERT INTO daily_plans (teacher_id, plan_date, domain_id, selected_competency_id, plan_content, explainability, groups_snapshot, generation_time_ms, claude_model)
                            VALUES ($1, $2, $3, $4, $5, '{}'::jsonb, $6, 0, 'test')""", teacher_id, TODAY, dom, snap["progressor"]["target"], json.dumps(content), json.dumps(snap))
    try:
        with TestClient(app) as c:
            def observe(items):
                r = c.post(f"/api/review/observed?teacher_id={teacher_id}", json={"session_date": str(TODAY), "items": [{"roll_number": rn, "competency_id": "N2.3.2", "status": st} for rn, st in items]})
                return r.status_code, r.json()

            def coverage(level, channel, domain="numeracy"):
                return c.get(f"/api/review/coverage/{teacher_id}/{TODAY}/{domain}/{level}?channel={channel}").json()

            print("an observed save says what happened to each child")
            st, j = observe([(3, "achieved"), (4, "partially_achieved"), (5, "partially_achieved")])
            check("three first results: all new", st == 200 and (j["new"], j["changed"], j["unchanged"]) == (3, 0, 0) and j["not_found"] == [], j)
            check("...per child, with no previous result", [(r["roll_number"], r["outcome"], r["previous"]) for r in j["results"]] == [(3, "new", None), (4, "new", None), (5, "new", None)], j["results"])
            st, j = observe([(4, "not_achieved"), (5, "partially_achieved"), (3, "achieved")])
            check("the teacher comes back and changes one, re-taps two the same: changed 1, unchanged 2", (j["new"], j["changed"], j["unchanged"]) == (0, 1, 2), j)
            ch = {r["roll_number"]: r for r in j["results"]}
            check("...roll 4 changed from PA to NA (the previous result is given)", ch[4]["outcome"] == "changed" and ch[4]["previous"] == "partially_achieved" and ch[4]["status"] == "not_achieved")
            st, j = observe([(99, "achieved"), (3, "partially_achieved")])
            check("a roll number not in the class is reported, never counted as saved", j["not_found"] == [99] and j["items_recorded"] == 1 and (j["new"], j["changed"]) == (0, 1), j)

            print("\ncoverage carries what was recorded")
            cov = coverage("progressor", "observed")
            check("each child's newest result today, keyed by roll: 3 PA (changed last), 4 NA, 5 PA", cov.get("recorded") == {"3": {"status": "partially_achieved"}, "4": {"status": "not_achieved"}, "5": {"status": "partially_achieved"}}, cov.get("recorded"))
            check("...and still who is done and who is left, as before", cov["analysed_rolls"] == [3, 4, 5] and cov["pending_rolls"] == [])
            check("another group's children are not in it", coverage("beginner", "observed").get("recorded") == {})
            observe([(1, "achieved")])                 # roll 1 is a Beginner, observed on the Progressors' skill
            check("...not even a child of another group with a result on this group's skill (roll 1, a Beginner)", "1" not in coverage("progressor", "observed").get("recorded", {}))
            check("another way of checking (photo) does not show observed results", coverage("progressor", "photo").get("recorded") == {})

            print("\nthe text to read aloud")
            ch = c.get(f"/api/review/channels/{teacher_id}/{TODAY}/r1_literacy").json()
            orf = [l for l in ch["levels"] if l["channel"] == "orf"]
            ps = orf[0].get("passage") if orf else None
            check("a reading-aloud group is given a text to read, with its title, words and word count", bool(ps and ps.get("id") and ps.get("title") and ps.get("text") and ps.get("word_count")), orf[:1])
            grade = await db.fetchval("SELECT target_grade FROM reading_passages WHERE id = $1", ps["id"]) if ps else None
            check("...never one the class read today (RP-004 was the day's passage), and at the skill's grade (L2.5.1: Grade 2)", bool(ps) and ps["id"] != "RP-004" and grade == "grade_2", (ps and ps["id"], grade))
            check("...the same text all day (it rotates by day, not by request)", c.get(f"/api/review/channels/{teacher_id}/{TODAY}/r1_literacy").json()["levels"][0].get("passage", {}).get("id") == ps["id"])
            check("a numeracy plan (no reading aloud) carries no passage", all("passage" not in l for l in c.get(f"/api/review/channels/{teacher_id}/{TODAY}/numeracy").json()["levels"]))
            r = c.post(f"/api/review/orf?teacher_id={teacher_id}", json={"session_date": str(TODAY), "roll_number": 4, "cwpm": 30, "error_count": 2, "competency_id": "L2.5.1"})
            stored = await db.fetchval("""SELECT e.evidence_data->>'passage_id' FROM assessment_evidence e JOIN children c ON c.id = e.child_id
                                          WHERE c.teacher_id = $1 AND c.roll_number = 4 AND e.channel = 'oral_reading'""", teacher_id)
            check("a score with no passage shown is accepted and stores no passage (never a made-up RP-004)", r.status_code == 200 and stored is None, (r.status_code, stored))

            print("\nreading aloud")
            for cwpm, err in ((30, 5), (42, 3)):
                r = c.post(f"/api/review/orf?teacher_id={teacher_id}", json={"session_date": str(TODAY), "roll_number": 3, "passage_id": ps["id"], "cwpm": cwpm, "error_count": err, "competency_id": "L2.5.1"})
                assert r.status_code == 200, r.text
            rec = coverage("progressor", "orf", "r1_literacy").get("recorded", {})
            check("scored twice: the newest entry is shown, with its two numbers (42 correct, 3 errors) and its status", rec.get("3", {}).get("cwpm") == 42 and rec["3"].get("errors") == 3 and rec["3"].get("status"), rec)
    finally:
        await db.execute("DELETE FROM assessment_evidence WHERE teacher_id = $1", teacher_id)
        await db.execute("DELETE FROM daily_plans WHERE teacher_id = $1", teacher_id)
        await _scratch.remove_class(db, teacher_id, school)
        await db.close()
    if failures:
        print(f"\nFAILED ({len(failures)})")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("\nOK: a save says what was new, changed or the same, and the Review can show each child's recorded result")


if __name__ == "__main__":
    asyncio.run(main())
