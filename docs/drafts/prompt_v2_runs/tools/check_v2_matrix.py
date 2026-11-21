"""Reads out/ from run_v2_matrix.py and checks each plan against what prompt v2 asks for. No AI, no database."""
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")
import json
import re
from pathlib import Path

import os as _os
OUT = Path(__file__).resolve().parent / _os.environ.get("V2_OUT", "out")
SONNET = {"in": float(_os.environ.get("P_IN", 2.0)), "out": float(_os.environ.get("P_OUT", 10.0)), "cr": float(_os.environ.get("P_CR", 0.10)), "cw": float(_os.environ.get("P_CW", 2.5))}
EXTRAS = {45: 1, 60: 2, 90: 3}
first_system = None
total = 0.0
rows = []
for f in sorted(OUT.glob("*.plan.json"), key=lambda p: (int(p.stem.split("_")[1].split(".")[0]), p.stem)):
    name = f.name.replace(".plan.json", "")
    skill, m = name.split("_")
    m = int(m)
    plan = json.loads(f.read_text(encoding="utf-8")) or {}
    reply = json.loads((OUT / f"{name}.reply.json").read_text(encoding="utf-8"))
    calls = json.loads((OUT / f"{name}.calls.json").read_text(encoding="utf-8"))
    log = (OUT / f"{name}.log.txt").read_text(encoding="utf-8")
    print(f"\n=== {name}  (served_from={plan.get('served_from')}, session_minutes={plan.get('session_minutes')})")
    cost = 0.0
    for c in calls:
        u = c["usage"]
        cc = ((u.get("input_tokens") or 0) * SONNET["in"] + (u.get("output_tokens") or 0) * SONNET["out"]
              + (u.get("cache_read_input_tokens") or 0) * SONNET["cr"] + (u.get("cache_creation_input_tokens") or 0) * SONNET["cw"]) / 1e6
        cost += cc
        kind = "plan" if isinstance(c.get("system"), list) else "helper"
        print(f"  call ({kind}, {c['seconds']} s): in {u.get('input_tokens')}, out {u.get('output_tokens')}, cache read {u.get('cache_read_input_tokens')}, cache write {u.get('cache_creation_input_tokens')}  ${cc:.4f}  stop={c['stop_reason']}")
        if kind == "plan":
            sysv = json.dumps(c["system"], ensure_ascii=False)
            if first_system is None:
                first_system = {}
            dom = skill[0]
            if dom in first_system and first_system[dom] != sysv:
                print("  !! the system block differs from the first plan's of this subject (no cache read possible)")
            first_system.setdefault(dom, sysv)
            user = c.get("user") or ""
            if re.search(r"\bRoll\b", user):
                print("  !! 'Roll' appears in the request")
    total += cost
    print(f"  cost ${cost:.4f}")
    if not plan:
        print("  !! no plan saved", reply)
        continue
    issues = []
    blocks = (plan.get("rotation_schedule") or {}).get("blocks") or []
    teach = [b for b in blocks if b.get("type") == "teach"]
    print("  blocks: " + ", ".join(f"{b.get('type')}{'/' + b['teach_group'] if b.get('teach_group') else ''} {b.get('duration_minutes')}" for b in blocks),
          f"= {sum(int(b.get('duration_minutes') or 0) for b in blocks)} min")
    for g in ("beginner", "progressor", "proficient"):
        ws = (plan.get("worksheets") or {}).get(g) or {}
        probs = ws.get("problems") or []
        kind = ws.get("sheet_kind") or "(3+N)"
        diags = [(p.get("number"), p.get("diagnostic_for_misconception")) for p in probs if p.get("diagnostic_for_misconception")]
        skill_g = (plan.get("group_skills") or {}).get(g)
        foreign = [d for _, d in diags if skill_g and not str(d).startswith(skill_g + "-")]
        tb = next((b for b in teach if b.get("teach_group") == g), {})
        you = ((tb.get("talking_points") or {}).get("you_do_hi") or "")
        says = re.findall(r"(\d+)\s*(?:से|-|–)\s*(\d+)", you)
        print(f"  {g:10} {skill_g:8} {kind:12} rc={ws.get('required_count')} n={len(probs)} diags={diags}  you_do ranges={says}")
        if kind == "(3+N)":
            if ws.get("required_count") != 3:
                issues.append(f"{g}: required_count {ws.get('required_count')}")
            if len(probs) != 3 + EXTRAS[m]:
                issues.append(f"{g}: {len(probs)} problems, not 3+{EXTRAS[m]}")
            if any(n and n > 3 for n, _ in diags):
                issues.append(f"{g}: a diagnostic on an extra")
            if probs and not diags:
                issues.append(f"{g}: no diagnostic on the core")
            if says and not any(a == "1" and b == "3" for a, b in says):
                issues.append(f"{g}: the You Do sends to {says}, not 1-3")
        if foreign:
            issues.append(f"{g}: foreign mistake IDs left {foreign}")
    text = json.dumps(plan, ensure_ascii=False)
    for pat, what in ((r"मैं [^\"]{0,40}(लिखता|लिखती|बोलता|बोलती|करता|करती) हूँ", "first-person teacher line"), ("बोर्ड पर देखो", "'बोर्ड पर देखो'")):
        if re.search(pat, text):
            issues.append(what)
    items = (plan.get("explainability") or {}).get("items") or []
    rem = (plan.get("review_prompts") or {}).get("observation_reminders_hi")
    print(f"  explainability items: {len(items)} ({', '.join(str(i.get('id') or i.get('title_en'))[:30] for i in items)}); observation reminders: {len(rem or [])}")
    w = reply.get("validation_warnings") or []
    print(f"  validation warnings ({len(w)}): " + ("; ".join(w) if w else "none"))
    for line in log.splitlines():
        if any(k in line for k in ("Diagnostic IDs:", "Worksheet repair:", "CFU", "top-up", "Stick repair:")):
            print("   log:", line.strip()[:220])
    print("  ISSUES: " + ("; ".join(issues) if issues else "none"))
    rows.append((name, len(issues), round(cost, 4)))
print(f"\nTOTAL ${total:.3f} over {len(rows)} plans")
for r in rows:
    print(" ", r)
