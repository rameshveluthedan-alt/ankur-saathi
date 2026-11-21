"""
Generate the recorded-block library (docs/drafts/BLOCK_LIBRARY_PLAN.md): teach and re-teach blocks, independent activities, anchor settings and
anchor tasks. Every piece passes the app's own checks; one JSON file per piece under db/seeds/library/<kind>/ and db/seeds/library/MANIFEST.json.

    cd backend
    # the keys and one prompt, with no call:
    venv/Scripts/python.exe ../scripts/generate_library.py --env-file .env --pilot --kinds teach --dry-run
    # normal calls (REAL, billed: only with the project lead's OK; Opus 5.5 by default):
    AI_ENABLED=true venv/Scripts/python.exe ../scripts/generate_library.py --env-file .env --pilot --kinds independent --max-usd 1
    # the full run at half price (Message Batches): submit, then collect when it has ended (it can take hours; run collect again until done):
    AI_ENABLED=true venv/Scripts/python.exe ../scripts/generate_library.py --env-file .env --all --kinds teach,reteach --batch-submit --max-usd 40
    AI_ENABLED=true venv/Scripts/python.exe ../scripts/generate_library.py --env-file .env --batch-collect --max-usd 40
    # the checks again on every stored piece (no AI):
    venv/Scripts/python.exe ../scripts/generate_library.py --env-file .env --recheck

Kinds: teach, reteach (one per recorded mistake), independent (2 per skill), setting (anchor settings, per subject; --themes limits them),
tasks (each skill's tasks in 3 settings; needs the settings first). A stopped run is started again: pieces already 'ok' are skipped. A piece that
fails the checks is asked for again ONCE with the reasons, then marked 'failed_checks' for a person. Every call is metered (kind 'library').
"""
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")
import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "prompts"), str(ROOT / "scripts")]

PILOT = ["N0.1.1", "N2.2.1", "N2.3.2", "L2.3.1", "L2.5.1", "L2.7.2", "N2.3.1", "N3.3.1", "L1.7.3", "L3.5.1"]
KINDS = ("teach", "reteach", "independent", "setting", "tasks")
# USD per million tokens: (input, output, cache read, cache write). The claude-api reference, Nov 2026; cache write assumed 1.25x input.
PRICES = {"claude-opus-5-5": (4.0, 20.0, 0.20, 5.0), "claude-sonnet-5-5": (2.0, 10.0, 0.10, 2.5), "claude-haiku-5-5": (0.10, 0.50, 0.01, 0.125)}
MAX_TOKENS = {"claude-opus-5-5": 20000}
BATCH_DISCOUNT = 0.5


def cost_of(model: str, usage) -> float:
    p_in, p_out, p_cr, p_cw = PRICES.get(model, PRICES["claude-sonnet-5-5"])
    g = (lambda k: (usage.get(k) if isinstance(usage, dict) else getattr(usage, k, 0)) or 0)
    return (g("input_tokens") * p_in + g("output_tokens") * p_out + g("cache_read_input_tokens") * p_cr + g("cache_creation_input_tokens") * p_cw) / 1e6


def pace_for(length: str):
    from session_shape import FIXED_LAYOUTS, pace_plan, pace_text
    from app.services.library_pieces import LENGTHS
    m = LENGTHS[length]
    fixed = {mins: pace for mins, pace, _ in FIXED_LAYOUTS[45]["slots"]}
    return pace_text(fixed.get(m) or pace_plan(m))


def load_manifest(root: Path) -> dict:
    f = root / "MANIFEST.json"
    man = json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {"format": 1, "pieces": {}}
    man.setdefault("batches", [])
    return man


