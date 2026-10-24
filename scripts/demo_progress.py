"""
Ankur Saathi — demo data for the Progress screen.

    python scripts/demo_progress.py seed  [--end-date 2026-10-16] [--yes]
    python scripts/demo_progress.py reset [--yes]
    python scripts/demo_progress.py status

  seed    does a reset, then records THREE CONSECUTIVE DAYS of Progressor worksheet evidence for N2.3.2,
          ending on --end-date (default: yesterday). It goes through the same code as a real photo
          (process_vision_results), so statuses, streaks and suggestions are exactly what the app would produce.
          Three qualifying days is what makes the Progress screen show 're-assess' flags; the photos you
          take on the demo day then become day 4.
          It also stores YESTERDAY'S PLAN (the three groups, their children's roll numbers and their skills for N2.3.2) with the decisions the demo teacher
          recorded at that review, so that the Plan screen has a yesterday to suggest from.
  reset   deletes ALL assessment evidence and status rows for the demo teacher and restores every child's
          level to the baseline in db/seeds/classroom/01_profile.sql (so a level change accepted during a
          rehearsal is undone). Stored plans are left alone, except the one that seed stores for the last seeded day (marked demo_seed), which reset removes.
  status  shows what is recorded now and which suggestions the Progress screen would show.

What the seed models (Progressor group, 14 children):
  rolls 4, 14, 18     Achieved on all 3 days            -> suggested: Progressor -> Proficient
  rolls 25, 27        Not achieved on all 3 days        -> suggested: Progressor -> Beginner (with the repeated mistake)
  the other 9         improving, mixed or steady        -> no suggestion yet
The plan tells the teacher to photograph rolls 4, 14, 18 and 25 for the Progressor sheet, so those are the
children the demo story follows.

Requires: pip install asyncpg
"""

import argparse
import asyncio
import json
import os
import random
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "prompts"))
sys.path.insert(0, os.path.dirname(__file__))

import anchor_common as ac
from vision_analysis import check_reassessment_flags, process_vision_results

DEMO_TEACHER = "10000001-aaaa-bbbb-cccc-000000000001"
COMPETENCY = "N2.3.2"
REQUIRED = 6
BASELINE_SQL = Path(__file__).resolve().parent.parent / "db" / "seeds" / "classroom" / "01_profile.sql"
BACKEND = Path(__file__).resolve().parent.parent / "backend"
SAMPLE_PLAN = Path(__file__).resolve().parent.parent / "db" / "seeds" / "sample_plans" / "N2.3.2.json"

# What the demo teacher "recorded" at yesterday's review (the Review screen's Advance / Re-teach / Not sure). The Progressors have NO decision on purpose: the three days of
# evidence recommend a re-teach, so the Plan screen shows the app's OWN recommendation. The Beginners advance, so the screen shows a decision-based suggestion too.
DEMO_DECISIONS = {"beginner": "advance"}

# roll -> (correct answers out of the 6 required, on each of the 3 days; the mistake behind the wrong ones; extras attempted on day 3)
PATTERNS = {
    4:  ([6, 6, 6], None, 2),    # the Progressor peer monitor: secure
    14: ([5, 6, 6], None, 1),    # one careless slip on day 1
    18: ([6, 5, 6], None, 0),    # one careless slip on day 2
    5:  ([3, 4, 5], "M1", 0),
    6:  ([4, 4, 5], "M2", 0),
    7:  ([5, 4, 5], "M3", 0),
    15: ([4, 5, 5], "M1", 0),
    16: ([3, 3, 4], "M1", 0),
    17: ([6, 4, 5], "M2", 0),
    19: ([3, 4, 4], "M2", 0),
    24: ([1, 3, 4], "M1", 0),
    26: ([2, 3, 3], "M1", 0),
    25: ([2, 2, 2], "M1", 0),    # persistent: forgets the carry every day
    27: ([2, 2, 1], "M2", 0),    # persistent: writes the whole ones sum every day
}


# ── problems and wrong answers ──────────────────────────────────────────────

