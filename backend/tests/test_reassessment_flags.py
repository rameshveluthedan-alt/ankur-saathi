"""
Levels change only through an assessment. Daily results can only raise a "consider re-assessing" flag, and only under these rules
(docs/LEVELS.md). This registers a scratch class, gives each child a pattern of daily evidence, and checks every flag.

    python backend/tests/test_reassessment_flags.py --env-file backend/.env

Needs the database with db/schema/07_register.sql loaded. It cleans up after itself.
"""
import asyncio
import json
import sys
from datetime import date, datetime, time, timedelta, timezone

import _scratch
from vision_analysis import check_reassessment_flags

TODAY = date.today()


async def main():
    db = await _scratch.connect()
    levels = {1: "beginner", 2: "beginner", **{r: "progressor" for r in range(3, 15)}, **{r: "proficient" for r in range(15, 19)}}
    teacher_id, school = await _scratch.make_class(db, {r: (lv, lv) for r, lv in levels.items()})
    failures = []
    try:
        comp = [r["id"] for r in await db.fetch("SELECT c.id FROM competencies c JOIN subdomains s ON s.id = c.subdomain_id WHERE s.domain_id = 'numeracy' AND (c.id LIKE 'N2.%' OR c.id LIKE 'N3.%') ORDER BY c.id LIMIT 10")]
        other = await db.fetchval("SELECT c.id FROM competencies c JOIN subdomains s ON s.id = c.subdomain_id WHERE s.domain_id = 'numeracy' AND c.id LIKE 'N1.1.%' ORDER BY c.id LIMIT 1")
        ids = {r["roll_number"]: r["id"] for r in await db.fetch("SELECT id, roll_number FROM children WHERE teacher_id = $1", teacher_id)}
        # a class registered today counts as assessed today; this class was registered long ago, so all the evidence below is "after" its levels were set
        await db.execute("UPDATE child_lakshya_positions SET last_assessed = now() - interval '60 days' WHERE child_id = ANY($1::uuid[])", list(ids.values()))
        by = lambda lv: sorted(r for r, l in levels.items() if l == lv)
        # five school days of stored plans (days 1..5 ago), a DIFFERENT group skill each day: prerequisite / today's skill / extension
        for d in range(1, 6):
            snap = {"beginner": {"rolls": by("beginner"), "target": comp[d - 1]}, "progressor": {"rolls": by("progressor"), "target": comp[d]},
                    "proficient": {"rolls": by("proficient"), "target": comp[d + 1]}}
            await db.execute("""INSERT INTO daily_plans (teacher_id, plan_date, domain_id, selected_competency_id, plan_content, explainability, groups_snapshot)
                                VALUES ($1, $2, 'numeracy', $3, '{}'::jsonb, '{}'::jsonb, $4::jsonb)""", teacher_id, TODAY - timedelta(days=d), comp[d], json.dumps(snap))
        target = lambda roll, d: comp[d - 1] if levels[roll] == "beginner" else comp[d] if levels[roll] == "progressor" else comp[d + 1]

        async def ev(roll, days_status, problems=8, skill=None, same_skill=None):
            """days_status: {days_ago: status}. By default the evidence is on that day's skill for the child's group."""
            for d, status in days_status.items():
                comp_id = skill or same_skill or target(roll, d) if d <= 5 else (skill or same_skill or comp[0])
                data = {"summary": {"total_problems": problems if not isinstance(problems, dict) else problems.get(d, 8)}, "scoring": {"accuracy": 0.9 if status == "achieved" else 0.2}}
                await db.execute("INSERT INTO assessment_evidence (child_id, competency_id, teacher_id, channel, status, evidence_data, session_date) VALUES ($1, $2, $3, 'written_photo', $4, $5::jsonb, $6)",
                                 ids[roll], comp_id, teacher_id, status, json.dumps(data), TODAY - timedelta(days=d))
        A, N, P = "achieved", "not_achieved", "partially_achieved"
        cases = {   # roll: (the pattern, expected flag or None)
            1: ("Beginner: achieved 4 days, a different prerequisite each day", "higher"),
            2: ("Beginner: not achieved 4 days (already the lowest level)", None),
            3: ("Progressor: achieved 5 days, a different skill each day", "higher"),
            4: ("Progressor: not achieved 5 days, a different skill each day", "lower"),
            5: ("Progressor: A, A, NA, A (3 of 4)", "higher"),
            6: ("Progressor: A, NA, A, NA (2 of 4)", None),
            7: ("Progressor: only 2 days of evidence", None),
            8: ("Progressor: achieved 3 days, but 18 days ago", None),
            9: ("Progressor: A, A, a thin sheet (3 problems), A", "higher"),
            10: ("Progressor: A, A, then two thin sheets (2 usable days)", None),
            11: ("Progressor: achieved 4 days on a skill NO group worked on", None),
            12: ("Progressor: achieved 3 days on the SAME skill, on dates with no stored plan", "higher"),
            13: ("Progressor: achieved 3 days, then re-assessed yesterday (evidence is older than the assessment)", None),
            14: ("Progressor: partially achieved 4 days (neither achieved nor missed)", None),
            15: ("Proficient: not achieved the NEW extension 4 days", None),
            16: ("Proficient: achieved the extension 4 days", None),
        }
        await ev(1, {4: A, 3: A, 2: A, 1: A}); await ev(2, {4: N, 3: N, 2: N, 1: N})
        await ev(3, {5: A, 4: A, 3: A, 2: A, 1: A}); await ev(4, {5: N, 4: N, 3: N, 2: N, 1: N})
        await ev(5, {4: A, 3: A, 2: N, 1: A}); await ev(6, {4: A, 3: N, 2: A, 1: N}); await ev(7, {2: A, 1: A})
        await ev(8, {20: A, 19: A, 18: A}, same_skill=comp[0])
        await ev(9, {4: A, 3: A, 2: A, 1: A}, problems={2: 3}); await ev(10, {4: A, 3: A, 2: A, 1: A}, problems={2: 3, 1: 3})
        await ev(11, {4: A, 3: A, 2: A, 1: A}, skill=other)
        await ev(12, {12: A, 11: A, 10: A}, same_skill=comp[1])
        await ev(13, {4: A, 3: A, 2: A})
        await db.execute("UPDATE child_lakshya_positions SET last_assessed = $2 WHERE child_id = $1 AND domain_id = 'numeracy'", ids[13],
                         datetime.combine(TODAY - timedelta(days=1), time(12, 0), tzinfo=timezone.utc))
        await ev(14, {4: P, 3: P, 2: P, 1: P}); await ev(15, {4: N, 3: N, 2: N, 1: N}); await ev(16, {4: A, 3: A, 2: A, 1: A})
        flags = {f["roll_number"]: f for f in await check_reassessment_flags(db, teacher_id, "numeracy", TODAY)}
        print(f"{'roll':<5}{'level':<11}{'pattern':<92}{'expected':<9}{'got':<9}")
        for roll, (what, expect) in cases.items():
            got = flags[roll]["direction"] if roll in flags else None
            ok = got == expect
            if not ok:
                failures.append(f"roll {roll} ({what}): expected {expect}, got {got}")
            print(f"{roll:<5}{levels[roll]:<11}{what:<92}{str(expect):<9}{str(got):<9}{'' if ok else '  <-- MISMATCH'}")
        print("\n   an example flag:", flags[3]["evidence_hi"][:150], "...")
        print("   it carries no accept or level change:", not any(k in flags[3] for k in ("accept", "to_level", "from_level")))
        # a flag changes nothing: the level is exactly as it was
        after = await db.fetchval("SELECT bpp_level FROM child_lakshya_positions WHERE child_id = $1 AND domain_id = 'numeracy'", ids[3])
        if after != "progressor":
            failures.append("computing a flag changed a level")
        # evidence from another subject must not count
        lit = await check_reassessment_flags(db, teacher_id, "r1_literacy", TODAY)
        if lit:
            failures.append("numeracy evidence produced a literacy flag")
    finally:
        await _scratch.remove_class(db, teacher_id, school)
        await db.close()
    if failures:
        print("\nFAILED")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("\nOK: flags appear only under the stated rules, and a flag changes no level")


if __name__ == "__main__":
    asyncio.run(main())
