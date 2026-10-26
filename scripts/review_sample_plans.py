#!/usr/bin/env python3
"""
Reading and signing the recorded sample plans (db/seeds/sample_plans).

A recorded plan is what a teacher, or an evaluator, sees when the AI limit is reached, so a person who reads Hindi must read it first. The files are JSON, which is no way to read a lesson, and
signing one by hand (a name inside a file full of quotation marks) is how a file gets broken. This does both:

    python scripts/review_sample_plans.py list                              which plans there are, and which still need a reader
    python scripts/review_sample_plans.py sheet L2.5.1                      writes docs/batch/review/L2.5.1.html: open it in a browser and read it
    python scripts/review_sample_plans.py sheet                             one sheet for every plan nobody has read and signed yet (with warnings or without)
    python scripts/review_sample_plans.py sign L2.5.1 --by "Vaishnavi"      writes "Vaishnavi, 2026-10-26" into the file, after she has read it

The sheet shows EVERY piece of text in the plan, in the order a teacher meets it, with the plan's warnings at the top. Signing does not change anything else in the file.
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import argparse
import copy
import html
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "prompts"))
PLANS = ROOT / "db" / "seeds" / "sample_plans"
SHEETS = ROOT / "docs" / "batch" / "review"

# the order a teacher meets a plan; anything else in the file follows
ORDER = ["anchor", "prep_hi", "rotation_schedule", "classroom_management", "worksheets", "review_prompts", "explainability"]
TITLES = {"anchor": "The story or activity (anchor)", "prep_hi": "Preparation", "rotation_schedule": "The lesson, block by block", "classroom_management": "Classroom management",
          "worksheets": "Worksheets", "review_prompts": "Review prompts", "explainability": "Why the plan is like this (shown to the teacher)"}


def status_of(plan) -> str:
    """'stub' (made by the fake model: never acceptable), 'reviewed' (a person has read it and signed), 'needs review' (nobody has read it, and the checks raised warnings), or 'not yet read'
    (nobody has read it; the checks raised none). EVERY plan must be read: the checks cover sums, structure and repeated wording, not whether the Hindi is natural or the story suits the children."""
    if not isinstance(plan, dict):
        return "invalid"
    if plan.get("_stub"):
        return "stub"
    if plan.get("_reviewed_by"):
        return "reviewed"
    return "needs review" if plan.get("_recorded_warnings") else "not yet read"


def sign_plan(plan: dict, by: str, today: str) -> dict:
    """The plan with `_reviewed_by` set to the reader's name and the date. Nothing else changes. A blank name, or a plan from the fake model, is refused."""
    by = (by or "").strip()
    if not by:
        raise ValueError("a name is needed: --by \"Name\"")
    if plan.get("_stub"):
        raise ValueError("this plan was made by the fake model (_stub): it is not a recorded plan and cannot be signed")
    out = dict(plan)
    out["_reviewed_by"] = f"{by}, {today}"
    return out


def _label(key: str) -> str:
    k = str(key)
    for suffix, text in (("_hi", " (Hindi)"), ("_en", " (English)")):
        if k.endswith(suffix):
            return k[: -len(suffix)].replace("_", " ") + text
    return k.replace("_", " ")


def as_teacher_sees(plan: dict):
    """(the plan as a teacher will see it, how many words the polite-Hindi pass changed). The app replays a recorded plan through that pass (prompts/hindi_style.py), so 'गिनो' is shown as 'गिनें': a reader
    judging the raw file would reject a plan for something the app already fixes. The file itself is never changed by this."""
    try:
        import hindi_style
    except ImportError:
        return plan, None
    shown = copy.deepcopy(plan)
    changes = hindi_style.soften_plan(shown)
    n = sum(len(v) if isinstance(v, (list, tuple, dict)) else int(v) for v in changes.values()) if isinstance(changes, dict) else None
    return shown, n


def _empty(v) -> bool:
    return v is None or v == "" or v == [] or v == {}


def _node(value, key=None) -> str:
    """A value as nested HTML: text as it is (escaped), lists as lists, objects as labelled lists. Every piece of text is shown; fields with nothing in them are not listed."""
    esc = html.escape
    head = f"<b>{esc(_label(key))}</b>" if key is not None else ""
    if isinstance(value, dict):
        return f"{head}<ul>" + "".join(f"<li>{_node(v, k)}</li>" for k, v in value.items() if not _empty(v)) + "</ul>"
    if isinstance(value, list):
        if all(not isinstance(v, (dict, list)) for v in value):
            return f"{head}<ul>" + "".join(f'<li><span lang="hi">{esc(str(v))}</span></li>' for v in value if not _empty(v)) + "</ul>"
        return f"{head}<ol>" + "".join(f"<li>{_node(v)}</li>" for v in value if not _empty(v)) + "</ol>"
    body = f'<span lang="hi">{esc("" if value is None else str(value))}</span>'
    return f"{head}: {body}" if key is not None else body