def day_problems(day: date) -> list[tuple[int, int]]:
    """Eight carry-once problems for a day: distinct answers, varied ones sums."""
    rng = random.Random(f"demo-progress:{day.isoformat()}")
    out, answers, ones_used = [], set(), set()
    wanted = [10, 12, 14, 16, 11, 13, 15, 17]
    for want in wanted:
        for _ in range(2000):
            a, b = rng.randint(11, 89), rng.randint(11, 89)
            if a == b or a % 10 == 0 or b % 10 == 0 or a % 10 + b % 10 != want or a // 10 + b // 10 + 1 > 9:
                continue
            if a + b in answers:
                continue
            out.append((a, b)); answers.add(a + b); ones_used.add(want)
            break
    return out


def wrong_answer(kind: str | None, a: int, b: int, rng: random.Random) -> tuple[int, bool | None]:
    """The wrong answer a child with this mistake gives, and whether a carry digit was written."""
    ones, tens = a % 10 + b % 10, a // 10 + b // 10
    if kind == "M1":                       # forgets the carry: answer is 10 short
        return tens * 10 + ones % 10, False
    if kind == "M2":                       # writes the whole ones sum: 3-digit answer such as 512
        return int(f"{tens}{ones}"), False
    if kind == "M3":                       # carries the ones digit instead of the tens digit
        return (tens + ones % 10) * 10 + ones % 10, True
    return a + b + rng.choice([-2, -1, 1, 2]), True        # a careless slip, no pattern


def child_result(roll: int, day: date, day_index: int) -> dict:
    correct_by_day, kind, extras_day3 = PATTERNS[roll]
    n_correct = correct_by_day[day_index]
    probs = day_problems(day)
    rng = random.Random(f"demo-child:{roll}:{day.isoformat()}")
    wrong_idx = set(rng.sample(range(REQUIRED), REQUIRED - n_correct))
    mis_id = f"{COMPETENCY}-{kind}" if kind else None
    flagged = bool(kind) and len(wrong_idx) >= 2        # one wrong answer is a slip; two or more is a pattern
    entries = []
    for i, (a, b) in enumerate(probs, start=1):
        right = a + b
        if i <= REQUIRED:
            if (i - 1) in wrong_idx:
                ans, carry = wrong_answer(kind if len(wrong_idx) >= 2 else None, a, b, rng)
                entry = {"number": i, "problem_hi": f"{a} + {b}", "extracted_answer": str(ans), "correct_answer": str(right),
                         "is_correct": False, "carry_written": carry, "confidence": "high"}
                if flagged:
                    entry.update(diagnosed_misconception=mis_id, diagnosis_reasoning=f"answer {ans} instead of {right}: matches {kind}")
            else:
                entry = {"number": i, "problem_hi": f"{a} + {b}", "extracted_answer": str(right), "correct_answer": str(right),
                         "is_correct": True, "carry_written": True, "confidence": "high"}
        else:
            attempted = day_index == 2 and (i - REQUIRED) <= extras_day3
            entry = {"number": i, "problem_hi": f"{a} + {b}", "extracted_answer": str(right) if attempted else None,
                     "correct_answer": str(right), "is_correct": True if attempted else None, "attempted": attempted,
                     "carry_written": True if attempted else None, "confidence": "high"}
        entries.append(entry)
    attempted_extras = sum(1 for e in entries[REQUIRED:] if e["extracted_answer"])
    total = REQUIRED + attempted_extras
    correct = sum(1 for e in entries if e["is_correct"])
    detected = [{"misconception_id": mis_id, "occurrences": len(wrong_idx), "confidence": "high",
                 "evidence_problems": sorted(i + 1 for i in wrong_idx)}] if flagged else []
    accuracy = round(correct / total, 3)
    label = ("achieved" if accuracy >= 0.80 and not detected else "not_achieved" if accuracy <= 0.40 else "partially_achieved")
    return {"roll_number": roll, "roll_number_confidence": "high", "problems": entries, "demo_seed": True,
            "summary": {"total_problems": total, "correct": correct, "accuracy": accuracy,
                        "overall_status": label, "detected_misconceptions": detected, "needs_verification": []}}


