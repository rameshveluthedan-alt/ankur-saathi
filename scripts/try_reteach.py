"""
Try the re-teach as the group's MAIN block with the REAL model (about 14 cents), and write what came out to a file a teacher can read.

A scratch class is built (rolls 1-3 Beginners, 4-6 Progressors, 7-8 Proficients), yesterday's photos are given a mistake in the Progressors' skill (rolls 4 and 5), and a plan is generated with the Progressors chosen for
re-teach. Nothing real is touched: the scratch class and plan are removed afterwards.

Run it from the repository root, like the batch tool. It uses backend/.env (your ANTHROPIC_API_KEY and DATABASE_URL), so a real run spends YOUR credits.

    python scripts\\try_reteach.py                                   (N2.3.2, the Progressors re-taught; asks before it spends)
    python scripts\\try_reteach.py --skill N2.3.2 --groups progressor,beginner --yes
    python scripts\\try_reteach.py --groups none --yes               (move on with every group: nothing is re-taught)
    python scripts\\try_reteach.py --stub --yes                      (free: a recorded plan instead of the model, to see the script work)
"""
import argparse
import asyncio
import contextlib
import io
import json
import os
import re
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

LEVELS = {1: "beginner", 2: "beginner", 3: "beginner", 4: "progressor", 5: "progressor", 6: "progressor", 7: "proficient", 8: "proficient"}


async def make_class(db, rs, grade="grade_2"):
    """A scratch teacher with 8 children, one level each. (Not the tests' helper: that one sets a dummy API key, which would override the real one in backend/.env.)"""
    tag = uuid.uuid4().hex[:6]
    school = f"TST-{tag}".upper()
    me = await rs.register_teacher(db, f"hash_tst_{tag}", school, [grade])
    rows = [{"row": i + 2, "grade": grade, "roll": str(r), "name": "", "numeracy": lv, "literacy": lv} for i, (r, lv) in enumerate(sorted(LEVELS.items()))]
    await rs.commit_register(db, me["teacher_id"], rows, "scratch.csv")
    return me["teacher_id"], school


