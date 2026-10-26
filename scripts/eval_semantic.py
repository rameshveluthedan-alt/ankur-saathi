#!/usr/bin/env python3
"""
Evidence for the semantic tier: is it trustworthy, where the curated ladder has nothing? Reads the vectors already loaded into the database (scripts/load_embeddings.py). Changes nothing in the database.

    python scripts\\eval_semantic.py --env-file backend\\.env --file db\\seeds\\content\\embeddings.json       reads the vectors FROM THE FILE: no pgvector needed (works on a laptop database whose columns are text)
    python scripts\\eval_semantic.py --env-file backend\\.env                                                  reads the vectors loaded INTO the database (needs pgvector)

Three things (the GATE of Thursday 29 Oct is decided on them):
  1. RECOVERY TEST. For every skill that HAS a curated (exact) anchor: rank all anchors valid for its domain and grade by closeness of meaning. Is the curated one 1st? In the top 3? Printed next to what a
     RANDOM ranking would score, so the number cannot flatter itself.
  2. A/B SHEET for Vaishnavi. For the skills the curated ladder serves only weakly (topic area / loose): today's pick and the semantic pick, in random order, WITHOUT saying which is which.
     Writes docs/semantic_ab_sheet.csv (for her) and docs/semantic_ab_key.csv (the key: keep it from her until she has answered).
  3. DETERMINISM AND SPEED: the same answer twice, and the time per choice.
"""
import argparse
import asyncio
import csv
import json
import math
import os
import random
import sys
import time
from math import comb
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(HERE), str(ROOT / "prompts"), str(ROOT / "backend")]
import anchor_common as ac                                  # noqa: E402
import embedding_texts as et                                # noqa: E402


def parse_vec(v):
    return json.loads(v) if isinstance(v, str) else [float(x) for x in v]


def cosine(a, b) -> float:
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
    return sum(x * y for x, y in zip(a, b)) / (na * nb) if na and nb else 0.0


def rank_anchors(skill_vec, anchors: list) -> list:
    """anchors: [{id, vec, ...}] -> the same dicts with 'sim', best first; ties go to the lower id (the same rule as the SQL)."""
    out = [dict(a, sim=cosine(skill_vec, a["vec"])) for a in anchors]
    out.sort(key=lambda a: (-round(a["sim"], 12), a["id"]))
    return out


def random_baseline(n: int, e: int, k: int) -> float:
    """The chance that a RANDOM ranking of n anchors puts at least one of the e curated ones in the first k."""
    k = min(k, n)
    return 1.0 if e >= n else 1 - comb(n - e, k) / comb(n, k)


def recovery(skills: list, anchors: list) -> dict:
    """skills: [{id, domain, grade, vec, exact_ids}]. Eligible anchors = same domain, grade inside the anchor's grade range. Only skills with at least one eligible curated anchor are tested."""
    rows = []
    for s in skills:
        pool = [a for a in anchors if a["domain"] == s["domain"] and s["grade"] in a["grades"]]
        exact = [a["id"] for a in pool if a["id"] in s["exact_ids"]]
        if not exact or not pool:
            continue
        ranked = rank_anchors(s["vec"], pool)
        best = min(i for i, a in enumerate(ranked, 1) if a["id"] in exact)
        rows.append({"skill": s["id"], "domain": s["domain"], "pool": len(pool), "exact": len(exact), "rank": best})
    n = len(rows)
    res = {"tested": n, "rows": rows}
    if n:
        res["hit1"] = sum(r["rank"] == 1 for r in rows) / n
        res["hit3"] = sum(r["rank"] <= 3 for r in rows) / n
        res["mrr"] = sum(1 / r["rank"] for r in rows) / n
        res["random_hit1"] = sum(random_baseline(r["pool"], r["exact"], 1) for r in rows) / n
        res["random_hit3"] = sum(random_baseline(r["pool"], r["exact"], 3) for r in rows) / n
    return res


async def vectors_from_file(db, data: dict):
    """({table: {id: vector}}, how many were left out): only vectors whose fingerprint equals the fingerprint of the row's CURRENT text (a vector made for an older text is stale and ignored)."""
    texts = await et.load_texts(db)
    out, stale = {}, 0
    for table in ("competencies", "anchor_activities"):
        out[table] = {}
        for rid, rec in data["tables"].get(table, {}).items():
            cur = texts[table].get(rid)
            if cur is not None and et.fingerprint(cur) == rec["hash"]:
                out[table][rid] = rec["vector"]
            else:
                stale += 1
    return out, stale