# ── baseline and reset ──────────────────────────────────────────────────────

def read_baseline() -> list[tuple]:
    """(child_id, domain, competency, level, source, evidence_days, last_assessed) from the classroom seed file."""
    text = BASELINE_SQL.read_text(encoding="utf-8")
    pat = re.compile(r"\('([0-9a-f-]{36})',\s*'(numeracy|r1_literacy)',\s*'([A-Z0-9.]+)',\s*'(beginner|progressor|proficient)',"
                     r"\s*'([a-z_]+)',\s*(\d+),\s*'(\d{4}-\d{2}-\d{2})'\)")
    rows = [(m[1], m[2], m[3], m[4], m[5], int(m[6]), date.fromisoformat(m[7])) for m in pat.finditer(text)]
    return rows


async def seed_yesterday_plan(db, teacher_id: str, day: date) -> dict:
    """Store the plan of `day` (the last seeded day) for the demo teacher: each group's children (roll numbers) and skill for COMPETENCY, the way a generated plan keeps them, with the decisions in DEMO_DECISIONS.
    Without it the Plan screen has no 'yesterday' to suggest from and says so. The plan itself is the recorded sample for N2.3.2 (it is yesterday's: nobody opens it). The row is marked `demo_seed`,
    so reset removes it and leaves every real plan alone. A real plan already stored for that date is replaced: the demo must tell the same story each day."""
    sys.path.insert(0, str(BACKEND))
    from app.services import group_skills, plan_service
    groups = {g["label"]: g for g in await plan_service.derive_groups_from_positions(db, teacher_id, "numeracy")}
    ladder = await group_skills.ladder(db, COMPETENCY)
    snapshot = {label: {"count": g["count"], "rolls": g["roll_numbers"], "target": ladder[label]["id"]} for label, g in groups.items()}
    explainability = {"demo_seed": True, **{f"teacher_decision_{label}": d for label, d in DEMO_DECISIONS.items() if label in snapshot}}
    plan = json.loads(SAMPLE_PLAN.read_text(encoding="utf-8"))
    await db.execute("""
        INSERT INTO daily_plans (teacher_id, plan_date, domain_id, selected_competency_id, plan_content, explainability, groups_snapshot)
        VALUES ($1, $2, 'numeracy', $3, $4::jsonb, $5::jsonb, $6::jsonb)
        ON CONFLICT (teacher_id, plan_date, domain_id) DO UPDATE SET selected_competency_id = EXCLUDED.selected_competency_id,
               plan_content = EXCLUDED.plan_content, explainability = EXCLUDED.explainability, groups_snapshot = EXCLUDED.groups_snapshot
    """, teacher_id, day, COMPETENCY, json.dumps(plan, ensure_ascii=False), json.dumps(explainability), json.dumps(snapshot))
    return snapshot


async def counts(db, teacher_id: str) -> dict:
    return {
        "evidence": await db.fetchval("SELECT count(*) FROM assessment_evidence WHERE teacher_id = $1", teacher_id),
        "status": await db.fetchval("SELECT count(*) FROM child_competency_status s JOIN children c ON c.id = s.child_id WHERE c.teacher_id = $1", teacher_id),
    }


