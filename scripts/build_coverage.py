"""
Ankur Saathi — coverage labels: how much of the knowledge base stands behind each skill.

    python scripts/build_coverage.py                       # reads docs/batch/batch_results.csv if it exists
    python scripts/build_coverage.py --load                # also writes the labels straight into the database

Writes db/seeds/content/06_coverage.sql (loaded by setup.sh), docs/coverage_report.csv and docs/COVERAGE.md.
The Plan screen shows one of four labels per skill:

  tested        run through the real model and passed every check (a valid plan, no warnings left after the automatic
                repairs, all three worksheets render), AND the anchor is an exact match from the bank, AND (literacy) the
                reading passage comes from the bank.
  ai_written    it ran and passed, but the anchor is not an exact match (the model adapts a related one or writes its own)
                or no bank passage fits. Usable, less validated.
  experimental  it failed, or checks still flag problems after the automatic repairs. Expect to edit.
  untested      not yet run through the real model.

Requires: pip install asyncpg
"""

import argparse
import asyncio
import csv
import os
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(Path(__file__).resolve().parent), str(ROOT / "prompts"), str(ROOT / "backend")]
import anchor_common as ac

# Verified by the team with the real model during development, before the batch run existed
KNOWN_TESTED = {"N2.3.2", "L2.6.1"}
TIER_ORDER = ["tested", "ai_written", "experimental", "untested"]


def domain_of(cid: str) -> str:
    return "numeracy" if cid.startswith("N") else "r1_literacy"


def decide(cid: str, anchor: str, passage: str, batch: dict | None) -> tuple[str, str]:
    """(tier, one plain sentence)"""
    if batch is None and cid in KNOWN_TESTED:
        batch = {"status": "ok", "warnings_after": "0", "render_ok": "yes"}
    if batch is None:
        return "untested", "Not yet run through the real model: the plan may need more editing."
    if batch["status"] != "ok" or batch.get("render_ok") != "yes":
        return "experimental", "Plan generation or the worksheets failed in testing."
    if int(batch.get("warnings_after") or 0) > 0:
        return "experimental", "The automatic checks still flag problems in this plan after repair: review it before use."
    reasons = []
    if anchor != "exact":
        reasons.append("the opening activity is adapted by the AI from a related one" if anchor in ("related", "topic_area", "loose")
                       else "the opening activity is written by the AI from scratch")
    if domain_of(cid) == "r1_literacy" and passage not in ("competency", "grade"):
        reasons.append("no reading passage from the bank fits this level")
    if reasons:
        return "ai_written", "Passed testing, but " + " and ".join(reasons) + "."
    return "tested", "Passed every check with the real model, using an exact anchor" + (" and a bank passage." if domain_of(cid) == "r1_literacy" else ".")