def render_sheet(plan: dict, skill: str, today: str = "") -> str:
    """One readable page for a recorded plan: its warnings first, then every part in the order a teacher meets it, then what to do after reading."""
    esc = html.escape
    warnings = plan.get("_recorded_warnings") or []
    shown, n_changed = as_teacher_sees(plan)
    sections = []
    keys = [k for k in ORDER if k in shown] + [k for k in shown if k not in ORDER and not str(k).startswith("_")]
    for k in keys:
        sections.append(f"<section><h2>{esc(TITLES.get(k, _label(k)))}</h2>{_node(shown[k])}</section>")
    seen_note = (f"<p class='note'>This is the plan <b>as a teacher will see it</b>: the app's polite-Hindi pass has already been applied ({n_changed} wording changes, for example informal commands made polite). "
                 "Judge this text, not the file.</p>") if n_changed is not None else "<p class='note'>The polite-Hindi pass could not be loaded: this is the recorded text as it is.</p>"
    warn_html = ("<div class='warn'><h2>Warnings the checks raised about this plan</h2><ul>" + "".join(f"<li lang='hi'>{esc(str(w))}</li>" for w in warnings) +
                 "</ul><p>A worksheet question that repeats five words from the lesson can let a child copy; a problem beyond the required number is not counted. Say whether these matter.</p></div>") if warnings else \
        "<div class='ok'>The checks raised no warnings about this plan. That does not mean it has been read: the checks cover sums, structure and repeated wording, not whether the Hindi is natural or the story suits the children.</div>"
    state = status_of(plan)
    sign = (f"<div class='sign'><h2>What to check</h2><ol>"
            "<li><b>The Hindi</b> is natural and polite, as a teacher would really say it to children of this age (not translated-sounding, not too difficult).</li>"
            "<li><b>The numbers and answers</b> are right: every answer in the worksheets and every example worked in the lesson.</li>"
            "<li><b>It teaches the skill it is named for</b>, and not another one, at the level of the children it is for.</li>"
            "<li><b>The story and the examples</b> suit a village classroom: nothing that leaves a child out, embarrasses one, or needs things a school will not have.</li>"
            "<li><b>No real name</b>, phone number or school appears anywhere.</li>"
            "<li><b>The warnings above:</b> does any of them matter to a child or a teacher? (Usually not, but say so.)</li></ol>"
            f"<h2>When you have read it</h2><p>If something is wrong, say what to change (do not edit the file; the plan can be recorded again for about 14 cents).</p><p>If it is good to show, ask whoever runs the tool to sign it: <code>python scripts/review_sample_plans.py sign {esc(skill)} --by \"Your name\"</code></p></div>")
    reviewed = f"<p class='by'>Reviewed by: {esc(str(plan['_reviewed_by']))}</p>" if plan.get("_reviewed_by") else ""
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>"
            f"<title>Review: recorded plan {esc(skill)}</title><style>"
            "body{font-family:'Noto Sans Devanagari','Nirmala UI','Segoe UI',system-ui,sans-serif;max-width:56rem;margin:1.5rem auto;padding:0 1rem;line-height:1.55;color:#1d2733}"
            "h1{font-size:1.4rem}h2{font-size:1.1rem;border-bottom:1px solid #cdd6df;padding-bottom:.2rem;margin-top:1.6rem}ul,ol{padding-left:1.3rem}li{margin:.25rem 0}"
            ".warn{background:#fff4e0;border:1px solid #e8c27a;padding:.6rem 1rem;border-radius:8px}.ok{background:#e9f6ec;border:1px solid #9fd0aa;padding:.6rem 1rem;border-radius:8px}"
            ".sign{background:#eef3f8;border:1px solid #c6d4e2;padding:.6rem 1rem;border-radius:8px;margin-top:2rem}code{background:#fff;padding:.1rem .3rem;border-radius:4px}"
            ".by{font-weight:600}.note{background:#eef3f8;padding:.4rem .8rem;border-radius:8px;font-size:.92rem}@media print{.sign{break-inside:avoid}}</style></head><body>"
            f"<h1>Recorded plan {esc(skill)}: for a reader</h1><p>Status: <b>{esc(state)}</b>. {esc(today)}</p>{reviewed}{seen_note}{warn_html}" + "".join(sections) + sign + "</body></html>")


def _load(skill: str):
    path = PLANS / f"{skill}.json"
    if not path.is_file():
        raise SystemExit(f"There is no recorded plan for {skill} in {PLANS}")
    return path, json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, plan: dict):
    with open(path, "w", encoding="utf-8", newline="\n") as f:          # LF everywhere: the same file on every machine
        f.write(json.dumps(plan, ensure_ascii=False, indent=1))
    json.loads(path.read_text(encoding="utf-8"))                           # prove it can still be read


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    sh = sub.add_parser("sheet"); sh.add_argument("skills", nargs="*")          # no names: every plan nobody has read and signed yet
    sg = sub.add_parser("sign"); sg.add_argument("skill"); sg.add_argument("--by", required=True); sg.add_argument("--date", default=None)
    args = ap.parse_args(argv)
    files = sorted(PLANS.glob("*.json"))
    if args.cmd == "list":
        for p in files:
            plan = json.loads(p.read_text(encoding="utf-8"))
            n = len(plan.get("_recorded_warnings") or []) if isinstance(plan, dict) else 0
            print(f"  {p.stem:<8} {status_of(plan):<13} {n} warning(s)   {plan.get('_reviewed_by') or ''}")
        return 0
    if args.cmd == "sheet":
        wanted = args.skills or [p.stem for p in files if status_of(json.loads(p.read_text(encoding="utf-8"))) in ("needs review", "not yet read")]
        if not wanted:
            print("Nothing needs a reader.")
            return 0
        SHEETS.mkdir(parents=True, exist_ok=True)
        (SHEETS / ".gitignore").write_text("*\n", encoding="utf-8")        # scratch: never committed
        for skill in wanted:
            _, plan = _load(skill)
            out = SHEETS / f"{skill}.html"
            out.write_text(render_sheet(plan, skill, today=date.today().isoformat()), encoding="utf-8")
            print(f"  {skill}: open {out}")
        return 0
    path, plan = _load(args.skill)
    try:
        signed = sign_plan(plan, args.by, args.date or date.today().isoformat())
    except ValueError as e:
        raise SystemExit(f"Not signed: {e}")
    _write_json(path, signed)
    print(f"  {args.skill}: signed: {signed['_reviewed_by']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