async def reset(db, teacher_id: str) -> dict:
    """Delete all evidence and status rows for the teacher and restore every position to the baseline."""
    baseline = read_baseline()
    in_db = await db.fetchval("SELECT count(*) FROM child_lakshya_positions p JOIN children c ON c.id = p.child_id WHERE c.teacher_id = $1", teacher_id)
    if len(baseline) != in_db:        # refuse to guess: the seed file and the database must describe the same class
        sys.exit(f"The baseline file lists {len(baseline)} positions but the database has {in_db} for this teacher. Nothing was changed.")
    before = await counts(db, teacher_id)
    await db.execute("DELETE FROM assessment_evidence WHERE teacher_id = $1", teacher_id)
    await db.execute("DELETE FROM child_competency_status WHERE child_id IN (SELECT id FROM children WHERE teacher_id = $1)", teacher_id)
    plans = await db.execute("DELETE FROM daily_plans WHERE teacher_id = $1 AND explainability ? 'demo_seed'", teacher_id)      # only the plans that seed stored
    restored = 0
    for cid, domain, comp, level, source, days, last in baseline:
        res = await db.execute("""
            UPDATE child_lakshya_positions SET current_competency_id = $3, bpp_level = $4, source = $5, evidence_days = $6,
                   last_assessed = $7, previous_competency_id = NULL, previous_bpp_level = NULL, level_changed_at = NULL, updated_at = NOW()
            WHERE child_id = $1 AND domain_id = $2 AND child_id IN (SELECT id FROM children WHERE teacher_id = $8)
        """, cid, domain, comp, level, source, days, last, teacher_id)
        restored += int(res.split()[-1])
    return {"evidence_deleted": before["evidence"], "status_deleted": before["status"], "positions_restored": restored, "plans_deleted": int(plans.split()[-1])}


# ── commands ────────────────────────────────────────────────────────────────

def confirm(args, message: str):
    if args.yes:
        return
    print(message)
    if input("Type yes to continue: ").strip().lower() != "yes":
        sys.exit("Cancelled. Nothing was changed.")


async def do_seed(db, teacher_id: str, end: date) -> tuple:
    """The whole seed, in the caller's transaction: reset, three days of evidence, and yesterday's plan. Returns (what reset did, the stored groups)."""
    r = await reset(db, teacher_id)
    for i, day in enumerate([end - timedelta(days=2), end - timedelta(days=1), end]):
        vision = [child_result(roll, day, i) for roll in sorted(PATTERNS)]
        await process_vision_results(db, teacher_id, day, COMPETENCY, vision, None, required_count=REQUIRED)
    return r, await seed_yesterday_plan(db, teacher_id, end)


async def cmd_seed(db, args):
    end = date.fromisoformat(args.end_date) if args.end_date else date.today() - timedelta(days=1)
    days = [end - timedelta(days=2), end - timedelta(days=1), end]
    confirm(args, f"This deletes ALL assessment evidence for the demo teacher, restores every child's level to the baseline, "
                  f"then records {days[0]} to {days[2]} for {len(PATTERNS)} Progressors.")
    async with db.transaction():
        r, snap = await do_seed(db, args.teacher_id, end)
    print(f"Reset: {r['evidence_deleted']} evidence rows and {r['status_deleted']} status rows deleted, {r['positions_restored']} positions restored.")
    print(f"Seeded {days[0]} to {days[2]} for {COMPETENCY}. Your photos on {days[2] + timedelta(days=1)} or later become the next day.")
    print(f"Stored the plan of {days[2]}: " + ", ".join(f"{k} {v['count']} children on {v['target']}" for k, v in snap.items()) + f"; decisions recorded: {DEMO_DECISIONS or 'none'}.\n")
    await cmd_status(db, args)


async def cmd_reset(db, args):
    confirm(args, "This deletes ALL assessment evidence and status rows for the demo teacher and restores every child's level to the baseline.")
    async with db.transaction():
        r = await reset(db, args.teacher_id)
    print(f"Deleted {r['evidence_deleted']} evidence rows and {r['status_deleted']} status rows; restored {r['positions_restored']} positions.")


