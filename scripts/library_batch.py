"""
The block library at half price: Message Batches (docs/drafts/BLOCK_LIBRARY_PLAN.md §3). Used by generate_library.py --batch-submit / --batch-collect.

The pinned SDK (anthropic 0.34) has no batches, so this calls the HTTP API directly (POST /v1/messages/batches, GET the batch, GET its
results_url: one JSON line per request). Each batch is saved in the manifest with a map from its custom ids to the pieces, so collecting works
from a new session too. A piece whose batch reply fails the checks is asked for again by ONE normal call with the reasons (full price).
The meter records batch calls at the normal price (it does not know the discount): a safe over-estimate.
"""
import hashlib
import json
from datetime import datetime, timezone

API = "https://api.anthropic.com/v1/messages/batches"
VERSION = "2023-06-01"


def custom_id(key: str) -> str:
    """Batch ids allow only letters, digits, '-' and '_' (a key has dots: N2.3.2): a stable hash of the key."""
    return "p" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:24]


def _headers(api_key: str) -> dict:
    return {"x-api-key": api_key, "anthropic-version": VERSION, "content-type": "application/json"}


def _info(job) -> dict:
    return {"key": job.key, "kind": job.kind, "skill_id": (job.skill or {}).get("id"), "domain": job.domain, "length": job.length, "mode": job.mode,
            "settings": job.extra.get("settings")}


def estimate(man: dict, jobs: list, model: str) -> float:
    """What the batch should cost: each kind's average cost so far (normal calls), halved; $0.08 a piece for a kind not yet made."""
    by_kind = {}
    for p in man["pieces"].values():
        if p.get("status") == "ok" and p.get("model") == model and p.get("cost_usd"):
            by_kind.setdefault(p["kind"], []).append(p["cost_usd"])
    avg = {k: sum(v) / len(v) for k, v in by_kind.items()}
    return sum(avg.get(j.kind, 0.08) for j in jobs) * 0.5


def spent_so_far(man: dict) -> float:
    return sum(float(p.get("cost_usd") or 0) for p in man["pieces"].values())


