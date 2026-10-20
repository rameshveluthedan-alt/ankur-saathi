"""
The Hindi style rules from Vaishnavi's review (docs/HINDI_STYLE.md): what the safety net changes in a plan, and what it must NOT touch.
No database needed.

    python backend/tests/test_hindi_style.py
"""

import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):          # a pipe on Windows uses a legacy code page that cannot print Hindi
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")
import copy
import glob
import json
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path[:0] = [os.path.join(ROOT, "prompts")]
import hindi_style as hs

failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


def fields(plan, regexes):
    """(path, text) of every string whose path matches one of the regexes."""
    out = []
    def walk(o, p=""):
        if isinstance(o, dict):
            for k, v in o.items(): walk(v, f"{p}.{k}")
        elif isinstance(o, list):
            for v in o: walk(v, f"{p}[]")
        elif isinstance(o, str) and any(r.match(p) for r in regexes):
            out.append((p, o))
    walk(plan)
    return out


def flat(plan):
    out = {}
    def walk(o, p=""):
        if isinstance(o, dict):
            for k, v in o.items(): walk(v, f"{p}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o): walk(v, f"{p}[{i}]")
        else:
            out[p] = o
    walk(plan)
    return out


def has(word, text):
    return re.search(hs._word(word), text) is not None


print("the exact sentences from the review copy")
t = lambda s, **kw: hs.soften_text(s, **kw)[0]
W = hs.FRAME_WORD          # the word chosen for the Tens | Ones frame (बॉक्स); the tests follow it
check("फालतू -> अतिरिक्त", t("इसमें कुछ फालतू बंडल भी रखें।") == "इसमें कुछ अतिरिक्त बंडल भी रखें।")
check("चुपचाप -> शांति से", t("और चुपचाप शुरू करें।") == "और शांति से शुरू करें।")
check("'मेरे पास आओ' -> 'आएँ' (also right before the danda)", t("शुरुआती समूह मेरे पास आओ।") == "शुरुआती समूह मेरे पास आएँ।")
check("'अपना काम बंद करो' -> 'रोक दें' and 'को दो' -> 'को दें'", t("अपना काम बंद करो और छड़ियाँ मॉनिटर को दो।") == "अपना काम रोक दें और छड़ियाँ मॉनिटर को दें।")
check("'कॉपी बंद करो' -> 'बंद करें' (closing a notebook is not stopping work)", t("कॉपी बंद करो और अपनी जगह जाओ।") == "कॉपी बंद करें और अपनी जगह जाएँ।")
check(f"'दहाई | इकाई का खाना' -> 'दहाई-इकाई का {W}'", t("पर दहाई | इकाई का खाना (Tens | Ones frame) रूल से") == f"पर दहाई-इकाई का {W} (Tens | Ones frame) रूल से")
check("grammar: 'कितने दहाई और कितने इकाई' -> 'कितनी दहाई और कितनी इकाई' (both are feminine)", t("बताएँ आलू के दाम 24 में कितने दहाई और कितने इकाई हैं?") == "बताएँ आलू के दाम 24 में कितनी दहाई और कितनी इकाई हैं?")
check("...and the correct forms are left alone", t("इकाई कितनी हुई? दहाई कितनी हुई? कितने सैकड़े हैं?") == "इकाई कितनी हुई? दहाई कितनी हुई? कितने सैकड़े हैं?")
check("a bare 'खाने में' says which frame in full", t("फिर खाने में पहले इकाई, फिर दहाई जोड़ो।", polite=False) == f"फिर दहाई-इकाई के {W} में पहले इकाई, फिर दहाई जोड़ो।")

print("what must NOT change")
for s in ["दो अंकों के जोड़ के 8 सवाल हल करें।", "पहले दो सवाल छड़ियों से करें।", "संख्या को दो भागों में बाँटें।", "उन्हें छड़ी से दिखाना और सिखाना है।",
          "रानी ने खाना खाया और 12 रुपये दिए।", "सब अपनी कॉपी बंद करें। आज बहुत अच्छा काम हुआ।", "हासिल के साथ खुली छड़ियाँ और शब्द-सवाल।", "मेरे पास आएँ।"]:
    check(f"unchanged: {s[:44]}", t(s) == s)
check("idempotent: a second pass changes nothing", all(t(t(s)) == t(s) for s in ["अपना काम बंद करो और छड़ियाँ मॉनिटर को दो।", "दहाई | इकाई का खाना", "फालतू चुपचाप आओ।"]))

print("on the real recorded plans")
plans = {os.path.basename(f): json.load(open(f, encoding="utf-8")) for f in sorted(glob.glob(os.path.join(ROOT, "db", "seeds", "sample_plans", "*.json")))}
check("there are recorded plans to test on", len(plans) >= 2)
for name, original in plans.items():
    plan = copy.deepcopy(original)
    counts = hs.soften_plan(plan)
    teacher = fields(plan, hs._SPEECH_RE + hs._NOTES_RE)
    printed = fields(plan, hs._PRINTED_RE)
    bad = [(p, w) for p, s in teacher for w in ("फालतू", "चुपचाप", "आओ", "जाओ", "सुनो", "खाना", "खाने") if has(w, s)]
    bad += [(p, "बंद करो/को दो") for p, s in teacher if "बंद करो" in s or re.search(r"को दो(?=[।\s]|$)", s)]
    check(f"{name}: no flagged word is left in what the teacher says or reads  ({counts})", not bad, bad[:3])
    check(f"{name}: the printed worksheet instructions lost the frame word", not any(has("खाना", s) or has("खाने", s) for _, s in printed))
    if "आओ" in json.dumps(original, ensure_ascii=False) or "बनाओ" in json.dumps(original, ensure_ascii=False):
        check(f"{name}: worksheet instructions keep the textbook style (जोड़ो / बनाओ), as decided for now",
              any(re.search(r"जोड़ो|बनाओ|लिखो|भरो", s) for _, s in fields(original, hs._PRINTED_RE)) == any(re.search(r"जोड़ो|बनाओ|लिखो|भरो", s) for _, s in printed))
    # nothing a child solves or reads, no answer, no explanation, no name was touched
    before, after = flat(original), flat(plan)
    touched = [p for p in before if before[p] != after.get(p)]
    allowed = hs._SPEECH_RE + hs._NOTES_RE + hs._PRINTED_RE
    def path_of(p):
        return re.sub(r"\[\d+\]", "[]", p)
    illegal = [p for p in touched if not any(r.match(path_of(p)) for r in allowed)]
    check(f"{name}: only teacher words and printed instructions changed ({len(touched)} fields); no problem, answer, passage or explanation", not illegal, illegal[:3])
    again = copy.deepcopy(plan)
    check(f"{name}: running it again changes nothing", hs.soften_plan(again) == {} and again == plan)

print("the open decision is one switch")
n232 = copy.deepcopy(plans["N2.3.2.json"])
hs.POLITE_IN_WORKSHEETS = True
hs.soften_plan(n232)
hs.POLITE_IN_WORKSHEETS = False
ws = " ".join(s for _, s in fields(n232, hs._PRINTED_RE))
check("POLITE_IN_WORKSHEETS=True also softens the printed instructions (जोड़ो -> जोड़ें)", "जोड़ें" in ws and "जोड़ो" not in ws)

print("the prompt")
check("the model is told the rules", all(w in hs.STYLE_PROMPT for w in ("आएँ", "रोक दें", "अतिरिक्त", "शांति से", f"दहाई-इकाई का {W}", "आज बहुत अच्छा काम हुआ")))
check("the prompt module uses the same source (orchestrate imports STYLE_PROMPT)", "from hindi_style import STYLE_PROMPT" in open(os.path.join(ROOT, "prompts", "orchestrate.py"), encoding="utf-8").read())

if failures:
    print(f"\nFAILED ({len(failures)})")
    sys.exit(1)
print("\nOK: the Hindi style rules change what they should and nothing else")