def save_manifest(root: Path, man: dict) -> None:
    root.mkdir(parents=True, exist_ok=True)
    tmp = root / "MANIFEST.json.tmp"
    tmp.write_text(json.dumps(man, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    tmp.replace(root / "MANIFEST.json")              # never a half-written manifest


async def skill_facts(db, skill_id: str):
    from orchestrate import fetch_competency, fetch_misconceptions
    from cfu_prompt import rank_mistakes
    from dataclasses import asdict
    c = await fetch_competency(db, skill_id)
    domain = await db.fetchval("SELECT s.domain_id FROM competencies c JOIN subdomains s ON s.id = c.subdomain_id WHERE c.id = $1", skill_id)
    skill = {**asdict(c), "domain_id": domain}
    mistakes = rank_mistakes([asdict(m) for m in await fetch_misconceptions(db, skill_id)], {})
    return skill, mistakes


# ── a job: one piece to make ─────────────────────────────────────────────────

class Job:
    """One piece: its kind and key, the request (the app's cached system rules + the piece prompt), and its check."""

    def __init__(self, kind, key, domain, prompt, check, skill=None, length=None, mode="normal", extra=None):
        self.kind, self.key, self.domain, self.prompt, self.check = kind, key, domain, prompt, check
        self.skill, self.length, self.mode, self.extra = skill, length, mode, extra or {}

    def system(self):
        from orchestrate import build_system_blocks
        return build_system_blocks(self.domain, cfu=True)

    def pversion(self):
        from app.services import library_pieces as lp
        return lp.prompt_version(self.system()[0]["text"], self.prompt(None)[-1500:])


def teach_job(skill, mistakes, length, plan_service, reteach=None):
    from app.services import library_pieces as lp, writing_sheets
    rules = writing_sheets.prompt_section({lp.GROUP: skill["id"]}, skill["domain_id"])
    key = lp.reteach_key(reteach["id"], length) if reteach else lp.teach_key(skill["id"], length)
    return Job("reteach" if reteach else "teach", key, skill["domain_id"],
               lambda reasons: lp.teach_prompt(skill, mistakes, length, pace_for(length), rules, reasons, reteach=reteach),
               lambda content: lp.check_teach_piece(content, skill, mistakes, length, plan_service, reteach=reteach),
               skill=skill, length=length, mode=reteach["id"] if reteach else "normal")


def independent_job(skill, variant):
    from app.services import library_parts as lpp
    return Job("independent", lpp.independent_key(skill["id"], variant), skill["domain_id"],
               lambda reasons: lpp.independent_prompt(skill, variant, reasons), lambda content: lpp.check_independent_piece(content, skill),
               skill=skill, mode=f"variant {variant}")


def setting_job(domain, theme):
    from app.services import library_parts as lpp
    return Job("setting", lpp.setting_key(domain, theme), domain, lambda reasons: lpp.setting_prompt(domain, theme, reasons),
               lambda content: lpp.check_setting_piece(content), mode=theme)


def tasks_job(skill, settings):
    from app.services import library_parts as lpp
    return Job("tasks", lpp.tasks_key(skill["domain_id"], skill["id"]), skill["domain_id"],
               lambda reasons: lpp.tasks_prompt(skill, settings, 3, reasons), lambda content: lpp.check_tasks_piece(content, skill, settings, 3),
               skill=skill, extra={"settings": sorted(settings)})


def settings_of(root: Path, domain: str) -> dict:
    """The anchor settings already made (status ok) for a subject: {key: content}."""
    man = load_manifest(root)
    out = {}
    for f in sorted((root / "setting").glob(f"{domain}__*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        if man["pieces"].get(rec["key"], {}).get("status") == "ok":
            out[rec["key"]] = rec["content"]
    return out


def write_piece(root: Path, man: dict, job: Job, content, result, model: str, cost: float, reasons=None) -> str:
    from app.services import library_pieces as lp
    status = "ok" if result and result["ok"] else "failed_checks"
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pversion = job.pversion()
    if content is not None:
        rec = {"format": lp.FORMAT_VERSION, "piece": job.kind, "key": job.key, "skill_id": (job.skill or {}).get("id"), "domain_id": job.domain,
               "mode": job.mode, "length": job.length, "minutes": lp.LENGTHS.get(job.length) if job.length else None, "content": content,
               "checks": result or {"ok": False, "fatal": reasons}, "model": model, "prompt_version": pversion, "created": created,
               "cost_usd": round(cost, 4), "review_status": "ai_drafted", "reviewed_by": None, "review_notes": None, **job.extra}
        f = lp.piece_path(root, job.kind, job.key)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    man["pieces"][job.key] = {"kind": job.kind, "skill_id": (job.skill or {}).get("id"), "domain_id": job.domain, "mode": job.mode,
                              "mistake_id": job.mode if job.kind == "reteach" else None, "length": job.length, "status": status,
                              "cost_usd": round(cost, 4), "model": model, "prompt_version": pversion, "updated": created,
                              "fatal": (result or {}).get("fatal") or reasons}
    save_manifest(root, man)
    return status


def _text_of(content_blocks) -> str:
    for b in content_blocks or []:
        t = b.get("type") if isinstance(b, dict) else getattr(b, "type", None)
        if t == "text":
            return b.get("text") if isinstance(b, dict) else b.text
    return ""


def judge(job: Job, text: str):
    """(content, result, reasons) for a reply text."""
    from app.services.model_json import parse_model_json
    try:
        content, _note = parse_model_json(text)
    except Exception as e:
        return None, None, [f"the reply was not valid JSON ({type(e).__name__})"]
    if not isinstance(content, dict):
        return None, None, ["the reply was not a JSON object"]
    result = job.check(content)
    return content, result, (None if result["ok"] else result["fatal"])


async def run_job(client, model: str, db, job: Job, root: Path, man: dict, spent: list, max_usd: float, log=print, first_reasons=None, first_cost=0.0):
    """Normal calls: up to two (the second with the first's rejection reasons; first_reasons when a batch attempt already failed)."""
    from app.services import ai_budget
    from app.services.model_options import thinking_body
    reasons, cost, result, content = first_reasons, first_cost, None, None
    for attempt in ((2,) if first_reasons else (1, 2)):
        if spent[0] >= max_usd:
            log(f"  STOP before {job.key}: ${spent[0]:.2f} spent, the cap is ${max_usd}")
            return "stopped"
        t0 = time.time()
        resp = await client.messages.create(model=model, max_tokens=MAX_TOKENS.get(model, 16000), system=job.system(),
                                            messages=[{"role": "user", "content": job.prompt(reasons)}], extra_body=thinking_body(model))
        c = cost_of(model, resp.usage)
        cost += c
        spent[0] += c
        await ai_budget.record(db, None, "library", model, resp.usage)
        content, result, reasons = judge(job, _text_of(resp.content))
        what = "ok" if result and result["ok"] else ("FAILED: " + "; ".join(reasons or [])[:200])
        log(f"  {job.key} attempt {attempt}: {what} (${c:.3f}, {time.time() - t0:.0f} s"
            + (f", {len(result['repairs'])} repair(s), {len(result['warnings'])} warning(s))" if result else ")"))
        if result and result["ok"]:
            break
    return write_piece(root, man, job, content, result, model, cost, reasons)


async def generate_one(client, model: str, db, skill: dict, mistakes: list, length: str, root: Path, man: dict, spent: list, max_usd: float, plan_service, log=print,
                       reteach: dict = None):
    """One teach piece, or a re-teach piece for ONE mistake (kept for the tests and old callers)."""
    return await run_job(client, model, db, teach_job(skill, mistakes, length, plan_service, reteach), root, man, spent, max_usd, log)


async def recheck(db, root: Path, plan_service, log=print) -> dict:
    """The checks again on every stored piece (the repairs are idempotent); files and manifest updated. No AI."""
    man, counts = load_manifest(root), {}
    settings_cache = {}
    for kind in KINDS:
        for f in sorted((root / kind).glob("*.json")) if (root / kind).is_dir() else []:
            rec = json.loads(f.read_text(encoding="utf-8"))
            job = None
            if kind in ("teach", "reteach", "independent", "tasks"):
                skill, mistakes = await skill_facts(db, rec["skill_id"])
            if kind in ("teach", "reteach"):
                rt = next((m for m in mistakes if m["id"] == rec.get("mode")), None) if kind == "reteach" else None
                job = teach_job(skill, mistakes, rec["length"], plan_service, rt)
            elif kind == "independent":
                job = independent_job(skill, int(str(rec["mode"]).split()[-1]))
            elif kind == "setting":
                job = setting_job(rec["domain_id"], rec["mode"])
            elif kind == "tasks":
                st = settings_cache.setdefault(rec["domain_id"], settings_of(root, rec["domain_id"]))
                job = tasks_job(skill, st)
            res = job.check(rec["content"])
            rec["checks"] = res
            f.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
            stt = "ok" if res["ok"] else "failed_checks"
            if rec["key"] in man["pieces"]:
                man["pieces"][rec["key"]].update(status=stt, fatal=res["fatal"])
            counts[stt] = counts.get(stt, 0) + 1
    save_manifest(root, man)
    log(f"rechecked: {counts}")
    return counts


async def build_jobs(db, args, root: Path, man: dict, plan_service) -> list:
    from app.services import library_pieces as lp, library_parts as lpp
    if args.all:
        skills = [r["id"] for r in await db.fetch("SELECT id FROM competencies WHERE is_active ORDER BY id")]
    else:
        skills = PILOT if args.pilot else [s.strip() for s in (args.skills or "").split(",") if s.strip()]
    lengths = [l.strip() for l in args.lengths.split(",") if l.strip() in lp.LENGTHS]
    kinds = [k.strip() for k in args.kinds.split(",") if k.strip() in KINDS]
    waiting = {m["key"] for b in man.get("batches") or [] if b.get("status") != "collected" for m in (b.get("map") or {}).values()}
    done = (lambda key: key in waiting or (not args.redo and man["pieces"].get(key, {}).get("status") == "ok"))     # a piece in an open batch is not asked for twice
    jobs = []
    if "setting" in kinds:
        themes = [t.strip() for t in (args.themes or "").split(",") if t.strip()]
        for domain, all_themes in lpp.ANCHOR_THEMES.items():
            for theme in (themes or all_themes):
                if theme in all_themes and not done(lpp.setting_key(domain, theme)):
                    jobs.append(setting_job(domain, theme))
    for sid in skills:
        skill, mistakes = await skill_facts(db, sid)
        if "teach" in kinds:
            jobs += [teach_job(skill, mistakes, l, plan_service) for l in lengths if not done(lp.teach_key(sid, l))]
        if "reteach" in kinds:
            jobs += [teach_job(skill, mistakes, l, plan_service, m) for m in mistakes for l in lengths if not done(lp.reteach_key(m["id"], l))]
        if "independent" in kinds:
            jobs += [independent_job(skill, v) for v in (1, 2) if not done(lpp.independent_key(sid, v))]
        if "tasks" in kinds and not done(lpp.tasks_key(skill["domain_id"], sid)):
            st = settings_of(root, skill["domain_id"])
            if len(st) >= 3:
                jobs.append(tasks_job(skill, st))
            else:
                print(f"  (no tasks for {sid}: fewer than 3 anchor settings are made for {skill['domain_id']}; make the settings first)")
    return jobs


async def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    import anchor_common as ac
    ac.add_db_args(ap)
    ap.add_argument("--skills", help="comma-separated skill ids")
    ap.add_argument("--pilot", action="store_true", help="the 10 pilot skills (plan §6)")
    ap.add_argument("--all", action="store_true", help="every active skill")
    ap.add_argument("--lengths", default="short,medium,long")
    ap.add_argument("--kinds", default="teach", help="comma-separated: " + ", ".join(KINDS))
    ap.add_argument("--themes", help="setting: only these themes (comma-separated, from library_parts.ANCHOR_THEMES)")
    ap.add_argument("--model", default=os.environ.get("LIBRARY_MODEL", "claude-opus-5-5"))
    ap.add_argument("--max-usd", type=float, default=3.0)
    ap.add_argument("--out", default=str(ROOT / "db" / "seeds" / "library"))
    ap.add_argument("--redo", action="store_true", help="generate again even if 'ok'")
    ap.add_argument("--dry-run", action="store_true", help="list the jobs and print the first prompt; no call")
    ap.add_argument("--recheck", action="store_true", help="run the checks again on the pieces already made (no AI call)")
    ap.add_argument("--batch-submit", action="store_true", help="send the jobs as ONE Message Batch (half price); collect later")
    ap.add_argument("--batch-collect", action="store_true", help="collect the ended batches; failed pieces are asked for again by a normal call")
    args = ap.parse_args()

    from app.core.config import get_settings
    from app.services import ai_budget, plan_service
    import library_batch as lb
    db = await ac.connect(args)
    try:
        root = Path(args.out)
        man = load_manifest(root)
        if args.recheck:
            await recheck(db, root, plan_service)
            return
        s = get_settings()
        real = bool(s.anthropic_api_key) and not s.anthropic_api_key.startswith("sk-dummy")
        if args.batch_collect:
            if not real:
                sys.exit("No real API key in this environment.")
            await lb.collect(db, root, man, args, plan_service, s.anthropic_api_key)
            return
        jobs = await build_jobs(db, args, root, man, plan_service)
        print(f"{len(jobs)} piece(s) to make ({', '.join(sorted({j.kind for j in jobs})) or 'none'}), model {args.model}, cap ${args.max_usd}")
        if args.dry_run:
            if jobs:
                print(jobs[0].prompt(None))
            return
        if not real:
            sys.exit("No real API key in this environment: nothing generated (use --dry-run to see the prompts).")
        ai_budget.operator_mode(True)
        await ai_budget.check(db, None, "plan")          # AI_ENABLED, the credit date, the reserve: a stop here costs nothing
        if args.batch_submit:
            await lb.submit(jobs, root, man, args.model, s.anthropic_api_key, args.max_usd)
            return
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=s.anthropic_api_key)
        spent, counts = [0.0], {}
        for job in jobs:
            st = await run_job(client, args.model, db, job, root, man, spent, args.max_usd)
            counts[st] = counts.get(st, 0) + 1
            if st == "stopped":
                break
        print(f"\nDone: {counts}; spent ${spent[0]:.3f}. Manifest: {root / 'MANIFEST.json'}")
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