async def remove_class(db, teacher_id, school):
    for sql, arg in (("DELETE FROM ai_usage WHERE school_id IN (SELECT id FROM schools WHERE school_code = $1)", school),):
        try:
            await db.execute(sql, arg)
        except Exception:
            pass
    if teacher_id:
        await db.execute("DELETE FROM assessment_evidence WHERE teacher_id = $1", teacher_id)
        await db.execute("DELETE FROM child_competency_status WHERE child_id IN (SELECT id FROM children WHERE teacher_id = $1)", teacher_id)
        await db.execute("DELETE FROM daily_plans WHERE teacher_id = $1", teacher_id)
        await db.execute("DELETE FROM teachers WHERE id = $1", teacher_id)
    await db.execute("DELETE FROM schools WHERE school_code = $1", school)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill", default="N2.3.2", help="the day's skill (the Progressors' skill)")
    ap.add_argument("--domain", default="numeracy")
    ap.add_argument("--groups", default="progressor", help="groups to re-teach, comma-separated; 'none' to move on with every group")
    ap.add_argument("--stub", action="store_true", help="free: use a recorded plan instead of the model")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--database-url", help="override DATABASE_URL")
    args = ap.parse_args()
    groups = [] if args.groups.strip().lower() == "none" else [g.strip() for g in args.groups.split(",") if g.strip()]

    os.chdir(BACKEND)                                           # the app reads backend/.env from here (this is what the batch tool does)
    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url
    if args.stub:
        os.environ.setdefault("ANTHROPIC_API_KEY", "stub")
    sys.path[:0] = [str(BACKEND), str(ROOT / "prompts")]
    import anthropic
    from app.core import database
    from app.core.config import get_settings
    from app.services import ai_budget, plan_service, register_service as rs
    if not args.stub and not get_settings().anthropic_api_key:
        sys.exit("ANTHROPIC_API_KEY is not set in backend/.env. Use --stub for a dry run.")
    if not args.stub and not args.yes:
        if input(f"This calls the real model once (about 14 cents of YOUR credits) for {args.skill}, re-teaching {groups or 'nobody'}. Type yes to start: ").strip().lower() != "yes":
            sys.exit("Cancelled. Nothing was run.")
    ai_budget.operator_mode()                                   # the team's own run: no daily caps (the total budget and the evaluator reserve still apply), as in the batch tool

    await database.create_pool()
    real_client = anthropic.AsyncAnthropic
    try:
        async with database.get_db() as db:
            teacher_id, school = await make_class(db, rs)
            try:
                if args.stub:
                    sample = json.load(open(ROOT / "db" / "seeds" / "sample_plans" / "N2.3.2.json", encoding="utf-8"))

                    class Fake:
                        async def create(self, **kw):
                            return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(sample, ensure_ascii=False))], stop_reason="end_turn", usage=SimpleNamespace(input_tokens=1, output_tokens=1))
                    anthropic.AsyncAnthropic = lambda **kw: SimpleNamespace(messages=Fake())
                day = date(2031, 2, 1)                          # a far-future plan date, so a real plan is never touched; the photos are dated the day BEFORE it
                kids = {r["roll_number"]: r["id"] for r in await db.fetch("SELECT id, roll_number FROM children WHERE teacher_id = $1", teacher_id)}
                mis = await db.fetch("SELECT id, competency_id, name_hi FROM misconceptions WHERE competency_id = $1 ORDER BY id", args.skill)
                if not mis:
                    print(f"No recorded mistakes for {args.skill}: the re-teach will use the skill's commonest mistakes.")
                else:
                    for roll in (4, 5):                         # two Progressors made the skill's first recorded mistake, yesterday
                        await db.execute("INSERT INTO assessment_evidence (child_id, competency_id, teacher_id, channel, status, evidence_data, detected_misconception_ids, session_date) "
                                         "VALUES ($1, $2, $3, 'written_photo', 'not_achieved', '{}'::jsonb, $4, $5)", kids[roll], args.skill, teacher_id, [mis[0]["id"]], day - timedelta(days=1))
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    await plan_service.generate_dainik_yojana(db, teacher_id, args.skill, args.domain, day, reteach_groups=groups)
                log = buf.getvalue()
                row = await db.fetchrow("SELECT plan_content FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2", teacher_id, day)
                plan = json.loads(row["plan_content"]) if isinstance(row["plan_content"], str) else row["plan_content"]
                out = [f"# Re-teach as the group's main block: {args.skill}", "", f"Re-teach chosen for: {', '.join(groups) or 'nobody (move on with every group)'}. "
                       f"Yesterday two Progressors (rolls 4 and 5) made the mistake {mis[0]['id'] + ' ' + (mis[0]['name_hi'] or '') if mis else '(none recorded)'}.", ""]
                for b in plan["rotation_schedule"]["blocks"]:
                    if b.get("type") not in ("teach", "reteach"):
                        continue
                    tp = b.get("talking_points") or {}
                    tag = "RE-TEACH" if b.get("reteach") else ("SEPARATE RE-TEACH BLOCK (not wanted)" if b["type"] == "reteach" else "teach")
                    out += [f"## {b.get('teach_group')}: {tag} ({b.get('duration_minutes')} min)", ""]
                    if b.get("reteach"):
                        out += [f"Children who made the mistake (stamped by the code): {b.get('affected_rolls')}", f"Mistakes: {json.dumps(b.get('reteach_mistakes'), ensure_ascii=False)}", ""]
                    for k, label in (("i_do_hi", "I Do"), ("we_do_hi", "We Do"), ("you_do_hi", "You Do")):
                        out += [f"**{label}:** {tp.get(k)}", ""]
                    out += [f"**The other groups meanwhile:** {b.get('other_groups_hi')}", ""]
                    for i, q in enumerate(b.get("cfu") or [], 1):
                        out += [f"- Show-me {i} [{q.get('kind')}]: {q.get('question_hi')}  ->  {q.get('expected_hi')}"] + [f"    - listen for: {x.get('wrong_answer_hi')} ({x.get('misconception_name_hi') or x.get('misconception_id')})" for x in q.get("listen_for") or []]
                    out.append("")
                warn = [l.strip() for l in log.splitlines() if "WARNING" in l or l.strip().startswith("- ")]
                out += ["## What the program noted", "", *[f"- {l}" for l in (warn or ["Plan shape OK"])], ""]
                text = "\n".join(out)
                dest = ROOT / "docs" / "batch" / f"try_reteach_{args.skill}.md"
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(text, encoding="utf-8")
                print(text)
                print(f"\nWritten to {dest}")
                usage = re.findall(r"usage=([^\n]+)", log)
                if usage:
                    print("Model usage:", usage[0][:140])
            finally:
                anthropic.AsyncAnthropic = real_client
                await remove_class(db, teacher_id, school)
                print("Scratch class and plan removed.")
    finally:
        await database.close_pool()


if __name__ == "__main__":
    asyncio.run(main())
