#!/usr/bin/env python3
"""
Checks a table of CURATED SKILL BRIDGES (for each skill: which skill the Beginners should work on, and which the Proficients) against the knowledge base BEFORE it is loaded.

    python scripts\\check_bridges.py --csv path\\to\\Curated_Skill_Bridges_FLN.csv --env-file backend\\.env

Reads the table tolerantly (an id may be followed by a description in brackets, a row may have no notes) and checks, for every row:
  - every skill id EXISTS in the knowledge base, is of the same subject, and its name in the table agrees with the knowledge base (a wrong id is the commonest fault);
  - the Beginners' skill is not ABOVE the anchor skill in grade, and the Proficients' is not BELOW it (the same rule the app enforces);
  - the Beginners' skill is in the anchor's prerequisite ancestry and the Proficients' in its descendants (otherwise the graph does not connect them: a CHECK, not an error);
  - whether it agrees with what the app derives today.
Writes docs/bridges_validation.csv (one row per table row, with the problems) and docs/skill_bridges_clean.csv (only ids, only the rows without errors). Changes nothing in the database.
"""
import argparse
import asyncio
import csv
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(HERE), str(ROOT / "backend")]
import anchor_common as ac                                  # noqa: E402

RANK = {"balvatika": 0, "grade_1": 1, "grade_2": 2, "grade_3": 3}
ID = re.compile(r"\b([NL]\d\.\d\.\d)\b")


def norm(s):
    return re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower().replace("≤", "<=")).split()


def sim(a, b):
    """How alike two skill names are, 0 to 1: the better of the character match and 'every word of the shorter name is in the longer one' (a shortened name is not a different skill)."""
    ta, tb = norm(a), norm(b)
    ratio = SequenceMatcher(None, " ".join(ta), " ".join(tb)).ratio()
    short, long_ = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    contained = len([w for w in short if w in long_]) / len(short) if short else 0
    return max(ratio, contained * 0.9)


def parse(path):
    """Rows as dicts: id, name, b_id, b_desc, p_id, p_desc, notes. Tolerant of '(description)' after an id and of missing notes."""
    text = Path(path).read_text(encoding="utf-8-sig")
    out = []
    for i, r in enumerate(csv.reader(text.splitlines()), 1):
        if not r or not r[0].strip() or r[0].strip().lower() in ("skill_id", "skill id"):
            continue
        r = [c.strip() for c in r] + [""] * 5
        def split(cell):
            m = ID.search(cell)
            desc = re.search(r"\((.*)\)", cell)
            return (m.group(1) if m else None), (desc.group(1).strip() if desc else "")
        b, bd = split(r[2]); p, pd = split(r[3])
        out.append({"line": i, "id": (ID.search(r[0]) or [None, None])[1] if ID.search(r[0]) else None, "name": r[1], "b_id": b, "b_desc": bd, "p_id": p, "p_desc": pd, "notes": r[4], "raw_b": r[2], "raw_p": r[3]})
    return out


