"""
The printed worksheets use the respectful forms (जोड़ें, लिखें, पढ़ें), decided 21 Oct, and nothing that depends on the OLD forms breaks: the classifiers that choose a
sheet's layout, and the number-word checker. Quoted text (what a child reads) is never changed. No database needed.

    python backend/tests/test_worksheet_polite.py
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):          # a pipe on Windows uses a legacy code page that cannot print Hindi
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import copy
import html as H
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, ".."), os.path.join(HERE, "..", "..", "prompts")]
from app.services import hindi_numbers as hn
from app.services import worksheet_service as ws
import hindi_style as hs

failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


def text_of(page: str) -> str:
    return H.unescape(re.sub(r"<style.*?</style>|<[^>]+>", " ", page, flags=re.S))


INFORMAL = re.compile(hs._word("(" + "|".join(map(re.escape, sorted(list(hs.POLITE_VERBS) + ["करो"], key=len, reverse=True))) + ")"))
PLAN = json.load(open(os.path.join(HERE, "..", "..", "db", "seeds", "sample_plans", "N2.3.2.json"), encoding="utf-8"))

print("the sample sheets that anyone can open")
for domain, comp in (("numeracy", "N2.3.2"), ("r1_literacy", "L2.6.1")):
    for level in ("beginner", "progressor", "proficient"):
        page = text_of(ws.render_sample_worksheet(level, domain, comp, "नमूना", "Sample"))
        left = sorted(set(INFORMAL.findall(page)))
        check(f"{domain} {level}: no informal command is left on the page", not left, left)
raw = ws.render_sample_worksheet("progressor", "numeracy", "N2.3.2", "नमूना", "Sample")
check("the template's own line is respectful: 'ज़रूर करें ... जल्दी खत्म हो तो करें'", "ज़रूर करें" in raw and "तो करें" in raw and "ज़रूर करो" not in raw)
check("the literacy passage label is respectful: 'अनुच्छेद पढ़ें'", "अनुच्छेद पढ़ें" in ws.render_sample_worksheet("progressor", "r1_literacy", "L2.6.1", "नमूना", "Sample"))

print("a plan stored BEFORE the change (informal text) still prints respectfully")
old = copy.deepcopy(PLAN)
old["worksheets"]["beginner"]["instructions_hi"] = "छड़ियों से बनाओ, फिर खाने में पहले इकाई जोड़ो।"
page = text_of(ws.render_worksheet(old, "beginner", "N2.3.1", "x", "x", "numeracy", "2026-10-21"))
check("the instruction prints as 'बनाएँ ... जोड़ें' and the frame is the box", "बनाएँ" in page and "जोड़ें" in page and "जोड़ो" not in page and "बॉक्स" in page and "खाने" not in page, page[:300])
page = text_of(ws.render_worksheet(PLAN, "progressor", "N2.3.2", "x", "x", "numeracy", "2026-10-21"))
check("a stored plan's word-problem and answer lines are unchanged apart from the verbs", "कुल कितने" in page)

print("quoted text on a sheet (what the child reads) is never changed")
q = copy.deepcopy(PLAN)
q["worksheets"]["progressor"]["problems"].append({"number": 9, "problem_hi": "इस वाक्य को पढ़ो: 'रानी, यहाँ आओ।'", "answer": "ok", "row_type": "plain"})
page = text_of(ws.render_worksheet(q, "progressor", "N2.3.2", "x", "x", "numeracy", "2026-10-21"))
check("the instruction outside the quotes is respectful and the quoted sentence is exactly as written", "इस वाक्य को पढ़ें" in page and "'रानी, यहाँ आओ।'" in page, page[-400:])

print("the classifiers that choose a sheet's layout recognise BOTH forms")
pairs = [("गिनो", "गिनें"), ("लिखो", "लिखें"), ("पढ़ो", "पढ़ें"), ("सुनो", "सुनें"), ("बोलो", "बोलें")]
same = True
for a, b in pairs:
    for fn, lvl in ((ws._enrich_numeracy_problem, "beginner"), (ws._enrich_literacy_problem, "beginner"), (ws._enrich_literacy_problem, "proficient")):
        ra = fn({"problem_hi": f"इन्हें {a}: क ख ग", "answer": "x"}, lvl)
        rb = fn({"problem_hi": f"इन्हें {b}: क ख ग", "answer": "x"}, lvl)
        ra.pop("problem_hi", None); rb.pop("problem_hi", None)
        if ra != rb:
            same = False
            print("     differs:", a, b, fn.__name__, lvl, {k: (ra.get(k), rb.get(k)) for k in set(ra) | set(rb) if ra.get(k) != rb.get(k)})
check("the same layout is chosen for 'X' and its respectful form, for every verb, level and subject", same)
layout = lambda text: {k: v for k, v in ws._enrich_literacy_problem({"problem_hi": text, "answer": "दिन"}, "beginner").items() if k != "problem_hi"}
check("a literacy line 'मात्रा लिखें' still gets the writing layout the old 'मात्रा लिखो' got (compared apart from the line's own text)", layout("मात्रा लिखें: द_न") == layout("मात्रा लिखो: द_न") and layout("मात्रा लिखें: द_न") != layout("कुछ और"), (layout("मात्रा लिखें: द_न"), layout("कुछ और")))

print("the number-word checker gives the same result for all three forms")
results = {}
for verb in ("लिखिए", "लिखो", "लिखें"):
    plan = {"worksheets": {"beginner": {"problems": [{"problem_hi": f"उनसठ अंकों में {verb}", "answer": "49"}, {"problem_hi": f"संख्या 83 को शब्दों में {verb}", "answer": "तिरासी"}]}}}
    log = hn.repair_number_words(plan)
    results[verb] = [p["problem_hi"].replace(verb, "V") for p in plan["worksheets"]["beginner"]["problems"]]
check("a wrong number word (उनसठ for 49) is corrected, whichever verb the line uses", all("उनचास" in r[0] and "उनसठ" not in r[0] for r in results.values()), results)
check("...and the result is identical for the three forms", results["लिखिए"] == results["लिखो"] == results["लिखें"], results)

print("the switch")
hs.POLITE_IN_WORKSHEETS = False
try:
    page = ws.render_sample_worksheet("progressor", "numeracy", "N2.3.2", "नमूना", "Sample")
    check("with POLITE_IN_WORKSHEETS=False the old template line and text come back", "ज़रूर करो" in page and "जोड़ो" in text_of(page))
finally:
    hs.POLITE_IN_WORKSHEETS = True
check("...and it is on by default", "ज़रूर करें" in ws.render_sample_worksheet("progressor", "numeracy", "N2.3.2", "नमूना", "Sample"))

if failures:
    print(f"\nFAILED ({len(failures)})")
    sys.exit(1)
print("\nOK: the printed worksheets are respectful, quote-safe, and nothing that depended on the old verbs broke")
