"""
Ankur Saathi: the skill ladder as one sheet, for review.

    python scripts/export_skill_ladder.py --env-file backend/.env        # writes docs/skill_ladder.csv

One row per skill (101): where it sits (subject, grade), what comes before and after it, how it maps to NIPUN Bharat and whether anyone has
confirmed that, and how much stands behind it (recorded mistakes, materials, a written activity, a real-model run). It is the sheet the state's
curriculum cell is asked to review and approve (docs/ROADMAP.md, section 9): the two `reviewer_` columns are left empty on purpose.

It reads the database and docs/batch/batch_results.csv and changes nothing. Curriculum data only: no child, no teacher, no school.
Requires: pip install asyncpg
"""
import argparse
import asyncio
import csv
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(Path(__file__).resolve().parent)]
import anchor_common as ac

OUT = ROOT / "docs" / "skill_ladder.csv"
BATCH = ROOT / "docs" / "batch" / "batch_results.csv"
GRADES = {"balvatika": 0, "grade_1": 1, "grade_2": 2, "grade_3": 3}

COLUMNS = ["id", "subject", "grade", "name_hi", "name_en", "assessment_mode", "comes_after (prerequisites)", "comes_before (follow-on)",
           "nipun_codes", "nipun_match", "nipun_review_status", "recorded_mistakes", "teaching_materials", "anchor_written_for_this_skill",
           "real_model_run", "reviewer_decision (agree / change)", "reviewer_notes"]


def last_batch_runs() -> dict:
    """The latest real-model run per skill from the batch file (it can hold several rows for one skill)."""
    runs = {}
    if BATCH.exists():
        for row in csv.DictReader(io.open(BATCH, encoding="utf-8-sig")):
            runs[row["competency_id"]] = row
    return runs


def ids(rows, key, kind_key="prerequisite_type", own=None):
    return "; ".join(f"{r[key]} ({r[kind_key]})" for r in rows)


async def build_rows(db) -> list:
    comps = await db.fetch("""SELECT c.id, c.name_en, c.name_hi, c.grade_level, c.assessment_modality, c.nipun_codes, c.nipun_match, c.nipun_review_status,
                                     s.domain_id
                              FROM competencies c JOIN subdomains s ON s.id = c.subdomain_id WHERE c.is_active ORDER BY s.domain_id, c.grade_level, c.sort_order, c.id""")
    pre = await db.fetch("SELECT competency_id, prerequisite_id, prerequisite_type FROM competency_prerequisites ORDER BY competency_id, prerequisite_id")
    mis = {r["competency_id"]: r["n"] for r in await db.fetch("SELECT competency_id, count(*) AS n FROM misconceptions GROUP BY 1")}
    tlm = {}
    for r in await db.fetch("SELECT unnest(competency_ids) AS cid, count(*) AS n FROM tlm_references WHERE is_active GROUP BY 1"):
        tlm[r["cid"]] = r["n"]
    anchors = {}
    for r in await db.fetch("SELECT id, primary_competency_ids, secondary_competency_ids FROM anchor_activities WHERE is_active ORDER BY id"):
        for cid in list(r["primary_competency_ids"] or []) + list(r["secondary_competency_ids"] or []):
            anchors.setdefault(cid, []).append(r["id"])
    after = {}
    before = {}
    for r in pre:
        after.setdefault(r["competency_id"], []).append(f"{r['prerequisite_id']} ({r['prerequisite_type']})")
        before.setdefault(r["prerequisite_id"], []).append(f"{r['competency_id']} ({r['prerequisite_type']})")
    runs = last_batch_runs()
    rows = []
    for c in comps:
        cid = c["id"]
        run = runs.get(cid)
        if run:
            ran = f"yes ({run['status']}, {run.get('warnings_after') or 0} check warnings left)"
        else:
            ran = "no"
        nip = c["nipun_codes"]
        rows.append([cid, "numeracy" if c["domain_id"] == "numeracy" else "Hindi literacy (R1)", c["grade_level"], c["name_hi"], c["name_en"], c["assessment_modality"],
                     "; ".join(after.get(cid, [])), "; ".join(before.get(cid, [])),
                     ", ".join(nip) if isinstance(nip, (list, tuple)) else (nip or ""), c["nipun_match"] or "", c["nipun_review_status"] or "",
                     mis.get(cid, 0), tlm.get(cid, 0), ", ".join(anchors.get(cid, [])) or "none", ran, "", ""])
    rows.sort(key=lambda r: (r[1], GRADES.get(r[2], 9), r[0]))
    return rows


async def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ac.add_db_args(ap)
    args = ap.parse_args()
    db = await ac.connect(args)
    try:
        rows = await build_rows(db)
    finally:
        await db.close()
    with io.open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        w.writerows(rows)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(rows)} skills")


if __name__ == "__main__":
    asyncio.run(main())