async def main():
    ap = argparse.ArgumentParser(description="Check a table of curated skill bridges against the knowledge base.")
    ap.add_argument("--csv", default=str(ROOT / "docs" / "Curated_Skill_Bridges_FLN.csv"), help="the table to check: a CSV you saved (for example from a Google Sheet: File > Download > Comma Separated Values). Default: docs\\Curated_Skill_Bridges_FLN.csv")
    ac.add_db_args(ap)
    args = ap.parse_args()
    if not Path(args.csv).exists():
        raise SystemExit(f"File not found: {args.csv}\n"
                         f"  Save your table as a CSV (in the Google Sheet: File > Download > Comma Separated Values), then give its FULL path, for example\n"
                         f"  python scripts\\check_bridges.py --csv C:\\dev\\Ankur-Saathi\\docs\\Curated_Skill_Bridges_FLN.csv --env-file backend\\.env\n"
                         f"  (or save it as docs\\Curated_Skill_Bridges_FLN.csv and leave --csv out). 'path\\to\\your_table.csv' in the instructions was only an EXAMPLE of a path.")
    rows = parse(args.csv)
    db = await ac.connect(args)
    from app.services import group_skills as gs
    comps = {r["id"]: dict(r) for r in await db.fetch("SELECT id, name_en, grade_level, subdomain_id FROM competencies")}
    edges = [(r["competency_id"], r["prerequisite_id"]) for r in await db.fetch("SELECT competency_id, prerequisite_id FROM competency_prerequisites")]
    pre, dep = {}, {}
    for c, p in edges:
        pre.setdefault(c, set()).add(p); dep.setdefault(p, set()).add(c)
    def closure(start, graph):
        seen, stack = set(), list(graph.get(start, ()))
        while stack:
            x = stack.pop()
            if x not in seen:
                seen.add(x); stack.extend(graph.get(x, ()))
        return seen
    report, clean, seen_ids = [], [], {}
    for r in rows:
        errs, checks = [], []
        s, b, p = r["id"], r["b_id"], r["p_id"]
        for label, k in (("skill", s), ("Beginners", b), ("Proficients", p)):
            if not k:
                errs.append(f"{label}: no skill id found in '{r['raw_b'] if label == 'Beginners' else r['raw_p'] if label == 'Proficients' else r['name']}'")
            elif k not in comps:
                errs.append(f"{label}: {k} DOES NOT EXIST in the knowledge base")
        if s in seen_ids:
            errs.append(f"{s} appears twice (lines {seen_ids[s]} and {r['line']})")
        seen_ids.setdefault(s, r["line"])
        if s in comps:
            sn = sim(r["name"], comps[s]["name_en"])
            if sn < 0.35:
                errs.append(f"the id {s} is a DIFFERENT skill in the knowledge base: table '{r['name'][:46]}' / KB '{comps[s]['name_en'][:46]}': WRONG ID?")
            elif sn < 0.65:
                checks.append(f"{s}: the name is worded differently: table '{r['name'][:46]}' / KB '{comps[s]['name_en'][:46]}'")
            for label, k, desc in (("Beginners", b, r["b_desc"]), ("Proficients", p, r["p_desc"])):
                if k in comps:
                    if k[0] != s[0]:
                        errs.append(f"{label}: {k} is of another subject than {s}")
                    if desc and not re.search(r"\bstays?\b", desc, re.I):          # '(Stays on skill)' is a note, not a description of a skill
                        sd = sim(desc, comps[k]["name_en"])
                        if sd < 0.30:
                            errs.append(f"{label}: {k} in the KB is '{comps[k]['name_en'][:46]}' but the table describes '{desc[:46]}': WRONG ID?")
                        elif sd < 0.50:
                            checks.append(f"{label}: {k} is '{comps[k]['name_en'][:40]}' in the KB, the table says '{desc[:40]}'")
            if b in comps and RANK.get(comps[b]["grade_level"], 9) > RANK.get(comps[s]["grade_level"], 9):
                errs.append(f"Beginners: {b} is of a HIGHER grade than {s}")
            if p in comps and RANK.get(comps[p]["grade_level"], 0) < RANK.get(comps[s]["grade_level"], 0):
                errs.append(f"Proficients: {p} is of a LOWER grade than {s}")
            if p == s:
                checks.append("Proficients stay on the skill itself")
            if b in comps and b != s and b not in closure(s, pre):
                checks.append(f"Beginners: {b} is NOT among {s}'s prerequisites (the graph does not connect them: the app's lists would not offer it)")
            if p in comps and p != s and p not in closure(s, dep):
                checks.append(f"Proficients: {p} is NOT among the skills that build on {s} (not connected in the graph)")
        now_b = await gs.derived_beginner_id(db, s) if s in comps else None
        now_p = await gs.derived_proficient_id(db, s) if s in comps else None
        status = "ERROR" if errs else ("CHECK" if checks else "OK")
        report.append({"line": r["line"], "skill": s, "status": status, "problems": " | ".join(errs), "to_check": " | ".join(checks),
                       "Beginners_in_table": b, "Beginners_in_KB": (comps.get(b) or {}).get("name_en", ""), "Proficients_in_table": p, "Proficients_in_KB": (comps.get(p) or {}).get("name_en", ""),
                       "app_now_Beginners": now_b, "app_now_Proficients": now_p, "Beginners_same_as_app": "" if not b else ("same" if b == now_b else "differs"), "Proficients_same_as_app": "" if not p else ("same" if p == now_p else "differs"), "notes": r["notes"]})
        if not errs:
            clean.append({"skill_id": s, "predecessor_id": b, "successor_id": p, "note": r["notes"], "status": status})
    out = ROOT / "docs"; out.mkdir(exist_ok=True)
    for name, data in (("bridges_validation.csv", report), ("skill_bridges_clean.csv", clean)):
        with open(out / name, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0])); w.writeheader(); w.writerows(data)
    n = lambda st: sum(1 for x in report if x["status"] == st)
    print(f"{len(report)} rows read: {n('OK')} OK, {n('CHECK')} CHECK (valid ids, the graph does not connect them), {n('ERROR')} ERROR.")
    print(f"Written: docs/bridges_validation.csv (every row, with the problems) and docs/skill_bridges_clean.csv ({len(clean)} rows without errors, ids only).")
    await db.close()
    return report, comps


if __name__ == "__main__":
    asyncio.run(main())
