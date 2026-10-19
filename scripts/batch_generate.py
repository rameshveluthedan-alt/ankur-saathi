"""
Ankur Saathi — real-model batch test.

Runs the SAME pipeline the app uses (retrieval, the model, the automatic repairs, the validator, the worksheet renderer)
for every skill, one after another, and records what happened. The result tells us which skills are safe to show a juror,
and gives the evaluation numbers for the deck.

    python scripts/batch_generate.py --limit 3                      # a first, cheap try on 3 skills
    python scripts/batch_generate.py --domain numeracy               # all 53 numeracy skills
    python scripts/batch_generate.py                                 # all 101 skills (about 2 hours, about $13)
    python scripts/batch_generate.py --only N2.3.2,L2.6.1 --redo     # run named skills again
    python scripts/batch_generate.py --stub --limit 4 --yes          # a dry run with a FAKE model: no key, no cost

It uses backend/.env (your ANTHROPIC_API_KEY and DATABASE_URL), so it spends YOUR credits. It asks before it starts,
stops when the estimated spend reaches --max-cost, and can be interrupted and resumed: skills already recorded as ok are skipped.
Plans are written under far-future dates so they never touch your real plans, and are deleted afterwards (--keep-plans keeps them).

Output: docs/batch/batch_results.csv (one row per skill). Then run: python scripts/build_coverage.py
"""

import argparse
import asyncio
import contextlib
import csv
import io
import json
import os
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
DEMO_TEACHER = "10000001-aaaa-bbbb-cccc-000000000001"
FIELDS = ["competency_id", "domain", "grade", "status", "error", "seconds", "input_tokens", "output_tokens", "repair_input_tokens",
          "repair_output_tokens", "est_cost_usd", "warnings_after", "warnings", "stick_repairs", "worksheet_repairs",
          "anchor_id", "anchor_match", "passage_match", "render_ok", "generated_at"]


def domain_of(cid: str) -> str:
    return "numeracy" if cid.startswith("N") else "r1_literacy"


# ── a fake model for dry runs ───────────────────────────────────────────────

def stub_plan(domain: str, prompt: str) -> dict:
    anchor = {k: "x" for k in ("narration_hi", "opening_question_hi", "closing_question_hi",
                               "beginner_participation_hi", "progressor_participation_hi", "proficient_participation_hi")}
    titles = re.findall(r'"([^"]+)" \((RP-\d+)\)', prompt.split("INDEPENDENT-PRACTICE PASSAGES")[-1]) if "INDEPENDENT-PRACTICE PASSAGES" in prompt else []
    others = " ".join(f"{t[0]} ({t[1]})" for t in titles)
    blocks = [{"type": "teach", "duration_minutes": 22, "teach_group": g, "other_groups_hi": others,
               "talking_points": {"i_do_hi": "पढ़कर दिखाएँ", "we_do_hi": "साथ में करें", "you_do_hi": "खुद करें"}} for g in ("beginner", "progressor", "proficient")]
    if domain == "numeracy":
        pairs = [(21, 14), (32, 15), (23, 16), (54, 23), (35, 12), (61, 28), (72, 17), (46, 33)]
        pr = [(a, b) for a, b in [(36, 27), (48, 35), (54, 26), (19, 43), (67, 28), (29, 17), (25, 38), (15, 47)]]
        pf = [(192, 641), (356, 287), (129, 463), (475, 238), (367, 156), (284, 419), (258, 367), (435, 289)]
        mk = lambda lst: [{"number": i, "problem_hi": f"{a} + {b}", "answer": str(a + b)} for i, (a, b) in enumerate(lst, 1)]
        ws = {"beginner": {"problems": mk(pairs), "required_count": 5}, "progressor": {"problems": mk(pr), "required_count": 6},
              "proficient": {"problems": mk(pf), "required_count": 8}}
    else:
        q = lambda n, t: {"number": n, "problem_hi": t, "answer": "उत्तर", "row_type": None, "answer_type": "lines"}
        sheet = lambda: {"instructions_hi": "पढ़ो", "required_count": 3, "passage_block": {"title": "x", "text": "y"},
                         "problems": [q(1, "पहला सवाल क्या है?"), q(2, "दूसरा सवाल क्या है?"), q(3, "तीसरा सवाल क्या है?")]}
        ws = {"beginner": {"instructions_hi": "सुनो", "required_count": 1, "problems": [q(1, "कौन था?")], "example_block": {"problem_hi": "क"}},
              "progressor": sheet(), "proficient": sheet()}
    return {"anchor": anchor, "prep_hi": ["चार्ट पेपर"], "rotation_schedule": {"blocks": blocks}, "worksheets": ws,
            "explainability": {"items": [{"title_hi": "t", "title_en": "t", "body_hi": "b", "body_en": "b"}]}}