async def submit(jobs, root, man, model, api_key, max_usd, http=None, log=print):
    from generate_library import MAX_TOKENS, save_manifest
    from app.services.model_options import thinking_body
    if not jobs:
        log("Nothing to submit.")
        return None
    est, spent = estimate(man, jobs, model), spent_so_far(man)
    if spent + est > max_usd:
        log(f"NOT submitted: ${spent:.2f} spent so far + about ${est:.2f} for this batch is over the cap ${max_usd}. Submit fewer pieces or raise the cap.")
        return None
    reqs, mapping = [], {}
    for j in jobs:
        cid = custom_id(j.key)
        mapping[cid] = _info(j)
        reqs.append({"custom_id": cid, "params": {"model": model, "max_tokens": MAX_TOKENS.get(model, 16000), "system": j.system(),
                                                  "messages": [{"role": "user", "content": j.prompt(None)}], **thinking_body(model)}})
    import httpx
    client = http or httpx.AsyncClient(timeout=120)
    try:
        r = await client.post(API, headers=_headers(api_key), json={"requests": reqs})
        if r.status_code >= 300:
            log(f"NOT submitted: HTTP {r.status_code}: {r.text[:300]}")
            return None
        batch = r.json()
    finally:
        if http is None:
            await client.aclose()
    man["batches"].append({"id": batch["id"], "model": model, "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                           "status": "submitted", "pieces": len(reqs), "estimate_usd": round(est, 2), "map": mapping})
    save_manifest(root, man)
    log(f"Submitted batch {batch['id']}: {len(reqs)} piece(s), about ${est:.2f}. Collect with --batch-collect (it can take up to 24 hours).")
    return batch["id"]


async def _rebuild(db, root, info, plan_service, cache):
    import generate_library as gl
    kind = info["kind"]
    if kind == "setting":
        return gl.setting_job(info["domain"], info["mode"])
    skill, mistakes = cache.get(info["skill_id"]) or await gl.skill_facts(db, info["skill_id"])
    cache[info["skill_id"]] = (skill, mistakes)
    if kind in ("teach", "reteach"):
        rt = next((m for m in mistakes if m["id"] == info["mode"]), None) if kind == "reteach" else None
        return gl.teach_job(skill, mistakes, info["length"], plan_service, rt)
    if kind == "independent":
        return gl.independent_job(skill, int(str(info["mode"]).split()[-1]))
    if kind == "tasks":
        st = gl.settings_of(root, info["domain"])
        return gl.tasks_job(skill, {k: v for k, v in st.items() if k in (info.get("settings") or st)})
    if kind == "tasks_extra":
        st = gl.settings_of(root, info["domain"])
        return gl.tasks_extra_job(skill, {k: st[k] for k in info.get("settings") or [] if k in st})
    raise ValueError(kind)


async def collect(db, root, man, args, plan_service, api_key, http=None, anthropic_client=None, log=print):
    """Every submitted batch that has ENDED: its replies checked and written; failures asked for again by a normal call (within the cap)."""
    import generate_library as gl
    from app.services import ai_budget
    import httpx
    client = http or httpx.AsyncClient(timeout=300)
    if anthropic_client is None:
        import anthropic
        anthropic_client = anthropic.AsyncAnthropic(api_key=api_key)
    spent = [gl_spent := sum(float(p.get("cost_usd") or 0) for p in man["pieces"].values())]
    counts, cache = {}, {}
    try:
        for b in [b for b in man["batches"] if b.get("status") != "collected"]:
            r = await client.get(f"{API}/{b['id']}", headers=_headers(api_key))
            info = r.json()
            if info.get("processing_status") != "ended":
                log(f"Batch {b['id']}: {info.get('processing_status')} ({json.dumps(info.get('request_counts') or {})}); collect again later.")
                continue
            res = await client.get(info["results_url"], headers=_headers(api_key))
            for line in res.text.splitlines():
                if not line.strip():
                    continue
                item = json.loads(line)
                meta = b["map"].get(item.get("custom_id"))
                if not meta:
                    continue
                if not args.redo and man["pieces"].get(meta["key"], {}).get("status") == "ok":
                    continue
                job = await _rebuild(db, root, meta, plan_service, cache)
                result = item.get("result") or {}
                if result.get("type") != "succeeded":
                    log(f"  {job.key}: the batch request {result.get('type')}: asked again by a normal call")
                    st = await gl.run_job(anthropic_client, b["model"], db, job, root, man, spent, args.max_usd, log)
                else:
                    msg = result["message"]
                    c = gl.cost_of(b["model"], msg.get("usage") or {}) * gl.BATCH_DISCOUNT
                    spent[0] += c
                    await ai_budget.record(db, None, "library", b["model"], msg.get("usage") or {})
                    content, checked, reasons = gl.judge(job, gl._text_of(msg.get("content")))
                    if checked and checked["ok"]:
                        st = gl.write_piece(root, man, job, content, checked, b["model"], c)
                        log(f"  {job.key}: ok (batch, ${c:.3f})")
                    else:
                        log(f"  {job.key}: failed in the batch ({'; '.join(reasons or [])[:160]}): asked again by a normal call")
                        st = await gl.run_job(anthropic_client, b["model"], db, job, root, man, spent, args.max_usd, log, first_reasons=reasons, first_cost=c)
                counts[st] = counts.get(st, 0) + 1
                if st == "stopped":
                    break
            if counts.get("stopped"):
                log(f"Batch {b['id']}: stopped by the cost cap; it stays open (collect again with a higher cap: pieces already ok are skipped).")
                gl.save_manifest(root, man)
                break
            b["status"] = "collected"
            b["collected"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            gl.save_manifest(root, man)
    finally:
        if http is None:
            await client.aclose()
    log(f"Collected: {counts}; library total so far ${spent[0]:.2f} (this run ${spent[0] - gl_spent:.2f}).")
    return counts