async def load(db, vectors=None):
    """(skills, anchors, number of skills, number of anchors). `vectors` = {table: {id: vector}} from the file, or None to read them from the database's vector columns."""
    skills_raw = await db.fetch("""SELECT c.id, c.name_en, c.name_hi, c.grade_level, s.domain_id FROM competencies c JOIN subdomains s ON s.id = c.subdomain_id WHERE c.is_active = TRUE ORDER BY c.id""")
    anchors_raw = await db.fetch("""SELECT id, title_en, title_hi, theme, description_en, domain_id, grade_range, primary_competency_ids, secondary_competency_ids
                                    FROM anchor_activities WHERE is_active = TRUE ORDER BY id""")
    if vectors is None:
        vectors = {t: {r["id"]: parse_vec(r["v"]) for r in await db.fetch(f"SELECT id, embedding::text AS v FROM {t} WHERE embedding IS NOT NULL")} for t in ("competencies", "anchor_activities")}
    anchors = [dict(id=a["id"], title_en=a["title_en"], title_hi=a["title_hi"], theme=a["theme"], desc=a["description_en"], domain=a["domain_id"], grades=list(a["grade_range"] or []),
                    exact_for=set((a["primary_competency_ids"] or []) + (a["secondary_competency_ids"] or [])), vec=vectors["anchor_activities"][a["id"]]) for a in anchors_raw if a["id"] in vectors["anchor_activities"]]
    skills = [dict(id=s["id"], name_en=s["name_en"], name_hi=s["name_hi"], domain=s["domain_id"], grade=s["grade_level"], vec=vectors["competencies"][s["id"]],
                   exact_ids={a["id"] for a in anchors if s["id"] in a["exact_for"]}) for s in skills_raw if s["id"] in vectors["competencies"]]
    return skills, anchors, len(skills_raw), len(anchors_raw)