def install_stub(plan_service):
    class FM:
        async def create(self, **kw):
            prompt = kw["messages"][0]["content"]
            domain = "r1_literacy" if "FIXED READING PASSAGES" in prompt else "numeracy"
            return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(stub_plan(domain, prompt), ensure_ascii=False))],
                                   stop_reason="end_turn", usage="Usage(input_tokens=9000, output_tokens=9500)")
    class FC:
        def __init__(self, **kw): self.messages = FM()
    plan_service.anthropic.AsyncAnthropic = FC


# ── one skill ───────────────────────────────────────────────────────────────

async def run_one(database, plan_service, worksheet_service, fetch_anchor_activity, comp, plan_date, teacher_id, args) -> dict:
    cid, grade, domain = comp["id"], comp["grade_level"], domain_of(comp["id"])
    row = {k: "" for k in FIELDS}
    row.update(competency_id=cid, domain=domain, grade=grade, generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    buf, t0 = io.StringIO(), time.time()
    async with database.get_db() as db:
        try:
            with contextlib.redirect_stdout(buf):
                res = await plan_service.generate_dainik_yojana(db, teacher_id, cid, domain, plan_date)
            row["status"] = "ok"
            warns = list(res.get("validation_warnings") or [])
        except Exception as e:                                    # a failed skill is a result, not a crash
            row["status"], row["error"], warns = "error", f"{type(e).__name__}: {e}"[:300], []
        row["seconds"] = round(time.time() - t0, 1)
        out = buf.getvalue()
        main_in = main_out = rep_in = rep_out = 0
        for line in out.splitlines():
            m = re.search(r"input_tokens=(\d+), output_tokens=(\d+)", line)
            if not m:
                continue
            if line.strip().startswith("Stick repair call"):
                rep_in += int(m.group(1)); rep_out += int(m.group(2))
            elif line.strip().startswith("Claude:"):
                main_in += int(m.group(1)); main_out += int(m.group(2))
        row.update(input_tokens=main_in, output_tokens=main_out, repair_input_tokens=rep_in, repair_output_tokens=rep_out,
                   est_cost_usd=round((main_in + rep_in) * args.price_in / 1e6 + (main_out + rep_out) * args.price_out / 1e6, 4),
                   warnings_after=len(warns), warnings=" | ".join(w[:140] for w in warns),
                   stick_repairs=sum(1 for l in out.splitlines() if l.strip().startswith("Stick repair:") and ("rewritten" in l or "replaced in code" in l)),
                   worksheet_repairs=sum(1 for l in out.splitlines() if l.strip().startswith("Worksheet repair:") and "NOTE" not in l))
        # what the knowledge base offered for this skill
        a = await fetch_anchor_activity(db, domain, grade, cid)
        row["anchor_id"], row["anchor_match"] = (a.id, a.match_quality) if a else ("", "none")
        if domain == "r1_literacy":
            gp = await plan_service.retrieve_group_passages(db, domain, {"progressor": cid}, plan_date)
            row["passage_match"] = (gp.get("progressor") or {}).get("match", "none")
        else:
            row["passage_match"] = "n/a"
        # can the three worksheets be rendered from the stored plan?
        row["render_ok"] = "no"
        if row["status"] == "ok":
            try:
                stored = await db.fetchrow("SELECT plan_content, groups_snapshot FROM daily_plans WHERE teacher_id=$1 AND plan_date=$2 AND domain_id=$3",
                                           teacher_id, plan_date, domain)
                plan_data = stored["plan_content"] if isinstance(stored["plan_content"], dict) else json.loads(stored["plan_content"])
                snap = stored["groups_snapshot"]; snap = json.loads(snap) if isinstance(snap, str) else (snap or {})
                ok = True
                for level in ("beginner", "progressor", "proficient"):
                    target = (snap.get(level) or {}).get("target") or cid
                    c = await db.fetchrow("SELECT name_hi, name_en FROM competencies WHERE id=$1", target)
                    html = worksheet_service.render_worksheet(plan_data=plan_data, level=level, competency_id=target,
                                                              competency_name_hi=c["name_hi"] if c else target,
                                                              competency_name_en=c["name_en"] if c else "", domain_id=domain, plan_date=str(plan_date))
                    ok = ok and len(html) > 2000
                row["render_ok"] = "yes" if ok else "no"
            except Exception as e:
                row["render_ok"] = "no"
                row["error"] = (row["error"] + f" render: {type(e).__name__}: {e}")[:300]
    return row


async def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", help="comma-separated skill ids")
    ap.add_argument("--domain", choices=["numeracy", "r1_literacy"], help="only this subject")
    ap.add_argument("--limit", type=int, help="only the first N skills (after the other filters)")
    ap.add_argument("--redo", action="store_true", help="run skills again even if already recorded as ok")
    ap.add_argument("--max-cost", type=float, default=25.0, help="stop when the estimated spend reaches this many USD (default 25)")
    ap.add_argument("--price-in", type=float, default=2.0, help="assumed USD per million input tokens (an estimate; default 2)")
    ap.add_argument("--price-out", type=float, default=10.0, help="assumed USD per million output tokens (an estimate; default 10)")
    ap.add_argument("--out", default=str(ROOT / "docs" / "batch" / "batch_results.csv"))
    ap.add_argument("--teacher-id", default=DEMO_TEACHER)
    ap.add_argument("--start-date", default="2031-01-01", help="first scratch plan date (far in the future, so real plans are never touched)")
    ap.add_argument("--keep-plans", action="store_true", help="keep the generated plans in the database")
    ap.add_argument("--stub", action="store_true", help="use a FAKE model: a dry run that costs nothing and needs no key")
    ap.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    ap.add_argument("--database-url", help="override DATABASE_URL")
    args = ap.parse_args()

    os.chdir(BACKEND)                                           # the app reads backend/.env from here
    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url
    if args.stub:
        os.environ.setdefault("ANTHROPIC_API_KEY", "stub")
    sys.path[:0] = [str(BACKEND), str(ROOT / "prompts")]
    from app.core import database
    from app.core.config import get_settings
    from app.services import plan_service, worksheet_service
    from orchestrate import fetch_anchor_activity
    if not args.stub and not get_settings().anthropic_api_key:
        sys.exit("ANTHROPIC_API_KEY is not set in backend/.env. Use --stub for a dry run.")
    if args.stub:
        install_stub(plan_service)

    await database.create_pool()
    async with database.get_db() as db:
        comps = [dict(r) for r in await db.fetch("SELECT id, grade_level FROM competencies WHERE is_active ORDER BY (id LIKE 'L%'), grade_level, sort_order, id")]
    if args.only:
        want = {x.strip() for x in args.only.split(",")}
        comps = [c for c in comps if c["id"] in want]
    if args.domain:
        comps = [c for c in comps if domain_of(c["id"]) == args.domain]
    out_path = Path(args.out)
    done = set()
    if out_path.exists() and not args.redo:
        done = {r["competency_id"] for r in csv.DictReader(out_path.open(encoding="utf-8")) if r["status"] == "ok"}
    todo = [c for c in comps if c["id"] not in done]
    if args.limit:
        todo = todo[:args.limit]
    if not todo:
        print("Nothing to do: every selected skill is already recorded as ok (use --redo to run again).")
        await database.close_pool()
        return
    est = len(todo) * 0.13
    print(f"{len(todo)} skill(s) to run ({len(comps) - len(todo)} skipped). Model: {'FAKE (stub)' if args.stub else get_settings().claude_model}.")
    print(f"Estimated cost {'$0 (stub)' if args.stub else f'about ${est:.0f} (12 to 14 cents each)'}; about {len(todo) * (0 if args.stub else 70) / 3600:.1f} hours; results go to {out_path}")
    if not args.yes and not args.stub:
        if input("This spends your Anthropic credits. Type yes to start: ").strip().lower() != "yes":
            sys.exit("Cancelled. Nothing was run.")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not out_path.exists()
    start = date.fromisoformat(args.start_date)
    spent, ok_n, rows = 0.0, 0, []
    with out_path.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if new_file:
            w.writeheader()
        for i, comp in enumerate(todo):
            if spent >= args.max_cost:
                print(f"Stopped: the estimated spend ${spent:.2f} reached --max-cost ${args.max_cost:.2f}. Run again to resume.")
                break
            row = await run_one(database, plan_service, worksheet_service, fetch_anchor_activity, comp, start + timedelta(days=i), args.teacher_id, args)
            w.writerow(row); fh.flush()
            rows.append(row); spent += float(row["est_cost_usd"] or 0)
            flag = "ok " if row["status"] == "ok" and not row["warnings_after"] and row["render_ok"] == "yes" else "!! "
            print(f"  {flag}{row['competency_id']:<8} {row['seconds']:>6}s  ${row['est_cost_usd']}  warnings={row['warnings_after']}  repairs={row['stick_repairs']}+{row['worksheet_repairs']}  anchor={row['anchor_match']}  {row['error'][:60]}")
            ok_n += row["status"] == "ok"
    if not args.keep_plans:
        async with database.get_db() as db:
            n = await db.fetchval("WITH d AS (DELETE FROM daily_plans WHERE teacher_id=$1 AND plan_date >= $2 AND plan_date < $3 RETURNING 1) SELECT count(*) FROM d",
                                  args.teacher_id, start, start + timedelta(days=len(todo) + 1))
        print(f"Removed {n} scratch plans from the database.")
    await database.close_pool()
    clean = sum(1 for r in rows if r["status"] == "ok" and not r["warnings_after"] and r["render_ok"] == "yes")
    print(f"\nDone: {len(rows)} run, {ok_n} generated, {clean} fully clean (no warnings, worksheets render), estimated spend ${spent:.2f}.")
    bad = [r for r in rows if not (r["status"] == "ok" and not r["warnings_after"] and r["render_ok"] == "yes")]
    for r in bad:
        print(f"  needs a look: {r['competency_id']}: {r['error'] or r['warnings'][:140] or 'worksheets did not render'}")
    print("Next: python scripts/build_coverage.py")


if __name__ == "__main__":
    asyncio.run(main())
