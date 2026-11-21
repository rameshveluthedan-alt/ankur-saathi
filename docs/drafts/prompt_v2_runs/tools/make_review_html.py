"""
One readable HTML file of the prompt-v2 test plans (docs/drafts/prompt_v2_runs/*.plan.json), for a person to read or print: per plan, the
anchor, the session block by block (minutes, pace, I Do / We Do / You Do, what the other groups do, the show-me questions with their answers),
each group's worksheet with answers and the mistake each core problem reveals, the preparation list and "Why this plan?". No AI, no database.

    python docs/drafts/prompt_v2_runs/tools/make_review_html.py [--out PATH]
"""
import sys as _sys
for _s in (_sys.stdout, _sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")
import argparse
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLANS = HERE.parent
ORDER = ["N2.3.2", "L2.7.2", "N0.1.1", "L2.5.1"]
NAMES = {"N2.3.2": "Two-digit addition with carry (maths, written)", "L2.7.2": "Writing connected sentences (Hindi, writing)",
         "N0.1.1": "Sorting by one attribute (maths, observed)", "L2.5.1": "Reading aloud (Hindi, fluency)"}
GROUP = {"beginner": "शुरुआती · Beginners", "progressor": "प्रगतिशील · Progressors", "proficient": "दक्ष · Proficients"}
PACE = {"recall": "Recall", "i_do": "I Do", "we_do": "We Do", "show_me": "Show-me", "you_do": "You Do"}


def e(x) -> str:
    return html.escape(str(x if x is not None else "")).replace("\n", "<br>")


def block_html(b: dict, n: int) -> str:
    t = b.get("type")
    head = f"<b>{e(b.get('time_start'))}</b> · {e(b.get('duration_minutes'))} min"
    if t != "teach":
        label = {"anchor": "Anchor (whole class)", "setup": "Setup", "transition": "Transition", "reteach": "Re-teach"}.get(t, t)
        return f"<div class='blk minor'>{head} · <b>{label}</b>{('<div class=script>' + e(b.get('script_hi')) + '</div>') if b.get('script_hi') else ''}</div>"
    g = b.get("teach_group")
    pace = " · ".join(f"{PACE.get(p['key'], p['key'])} {p['min']}" for p in b.get("pace") or [])
    tp = b.get("talking_points") or {}
    rows = "".join(f"<tr><th>{k}</th><td>{e(tp.get(v))}</td></tr>" for k, v in (("I Do", "i_do_hi"), ("We Do", "we_do_hi"), ("You Do", "you_do_hi")) if tp.get(v))
    cfu = "".join(
        f"<li>{e(q.get('question_hi'))} <span class=ans>→ {e(q.get('expected_hi'))}</span>"
        + "".join(f"<div class=listen>listen for: {e(x.get('wrong_answer_hi'))} ({e(x.get('misconception_name_en') or x.get('misconception_id'))})</div>" for x in q.get("listen_for") or [])
        + "</li>" for q in b.get("cfu") or [])
    rt = " <span class=tag>RE-TEACH</span>" if b.get("reteach") else ""
    return (f"<div class='blk teach {g}'><div class=bh>{head} · <b>Teach: {GROUP.get(g, g)}</b>{rt}{(' <span class=pace>⏱ ' + pace + '</span>') if pace else ''}</div>"
            f"<table class=tp>{rows}</table>"
            + (f"<div class=others><b>Meanwhile:</b> {e(b.get('other_groups_hi'))}</div>" if b.get("other_groups_hi") else "")
            + (f"<div class=cfu><b>Show-me questions</b><ol>{cfu}</ol></div>" if cfu else "") + "</div>")


def sheet_html(g: str, ws: dict) -> str:
    kind = ws.get("sheet_kind") or "3 + N"
    rc = ws.get("required_count")
    probs = "".join(
        f"<tr class='{'core' if (rc and p.get('number', 99) <= rc) else 'extra'}'><td>{e(p.get('number'))}</td><td>{e(p.get('problem_hi'))}</td>"
        f"<td class=ans>{e(p.get('answer'))}</td><td class=diag>{e(p.get('diagnostic_for_misconception') or '')}</td></tr>" for p in ws.get("problems") or [])
    extra = ""
    if ws.get("passage_block"):
        extra += f"<div class=passage><b>{e(ws['passage_block'].get('title'))}</b><br>{e(ws['passage_block'].get('text'))}</div>"
    if ws.get("writing_task"):
        extra += f"<div><b>Writing task:</b> {e(ws['writing_task'].get('topic_hi'))}</div>"
    if ws.get("checklist"):
        extra += "<div><b>Checklist:</b> " + " · ".join(e(c.get("item_hi")) for c in ws["checklist"]) + "</div>"
    if ws.get("observe"):
        o = ws["observe"]
        extra += f"<div class=observe><b>Task to watch:</b> {e(o.get('task_hi'))}<br><b>Look for:</b> " + " · ".join(
            f"{k}: {e(v)}" for k, v in (o.get("look_for") or {}).items()) + "</div>"
    return (f"<div class=sheet><h4>{GROUP.get(g, g)} <span class=kind>{e(kind)} sheet · required {e(rc)}</span></h4>"
            f"<div class=instr>{e(ws.get('instructions_hi'))}</div>{extra}"
            + (f"<table class=probs><tr><th>#</th><th>problem</th><th>answer</th><th>mistake it reveals</th></tr>{probs}</table>" if probs else "") + "</div>")


def plan_html(skill: str, minutes: int, p: dict) -> str:
    a = p.get("anchor") or {}
    gs = p.get("group_skills") or {}
    blocks = (p.get("rotation_schedule") or {}).get("blocks") or []
    total = sum(int(b.get("duration_minutes") or 0) for b in blocks)
    out = [f"<section id='{skill}_{minutes}'><h2>{skill} · {minutes} minutes <small>{e(NAMES.get(skill, ''))}</small></h2>",
           f"<p class=meta>Groups: {' · '.join(f'{GROUP[g]}: {e(gs.get(g))}' for g in GROUP)} · blocks add up to {total} min</p>",
           "<h3>Anchor (whole class)</h3><div class=anchor>",
           f"<p><b>{e(a.get('title_hi'))}</b></p><p>{e(a.get('narration_hi'))}</p><p><b>Opening:</b> {e(a.get('opening_question_hi'))}</p><ul>",
           "".join(f"<li><b>{GROUP[g]}:</b> {e(a.get(g + '_participation_hi'))}</li>" for g in GROUP),
           f"</ul><p><b>Closing:</b> {e(a.get('closing_question_hi'))}</p></div>",
           "<h3>The session</h3>", "".join(block_html(b, i) for i, b in enumerate(blocks)),
           "<h3>Worksheets</h3>", "".join(sheet_html(g, (p.get("worksheets") or {}).get(g) or {}) for g in GROUP),
           "<h3>Before class</h3><ul>" + "".join(f"<li>{e(x)}</li>" for x in p.get("prep_hi") or []) + "</ul>",
           "<h3>Why this plan?</h3>" + "".join(f"<div class=why><b>{e(i.get('title_en') or i.get('title_hi'))}</b><br>{e(i.get('body_en'))}</div>"
                                               for i in (p.get("explainability") or {}).get("items") or []),
           "</section>"]
    return "".join(out)


CSS = """body{font-family:'Noto Sans Devanagari','Nirmala UI',Arial,sans-serif;max-width:980px;margin:24px auto;padding:0 16px;color:#222;line-height:1.5}
h1{font-size:22px}h2{border-top:3px solid #2d6a4f;padding-top:14px;margin-top:40px}h2 small{font-weight:normal;color:#666;font-size:14px}
h3{color:#2d6a4f;margin-bottom:6px}.meta{color:#555;font-size:13px}.anchor,.why{background:#f4f8f5;padding:8px 12px;border-radius:6px;margin:6px 0}
.blk{border:1px solid #ddd;border-radius:6px;padding:8px 10px;margin:6px 0}.blk.minor{background:#fafafa;color:#555;font-size:13px}
.blk.beginner{border-left:5px solid #e07a5f}.blk.progressor{border-left:5px solid #3d85c6}.blk.proficient{border-left:5px solid #6aa84f}
.pace{background:#eef;border-radius:8px;padding:1px 6px;font-size:12px}.tag{background:#fde2e2;color:#a00;border-radius:6px;padding:0 6px;font-size:12px}
table.tp th{text-align:left;vertical-align:top;width:70px;color:#2d6a4f}table{border-collapse:collapse;width:100%}
.probs td,.probs th{border:1px solid #ddd;padding:3px 6px;font-size:14px}.probs tr.extra{color:#777}.ans{color:#0a6}.diag{font-size:12px;color:#a50}
.others{font-size:13px;color:#444;margin-top:4px}.cfu{margin-top:4px}.listen{font-size:12px;color:#a50}.sheet{border:1px dashed #bbb;padding:6px 10px;margin:8px 0;border-radius:6px}
.kind{font-weight:normal;font-size:12px;color:#666}.passage,.observe{background:#fffbea;padding:6px;margin:4px 0;font-size:14px}.instr{font-size:13px;color:#444}
.script{font-size:13px;color:#444}nav a{margin-right:10px}@media print{section{page-break-before:always}nav{display:none}}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(PLANS / "REVIEW_PLANS_v2.html"))
    out = Path(ap.parse_args().out)
    files = [(s, m, PLANS / f"{s}_{m}.plan.json") for s in ORDER for m in (45, 60, 90)]
    nav = " ".join(f"<a href='#{s}_{m}'>{s} {m}</a>" for s, m, f in files if f.is_file())
    body = "".join(plan_html(s, m, json.loads(f.read_text(encoding="utf-8"))) for s, m, f in files if f.is_file())
    doc = (f"<!doctype html><html lang=hi><head><meta charset=utf-8><title>Prompt v2: the 12 test plans</title><style>{CSS}</style></head><body>"
           "<h1>Prompt v2: the 12 test plans (real model, made with the final code, 20-21 Nov 2026)</h1>"
           "<p>Four skills at 45, 60 and 90 minutes, as the app saved them after all its code checks. "
           "Core problems are in black, extras in grey; the green answers are the answer key; the brown code is the mistake a core problem reveals.</p>"
           f"<nav>{nav}</nav>{body}</body></html>")
    out.write_text(doc, encoding="utf-8")
    print(f"written: {out} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