async def main():
    ap = argparse.ArgumentParser(description="Evidence for the semantic tier.", epilog=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", help="read the vectors from this embeddings file (db/seeds/content/embeddings.json) instead of from the database: no pgvector needed")
    ap.add_argument("--out-dir", default=str(ROOT / "docs"))
    ap.add_argument("--seed", type=int, default=29)
    ac.add_db_args(ap)
    args = ap.parse_args()
    db = await ac.connect(args)
    try:
        import orchestrate as o
        db_ready = await o._vectors_ready(db)
        if args.file:
            import load_embeddings as le
            data = json.loads(Path(args.file).read_text(encoding="utf-8"))
            problems = le.validate_file(data)
            if problems:
                print(f"{args.file} cannot be used: {problems[0]}")
                return 1
            vectors, stale = await vectors_from_file(db, data)
            print(f"Vectors read from {Path(args.file).name} ({data['model']}); {stale} left out as stale (made for an older text).")
            skills, anchors, n_skills, n_anchors = await load(db, vectors)
        else:
            if not db_ready:
                print("This database has no vector columns (or no pgvector). Load the embeddings first (scripts\\load_embeddings.py), or read the file directly: --file db\\seeds\\content\\embeddings.json")
                return 1
            skills, anchors, n_skills, n_anchors = await load(db)
        if len(skills) < n_skills or len(anchors) < n_anchors:
            print(f"Only {len(skills)} of {n_skills} skills and {len(anchors)} of {n_anchors} anchors have a usable vector: run scripts\\embed_content.py again.")
            return 1
        # ---- 1. recovery
        rec = recovery(skills, anchors)
        print(f"1. RECOVERY TEST: {rec['tested']} skills have a curated anchor; is it ranked first / in the top 3 by closeness of meaning?")
        print(f"   first:     {rec['hit1']:.0%}   (a random ranking would give {rec['random_hit1']:.0%})")
        print(f"   top 3:     {rec['hit3']:.0%}   (a random ranking would give {rec['random_hit3']:.0%})")
        print(f"   mean reciprocal rank: {rec['mrr']:.2f}")
        for d in sorted({r['domain'] for r in rec["rows"]}):
            sub = recovery([s for s in skills if s["domain"] == d], anchors)
            print(f"   {d:<14} {sub['tested']:>3} skills: first {sub['hit1']:.0%} (random {sub['random_hit1']:.0%}), top 3 {sub['hit3']:.0%} (random {sub['random_hit3']:.0%})")
        # ---- 2. the A/B sheet
        os.environ["SEMANTIC_RETRIEVAL"] = "off"
        current = {}
        for s in skills:
            a = await o.fetch_anchor_activity(db, s["domain"], s["grade"], s["id"])
            current[s["id"]] = (a.id if a else None, a.match_quality if a else "none")
        weak = [s for s in skills if current[s["id"]][1] in ("topic_area", "loose")]
        by_id = {a["id"]: a for a in anchors}
        rng = random.Random(args.seed)
        sheet, key, same = [], [], 0
        for s in weak:
            pool = [a for a in anchors if a["domain"] == s["domain"] and s["grade"] in a["grades"]]
            if not pool:
                continue
            pick = rank_anchors(s["vec"], pool)[0]
            cur_id = current[s["id"]][0]
            if pick["id"] == cur_id:
                same += 1
                continue
            cur = by_id[cur_id]
            first_is_current = rng.random() < 0.5
            a, b = (cur, pick) if first_is_current else (pick, cur)
            sheet.append({"skill": s["id"], "skill_en": s["name_en"], "skill_hi": s["name_hi"], "grade": s["grade"],
                          "A_title": a["title_en"], "A_title_hi": a["title_hi"], "A_theme": a["theme"], "A_what": (a["desc"] or "")[:160],
                          "B_title": b["title_en"], "B_title_hi": b["title_hi"], "B_theme": b["theme"], "B_what": (b["desc"] or "")[:160],
                          "WHICH_FITS_THIS_SKILL_BETTER (A / B / same)": "", "notes": ""})
            key.append({"skill": s["id"], "A_is": "current" if first_is_current else "semantic", "B_is": "semantic" if first_is_current else "current",
                        "current_id": cur_id, "current_tier": current[s["id"]][1], "semantic_id": pick["id"], "similarity": round(pick["sim"], 3)})
        out = Path(args.out_dir)
        out.mkdir(parents=True, exist_ok=True)
        for name, rows in (("semantic_ab_sheet.csv", sheet), ("semantic_ab_key.csv", key)):
            if rows:
                with open(out / name, "w", newline="", encoding="utf-8-sig") as f:
                    w = csv.DictWriter(f, fieldnames=list(rows[0]))
                    w.writeheader()
                    w.writerows(rows)
        print(f"\n2. A/B SHEET: {len(weak)} skills are served only weakly today (topic area or loose). For {same} of them the semantic pick is the SAME anchor; "
              f"{len(sheet)} differ and are in docs/semantic_ab_sheet.csv (options A/B in random order, unlabelled). The key is docs/semantic_ab_key.csv: do NOT show it to the judge until she has answered.")
        # ---- 3. determinism and speed (the SQL tier itself: needs a database with pgvector and the vectors loaded)
        if not db_ready or args.file:
            print("\n3. DETERMINISM AND SPEED: not measured here (it tests the SQL tier, which needs a database with pgvector and the vectors loaded: run this script without --file there).")
            print("\nGATE (Thu 29 Oct, noon): ON only if the recovery test is clearly above the random numbers, Vaishnavi prefers the semantic pick in about half or more of the differing skills, and no test fails.")
            return 0
        os.environ["SEMANTIC_RETRIEVAL"] = "on"
        t0 = time.perf_counter()
        first = [(await o.fetch_anchor_activity(db, s["domain"], s["grade"], s["id"])) for s in skills]
        dt = time.perf_counter() - t0
        second = [(await o.fetch_anchor_activity(db, s["domain"], s["grade"], s["id"])) for s in skills]
        ids = lambda xs: [(a.id, a.match_quality) if a else None for a in xs]
        sem = [a for a in first if a and a.match_quality == "semantic"]
        print(f"\n3. DETERMINISM AND SPEED: the same answer twice for all {len(skills)} skills: {ids(first) == ids(second)}; {len(sem)} skills now get a 'semantic' anchor; "
              f"{1000 * dt / len(skills):.1f} ms per skill (the whole ladder, including the vector search).")
        print("\nGATE (Thu 29 Oct, noon): ON only if the recovery test is clearly above the random numbers, Vaishnavi prefers the semantic pick in about half or more of the differing skills, and no test fails.")
    finally:
        await db.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