async def cmd_status(db, args):
    c = await counts(db, args.teacher_id)
    print(f"Recorded now: {c['evidence']} evidence rows, {c['status']} status rows.")
    rows = await db.fetch("""
        SELECT ch.roll_number, s.status, s.consecutive_days_at_status AS streak, s.active_misconception_ids AS mis
        FROM child_competency_status s JOIN children ch ON ch.id = s.child_id
        WHERE ch.teacher_id = $1 AND s.competency_id = $2 ORDER BY ch.roll_number""", args.teacher_id, COMPETENCY)
    if rows:
        short = {"achieved": "A", "partially_achieved": "PA", "not_achieved": "NA"}
        print(f"\n{COMPETENCY} status by roll (latest status, streak in days):")
        print("  " + "   ".join(f"{r['roll_number']}:{short[r['status']]}x{r['streak']}" for r in rows))
    recs = await check_reassessment_flags(db, args.teacher_id, "numeracy")
    print(f"\n'Consider re-assessing' flags the Progress screen shows ({len(recs)}). They change no level: only an assessment does.")
    for r in recs:
        word = "doing well" if r["direction"] == "higher" else "struggling "
        print(f"  {word} roll {r['roll_number']:>2}: level {r['level']}, {r['matching_days']} of the last {r['days_counted']} days")
    if not recs:
        print("  none yet (a child needs 3 qualifying days among the last 4, mostly Achieved or mostly Not achieved)")
    await print_suggestions(db, args.teacher_id)


async def print_suggestions(db, teacher_id: str):
    """What the Plan screen would suggest for each group today, from the last plan and the evidence."""
    sys.path.insert(0, str(BACKEND))
    from app.services import group_skills
    rows = await db.fetch("SELECT plan_date, selected_competency_id, plan_content, explainability, groups_snapshot FROM daily_plans WHERE teacher_id = $1 AND domain_id = 'numeracy' AND plan_date >= $2 ORDER BY plan_date DESC",
                          teacher_id, date.today() - timedelta(days=14))
    used = next((r["plan_date"] for r in rows if r["plan_date"] < date.today()), None)
    print(f"\nPlans stored for the last 14 days (the Plan screen takes the latest one BEFORE today, {date.today()}, as 'yesterday'):")
    if not rows:
        print("  none")
    for r in rows:
        j = lambda v: json.loads(v) if isinstance(v, str) else (v or {})
        expl, snap, retaught = j(r["explainability"]), j(r["groups_snapshot"]), group_skills.reteached_groups(r["plan_content"])
        parts = [f"{label} {snap[label].get('target')}" + (" RE-TAUGHT" if label in retaught else "") + (f" [decision {expl.get('teacher_decision_' + label)}]" if expl.get("teacher_decision_" + label) else "") for label in ("beginner", "progressor", "proficient") if label in snap]
        print(f"  {r['plan_date']}  {r['selected_competency_id']:<7} {'seeded by this script' if expl.get('demo_seed') else 'made in the app':<22} " + "; ".join(parts) + ("   <-- 'yesterday'" if r["plan_date"] == used else ""))
    p = await group_skills.propose(db, teacher_id, "numeracy", date.today())
    if not p["has_history"]:
        print("\nThe Plan screen has no earlier plan to suggest from (no plan in the last 14 days): it says so, and derives each group's skill from the skill chosen.")
        return
    print(f"\nWhat the Plan screen suggests today, from the plan of {p['previous_date']}:")
    for label in ("beginner", "progressor", "proficient"):
        g = p["groups"].get(label)
        if not g:
            continue
        ev = g["evidence"]
        saw = f"{ev['with_mistakes']} of {ev['assessed']} assessed made a mistake (needed {ev['needed']})" if ev["assessed"] else "no evidence"
        goes = f"suggests {g['proposed']['id']} ({g['reason']})" if g["proposed"] else "no suggestion: the skill follows the one chosen"
        print(f"  {label:<10} yesterday {g['previous_target']['id']}, decision {g['previous_decision'] or 'none'}; {saw}; {goes}")


async def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["seed", "reset", "status"])
    ap.add_argument("--end-date", help="last seeded day, YYYY-MM-DD (default: yesterday)")
    ap.add_argument("--teacher-id", default=DEMO_TEACHER)
    ap.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    ac.add_db_args(ap)
    args = ap.parse_args()
    db = await ac.connect(args)
    try:
        await {"seed": cmd_seed, "reset": cmd_reset, "status": cmd_status}[args.command](db, args)
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
