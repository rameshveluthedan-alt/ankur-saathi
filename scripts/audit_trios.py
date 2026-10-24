#!/usr/bin/env python3
"""
Audit of the knowledge graph AS THE APP USES IT.

For every skill, the plan puts the Beginners on its PREDECESSOR and the Proficients on its SUCCESSOR. The app derives them with a simple rule (group_skills.derived_beginner_id / derived_proficient_id: the first hard
prerequisite by id, and the first hard dependent by its place in its strand). Teachers trust the three skills only if they read like chapters of one story, so this script lists, for every skill, what the app derives,
flags the cases a person should look at, and proposes a better pick by a stated rule. It changes nothing in the database or the app.

    python scripts\\audit_trios.py --env-file backend\\.env

Writes docs/graph_audit_trios.csv (open it in Excel: one row per skill) and prints a summary.
"""
import argparse
import asyncio
import csv
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(HERE), str(ROOT / "backend")]
import anchor_common as ac                                  # noqa: E402

RANK = {"balvatika": 0, "grade_1": 1, "grade_2": 2, "grade_3": 3}
OUT = ROOT / "docs" / "graph_audit_trios.csv"


def best_predecessor(s, hard_pre, sub, rank, order):
    """The proposed bridge: among the hard prerequisites, the one in the SAME strand first, then the closest in grade (never above the skill), then the latest in its strand (closest before the skill), then the id."""
    cands = hard_pre.get(s, [])
    if not cands:
        return None
    def key(c):
        gap = rank[s] - rank[c]
        return (0 if sub[c] == sub[s] else 1, 0 if gap >= 0 else 1, gap if gap >= 0 else 9, -order[c], c)
    return min(cands, key=key)


def best_successor(s, hard_dep, sub, rank, order):
    """The proposed extension: among the hard dependents, the one in the SAME strand first, then the closest in grade (never below the skill), then the earliest in its strand, then the id."""
    cands = hard_dep.get(s, [])
    if not cands:
        return None
    def key(d):
        gap = rank[d] - rank[s]
        return (0 if sub[d] == sub[s] else 1, 0 if gap >= 0 else 1, gap if gap >= 0 else 9, order[d], d)
    return min(cands, key=key)


