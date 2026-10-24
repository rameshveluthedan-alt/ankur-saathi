#!/usr/bin/env python3
"""
Curated skill bridges: load the reviewer's decisions into the app.

For a skill (the day's ANCHOR) a bridge says which skill the BEGINNERS work on (its predecessor) and which the PROFICIENTS work on (its successor). The app consults the table `skill_bridges`
FIRST and uses the graph rule where a skill has no approved bridge. Only APPROVED rows are ever stored. Nothing here touches the AI or the children's data.

THE WORKING FILE is db/seeds/content/07_skill_bridges.csv (columns skill_id, predecessor_id, successor_id, note, approved). It is YOURS to edit; later packages never overwrite it.

    python scripts\\load_bridges.py --init                                      once: create the working file from the starter (every row NOT approved)
    python scripts\\load_bridges.py --from-review docs\\skill_bridges_for_review.csv   take the reviewer's decisions from the review sheet into the working file (no database needed)
    python scripts\\load_bridges.py --check --env-file backend\\.env            validate the approved rows against the knowledge base, change nothing
    python scripts\\load_bridges.py --env-file backend\\.env                    validate, then load (creates the table if it is missing; removes bridges no longer approved)
    python scripts\\load_bridges.py --dry-run --env-file backend\\.env          say what loading WOULD change

In the review sheet the reviewer writes, in REVIEWER_decision_Beginners / REVIEWER_decision_Proficients, either a skill id (that is the decision) or OK (accept the proposal beside it).
A cell left empty is no decision: that side follows the graph rule. The nightly job runs this script too (a failure there never stops the demo reset).
"""
import argparse
import asyncio
import csv
import io
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(HERE), str(ROOT / "backend")]
import anchor_common as ac                                  # noqa: E402

WORKING = ROOT / "db" / "seeds" / "content" / "07_skill_bridges.csv"
STARTER = ROOT / "db" / "seeds" / "content" / "07_skill_bridges.starter.csv"
DDL = ROOT / "db" / "schema" / "11_skill_bridges.sql"
FIELDS = ["skill_id", "predecessor_id", "successor_id", "note", "approved"]
ID = re.compile(r"\b([NL]\d\.\d\.\d)\b")
YES = {"yes", "y", "true", "1", "approved", "ok", "हाँ", "हां", "ठीक", "सही", "✓"}
RANK = {"balvatika": 0, "grade_1": 1, "grade_2": 2, "grade_3": 3}


def first_id(cell):
    m = ID.search(cell or "")
    return m.group(1) if m else None


def is_yes(cell):
    return (cell or "").strip().lower() in YES


def missing_file_message(path):
    return (f"File not found: {path}\n"
            f"  - if this is the WORKING file, create it once with:  python scripts\\load_bridges.py --init\n"
            f"  - if you meant a CSV you exported from a Google Sheet (File > Download > Comma Separated Values), save it and give its FULL path, "
            f"for example  --csv C:\\dev\\Ankur-Saathi\\docs\\my_table.csv")


