"""
Generate pieces of the recorded-block library (docs/drafts/BLOCK_LIBRARY_PLAN.md). Step 1: TEACH blocks.

    cd backend
    # what would be generated, and one prompt, with no call:
    ../backend/venv/Scripts/python.exe ../scripts/generate_library.py --env-file .env --pilot --dry-run
    # the pilot (REAL calls: only with the project lead's OK; Opus 5.5 by default):
    AI_ENABLED=true ../backend/venv/Scripts/python.exe ../scripts/generate_library.py --env-file .env --pilot --max-usd 3

One JSON file per piece under db/seeds/library/<kind>/, and db/seeds/library/MANIFEST.json with every key's status. A run that stops (the cap,
an error, the machine) is simply started again: pieces already 'ok' are skipped. A piece that fails the checks is generated again ONCE with the
reasons; if it fails again it is marked 'failed_checks' for a person. Every call is metered (kind 'library').
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
# USD per million tokens: (input, output, cache read, cache write). The claude-api reference, Nov 2026; cache write assumed 1.25x input.
PRICES = {"claude-opus-5-5": (4.0, 20.0, 0.20, 5.0), "claude-sonnet-5-5": (2.0, 10.0, 0.10, 2.5), "claude-haiku-5-5": (0.10, 0.50, 0.01, 0.125)}
MAX_TOKENS = {"claude-opus-5-5": 20000}


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
    return json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {"format": 1, "pieces": {}}


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


async def generate_one(client, model: str, db, skill: dict, mistakes: list, length: str, root: Path, man: dict, spent: list, max_usd: float, plan_service, log=print):
    """One teach piece: up to two calls (the second with the first's rejection reasons). Writes the file and updates the manifest."""
    from app.services import ai_budget, library_pieces as lp, writing_sheets
    from app.services.model_json import parse_model_json
    from app.services.model_options import thinking_body
    from orchestrate import build_system_blocks
    key = lp.teach_key(skill["id"], length)
    system = build_system_blocks(skill["domain_id"], cfu=True)
    pversion = lp.prompt_version(system[0]["text"])
    kind_rules = writing_sheets.prompt_section({lp.GROUP: skill["id"]}, skill["domain_id"])
    reasons, cost, result, content = None, 0.0, None, None
    for attempt in (1, 2):
        if spent[0] >= max_usd:
            log(f"  STOP before {key}: ${spent[0]:.2f} spent, the cap is ${max_usd}")
            return "stopped"
        user = lp.teach_prompt(skill, mistakes, length, pace_for(length), kind_rules, reasons)
        t0 = time.time()
        resp = await client.messages.create(model=model, max_tokens=MAX_TOKENS.get(model, 16000), system=system,
                                            messages=[{"role": "user", "content": user}], extra_body=thinking_body(model))
        c = cost_of(model, resp.usage)
        cost += c
        spent[0] += c
        await ai_budget.record(db, None, "library", model, resp.usage)
        text = next((b.text for b in resp.content if getattr(b, "type", None) == "text"), "")
        try:
            content, _note = parse_model_json(text)
        except Exception as e:
            reasons = [f"the reply was not valid JSON ({type(e).__name__})"]
            log(f"  {key} attempt {attempt}: not JSON (${c:.3f}, {time.time() - t0:.0f} s)")
            continue
        result = lp.check_teach_piece(content, skill, mistakes, length, plan_service)
        log(f"  {key} attempt {attempt}: {'ok' if result['ok'] else 'FAILED: ' + '; '.join(result['fatal'])[:200]} "
            f"(${c:.3f}, {time.time() - t0:.0f} s, {len(result['repairs'])} repair(s), {len(result['warnings'])} warning(s))")
        if result["ok"]:
            break
        reasons = result["fatal"]
    status = "ok" if result and result["ok"] else "failed_checks"
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if content is not None:
        rec = lp.record(key, "teach", skill["id"], length, content, result or {"ok": False, "fatal": reasons}, model, pversion, cost, created)
        f = lp.piece_path(root, "teach", key)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    man["pieces"][key] = {"kind": "teach", "skill_id": skill["id"], "length": length, "status": status, "cost_usd": round(cost, 4),
                          "model": model, "prompt_version": pversion, "updated": created, "fatal": (result or {}).get("fatal") or reasons}
    save_manifest(root, man)
    return status


async def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    import anchor_common as ac
    ac.add_db_args(ap)
    ap.add_argument("--skills", help="comma-separated skill ids")
    ap.add_argument("--pilot", action="store_true", help="the 10 pilot skills (plan §6)")
    ap.add_argument("--all", action="store_true", help="every active skill")
    ap.add_argument("--lengths", default="short,medium,long")
    ap.add_argument("--model", default=os.environ.get("LIBRARY_MODEL", "claude-opus-5-5"))
    ap.add_argument("--max-usd", type=float, default=3.0)
    ap.add_argument("--out", default=str(ROOT / "db" / "seeds" / "library"))
    ap.add_argument("--redo", action="store_true", help="generate again even if 'ok'")
    ap.add_argument("--dry-run", action="store_true", help="list the keys and print the first prompt; no call")
    args = ap.parse_args()

    from app.core.config import get_settings
    from app.services import ai_budget, library_pieces as lp, plan_service
    db = await ac.connect(args)
    try:
        if args.all:
            skills = [r["id"] for r in await db.fetch("SELECT id FROM competencies WHERE is_active ORDER BY id")]
        else:
            skills = PILOT if args.pilot else [s.strip() for s in (args.skills or "").split(",") if s.strip()]
        lengths = [l.strip() for l in args.lengths.split(",") if l.strip() in lp.LENGTHS]
        root = Path(args.out)
        man = load_manifest(root)
        todo = [(s, l) for s in skills for l in lengths
                if args.redo or man["pieces"].get(lp.teach_key(s, l), {}).get("status") != "ok"]
        print(f"{len(skills)} skill(s) x {len(lengths)} length(s): {len(todo)} piece(s) to make, model {args.model}, cap ${args.max_usd}")
        if args.dry_run:
            if todo:
                skill, mistakes = await skill_facts(db, todo[0][0])
                from app.services import writing_sheets
                print(lp.teach_prompt(skill, mistakes, todo[0][1], pace_for(todo[0][1]), writing_sheets.prompt_section({lp.GROUP: skill["id"]}, skill["domain_id"])))
            return
        s = get_settings()
        if not s.anthropic_api_key or s.anthropic_api_key.startswith("sk-dummy"):
            sys.exit("No real API key in this environment: nothing generated (use --dry-run to see the prompts).")
        ai_budget.operator_mode(True)
        await ai_budget.check(db, None, "plan")          # AI_ENABLED, the credit date, the reserve: a stop here costs nothing
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=s.anthropic_api_key)
        spent = [0.0]
        counts = {}
        for sid, length in todo:
            skill, mistakes = await skill_facts(db, sid)
            st = await generate_one(client, args.model, db, skill, mistakes, length, root, man, spent, args.max_usd, plan_service)
            counts[st] = counts.get(st, 0) + 1
            if st == "stopped":
                break
        print(f"\nDone: {counts}; spent ${spent[0]:.3f}. Manifest: {root / 'MANIFEST.json'}")
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