async def main():
    ap = argparse.ArgumentParser(description="Audit the predecessor and successor the app derives for every skill.")
    ac.add_db_args(ap)
    args = ap.parse_args()
    db = await ac.connect(args)
    from app.services import group_skills as gs             # the REAL rules the plan uses
    comps = {r["id"]: dict(r) for r in await db.fetch("SELECT id, subdomain_id, name_en, name_hi, grade_level, sort_order FROM competencies WHERE is_active IS NOT FALSE ORDER BY id")}
    edges = [dict(r) for r in await db.fetch("SELECT competency_id, prerequisite_id, prerequisite_type FROM competency_prerequisites")]
    sub = {k: v["subdomain_id"] for k, v in comps.items()}
    rank = {k: RANK.get(v["grade_level"], 9) for k, v in comps.items()}
    order = {k: v["sort_order"] or 0 for k, v in comps.items()}
    hard_pre, soft_pre, hard_dep = {}, {}, {}
    for e in edges:
        c, p = e["competency_id"], e["prerequisite_id"]
        if c not in comps or p not in comps:
            continue
        if e["prerequisite_type"] == "hard":
            hard_pre.setdefault(c, []).append(p)
            hard_dep.setdefault(p, []).append(c)
        else:
            soft_pre.setdefault(c, []).append(p)
    rows, tally, examples = [], Counter(), {}
    for s, c in comps.items():
        cur_b, cur_x = await gs.derived_beginner_id(db, s), await gs.derived_proficient_id(db, s)
        sug_b = best_predecessor(s, hard_pre, sub, rank, order) or s
        sug_x = best_successor(s, hard_dep, sub, rank, order) or s
        flags = []
        if not hard_pre.get(s):
            flags.append("NO_BRIDGE: no hard prerequisite, the Beginners work on the skill itself" + (" (a SOFT prerequisite exists: " + ",".join(soft_pre[s]) + ")" if soft_pre.get(s) else ""))
        if len(hard_pre.get(s, [])) >= 2:
            flags.append("MANY_PREREQS: " + ",".join(sorted(hard_pre[s])) + " (the app takes the first by id)")
        if cur_b != s and sub[cur_b] != sub[s] and any(sub[p] == sub[s] for p in hard_pre.get(s, [])):
            flags.append("PREDECESSOR_OTHER_STRAND: a prerequisite in the same strand exists")
        if cur_b != s and rank[s] - rank[cur_b] >= 2:
            flags.append(f"PREDECESSOR_FAR: {rank[s] - rank[cur_b]} grades below")
        if cur_b != s and rank[cur_b] > rank[s]:
            flags.append("DATA: a prerequisite of a HIGHER grade than the skill")
        if not hard_dep.get(s):
            flags.append("NO_EXTENSION: nothing depends on it, the Proficients work on the skill itself")
        if len(hard_dep.get(s, [])) >= 2:
            flags.append("MANY_DEPENDENTS: " + ",".join(sorted(hard_dep[s])) + " (the app takes the first by its place in its strand)")
        if cur_x != s and sub[cur_x] != sub[s] and any(sub[d] == sub[s] for d in hard_dep.get(s, [])):
            flags.append("SUCCESSOR_OTHER_STRAND: a dependent in the same strand exists")
        if cur_x != s and rank[cur_x] - rank[s] >= 2:
            flags.append(f"SUCCESSOR_CLIFF: {rank[cur_x] - rank[s]} grades above")
        changes = (cur_b != sug_b) or (cur_x != sug_x)
        for f in flags:
            tally[f.split(":")[0]] += 1
            examples.setdefault(f.split(":")[0], []).append(s)
        if cur_b != sug_b:
            tally["PROPOSAL_CHANGES_PREDECESSOR"] += 1
        if cur_x != sug_x:
            tally["PROPOSAL_CHANGES_SUCCESSOR"] += 1
        nm = lambda k: f"{k} {comps[k]['name_en']}" if k in comps else k
        names = lambda ids: " ; ".join(nm(i) for i in sorted(ids))
        # a decision is needed where the app's pick is ARBITRARY (several candidates: it takes the first), in ANOTHER STRAND, or where a skill above Balvatika has NO predecessor at all (a gap in the graph).
        # "no successor" is only information: many skills end a chain.
        needs = any(x in f for f in flags for x in ("MANY_PREREQS", "MANY_DEPENDENTS", "OTHER_STRAND")) or (not hard_pre.get(s) and c["grade_level"] != "balvatika")
        priority = "1" if (any("OTHER_STRAND" in f for f in flags) or (not hard_pre.get(s) and c["grade_level"] != "balvatika")) else ("2" if needs else "")
        rows.append({"skill": s, "name_en": c["name_en"], "name_hi": c["name_hi"], "grade": c["grade_level"], "strand": c["subdomain_id"],
                     "needs_a_decision": "YES" if needs else "", "priority (1 = look first)": priority, "hard_prerequisites (candidate predecessors)": names(hard_pre.get(s, [])), "soft_prerequisites": names(soft_pre.get(s, [])), "hard_dependents (candidate successors)": names(hard_dep.get(s, [])),
                     "app_now_Beginners": nm(cur_b), "app_now_Proficients": nm(cur_x), "proposed_Beginners": nm(sug_b), "proposed_Proficients": nm(sug_x),
                     "proposal_differs": "YES" if changes else "", "flags": " | ".join(flags), "your_decision_Beginners": "", "your_decision_Proficients": "", "notes": ""})
    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} skills audited ({sum(1 for k in comps if k.startswith('N'))} numeracy, {sum(1 for k in comps if not k.startswith('N'))} literacy). Written: {OUT}\n")
    for subject, test in (("numeracy", lambda k: k.startswith("N")), ("literacy", lambda k: not k.startswith("N"))):
        sel = [r for r in rows if r["needs_a_decision"] and test(r["skill"])]
        print(f"  {len(sel):>3} {subject} skills are marked needs_a_decision = YES: priority 1 (another strand, or no predecessor above Balvatika): {sum(1 for r in sel if r['priority (1 = look first)'] == '1')}; priority 2 (several candidates in the same strand): {sum(1 for r in sel if r['priority (1 = look first)'] == '2')}")
    print("\nWhat a person should look at (number of skills):")
    for k, n in sorted(tally.items(), key=lambda kv: -kv[1]):
        print(f"  {n:>3}  {k}" + (f"   e.g. {', '.join(examples[k][:5])}" if k in examples else ""))
    shown = [r for r in rows if r["proposal_differs"]][:8]
    print("\nWhere the proposed rule differs from what the app does now (first 8):")
    for r in shown:
        print(f"  {r['skill']:<7} Beginners: {r['app_now_Beginners'][:48]:<48} -> {r['proposed_Beginners'][:48]}")
        print(f"          Proficients: {r['app_now_Proficients'][:46]:<46} -> {r['proposed_Proficients'][:48]}")
    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