async def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--batch", default=str(ROOT / "docs" / "batch" / "batch_results.csv"))
    ap.add_argument("--load", action="store_true", help="also upsert the labels into the database")
    ac.add_db_args(ap)
    args = ap.parse_args()

    from orchestrate import fetch_anchor_activity
    db = await ac.connect(args)
    comps = await db.fetch("""SELECT c.id, c.grade_level, c.name_en, c.nipun_match FROM competencies c
                              ORDER BY (c.id LIKE 'L%'), c.grade_level, c.sort_order, c.id""")
    batch = {}
    bp = Path(args.batch)
    if bp.exists():
        for r in csv.DictReader(bp.open(encoding="utf-8")):
            batch[r["competency_id"]] = r                      # the latest row per skill wins
    rows = []
    for c in comps:
        cid, domain = c["id"], domain_of(c["id"])
        a = await fetch_anchor_activity(db, domain, c["grade_level"], cid)
        anchor = a.match_quality if a else "none"
        passage = "n/a"
        if domain == "r1_literacy":
            from app.services import plan_service
            gp = await plan_service.retrieve_group_passages(db, domain, {"progressor": cid}, date(2026, 11, 2))
            passage = (gp.get("progressor") or {}).get("match", "none")
        b = batch.get(cid)
        tier, note = decide(cid, anchor, passage, b)
        rows.append({"competency_id": cid, "name": c["name_en"], "grade": c["grade_level"], "domain": domain, "tier": tier, "anchor_match": anchor,
                     "passage_match": passage, "nipun_match": c["nipun_match"] or "", "batch_status": (b or {}).get("status", "not_run"),
                     "batch_warnings": (b or {}).get("warnings_after", ""), "note": note, "tested_at": (b or {}).get("generated_at", "")})
    if args.load:
        for r in rows:
            await db.execute("""INSERT INTO competency_coverage (competency_id, tier, anchor_match, passage_match, nipun_match, batch_status, batch_warnings, note, tested_at)
                                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
                                ON CONFLICT (competency_id) DO UPDATE SET tier=$2, anchor_match=$3, passage_match=$4, nipun_match=$5,
                                batch_status=$6, batch_warnings=$7, note=$8, tested_at=$9""",
                             r["competency_id"], r["tier"], r["anchor_match"], r["passage_match"], r["nipun_match"] or None, r["batch_status"],
                             int(r["batch_warnings"]) if r["batch_warnings"] != "" else None, r["note"],
                             __import__("datetime").datetime.fromisoformat(r["tested_at"]) if r["tested_at"] else None)
    await db.close()

    q = lambda v: "NULL" if v in (None, "") else "'" + str(v).replace("'", "''") + "'"
    sql = ["-- Coverage labels per skill. Written by scripts/build_coverage.py. Do not edit by hand.", ""]
    for r in rows:
        sql.append("INSERT INTO competency_coverage (competency_id, tier, anchor_match, passage_match, nipun_match, batch_status, batch_warnings, note, tested_at) VALUES "
                   f"({q(r['competency_id'])}, {q(r['tier'])}, {q(r['anchor_match'])}, {q(r['passage_match'])}, {q(r['nipun_match'])}, {q(r['batch_status'])}, "
                   f"{r['batch_warnings'] if r['batch_warnings'] != '' else 'NULL'}, {q(r['note'])}, {q(r['tested_at'])}) "
                   "ON CONFLICT (competency_id) DO UPDATE SET tier = EXCLUDED.tier, anchor_match = EXCLUDED.anchor_match, passage_match = EXCLUDED.passage_match, "
                   "nipun_match = EXCLUDED.nipun_match, batch_status = EXCLUDED.batch_status, batch_warnings = EXCLUDED.batch_warnings, note = EXCLUDED.note, tested_at = EXCLUDED.tested_at;")
    (ROOT / "db" / "seeds" / "content" / "06_coverage.sql").write_text("\n".join(sql) + "\n", encoding="utf-8")
    with (ROOT / "docs" / "coverage_report.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

    by = Counter((r["domain"], r["tier"]) for r in rows)
    anchors, passages = Counter(r["anchor_match"] for r in rows), Counter(r["passage_match"] for r in rows if r["domain"] == "r1_literacy")
    md = ["# Knowledge-base coverage", "", f"Generated by `scripts/build_coverage.py` ({'from a real-model batch run' if batch else 'no batch run yet: only skills verified during development count as tested'}).", "",
          "| Label | Numeracy | Literacy | Total |", "| --- | ---: | ---: | ---: |"]
    for t in TIER_ORDER:
        n, l = by[("numeracy", t)], by[("r1_literacy", t)]
        md.append(f"| {t} | {n} | {l} | {n + l} |")
    md += ["", "What stands behind a skill:", "",
           f"- Layer 1 (skills, prerequisites, common mistakes, NIPUN alignment): all {len(rows)} skills.",
           f"- Anchor activity from the bank: exact match for {anchors['exact']}, related {anchors['related']}, topic area {anchors['topic_area']}, loose {anchors['loose']}, none {anchors['none']}.",
           f"- Literacy reading passages from the bank: by skill {passages['competency']}, by grade {passages['grade']}, none {passages['none']}.", "",
           "Labels: **tested** = passed every automatic check with the real model, with an exact anchor (and a bank passage for literacy). "
           "**ai_written** = passed, but part of the content is adapted or written by the AI. **experimental** = failed or checks still flag problems. "
           "**untested** = not yet run with the real model.", ""]
    for t in ("experimental", "ai_written", "untested"):
        sel = [r for r in rows if r["tier"] == t]
        if sel:
            md += [f"## {t} ({len(sel)})", ""] + [f"- {r['competency_id']} {r['name']}: {r['note']}" for r in sel] + [""]
    (ROOT / "docs" / "COVERAGE.md").write_text("\n".join(md), encoding="utf-8")
    print(f"{len(rows)} skills labelled:", {t: sum(v for (d, tt), v in by.items() if tt == t) for t in TIER_ORDER})
    print("Wrote db/seeds/content/06_coverage.sql, docs/coverage_report.csv, docs/COVERAGE.md" + (" and loaded the database" if args.load else ""))


if __name__ == "__main__":
    asyncio.run(main())
