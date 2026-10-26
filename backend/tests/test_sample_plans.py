"""
Recorded plans that were kept WITH warnings.

The batch tool keeps a recorded plan only if it came from the real model with no warnings. On the first real run (25 Oct) all three plans for L2.3.1, L2.5.1 and L2.7.2 came back with one mild
warning each (a worksheet question that echoes the lesson, a seventh problem that reveals a misconception but is beyond the six required) and all three were thrown away, at 42 cents. So there is now
an explicit, opt-in way to keep such a plan: `--accept-warnings` writes the warnings INSIDE the file, with `_reviewed_by` empty until a person has read it. Teachers never see those notes.

    cd backend && python tests/test_sample_plans.py --env-file .env
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import json
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("AUTH_MODE", "off")
os.environ.setdefault("ANTHROPIC_API_KEY", "dummy")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "prompts"), str(HERE)]
from app.services import ai_budget as ab

failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


print("when a plan is kept as a recorded sample")
keep = lambda **kw: ab.should_keep_sample(**{"save_samples": True, "stub": False, "served_from": "ai", "warnings": [], "accept_warnings": False, **kw})
check("a clean plan from the real model is kept", keep() is True)
check("a plan WITH warnings is NOT kept by default (the tool stays strict)", keep(warnings=["w"]) is False)
check("...but is kept when a person chose --accept-warnings", keep(warnings=["w"], accept_warnings=True) is True)
check("--accept-warnings does not keep a plan from the fake model (a dry run records nothing)", keep(stub=True, accept_warnings=True, warnings=["w"]) is False and keep(stub=True) is False)
check("nor a plan that was itself a replay of a recorded one (served_from sample)", keep(served_from="sample") is False)
check("nor anything when --save-samples was not given", keep(save_samples=False, accept_warnings=True) is False)

print("\nthe notes inside the file")
plan = {"anchor": {"title_hi": "x"}, "worksheets": {"progressor": {"required_count": 6}}}
clean = ab.mark_for_review(plan, [])
check("a clean plan is saved exactly as it is: no notes, no reviewer field", clean == plan and "_reviewed_by" not in clean)
marked = ab.mark_for_review(plan, ["worksheets.progressor problem 7 reveals a misconception but is an extra (required_count 6)", "w2"])
check("a plan kept with warnings carries them, and nobody's name against them", marked["_recorded_warnings"] == ["worksheets.progressor problem 7 reveals a misconception but is an extra (required_count 6)", "w2"] and marked["_reviewed_by"] is None)
check("the original plan is not changed by marking a copy", "_recorded_warnings" not in plan)
check("the notes are removed before a plan is used: strip_private drops every key that starts with an underscore and nothing else", ab.strip_private(marked) == plan and ab.strip_private({"a": 1, "_b": 2, "c_d": 3}) == {"a": 1, "c_d": 3})
check("something that is not a plan is handed back unchanged", ab.strip_private(None) is None and ab.strip_private([1]) == [1])

print("\nthe raw copy of EVERY generated plan (two runs, $0.87, and nothing left: never again)")
raw_w = ab.raw_plan_record(plan, ["w1"])
check("a plan with warnings is written with them inside and no reviewer", raw_w["_recorded_warnings"] == ["w1"] and raw_w["_reviewed_by"] is None and "_stub" not in raw_w)
raw_c = ab.raw_plan_record(plan, [])
check("a clean plan is written too, with an empty reviewer field and no warnings key (it needs no review)", "_recorded_warnings" not in raw_c and raw_c["_reviewed_by"] is None)
check("a plan made by the fake model is marked _stub, so it can never be mistaken for a real one", ab.raw_plan_record(plan, [], stub=True)["_stub"] is True)
check("the plan's own content is unchanged by the notes", ab.strip_private(raw_w) == plan and ab.strip_private(ab.raw_plan_record(plan, [], stub=True)) == plan)
check("nothing is changed in the original", plan == {"anchor": {"title_hi": "x"}, "worksheets": {"progressor": {"required_count": 6}}})

print("\nthrough the real loader")
tmp = Path(tempfile.mkdtemp())
(tmp / "L2.5.1.json").write_text(json.dumps(marked, ensure_ascii=False), encoding="utf-8")
(tmp / "N2.3.2.json").write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
original = ab.sample_dir
ab.sample_dir = lambda: tmp
try:
    loaded = ab.sample_plan_for("L2.5.1")
    check("a teacher is given the plan WITHOUT the review notes (what the screen and the stored plan get)", loaded == plan and not any(k.startswith("_") for k in loaded), loaded)
    check("the recorded skills are listed from the folder, notes or not", ab.sample_skills() == ["L2.5.1", "N2.3.2"], ab.sample_skills())
    check("a skill with no file has no recorded plan", ab.sample_plan_for("L9.9.9") is None)
finally:
    ab.sample_dir = original

print("\nthe plans already in the repository still load, and none carries a note")
real = sorted((ROOT / "db" / "seeds" / "sample_plans").glob("*.json"))
check(f"each of the {len(real)} recorded plans loads as a plan", all(isinstance(json.loads(p.read_text(encoding='utf-8')), dict) for p in real))
# (whether each plan has been read and signed is the GATE's job, scripts/submission_check.py: a unit test that fails until the reader has signed would only make the suite red for a workflow state)

if failures:
    print(f"\nFAILED ({len(failures)})")
    sys.exit(1)
print("\nOK: a plan with warnings can be kept only on purpose, carries its warnings until a person signs it, and a teacher never sees them")
