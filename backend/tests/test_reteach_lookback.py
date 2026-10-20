"""
Re-teaching uses the misconceptions found at the teacher's most recent review. It must look back past a weekend, stay inside one
subject, and never use a review from the same day or from more than a week ago.

    python backend/tests/test_reteach_lookback.py --env-file backend/.env
"""
import asyncio
import json
import sys
from datetime import date, timedelta

import _scratch
from app.services.plan_service import previous_review_feedback

TODAY = date.today()


async def main():
    db = await _scratch.connect()
    teacher_id, school = await _scratch.make_class(db, {1: ("progressor", "progressor"), 2: ("progressor", "progressor")})
    failures = []
    try:
        child = await db.fetchval("SELECT id FROM children WHERE teacher_id = $1 ORDER BY roll_number LIMIT 1", teacher_id)
        num = await db.fetch("SELECT m.id, m.competency_id FROM misconceptions m JOIN competencies c ON c.id = m.competency_id JOIN subdomains s ON s.id = c.subdomain_id WHERE s.domain_id = 'numeracy' ORDER BY m.id LIMIT 3")
        lit = await db.fetch("SELECT m.id, m.competency_id FROM misconceptions m JOIN competencies c ON c.id = m.competency_id JOIN subdomains s ON s.id = c.subdomain_id WHERE s.domain_id = 'r1_literacy' ORDER BY m.id LIMIT 1")
        assert len(num) >= 2 and lit, "the knowledge base needs numeracy and literacy misconceptions"
        m1, m2 = num[0], num[1]

        async def evidence(day_offset, mis, row):
            await db.execute("INSERT INTO assessment_evidence (child_id, competency_id, teacher_id, channel, status, evidence_data, detected_misconception_ids, session_date) "
                             "VALUES ($1, $2, $3, 'written_photo', 'not_achieved', '{}'::jsonb, $4, $5)", child, row["competency_id"], teacher_id, mis, TODAY - timedelta(days=day_offset))

        async def check(label, expected_ids, expected_offset, domain="numeracy"):
            ids, found = await previous_review_feedback(db, teacher_id, domain, TODAY)
            off = (TODAY - found).days if found else None
            ok = sorted(ids) == sorted(expected_ids) and off == expected_offset
            print(f"  {label:<86} -> {sorted(ids)} on day -{off}  {'OK' if ok else 'MISMATCH'}")
            if not ok:
                failures.append(f"{label}: expected {sorted(expected_ids)} at -{expected_offset}, got {sorted(ids)} at -{off}")

        await check("no review at all", [], None)
        await evidence(3, [m1["id"]], m1)                                    # a Friday review; today is Monday
        await check("a review 3 days ago (Friday) feeds a Monday plan", [m1["id"]], 3)
        await evidence(0, [m2["id"]], m2)
        await check("a review the SAME day is not 'previous' (it is today's)", [m1["id"]], 3)
        await evidence(1, [m2["id"]], m2)
        await check("the MOST RECENT review wins (yesterday's, not Friday's)", [m2["id"]], 1)
        ids, found = await previous_review_feedback(db, teacher_id, "r1_literacy", TODAY)
        print(f"  {'numeracy reviews do not leak into a literacy plan':<86} -> {ids} {found}  {'OK' if not ids and not found else 'MISMATCH'}")
        if ids or found:
            failures.append("a numeracy review leaked into a literacy plan")
        await db.execute("DELETE FROM assessment_evidence WHERE teacher_id = $1", teacher_id)
        await evidence(9, [m1["id"]], m1)
        await check("a review 9 days ago is too old (the limit is a week)", [], None)
        await db.execute("DELETE FROM assessment_evidence WHERE teacher_id = $1", teacher_id)
        await evidence(2, None, m1)
        await check("the last review found no misconceptions: nothing to re-teach (the group got it)", [], 2)
        await evidence(5, [m1["id"]], m1)
        await check("...and an older review's gaps are NOT used instead", [], 2)
    finally:
        await _scratch.remove_class(db, teacher_id, school)
        await db.close()
    if failures:
        print("\nFAILED")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("\nOK: the re-teach context comes from the most recent review in the same subject, within a week")


if __name__ == "__main__":
    asyncio.run(main())