def read_working(path):
    """The rows of a bridges CSV, tolerant: a cell may hold 'N2.3.2 Adds two ...' (the id is taken from it), 'approved' may be yes/y/true/1/ok."""
    path = Path(path)
    if not path.exists():
        raise SystemExit(missing_file_message(path))
    rows = []
    for i, r in enumerate(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8-sig"))), 2):
        if not any((v or "").strip() for v in r.values() if isinstance(v, str)):
            continue
        rows.append({"line": i, "skill_id": first_id(r.get("skill_id")), "raw_skill": (r.get("skill_id") or "").strip(),
                     "predecessor_id": first_id(r.get("predecessor_id")), "successor_id": first_id(r.get("successor_id")),
                     "note": (r.get("note") or "").strip(), "approved": is_yes(r.get("approved"))})
    return rows


def write_working(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in sorted(rows, key=lambda r: r["skill_id"] or ""):
            w.writerow({"skill_id": r["skill_id"], "predecessor_id": r["predecessor_id"] or "", "successor_id": r["successor_id"] or "", "note": r["note"], "approved": "yes" if r["approved"] else ""})


def read_review(path):
    """The reviewer's decisions from the review sheet: ([rows to merge], [problems]). A side with no decision is left to the graph rule; a row with no decision at all is skipped."""
    path = Path(path)
    if not path.exists():
        raise SystemExit(missing_file_message(path))
    out, problems = [], []
    for i, r in enumerate(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8-sig"))), 2):
        sid = first_id(r.get("skill"))
        if not sid:
            continue
        sides = []
        for label, proposal_col, decision_col in (("Beginners", "Beginners (predecessor)", "REVIEWER_decision_Beginners"), ("Proficients", "Proficients (successor)", "REVIEWER_decision_Proficients")):
            cell = (r.get(decision_col) or "").strip()
            if not cell:
                sides.append(None)
            elif cell.lower() in YES:
                prop = first_id(r.get(proposal_col))
                if prop:
                    sides.append(prop)
                else:
                    sides.append(None)
                    problems.append(f"line {i} {sid}: {label}: 'OK' but there is no proposal to accept: write a skill id")
            elif first_id(cell):
                sides.append(first_id(cell))
            else:
                sides.append(None)
                problems.append(f"line {i} {sid}: {label}: cannot read '{cell[:40]}': write a skill id such as N2.3.2, or OK")
        if sides[0] or sides[1]:
            out.append({"line": i, "skill_id": sid, "raw_skill": sid, "predecessor_id": sides[0], "successor_id": sides[1], "note": (r.get("REVIEWER_notes") or "").strip() or "reviewer's decision", "approved": True})
    return out, problems


def merge(working, decided):
    """The decided rows replace the working rows of the same skill; every other working row is kept."""
    by = {r["skill_id"]: r for r in working if r["skill_id"]}
    for d in decided:
        by[d["skill_id"]] = d
    return list(by.values())


async def validate(db, rows):
    """(rows that can be loaded, errors [(line, skill, message)], warnings, how many rows are not approved). Only approved rows are checked: a row nobody approved is never loaded and never an error."""
    comps = {r["id"]: r["grade_level"] for r in await db.fetch("SELECT id, grade_level FROM competencies")}
    pre = {}
    for r in await db.fetch("SELECT competency_id, prerequisite_id FROM competency_prerequisites"):
        pre.setdefault(r["competency_id"], set()).add(r["prerequisite_id"])
    dep = {}
    for c, ps in pre.items():
        for p in ps:
            dep.setdefault(p, set()).add(c)

    def closure(start, graph):
        seen, stack = set(), list(graph.get(start, ()))
        while stack:
            x = stack.pop()
            if x not in seen:
                seen.add(x)
                stack.extend(graph.get(x, ()))
        return seen
    good, errors, warnings, seen, unapproved = [], [], [], {}, 0
    for r in rows:
        if not r["approved"]:
            unapproved += 1
            continue
        s, b, p, problems = r["skill_id"], r["predecessor_id"], r["successor_id"], []
        if not s or s not in comps:
            problems.append(f"the skill {s or r['raw_skill']!r} does not exist")
        if s in seen:
            problems.append(f"{s} is approved twice (lines {seen[s]} and {r['line']})")
        seen.setdefault(s, r["line"])
        if not b and not p:
            problems.append("neither a predecessor nor a successor is given")
        for label, k in (("Beginners' predecessor", b), ("Proficients' successor", p)):
            if k and k not in comps:
                problems.append(f"{label} {k} does not exist")
            elif k and s in comps and k[0] != s[0]:
                problems.append(f"{label} {k} is of another subject than {s}")
        if s in comps:
            if b in comps and RANK.get(comps[b], 9) > RANK.get(comps[s], 9):
                problems.append(f"Beginners' predecessor {b} is of a HIGHER grade than {s}")
            if p in comps and RANK.get(comps[p], 0) < RANK.get(comps[s], 0):
                problems.append(f"Proficients' successor {p} is of a LOWER grade than {s}")
            if not problems:
                if b and b != s and b not in closure(s, pre):
                    warnings.append(f"{s}: {b} is not among its prerequisites in the graph (loaded: the reviewer decided; the graph may be missing a link)")
                if p and p != s and p not in closure(s, dep):
                    warnings.append(f"{s}: {p} is not among the skills that build on it in the graph (loaded: the reviewer decided; the graph may be missing a link)")
        if problems:
            errors.append((r["line"], s or r["raw_skill"], "; ".join(problems)))
        else:
            good.append(r)
    return good, errors, warnings, unapproved


async def table_exists(db):
    return bool(await db.fetchval("SELECT to_regclass('skill_bridges') IS NOT NULL"))


async def sync(db, rows, dry_run=False):
    """Make the table hold exactly the given (validated, approved) rows. Returns the counts. A dry run creates and changes nothing."""
    exists = await table_exists(db)
    if not exists and not dry_run:
        await db.execute(DDL.read_text(encoding="utf-8"))
        exists = True
    current = {r["skill_id"]: dict(r) for r in await db.fetch("SELECT skill_id, predecessor_id, successor_id, note FROM skill_bridges")} if exists else {}
    wanted = {r["skill_id"]: r for r in rows}
    counts = {"inserted": 0, "updated": 0, "unchanged": 0, "removed": 0}
    for s, r in wanted.items():
        now = current.get(s)
        if not now:
            counts["inserted"] += 1
        elif (now["predecessor_id"], now["successor_id"], now["note"] or "") == (r["predecessor_id"], r["successor_id"], r["note"] or ""):
            counts["unchanged"] += 1
        else:
            counts["updated"] += 1
    counts["removed"] = sum(1 for s in current if s not in wanted)
    if dry_run:
        return counts
    async with db.transaction():
        for s, r in wanted.items():
            await db.execute("""
                INSERT INTO skill_bridges (skill_id, predecessor_id, successor_id, note, approved, updated_at) VALUES ($1, $2, $3, $4, TRUE, now())
                ON CONFLICT (skill_id) DO UPDATE SET predecessor_id = EXCLUDED.predecessor_id, successor_id = EXCLUDED.successor_id, note = EXCLUDED.note, approved = TRUE, updated_at = now()
            """, s, r["predecessor_id"], r["successor_id"], r["note"] or None)
        await db.execute("DELETE FROM skill_bridges WHERE NOT (skill_id = ANY($1::text[]))", list(wanted))
    return counts


async def main():
    ap = argparse.ArgumentParser(description="Load the reviewer's skill bridges into the app.", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--csv", help=f"the working file (default {WORKING.relative_to(ROOT)})")
    ap.add_argument("--init", action="store_true", help="create the working file from the starter (every row not approved)")
    ap.add_argument("--force", action="store_true", help="with --init: replace an existing working file")
    ap.add_argument("--from-review", metavar="SHEET", help="take the reviewer's decisions from the review sheet into the working file")
    ap.add_argument("--check", action="store_true", help="validate the approved rows against the knowledge base and change nothing")
    ap.add_argument("--dry-run", action="store_true", help="say what loading would change, change nothing")
    ac.add_db_args(ap)
    args = ap.parse_args()
    path = Path(args.csv) if args.csv else WORKING
    if args.init:
        if path.exists() and not args.force:
            print(f"{path} already exists: left alone (use --force to replace it).")
            return 0
        if not STARTER.exists():
            raise SystemExit(f"The starter file is missing: {STARTER}")
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(STARTER, path)
        print(f"Created {path} from the starter: {len(read_working(path))} proposed bridges, NONE approved yet. Edit the 'approved' column (write yes), or use --from-review with the reviewer's sheet.")
        return 0
    if args.from_review:
        decided, problems = read_review(args.from_review)
        base = read_working(path) if path.exists() else (read_working(STARTER) if STARTER.exists() else [])
        merged = merge(base, decided)
        write_working(path, merged)
        print(f"{len(decided)} skills with a reviewer's decision were taken into {path} ({sum(1 for r in merged if r['approved'])} approved in all, {len(merged)} rows).")
        for p in problems:
            print("  PROBLEM:", p)
        print("Next: python scripts\\load_bridges.py --check --env-file backend\\.env   (then without --check to load).")
        return 1 if problems else 0
    if not args.csv and not path.exists():
        print(f"No working file ({path.relative_to(ROOT)}): no curated bridges to load. Create it with:  python scripts\\load_bridges.py --init")
        return 0
    rows = read_working(path)
    db = await ac.connect(args)
    try:
        good, errors, warnings, unapproved = await validate(db, rows)
        print(f"{len(rows)} rows in {path.name}: {len(good)} approved and valid, {len(errors)} approved but WRONG, {unapproved} not approved.")
        for line, skill, msg in errors:
            print(f"  ERROR line {line} {skill}: {msg}")
        for w in warnings:
            print("  note:", w)
        if args.check:
            print("(--check: nothing was changed)")
        else:
            c = await sync(db, good, dry_run=args.dry_run)
            print(("WOULD " if args.dry_run else "") + f"{'change' if args.dry_run else 'changed'} the table: {c['inserted']} added, {c['updated']} updated, {c['unchanged']} unchanged, {c['removed']} removed.")
        return 1 if errors else 0
    finally:
        await db.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
