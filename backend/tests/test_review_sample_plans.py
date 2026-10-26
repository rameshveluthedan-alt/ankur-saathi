"""
Reading and signing a recorded plan (scripts/review_sample_plans.py).

A recorded plan is what a teacher sees when the AI limit is reached, so someone who reads Hindi must read it first, and she should not have to read JSON or edit it by hand to sign it.

    cd backend && python tests/test_review_sample_plans.py --env-file .env
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import contextlib
import html
import io
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "prompts")]
import review_sample_plans as rs

failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


def strings(x, out=None):
    out = [] if out is None else out
    if isinstance(x, dict):
        for k, v in x.items():
            if not str(k).startswith("_"):
                strings(v, out)
    elif isinstance(x, list):
        for v in x:
            strings(v, out)
    elif isinstance(x, str):
        out.append(x)
    return out


print("what state a plan is in")
check("a plan kept with warnings and no reader is 'needs review'", rs.status_of({"a": 1, "_recorded_warnings": ["w"], "_reviewed_by": None}) == "needs review")
check("once someone signed it, 'reviewed'", rs.status_of({"_recorded_warnings": ["w"], "_reviewed_by": "Vaishnavi, 2026-10-26"}) == "reviewed")
check("a plan with NO warnings is still 'not yet read': the checks cover sums and structure, not whether the Hindi is natural, so a person must read it too", rs.status_of({"a": 1}) == "not yet read" and rs.status_of({"a": 1, "_reviewed_by": None}) == "not yet read")
check("signed, with or without warnings, it is 'reviewed'", rs.status_of({"a": 1, "_reviewed_by": "V, 2026-10-26"}) == "reviewed")
check("a plan from the fake model is 'stub', whatever else it says", rs.status_of({"_stub": True, "_reviewed_by": "x"}) == "stub")
check("something that is not a plan is 'invalid'", rs.status_of([1]) == "invalid" and rs.status_of(None) == "invalid")

print("\nsigning")
plan = {"anchor": {"title_hi": "x"}, "_recorded_warnings": ["w"], "_reviewed_by": None}
signed = rs.sign_plan(plan, "  Vaishnavi ", "2026-10-26")
check("the name and the date are written, trimmed", signed["_reviewed_by"] == "Vaishnavi, 2026-10-26")
check("nothing else changes, and the original is untouched", {k: v for k, v in signed.items() if k != "_reviewed_by"} == {k: v for k, v in plan.items() if k != "_reviewed_by"} and plan["_reviewed_by"] is None)
for bad in ("", "   ", None):
    try:
        rs.sign_plan(plan, bad, "2026-10-26"); refused = False
    except ValueError:
        refused = True
    check(f"a blank name ({bad!r}) is refused: a signature with no name proves nothing", refused)
try:
    rs.sign_plan({"_stub": True}, "A", "2026-10-26"); refused = False
except ValueError as e:
    refused = "fake model" in str(e)
check("a plan made by the fake model cannot be signed", refused)

print("\nthe page a reader sees")
tricky = {"anchor": {"title_hi": "<script>alert(1)</script> जोड़ & घटाव", "narration_hi": "कहानी"}, "prep_hi": ["पेंसिल", "कॉपी"], "_recorded_warnings": ["worksheets.proficient problem 5 repeats wording: «बंदर कहाँ कूद रहे थे»"], "_reviewed_by": None}
page = rs.render_sheet(tricky, "L2.5.1", today="2026-10-26")
check("the warnings are on the page, in full", "बंदर कहाँ कूद रहे थे" in page and "Warnings the checks raised" in page)
check("text from the plan is shown, and HTML in it is shown as text, never run", "&lt;script&gt;alert(1)&lt;/script&gt;" in page and "<script>alert(1)" not in page and "जोड़ &amp; घटाव" in page)
check("a list is shown as a list of its items", "पेंसिल" in page and "कॉपी" in page)
check("the page says what to do afterwards and gives the signing command for THIS skill", "review_sample_plans.py sign L2.5.1" in page and "do not edit the file" in page)
check("the page carries a checklist: the Hindi, the numbers and answers, the right skill, the story and examples, no real names, the warnings", all(x in page for x in ("The Hindi</b> is natural and polite", "The numbers and answers</b> are right", "It teaches the skill it is named for", "suit a village classroom", "No real name</b>", "The warnings above:</b>")))
quiet = rs.render_sheet({"anchor": {"title_hi": "x"}}, "N2.3.2")
check("a plan with no warnings says so, and says that this does not mean it has been read", "raised no warnings" in quiet and "does not mean it has been read" in quiet and "not yet read" in quiet)
check("a signed plan shows who signed it", "Reviewed by: Vaishnavi, 2026-10-26" in rs.render_sheet({"anchor": {}, "_reviewed_by": "Vaishnavi, 2026-10-26"}, "N2.3.2"))
check("the tool's own notes (the names of _recorded_warnings and _reviewed_by) are not listed as if they were lesson text", "_recorded_warnings" not in page and "_reviewed_by" not in page and "recorded warnings" not in page.lower().replace("warnings the checks raised", ""))

print("\nwhat the reader is shown is what a teacher will see")
polite = rs.render_sheet({"anchor": {"narration_hi": "बोर्ड पर 5 चीज़ों के नाम गिनो। फिर बताओ आलू के दाम कितने हैं?"}}, "N2.3.2")
check("informal commands are already polite on the page (गिनो -> गिनें, बताओ -> बताएँ), as the app shows them", "गिनें" in polite and "बताएँ" in polite and "गिनो" not in polite and "बताओ" not in polite)
check("and the page says so, with how many wordings changed, so the reader judges the right text", "as a teacher will see it" in polite and "wording changes" in polite)
orig = {"anchor": {"narration_hi": "नाम गिनो।"}}
shown, n = rs.as_teacher_sees(orig)
check("the plan itself is never changed by showing it (the signed file keeps the recorded text)", orig == {"anchor": {"narration_hi": "नाम गिनो।"}} and shown["anchor"]["narration_hi"] != orig["anchor"]["narration_hi"])
lst = rs.render_sheet({"prep_hi": ["पहला", "दूसरा", "तीसरा"], "anchor": {"title_hi": "x", "narration_hi": ""}}, "N2.3.2")
check("a list is shown as separate bullet items, not run together", lst.count("<li><span lang=\"hi\">") >= 3 and "पहला, दूसरा" not in lst)
check("a field with nothing in it is not listed", "narration" not in lst)

print("\nNOTHING is left out: every piece of text a teacher will see, in the real recorded plans, is on its page")
real = sorted((ROOT / "db" / "seeds" / "sample_plans").glob("*.json"))
for p in real:
    d = json.loads(p.read_text(encoding="utf-8"))
    teacher_sees, _ = rs.as_teacher_sees(d)
    page = rs.render_sheet(d, p.stem)
    missing = [s for s in strings(teacher_sees) if s.strip() and html.escape(s) not in page]
    check(f"{p.name}: all {len(strings(teacher_sees))} pieces of text appear on the page", not missing, missing[:2])
check("there are recorded plans to check", len(real) >= 1)

print("\nthe command line, on a copy")
tmp = Path(tempfile.mkdtemp())
(tmp / "plans").mkdir()
rs.PLANS = tmp / "plans"
rs.SHEETS = tmp / "sheets"
src = {"anchor": {"title_hi": "शीर्षक"}, "prep_hi": ["a"], "_recorded_warnings": ["w1"], "_reviewed_by": None}
(rs.PLANS / "L2.5.1.json").write_text(json.dumps(src, ensure_ascii=False, indent=1), encoding="utf-8")
(rs.PLANS / "N2.3.2.json").write_text(json.dumps({"anchor": {"title_hi": "ठीक"}}, ensure_ascii=False), encoding="utf-8")
out = io.StringIO()
with contextlib.redirect_stdout(out):
    rs.main(["list"])
check("list shows each plan, its state and its warnings: one 'needs review' (it has warnings), one 'not yet read' (it has none)", "L2.5.1" in out.getvalue() and "needs review" in out.getvalue() and "N2.3.2" in out.getvalue() and "not yet read" in out.getvalue(), out.getvalue())
with contextlib.redirect_stdout(io.StringIO()):
    rs.main(["sheet"])
check("'sheet' with no names writes a page for EVERY plan nobody has read, with warnings or without (the one with no warnings used to be skipped)", sorted(p.name for p in rs.SHEETS.glob("*.html")) == ["L2.5.1.html", "N2.3.2.html"], [p.name for p in rs.SHEETS.iterdir()])
check("the pages are kept out of git (their folder ignores itself)", (rs.SHEETS / ".gitignore").read_text() == "*\n")
with contextlib.redirect_stdout(io.StringIO()):
    rs.main(["sign", "L2.5.1", "--by", "Vaishnavi", "--date", "2026-10-26"])
raw = (rs.PLANS / "L2.5.1.json").read_bytes()
after = json.loads(raw.decode("utf-8"))
check("signing writes the name and date and leaves everything else as it was", after["_reviewed_by"] == "Vaishnavi, 2026-10-26" and after["anchor"] == src["anchor"] and after["_recorded_warnings"] == ["w1"])
check("the file is still valid JSON, in UTF-8, with Hindi readable as Hindi (not \\u escapes) and no carriage returns (the same file on every machine)", "शीर्षक".encode("utf-8") in raw and b"\\u" not in raw and b"\r" not in raw)
with contextlib.redirect_stdout(io.StringIO()):
    rs.main(["sign", "N2.3.2", "--by", "Vaishnavi", "--date", "2026-10-26"])
before = sorted(p.name for p in rs.SHEETS.glob("*.html"))
out2 = io.StringIO()
with contextlib.redirect_stdout(out2):
    rs.main(["sheet"])
check("once BOTH are signed, 'sheet' with no names says nothing needs a reader and writes nothing new", "Nothing needs a reader" in out2.getvalue() and sorted(p.name for p in rs.SHEETS.glob("*.html")) == before, out2.getvalue())
try:
    rs.main(["sign", "L9.9.9", "--by", "A"]); gone = False
except SystemExit as e:
    gone = "no recorded plan" in str(e)
check("signing a skill with no recorded plan is refused with a message", gone)
try:
    rs.main(["sign", "L2.5.1", "--by", "  "]); blank = False
except SystemExit as e:
    blank = "name is needed" in str(e)
check("signing with a blank name from the command line is refused too", blank)

if failures:
    print(f"\nFAILED ({len(failures)})")
    sys.exit(1)
print("\nOK: a plan can be read as a page with nothing left out, and signed without touching the JSON by hand")
