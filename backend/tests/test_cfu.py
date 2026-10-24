"""
Check for understanding in every lesson: the model writes show-me questions, the CODE decides which a teacher may use.
Pure rules (the checks, the cleaning, the prompt), then a real class through the whole pipeline with a stand-in model, then the switch.

    python scripts/add_cfu_setting.py        (once: adds the CFU_ENABLED line to config.py; the switch test needs it)
    cd backend && AUTH_MODE=off python tests/test_cfu.py --env-file .env
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):          # a pipe on Windows uses a legacy code page that cannot print Hindi
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import asyncio
import contextlib
import copy
import io
import json
import os
import sys
from datetime import date, timedelta
from types import SimpleNamespace

os.environ.setdefault("AUTH_MODE", "off")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "..", "prompts"), os.path.join(HERE, "..")]
import _scratch
import anthropic
import cfu_prompt
from app.services import cfu
from app.services import plan_service
from app.core.config import get_settings

TODAY = date.today()
failures = []
SAMPLE = json.load(open(os.path.join(HERE, "..", "..", "db", "seeds", "sample_plans", "N2.3.2.json"), encoding="utf-8"))


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


lf = lambda mid, w: [{"misconception_id": mid, "wrong_answer_hi": w}]
V = {"X-M1", "X-M2"}
ck = lambda item, avoid=(), rules=None, strict=True, compare=True, lesson_results=(): cfu.check_item(item, valid_ids=V, avoid=set(avoid), rules=rules or {}, strict=strict, compare=compare, lesson_results=frozenset(lesson_results))

print("the checks on one question")
check("compute: a right expected answer passes", not ck({"kind": "compute", "question_hi": "58 + 27 कितना होगा?", "expected_hi": "85", "listen_for": lf("X-M1", "75")}))
check("compute: a wrong expected answer is dropped", "real result 85" in " ".join(ck({"kind": "compute", "question_hi": "58 + 27 कितना होगा?", "expected_hi": "84", "listen_for": lf("X-M1", "75")})))
check("compute: a question that states its own answer is dropped", ck({"kind": "compute", "question_hi": "58 + 27 = 85 कैसे?", "expected_hi": "85", "listen_for": lf("X-M1", "75")}) != [])
check("choose: passes when the real result is offered and expected", not ck({"kind": "choose", "question_hi": "58 + 27: उत्तर 75 है या 85?", "expected_hi": "85, क्योंकि 8 + 7 = 15", "listen_for": lf("X-M1", "75")}))
check("choose: dropped when the real result is not among the offered answers", ck({"kind": "choose", "question_hi": "58 + 27: उत्तर 75 है या 95?", "expected_hi": "85", "listen_for": lf("X-M1", "75")}) != [])
check("spot_error: passes when the worked line really is wrong and the answer gives the real result", not ck({"kind": "spot_error", "question_hi": "47 + 25 = 612: सही या गलत?", "expected_hi": "गलत। सही उत्तर 72", "listen_for": lf("X-M2", "612")}))
check("spot_error: a line that is actually right is a fair decoy, but then the answer must say सही (saying गलत is dropped)", ck({"kind": "spot_error", "question_hi": "47 + 25 = 72: सही या गलत?", "expected_hi": "सही", "listen_for": lf("X-M1", "x")}) == [] and ck({"kind": "spot_error", "question_hi": "47 + 25 = 72: सही या गलत?", "expected_hi": "गलत", "listen_for": lf("X-M1", "x")}) != [])
check("a wrong worked line in the expected answer is dropped (8 + 7 = 14)", ck({"kind": "answer", "question_hi": "इकाई का योग क्या है?", "expected_hi": "8 + 7 = 14", "listen_for": lf("X-M1", "5")}) != [])
check("subtraction and multiplication are checked too", not ck({"kind": "compute", "question_hi": "78 − 35 कितना होगा?", "expected_hi": "43", "listen_for": [], "shows_hi": "x"}) and not ck({"kind": "compute", "question_hi": "4 × 5 कितना होगा?", "expected_hi": "20", "listen_for": [], "shows_hi": "x"})
      and ck({"kind": "compute", "question_hi": "78 − 35 कितना होगा?", "expected_hi": "44", "listen_for": [], "shows_hi": "x"}) != [])
check("an invented mistake id with no 'shows' line is dropped", ck({"kind": "answer", "question_hi": "इकाई क्या है?", "expected_hi": "2", "listen_for": lf("N9.9.9-M1", "12")}) != [])
check("a question with no recorded mistake is fine if it says what a right answer shows", not ck({"kind": "answer", "question_hi": "इकाई क्या है?", "expected_hi": "2", "listen_for": [], "shows_hi": "बच्चा इकाई पहचानता है"}))
check("reusing an example from the lesson or worksheet is dropped (in either order)", ck({"kind": "compute", "question_hi": "38 + 45 कितना होगा?", "expected_hi": "83", "listen_for": lf("X-M1", "73")}, avoid={("+", 38, 45)}) != []
      and ck({"kind": "compute", "question_hi": "45 + 38 कितना होगा?", "expected_hi": "83", "listen_for": lf("X-M1", "73")}, avoid={("+", 38, 45)}) != [])
check("a skill 'without regrouping' gets no question that needs a carry", ck({"kind": "compute", "question_hi": "38 + 47 कितना होगा?", "expected_hi": "85", "listen_for": [], "shows_hi": "x"}, rules={"no_carry": True}) != []
      and not ck({"kind": "compute", "question_hi": "21 + 36 कितना होगा?", "expected_hi": "57", "listen_for": [], "shows_hi": "x"}, rules={"no_carry": True}))
check("a skill 'without borrowing' gets no question that needs a borrow", ck({"kind": "compute", "question_hi": "52 − 17 कितना होगा?", "expected_hi": "35", "listen_for": [], "shows_hi": "x"}, rules={"no_borrow": True}) != []
      and not ck({"kind": "compute", "question_hi": "86 − 43 कितना होगा?", "expected_hi": "43", "listen_for": [], "shows_hi": "x"}, rules={"no_borrow": True}))
check("an answer too long to write on a slate is dropped", ck({"kind": "answer", "question_hi": "क्यों?", "expected_hi": "x" * 200, "listen_for": lf("X-M1", "x")}) != [])
check("rules are read from the skill's name", cfu.skill_rules("Adds two 2-digit numbers without regrouping")["no_carry"] and cfu.skill_rules("Subtracts 2-digit numbers without borrowing")["no_borrow"] and not any(cfu.skill_rules("Adds with regrouping").values()))

print("readiness and observed skills (found in the first real-model run: good questions were dropped for 'needing an operation')")
sh = {"listen_for": [], "shows_hi": "बच्चा पहचानता है"}
check("a three-way comparison of equal amounts passes, whatever kind the model gave it", not ck({"kind": "choose", "question_hi": "3 फूल और 3 फूल हैं। ज़्यादा, कम या बराबर?", "expected_hi": "बराबर", **sh}, strict=False))
check("...and is wrong if the amounts differ but the answer says बराबर", ck({"kind": "choose", "question_hi": "5 फूल और 3 फूल हैं। ज़्यादा, कम या बराबर?", "expected_hi": "बराबर", **sh}, strict=False) != [])
check("in an observed skill a compute or spot_error question with no sum is kept, not dropped", not ck({"kind": "compute", "question_hi": "गिनकर बताइए: कितने फूल हैं?", "expected_hi": "4", **sh}, strict=False) and not ck({"kind": "spot_error", "question_hi": "बोर्ड पर देखो: ● ○ ● ● लिखा है। पैटर्न सही है?", "expected_hi": "गलत", **sh}, strict=False))
check("in a COMPUTATION skill the same questions stay dropped (arithmetic written in words cannot be checked)", ck({"kind": "compute", "question_hi": "सैंतीस और बीस जोड़ें", "expected_hi": "57", **sh}, strict=True) != [] and ck({"kind": "spot_error", "question_hi": "बोर्ड पर देखो: जोड़ में गलती है। कहाँ?", "expected_hi": "x", **sh}, strict=True) != [])
check("a plain comparison is verified in every skill: 'which is bigger, 47 or 74?'", not ck({"kind": "choose", "question_hi": "47 और 74 में कौन बड़ा है?", "expected_hi": "74", **sh}) and ck({"kind": "choose", "question_hi": "47 और 74 में कौन बड़ा है?", "expected_hi": "47", **sh}) != []
      and not ck({"kind": "choose", "question_hi": "47 और 74 में कौन छोटा है?", "expected_hi": "47", **sh}) and ck({"kind": "answer", "question_hi": "47 और 74 में कौन छोटा है?", "expected_hi": "74", **sh}) != [])
check("'how many more to stay equal' (5 and 5, answer 0) is not mistaken for the three-way question", not ck({"kind": "answer", "question_hi": "5 पत्ते और 5 पत्ते हैं। कितने और जोड़ें तो बराबर रहें? संख्या लिखें।", "expected_hi": "0", **sh}, strict=False))
check("a real sum is still checked in an observed skill (the arithmetic does not go away)", ck({"kind": "compute", "question_hi": "2 + 2 कितना होगा?", "expected_hi": "5", **sh}, strict=False) != [])

print("literacy skills typed 'computation' in the knowledge base (found before the first literacy run: eight skills such as punctuation and matras)")
from types import SimpleNamespace as _NS
ctype = lambda t, dom: plan_service._cfu_criteria_type(_NS(apna_criteria={"type": t} if t else None), dom)
check("a LITERACY skill is never strict, even when the knowledge base types it 'computation'", ctype("computation", "r1_literacy") == "literacy" and ctype("observational", "r1_literacy") == "literacy" and ctype("fluency", "r1_literacy") == "literacy")
check("a NUMERACY computation skill stays strict, and the other numeracy types are read as they are", ctype("computation", "numeracy") == "computation" and ctype("observational", "numeracy") == "observational" and ctype(None, "numeracy") is None)
check("the type is also read when the database hands it over as text", plan_service._cfu_criteria_type(_NS(apna_criteria='{"type": "computation"}'), "numeracy") == "computation")
punct = {"kind": "choose", "question_hi": "'आपका नाम क्या है' के अंत में कौन-सा चिह्न लगेगा: ‘।’ या ‘?’", "expected_hi": "?", "listen_for": [], "shows_hi": "बच्चा प्रश्नवाचक वाक्य पहचानता है"}
for ctype_kb, kept_expected in (("literacy", 1), ("computation", 1)):
    kb = {"progressor": {"competency_id": "L", "name_en": "Uses punctuation marks correctly", "name_hi": "x", "criteria_type": ctype_kb, "mistakes": []}}
    pl = {"rotation_schedule": {"blocks": [{"type": "teach", "teach_group": "progressor", "talking_points": {}, "cfu": [copy.deepcopy(punct)]}]}}
    cfu.clean_plan_cfu(pl, kb)
    check(f"a punctuation question (kind choose, no sum) is {'KEPT' if kept_expected else 'dropped'} when the skill is checked as '{ctype_kb}'", len(pl["rotation_schedule"]["blocks"][0]["cfu"]) == kept_expected)

print("word counts (found in the third literacy run: 'हम सब मिलकर / ...' has three words, the answer said 4)")
wc = lambda q_, e_: ck({"kind": "answer", "question_hi": q_, "expected_hi": e_, **sh})
Q_PROF = "बोर्ड पर लिखता/लिखती हूँ: 'हम सब मिलकर / स्कूल के मैदान में / खेलने गए।' पहले हिस्से के बाद रुकें तो कितने शब्द पढ़ने के बाद रुकेंगे? उँगलियों पर दिखाएँ।"
Q_PROG = "बोर्ड पर लिखता/लिखती हूँ: 'बच्चे स्कूल से घर आए।' अगर इसे दो हिस्सों में पढ़ें, तो पहले हिस्से में कितने शब्द होंगे? (बच्चे स्कूल से / घर आए) उँगलियों पर दिखाएँ।"
Q_TOT = "बोर्ड पर लिखता/लिखती हूँ: 'राम घर जाता है।' इस वाक्य में कुल कितने शब्द हैं? उँगलियों पर दिखाएँ।"
Q_ORD = "बोर्ड पर वाक्य है: 'पिता जी बाज़ार गए।' इसका तीसरा शब्द कौन सा है? उसे कॉपी पर लिखें।"
check("the words before a split are counted: 3 is right and 4 is wrong ('हम सब मिलकर'), and the gender-neutral 'लिखता/लिखती' is not taken for a split", wc(Q_PROF, "3") == [] and "3 words before the first slash" in " ".join(wc(Q_PROF, "4")))
check("a split shown in brackets works too: 3 is right, 2 is wrong", wc(Q_PROG, "3") == [] and wc(Q_PROG, "2") != [])
check("'how many words in this sentence' is checked: 4 is right, 5 is wrong, and an answer in words is left alone", wc(Q_TOT, "4") == [] and wc(Q_TOT, "5") != [] and wc(Q_TOT, "चार") == [])
check("'the third word' is checked against the sentence: बाज़ार is right, जी is wrong", wc(Q_ORD, "बाज़ार") == [] and wc(Q_ORD, "जी") != [] and wc(Q_ORD.replace("तीसरा", "दूसरा"), "जी") == [])
check("'पहला विराम किस शब्द के बाद' (the first PAUSE) is not mistaken for 'the first word'", wc("'बच्चे स्कूल से घर आए' पहला विराम किस शब्द के बाद लें? संख्या दिखाएँ।", "3") == [])

print("the number of a pause (found in the second literacy run: '2 (बच्चे स्कूल से / घर आए)', but three words come before the slash)")
pz = lambda e: ck({"kind": "answer", "question_hi": "पहला विराम किस शब्द के बाद लें? उंगली पर संख्या दिखाएँ।", "expected_hi": e, **sh})
check("a pause number that does not match the words before the slash is dropped", pz("2 (बच्चे स्कूल से / घर आए)") != [] and "words before the slash" in " ".join(pz("2 (बच्चे स्कूल से / घर आए)")))
check("the right number passes (3 words before the slash; and 1 word)", pz("3 (बच्चे स्कूल से / घर आए)") == [] and pz("1 (बच्चे / स्कूल से घर आए)") == [])
check("answers that merely look similar are not touched ('2 (सील)', '4 शब्द (4 उँगलियाँ)', '2')", all(pz(e) == [] for e in ("2 (सील)", "4 शब्द (4 उँगलियाँ)", "2", "बाईं ओर")))

print("numbers that are LABELS in a literacy question (found in the first literacy run: 'the expected answer should be 2, the bigger of 1 and 2' dropped a good question)")
labels = [{"kind": "choose", "question_hi": "वाक्य 1 और वाक्य 2 में कौन सा बड़ा है?", "expected_hi": "वाक्य 1, क्योंकि उसमें ज़्यादा शब्द हैं", **sh},
          {"kind": "choose", "question_hi": "कौन सा वाक्य अधिक लंबा है: 1 या 2?", "expected_hi": "1", **sh},
          {"kind": "answer", "question_hi": "अनुच्छेद 1 और अनुच्छेद 2 में किसमें अधिक वाक्य हैं? कौन सा बड़ा है?", "expected_hi": "अनुच्छेद 1", **sh}]
for ctype_kb in ("literacy",):
    kb = {"progressor": {"competency_id": "L", "name_en": "x", "name_hi": "x", "criteria_type": ctype_kb, "mistakes": []}}
    pl = {"rotation_schedule": {"blocks": [{"type": "teach", "teach_group": "progressor", "talking_points": {}, "cfu": copy.deepcopy(labels)}]}}
    ln_, _ = cfu.clean_plan_cfu(pl, kb)
    check("none of the three literacy questions with labelled numbers is DROPPED (the comparison check does not run for literacy; two are used)", not any("dropped" in l for l in ln_) and len(pl["rotation_schedule"]["blocks"][0]["cfu"]) == cfu.MAX_ITEMS, ln_)
check("the same questions ARE judged as numeric comparisons when the check is on (so the switch is what protects literacy)", all(ck(item, strict=False, compare=True) != [] for item in labels[:2]) and all(ck(item, strict=False, compare=False) == [] for item in labels))
check("a numeracy comparison is still verified, but only when the question really asks WHICH is bigger or smaller", ck({"kind": "choose", "question_hi": "47 और 74 में कौन बड़ा है?", "expected_hi": "47", **sh}) != []
      and ck({"kind": "answer", "question_hi": "वाक्य 1 और वाक्य 2 में बड़ा वाक्य लिखें।", "expected_hi": "वाक्य 1", **sh}, strict=False) == [])

print("what the first broad run (16 skills) dropped wrongly: the check must judge what a question ASKS, not the skill's type")
sh2 = {"listen_for": [], "shows_hi": "बच्चा पहचानता है"}
check("a pattern question (N1.1.1 is typed 'computation') is kept in a numeracy skill: it asks for no arithmetic", ck({"kind": "spot_error", "question_hi": "बोर्ड पर देखो: ● ○ ● ● लिखा है। पैटर्न सही है? सही या गलत?", "expected_hi": "गलत", **sh2}, strict=True) == []
      and ck({"kind": "choose", "question_hi": "किस आकृति में 4 कोने हैं: 1 या 2?", "expected_hi": "1", **sh2}, strict=True) == [])
check("arithmetic written in WORDS with digits is checked for plausibility: 50 - 20 = 30 passes, 40 does not", ck({"kind": "compute", "question_hi": "रीता के पास 50 रुपये थे। उसने 20 रुपये खर्च किए। कितने रुपये बचे?", "expected_hi": "30 रुपये", **sh2}, strict=True) == []
      and ck({"kind": "compute", "question_hi": "रीता के पास 50 रुपये थे। उसने 20 रुपये खर्च किए। कितने रुपये बचे?", "expected_hi": "40 रुपये", **sh2}, strict=True) != [])
check("a two-step word problem is plausible too: 3 x 12 - 10 = 26 passes, 28 does not", ck({"kind": "compute", "question_hi": "3 थान हैं, हर थान में 12 मीटर कपड़ा है। 10 मीटर बिक गया। कितना कपड़ा बचा?", "expected_hi": "26 मीटर", **sh2}, strict=True) == []
      and ck({"kind": "compute", "question_hi": "3 थान हैं, हर थान में 12 मीटर कपड़ा है। 10 मीटर बिक गया। कितना कपड़ा बचा?", "expected_hi": "28 मीटर", **sh2}, strict=True) != [])
check("arithmetic in words with NO digits cannot be checked: dropped in numeracy, kept in an observed skill", ck({"kind": "compute", "question_hi": "सैंतीस और बीस जोड़ें", "expected_hi": "57", **sh2}, strict=True) != [] and ck({"kind": "compute", "question_hi": "सैंतीस और बीस जोड़ें", "expected_hi": "57", **sh2}, strict=False) == [])
decoy = lambda e_: ck({"kind": "spot_error", "question_hi": "बोर्ड पर देखो: 6 × 7 = 42 लिखा है। सही या गलत?", "expected_hi": e_, **sh2})
check("a 'right or wrong?' question whose line is RIGHT is a fair decoy: the answer must say सही; saying गलत, or neither, is wrong", decoy("सही") == [] and decoy("सही, 6 × 7 = 42") == [] and decoy("गलत") != [] and decoy("42") != [])
check("an answer written as a Hindi number word counts (मेरा 2 × 2 = चार), a wrong word does not", ck({"kind": "compute", "question_hi": "2 × 2 कितना होगा?", "expected_hi": "चार", **sh2}) == [] and ck({"kind": "compute", "question_hi": "2 × 2 कितना होगा?", "expected_hi": "पाँच", **sh2}) != [])
check("the length of a PHRASE is not mistaken for the total ('पहला वाक्यांश कितने शब्द का है?' answer 3 for a 7-word sentence), but the TOTAL is still checked",
      ck({"kind": "answer", "question_hi": "'आज हम सब मिलकर बाज़ार जाएँगे।' पहला वाक्यांश कितने शब्द का है? उँगलियों पर दिखाएँ।", "expected_hi": "3", **sh2}) == []
      and ck({"kind": "answer", "question_hi": "'आज हम सब मिलकर बाज़ार जाएँगे।' इस वाक्य में कुल कितने शब्द हैं?", "expected_hi": "3", **sh2}) != [])
kb_ws = {"progressor": {"competency_id": "N", "name_en": "Adds two single-digit numbers", "name_hi": "x", "criteria_type": "computation", "mistakes": [{"id": "X-M1", "name_hi": "m", "diagnostic_indicator": "d"}]}}
pl_ws = {"worksheets": {"progressor": {"problems": [{"problem_hi": "7 + 8"}, {"problem_hi": "9 + 6"}]}},
         "rotation_schedule": {"blocks": [{"type": "teach", "teach_group": "progressor", "talking_points": {"i_do_hi": "बोर्ड पर 5 + 9 लिखें।"}, "cfu": [
             {"kind": "compute", "question_hi": "7 + 8 कितना होगा?", "expected_hi": "15", "listen_for": lf("X-M1", "14")}, {"kind": "compute", "question_hi": "5 + 9 कितना होगा?", "expected_hi": "14", "listen_for": lf("X-M1", "13")},
             {"kind": "compute", "question_hi": "6 + 6 कितना होगा?", "expected_hi": "12", "listen_for": lf("X-M1", "11")}]}]}}
ws_lines, _ = cfu.clean_plan_cfu(pl_ws, kb_ws)
check("single-digit sums (N1.3.1: 45 pairs): a worksheet repeat (7 + 8) is kept, a repeat of the lesson's own 5 + 9 is dropped, and the third question is kept",
      [q["question_hi"][:5] for q in pl_ws["rotation_schedule"]["blocks"][0]["cfu"]] == ["7 + 8", "6 + 6"] and any("5 + 9" in l and "dropped" in l for l in ws_lines), ws_lines)

print("the second broad run: questions that were fine and still dropped (N3.3.3 and N3.3.6), and the one the model really got wrong (N1.3.1)")
sh3 = {"listen_for": [], "shows_hi": "बच्चा पहचानता है"}
chain = lambda e_: ck({"kind": "compute", "question_hi": "2 + 2 + 2 + 2 को गुणा के रूप में लिखें: 4 × 2 कितना होगा? उत्तर लिखें।", "expected_hi": e_, **sh3})
check("a chain is one expression and the question asks about the LAST one: '2 + 2 + 2 + 2 ... 4 x 2' has the answer 8, not 4", chain("8") == [] and chain("6") != [])
check("a chain of three is added whole: 5 + 3 + 2 = 10", ck({"kind": "compute", "question_hi": "5 + 3 + 2 कितना होगा?", "expected_hi": "10", **sh3}) == [] and ck({"kind": "compute", "question_hi": "5 + 3 + 2 कितना होगा?", "expected_hi": "8", **sh3}) != [])
eqv = lambda e_: ck({"kind": "choose", "question_hi": "5 + 5 + 5 का गुणा रूप कौन सा है: 3 × 5 या 5 × 5? 1 या 2 उँगली दिखाएँ।", "expected_hi": e_, **sh3})
check("a choice BETWEEN expressions: 5 + 5 + 5 equals 3 x 5, so that is the right option, and the wrong option is dropped", eqv("1 उँगली (3 × 5)") == [] and eqv("2 उँगली (5 × 5)") != [] and eqv("1") == [])
check("a choice between expressions where NO option equals the starting one is the model's error", ck({"kind": "choose", "question_hi": "5 + 5 + 5 का गुणा रूप कौन सा है: 4 × 5 या 5 × 5? 1 या 2 दिखाएँ।", "expected_hi": "1 (4 × 5)", **sh3}) != [])
check("a hyphen between digits is '25 in each', not subtraction: 4 packets of 25 pencils, 30 given away, 70 left (and 75 is impossible)",
      ck({"kind": "compute", "question_hi": "4 पैकेट में 25-25 पेंसिल हैं, 30 पेंसिल दे दीं। कितनी बचीं?", "expected_hi": "70", **sh3}) == []
      and ck({"kind": "compute", "question_hi": "4 पैकेट में 25-25 पेंसिल हैं, 30 पेंसिल दे दीं। कितनी बचीं?", "expected_hi": "75", **sh3}) != [])
check("a real subtraction written with spaces is still a subtraction", ck({"kind": "compute", "question_hi": "50 - 20 कितना होगा?", "expected_hi": "30", **sh3}) == [] and ck({"kind": "compute", "question_hi": "50 - 20 कितना होगा?", "expected_hi": "70", **sh3}) != [])
wp = lambda e_: ck({"kind": "spot_error", "question_hi": "बोर्ड पर देखो: 3 थैलों में 15-15 आम हैं, 9 आम खराब निकले, बचे कितने? उत्तर 39 लिखा है। सही है या गलत?", "expected_hi": e_, **sh3})
check("a word problem with a child's answer but no equation: the correct answer in the key must be possible (3 x 15 - 9 = 36 is, 40 is not)", wp("गलत; सही उत्तर 36") == [] and wp("गलत; सही उत्तर 40") != [])
wrong_key = ck({"kind": "spot_error", "question_hi": "बोर्ड पर लिखें: 62 + 15 = 87। सही है या गलत? गलत है तो सही उत्तर लिखें", "expected_hi": "सही है", **sh3})
check("N1.3.1: the line 62 + 15 = 87 is WRONG (77), so the key 'सही है' is the model's mistake and is rightly dropped", wrong_key != [], wrong_key)

print("a wrong line when the child only writes सही or गलत (N3.3.6: '356 + 187 = 433', key 'गलत' was dropped for lacking the real result 543)")
verdict_q = "बोर्ड पर लिखें: 356 + 187 = 433। सही या गलत? सही लगे तो 'सही' और गलत लगे तो 'गलत' लिखें।"
vk = lambda e_, q_=verdict_q: ck({"kind": "spot_error", "question_hi": q_, "expected_hi": e_, **sh3})
check("the child writes only the verdict: the key 'गलत' is complete (the real result is not needed), 'सही' is wrong, and 'सही नहीं है' (NOT right) counts as गलत", vk("गलत") == [] and vk("सही") != [] and vk("सही नहीं है") == [] and vk("गलत; 356 + 187 = 543") == [])
ask_q = "बोर्ड पर लिखें: 62 + 15 = 87। सही या गलत? गलत है तो सही उत्तर लिखें।"
check("when the question ASKS for the correct answer the key must give it (77): 'गलत' alone is incomplete, 'गलत; सही उत्तर 77' passes, 'सही है' is wrong, and a bare 'सही उत्तर 77' is not read as a verdict",
      vk("गलत", ask_q) != [] and vk("गलत; सही उत्तर 77", ask_q) == [] and vk("सही है", ask_q) != [] and vk("सही उत्तर 77", ask_q) == [])
check("a correct line with the key 'सही नहीं' is wrong (it says the right line is not right)", ck({"kind": "spot_error", "question_hi": "बोर्ड पर देखो: 6 × 7 = 42 लिखा है। सही या गलत?", "expected_hi": "सही नहीं", **sh3}) != [])

print("what the teachers' review ruled out (Vaishnavi, 23 Oct)")
shx = {"listen_for": [], "shows_hi": "बच्चा पहचानता है"}
story = lambda q_: ck({"kind": "answer", "question_hi": q_, "expected_hi": "गलत", **shx}, strict=False)
check("a question told as a story about a child is dropped, with the reason and what to write instead", all(story(q_) != [] and "story about a child" in " ".join(story(q_)) for q_ in ("एक बच्चे ने 8 + 3 = 10 लिखा। सही या गलत?", "बच्चे ने 9 कंकड़ गिने। फिर दोबारा गिना।", "एक बच्चा कहता है: तेज़ पढ़ो। सही या गलत?", "दो बच्चों ने वाक्य पढ़ा। कौन सा अच्छा है?")))
check("...the same thing written as what is ON THE BOARD is kept", story("बोर्ड पर देखो: 34 + 28 = 52 लिखा है। क्या यह सही है?") == [])
check("a child inside QUOTES is not a story (it may be the sentence the children read), and the teacher's own first person is fine", story("'बच्चे ने किताब पढ़ी' के अंत में कौन-सा चिह्न लगेगा?") == [] and story("मैं 'गाय हरी घर खाती है' पढ़ती हूँ। सही या गलत?") == [])
check("a question about the structure or purpose of a paragraph is dropped; punctuation and 'what happened first' are kept", story("अनुच्छेद का पहला वाक्य किस काम के लिए होता है?") != [] and story("अनुच्छेद में 'परिचय' और 'निष्कर्ष' में से क्या पहले आता है?") != [] and story("अनुच्छेद के अंत में कौन-सा चिह्न लगेगा?") == [] and story("कहानी में पहले क्या हुआ: 1 या 2?") == [])
check("two show-me questions per group (a lesson has no time for more: eight in a block cost 5 to 7 minutes of 27)", cfu.MAX_ITEMS == 2 and cfu.MIN_ITEMS == 2)

print("cleaning a whole plan")
KB = {"progressor": {"competency_id": "X", "name_en": "Adds with regrouping", "name_hi": "x", "mistakes": [
          {"id": "X-M1", "name_hi": "हासिल भूलना", "diagnostic_indicator": "Answer is exactly 10 less than correct"}, {"id": "X-M2", "name_hi": "पूरा योग लिखना", "diagnostic_indicator": "Three digits where two expected"}]},
      "beginner": {"competency_id": "Y", "name_en": "Adds two 2-digit numbers without regrouping", "name_hi": "y", "mistakes": []}}
good = lambda q, e, mid, w: {"kind": "compute", "question_hi": q, "expected_hi": e, "listen_for": lf(mid, w)}
plan = {"worksheets": {"progressor": {"problems": [{"problem_hi": "12 + 19"}]}},
        "rotation_schedule": {"blocks": [{"type": "anchor", "cfu": [{"junk": 1}]},
            {"type": "teach", "teach_group": "progressor", "talking_points": {"i_do_hi": "बोर्ड पर 47 + 25 लिखें।", "we_do_hi": "", "you_do_hi": ""}, "cfu": [
                good("58 + 27 कितना होगा?", "85", "X-M1", "75"),                         # fine
                good("29 + 48 कितना होगा?", "76", "X-M1", "x"),                          # wrong answer: dropped
                good("47 + 25 कितना होगा?", "72", "X-M1", "x"),                          # reuses the lesson's example: dropped
                {"kind": "answer", "question_hi": "इकाई का योग 13: इकाई में क्या?", "expected_hi": "3", "listen_for": [{"misconception_id": "X-M2", "wrong_answer_hi": "13"}, {"misconception_id": "N9-M9", "wrong_answer_hi": "q"}]},
                good("12 + 19 कितना होगा?", "31", "X-M1", "x"),                          # repeats a worksheet problem: KEPT and noted (only a repeat of the LESSON's example is dropped)
                good("36 + 48 कितना होगा?", "84", "X-M2", "714"), good("67 + 15 कितना होगा?", "82", "X-M1", "72"), good("28 + 46 कितना होगा?", "74", "X-M1", "64")]},
            {"type": "teach", "teach_group": "beginner", "talking_points": {}, "cfu": [{"kind": "compute", "question_hi": "21 + 36 कितना होगा?", "expected_hi": "57", "listen_for": [], "shows_hi": "बच्चा दहाई और इकाई अलग जोड़ता है"}]},
            {"type": "teach", "teach_group": "proficient", "talking_points": {}}]}}
lines, stats = cfu.clean_plan_cfu(plan, KB)
blocks = plan["rotation_schedule"]["blocks"]
prog, beg, prof = blocks[1], blocks[2], blocks[3]
check("a block that is not a teach block gets no CFU, whatever the model wrote", "cfu" not in blocks[0])
check("the invalid questions are dropped and the valid ones kept (58+27 and the grounded answer item are the first two valid ones: more are valid, but only two are allowed)", len(prog["cfu"]) == cfu.MAX_ITEMS and prog["cfu"][0]["question_hi"].startswith("58 + 27") and prog["cfu"][1]["kind"] == "answer", [q["question_hi"] for q in prog["cfu"]])
check("only the two bad ones are dropped (a wrong answer, a repeat of the LESSON's example), each with its reason and the question itself in the log; the worksheet repeat is kept and noted", sum("dropped" in l for l in lines) == 2 and any("already used" in l and "47 + 25" in l for l in lines) and any("real result 77" in l for l in lines) and any("kept, though it repeats a worksheet problem" in l for l in lines), lines)
check("a question beyond the allowed two is left out, and that is logged", any(f"beyond the {cfu.MAX_ITEMS} allowed" in l for l in lines))
item = next(q for q in prog["cfu"] if q["kind"] == "answer")
check("the mistake's Hindi name and its detect sign come from the knowledge base, not from the model", item["listen_for"] == [{"misconception_id": "X-M2", "misconception_name_hi": "पूरा योग लिखना", "detect_en": "Three digits where two expected", "wrong_answer_hi": "13"}], item["listen_for"])
check("an invented mistake id is removed from listen_for, the rest of the question stays", len(item["listen_for"]) == 1 and any("N9-M9" in l for l in lines))
check("a skill with recorded mistakes is marked grounded, and every kept question names one", prog["cfu_grounded"] is True and all(q["grounded"] for q in prog["cfu"]) and "cfu_note_hi" not in prog)
check("a skill with NO recorded mistakes is kept only through 'what a right answer shows', marked, and the screen note is set by the code", beg["cfu_grounded"] is False and len(beg["cfu"]) == 1 and beg["cfu"][0]["grounded"] is False and "दर्ज नहीं" in beg["cfu_note_hi"] and beg["cfu_note_en"])
check("a block where the model wrote no CFU gets an empty list and is logged", prof["cfu"] == [] and any("proficient: no CFU written" in l for l in lines))
check("the stats say what was written and kept", stats["progressor"] == {"written": 8, "kept": cfu.MAX_ITEMS, "grounded_items": cfu.MAX_ITEMS, "skill_has_mistakes": True} and stats["beginner"]["kept"] == 1, stats)
lines2, _ = cfu.clean_plan_cfu({"rotation_schedule": {"blocks": [
    {"type": "teach", "teach_group": "progressor", "talking_points": {"i_do_hi": "x", "cfu": [good("58 + 27 कितना होगा?", "85", "X-M1", "75"), good("68 + 17 कितना होगा?", "85", "X-M1", "75")]}},
    {"type": "teach", "teach_group": "beginner", "talking_points": {"i_do_hi": "x"}, "mystery_key": 1}]}}, KB)
check("questions the model put among the talking points are found and moved out of them", not any("cfu" in (b.get("talking_points") or {}) for b in []) and any("under talking_points: moved" in l for l in lines2), lines2)
check("when nothing was written the log says which keys the block has (to see what the model did instead)", any("no CFU written (the model's block has:" in l and "mystery_key" in l and "cfu_grounded" not in l for l in lines2), lines2)
check("strip_cfu removes everything", (cfu.strip_cfu(plan) or True) and not any(k in b for b in blocks for k in ("cfu", "cfu_grounded", "cfu_note_hi")))

print("a wrong answer that is a RIGHT answer in the lesson (first real re-teach run: '176 + 349 = 425' on the board, while the I Do's right answer to 267 + 158 was 425)")
spw = lambda q_, e_: {"kind": "spot_error", "question_hi": q_, "expected_hi": e_, "listen_for": lf("X-M1", "425")}
w425 = spw("बोर्ड पर देखें: 176 + 349 = 425 लिखा है। सही या गलत?", "गलत, सही उत्तर 525")
check("the wrong line is dropped when its answer is a right answer in the lesson, and the reason says so", any("right answer in this group's lesson" in p for p in ck(w425, lesson_results={425, 15, 11})), ck(w425, lesson_results={425}))
check("...and kept when the lesson never works that number out", ck(w425) == [] and ck(w425, lesson_results={83, 13, 43}) == [])
check("a small number is not a collision (single digits are everywhere in a lesson)", ck(spw("बोर्ड पर देखें: 3 + 4 = 8 लिखा है। सही या गलत?", "गलत, सही उत्तर 7"), lesson_results={8}) == [])
lesson_plan = {"rotation_schedule": {"blocks": [{"type": "teach", "teach_group": "progressor", "talking_points": {"i_do_hi": "बोर्ड पर 267 + 158 लिखें और हल करें।", "we_do_hi": "185 + 247 साथ में हल करें।", "you_do_hi": ""}, "cfu": [dict(w425), good("286 + 157 कितना होगा?", "443", "X-M1", "343")]}]}}
ll, _ = cfu.clean_plan_cfu(lesson_plan, KB)
check("through the whole plan: the colliding question is dropped with its reason in the log, and the other one is kept", [q["question_hi"][:8] for q in lesson_plan["rotation_schedule"]["blocks"][0]["cfu"]] == ["286 + 15"] and any("right answer in this group's lesson" in l for l in ll), ll)
check("the lesson's right answers are the results of the operations in it, I Do, We Do and You Do", cfu._lesson_results(lesson_plan["rotation_schedule"]["blocks"][0]) >= {425, 432})

print("what the second real batch run showed (23 Oct): the strings are from the run")
person = lambda q_: ck({"kind": "answer", "question_hi": q_, "expected_hi": "गलत", **shx}, strict=False)
check("a story about ANY person is dropped, not only 'a child': 'एक पाठक ने', 'किसी ने', 'एक विद्यार्थी ने'", all(person(q_) != [] and "story" in " ".join(person(q_)) for q_ in ("बोर्ड पर लिखा है: 'तोता हरे रंग का था।' एक पाठक ने इसे 'तोता हरा रंग का था' पढ़ा। क्या यह पढ़ना सही है या गलत?", "किसी ने 'श्रमिक मधुमक्खियाँ' को 'श्रमिक मधुमक्खी' पढ़ दिया। क्या यह ठीक पढ़ना है: सही या गलत?", "एक विद्यार्थी ने 7 + 5 = 11 लिखा। सही या गलत?")))
check("...while the teacher's own first person and a line on the board are kept", person("मैं 'तोता हरे रंग का था' को 'तोता हरा रंग का था' पढ़ता/पढ़ती हूँ। क्या यह सही है?") == [] and person("बोर्ड पर देखें: 7 + 5 = 11 लिखा है। सही या गलत?") == [])
check("'which sentence is different from the topic' is dropped even without the word 'paragraph' (the batch run had one), and 'sequence' and 'punctuation' questions are not mistaken for it",
      person("बोर्ड पर लिखा है: 'मेरा विषय है मेरा स्कूल। मेरे स्कूल में एक बड़ा मैदान है। मुझे आम बहुत पसंद हैं।' कौन सा वाक्य विषय से अलग है? संख्या (1, 2 या 3) लिखें।") != []
      and person("'पेड़ पर कौन बैठा है' के अंत में कौन-सा चिह्न लगेगा?") == [] and person("कहानी में पहले कौन सा वाक्य आएगा: 1 या 2?") == [])
long_q = "बोर्ड पर लिखें: दहाई-इकाई के बॉक्स में 43 + 25 में पहली पंक्ति 4 दहाई और 3 इकाई, दूसरी पंक्ति में 2 इकाई और 5 दहाई लिखी है, यानी अंक उलटे स्तंभ में हैं। क्या यह सही है? सही हो तो 1, गलत हो तो 2 उँगलियाँ दिखाएँ।"
good_q = "मैं वाक्य दो तरह से पढ़ूँगा/पढ़ूँगी: 1) हम...स्कूल...जाते...हैं 2) हम स्कूल जाते हैं। कौन सा पढ़ना ठीक है: 1 या 2? उंगलियों से दिखाएँ।"
check("a 210-character verbal description of a table, which also gives its answer away, is too long; the longest good question seen (134 characters) is kept",
      len(long_q) > cfu.MAX_QUESTION_CHARS >= len(good_q) and ck({"kind": "spot_error", "question_hi": long_q, "expected_hi": "गलत", **shx}, strict=False) != [] and ck({"kind": "choose", "question_hi": good_q, "expected_hi": "2", **shx}, strict=False) == [])
check("a key is a verdict and a number: 100 characters at most (the key that reversed the places was an explanation)", cfu.MAX_EXPECTED_CHARS == 100 and ck({"kind": "answer", "question_hi": "क्यों?", "expected_hi": "ग" * 120, **shx}, strict=False) != [] and ck({"kind": "answer", "question_hi": "क्यों?", "expected_hi": "गलत, सही उत्तर 83 है (इकाई 13 में से 1 हासिल दहाई में जुड़ा नहीं)", **shx}, strict=False) == [])
kb_v = {"beginner": {"competency_id": "N", "name_en": "Adds without regrouping", "name_hi": "x", "criteria_type": "computation", "mistakes": [{"id": "X-M1", "name_hi": "m", "diagnostic_indicator": "d"}]}}
mk = lambda q_, e_, w_: {"kind": "compute", "question_hi": q_, "expected_hi": e_, "listen_for": lf("X-M1", w_)}
vp = {"rotation_schedule": {"blocks": [{"type": "teach", "teach_group": "beginner", "talking_points": {}, "cfu": [
    mk("बोर्ड पर देखें: 52 + 36। जोड़ स्लेट पर लिखें।", "88", "इकाई और दहाई मिलाकर गलत उत्तर, जैसे 7 + 8 जैसा बेमेल जोड़"),
    mk("बोर्ड पर देखें: 23 + 14। जोड़ स्लेट पर लिखें।", "37", "तीन-चार जैसा बेतरतीब उत्तर, जैसे 99 या 79"),
    mk("बोर्ड पर देखें: 41 + 27। जोड़ स्लेट पर लिखें।", "68", "115"),
    mk("बोर्ड पर देखें: 12 + 31। जोड़ स्लेट पर लिखें।", "43", "उत्तर नहीं लिखा या अंदाज़ से कोई संख्या लिखी")]}]}}
vl, _ = cfu.clean_plan_cfu(vp, kb_v)
kept_v = [q["question_hi"] for q in vp["rotation_schedule"]["blocks"][0]["cfu"]]
check("a 'listen for' that only DESCRIBES ('जैसे 7 + 8 जैसा बेमेल जोड़', 'बेतरतीब उत्तर') is removed, and a question left with nothing is dropped; an exact answer ('115') and a behaviour ('उत्तर नहीं लिखा...') stay",
      len(kept_v) == 2 and "41 + 27" in kept_v[0] and "12 + 31" in kept_v[1] and sum("removed 1 vague listen-for" in l for l in vl) == 2, (kept_v, vl))
check("a vague note is only removed for a NUMERIC question: a literacy question may describe", cfu._without_vague_listen({"kind": "compute", "listen_for": lf("X-M1", "कोई जैसा उत्तर")}, False)[1] == 0)

print("the log line 'the model's block has' lists what the MODEL wrote, not what the code stamped (seen in the first re-teach test output)")
pl_k = {"rotation_schedule": {"blocks": [{"type": "teach", "teach_group": "progressor", "talking_points": {}, "reteach": True, "affected_rolls": [4, 5], "reteach_mistakes": [], "mystery_key": 1}]}}
lk, _ = cfu.clean_plan_cfu(pl_k, KB)
check("a re-teach block's own marks (reteach, affected_rolls, reteach_mistakes) are not listed as keys the model wrote, but the model's keys are", any("mystery_key" in l for l in lk) and not any(k in l for l in lk for k in ("reteach", "affected_rolls")), lk)

print("the prompt")
M = [{"id": "A-M1", "name_hi": "एक", "severity": "moderate", "frequency": "uncommon", "error_pattern": "p1", "diagnostic_indicator": "d1", "example_correct": "c", "example_incorrect": "w"},
     {"id": "A-M2", "name_hi": "दो", "severity": "critical", "frequency": "very_common", "error_pattern": "p2", "diagnostic_indicator": "d2", "example_correct": None, "example_incorrect": None},
     {"id": "A-M3", "name_hi": "तीन", "severity": "moderate", "frequency": "common", "error_pattern": "p3", "diagnostic_indicator": "d3", "example_correct": "c", "example_incorrect": "w"}]
check("mistakes are ranked: most common and most serious first", [m["id"] for m in cfu_prompt.rank_mistakes(M, {})] == ["A-M2", "A-M3", "A-M1"])
check("...and a mistake detected at the last review comes before everything", [m["id"] for m in cfu_prompt.rank_mistakes(M, {"A-M1": 2})][0] == "A-M1")
txt = cfu_prompt.render_cfu_section({"beginner": {"competency_id": "B", "name_en": "b", "name_hi": "ब", "mistakes": []}, "progressor": {"competency_id": "A", "name_en": "a", "name_hi": "अ", "mistakes": M}}, {"A-M1": 2})
check("the rules say: write 3, most important first, two are used; no story about a child, no objects, no abstract paragraph questions, real matra pairs, plain Hindi",
      all(w in txt for w in ("MOST IMPORTANT FIRST", "Do NOT tell a story about a child", "No object is ever handed out", "NEVER about the structure or purpose of a paragraph", "दिन / दीन", "इसके बाद", "a choice is better than writing")))
check("the rules say a wrong line must not carry a number the lesson shows as right, and that listen_for is the exact wrong answer, never a description", all(w in txt for w in ("must never be a number the lesson shows as a RIGHT answer", "EXACT wrong answer", "never a description")))
check("the rules say: no person who 'did' something, a key is only a verdict and a number, no table described in words, punctuation choices as '1) । 2) ?'",
      all(w in txt for w in ("No PERSON at all", "ONLY: no explanation", "Never describe a drawing or a table in words", "1) । 2) ?")))
check("the section carries the rules, the show-me, and no choral answering", "SHOW-ME" in txt and "Never choral" in txt and '"cfu"' in txt)
check("it allows other ways to show an answer (fingers, cards, drawing) for readiness skills, and asks for questions in EVERY skill", "fingers" in txt and "cards" in txt and "EVERY skill" in txt)
check("it asks for self-contained questions, one task each, nothing copied or written as a sentence, a number for pauses, and different shapes for the groups (found in the first literacy run)",
      all(w in txt for w in ("SELF-CONTAINED", "Never give the answer away", "ONE thing per question", "NEVER ask them to copy a sentence", "NUMBER of the word after which to pause", "must not get questions of the same shape")))
check("it also asks the teacher to be told exactly what to write on the board, to count the words before a pause, to stay at the children's age and to let every child answer from their own place",
      all(w in txt for w in ("WITHOUT the line on top", "words BEFORE the slash", "no percentages", "touch the letter on the board")))
check("it asks for the right answer to be ONLY the answer, no non-words to write, and finger choices for Beginners",
      all(w in txt for w in ("is ONLY the answer", "not a real word", "finger choice")))
check("it says what each kind is for, so a plain comparison is not labelled compute, and it does not ask the question to repeat the procedure", "Anything else is" in txt and "Do not repeat the show-me procedure" in txt)
check("each group gets its own skill and its own mistakes, the detected one flagged first", "GROUP PROGRESSOR" in txt and txt.index("A-M1") < txt.index("A-M2") and "DETECTED at the last review in 2 child(ren)" in txt)
check("a group with no recorded mistakes is told to test the key idea", "No mistakes are recorded for this skill" in txt.split("GROUP PROGRESSOR")[0])
check("at most four mistakes per group", cfu_prompt.render_cfu_section({"progressor": {"competency_id": "A", "mistakes": [dict(M[0], id=f"A-M{i}") for i in range(9)]}}).count("pattern:") == 4)
check("nothing at all when CFU is switched off", cfu_prompt.render_cfu_section(None) == "" and cfu_prompt.render_cfu_section({}) == "")


class FakeMessages:
    def __init__(self, cfu_by_group):
        self.prompts, self.cfu_by_group = [], cfu_by_group

    async def create(self, **kw):
        self.prompts.append(kw["messages"][0]["content"])
        plan = copy.deepcopy(SAMPLE)
        for b in plan["rotation_schedule"]["blocks"]:
            if b.get("type") == "teach" and b.get("teach_group") in self.cfu_by_group:
                b["cfu"] = copy.deepcopy(self.cfu_by_group[b["teach_group"]])
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(plan, ensure_ascii=False))], stop_reason="end_turn", usage=SimpleNamespace(input_tokens=6000, output_tokens=9000))


async def main():
    db = await _scratch.connect()
    levels = {1: "beginner", 2: "beginner", 3: "beginner", 4: "progressor", 5: "progressor", 6: "progressor", 7: "proficient", 8: "proficient"}
    teacher_id, school = await _scratch.make_class(db, {r: (lv, lv) for r, lv in levels.items()}, grade="grade_2")
    real_client = anthropic.AsyncAnthropic
    settings = get_settings()
    try:
        ids = {c: [r["id"] for r in await db.fetch("SELECT id FROM misconceptions WHERE competency_id = $1 ORDER BY sort_order", c)] for c in ("N2.3.1", "N2.3.2", "N3.3.1", "N2.3.3")}
        print("\nthe whole pipeline, with a stand-in model (selected skill N2.3.2; Beginner N2.3.1, Progressor N2.3.2, Proficient N3.3.1)")
        check("the knowledge base has recorded mistakes for the three skills and none for N2.3.3", all(ids[c] for c in ("N2.3.1", "N2.3.2", "N3.3.1")) and not ids["N2.3.3"], ids)
        M1, M2 = [i for i in ids["N2.3.2"] if i.endswith("M1")][0], [i for i in ids["N2.3.2"] if i.endswith("M2")][0]
        written = {
            "progressor": [{"kind": "compute", "question_hi": "68 + 17 कितना होगा?", "expected_hi": "85", "listen_for": lf(M1, "75")},
                           {"kind": "choose", "question_hi": "39 + 47: उत्तर 76 है या 86?", "expected_hi": "86", "listen_for": lf(M1, "76")},       # its own right answer: two questions of one group may not share one (test_cfu_answers.py)
                           {"kind": "compute", "question_hi": "29 + 48 कितना होगा?", "expected_hi": "76", "listen_for": lf(M1, "66")},              # wrong answer: dropped
                           {"kind": "answer", "question_hi": "इकाई का योग 13 आए तो इकाई में क्या?", "expected_hi": "3", "listen_for": lf("N9.9.9-M1", "13")}],  # invented id, no shows: dropped
            "beginner": [{"kind": "compute", "question_hi": "21 + 36 कितना होगा?", "expected_hi": "57", "listen_for": lf(ids["N2.3.1"][0], "x")},
                         {"kind": "compute", "question_hi": "38 + 47 कितना होगा?", "expected_hi": "85", "listen_for": lf(ids["N2.3.1"][0], "x")},                # needs a carry: dropped
                         {"kind": "answer", "question_hi": "47 में कितनी दहाई हैं?", "expected_hi": "4", "listen_for": [], "shows_hi": "बच्चा दहाई पहचानता है"}],
            "proficient": "not a list at all"}
        # a mistake detected at the last review: two Progressors made M2 yesterday
        kids = {r["roll_number"]: r["id"] for r in await db.fetch("SELECT id, roll_number FROM children WHERE teacher_id = $1", teacher_id)}
        mrow = await db.fetchrow("SELECT competency_id FROM misconceptions WHERE id = $1", M2)
        for r in (4, 5):
            await db.execute("INSERT INTO assessment_evidence (child_id, competency_id, teacher_id, channel, status, evidence_data, detected_misconception_ids, session_date) VALUES ($1, $2, $3, 'written_photo', 'not_achieved', '{}'::jsonb, $4, $5)",
                             kids[r], mrow["competency_id"], teacher_id, [M2], TODAY - timedelta(days=1))
        fake = FakeMessages(written)
        anthropic.AsyncAnthropic = lambda **kw: SimpleNamespace(messages=fake)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            await plan_service.generate_dainik_yojana(db, teacher_id, "N2.3.2", "numeracy", TODAY)
        log, prompt = buf.getvalue(), fake.prompts[-1]
        row = await db.fetchrow("SELECT plan_content FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2", teacher_id, TODAY)
        pc = json.loads(row["plan_content"]) if isinstance(row["plan_content"], str) else row["plan_content"]
        blocks = {b["teach_group"]: b for b in pc["rotation_schedule"]["blocks"] if b.get("type") == "teach"}
        check("the prompt carries the CFU rules", "CHECK FOR UNDERSTANDING" in prompt and "SHOW-ME" in prompt)
        check("each group's OWN skill and its recorded mistakes are in the prompt (the Beginners' N2.3.1 and the Proficients' N3.3.1, not only the selected skill's)",
              all(f"GROUP {g.upper()}" in prompt for g in ("BEGINNER", "PROGRESSOR", "PROFICIENT")) and ids["N2.3.1"][0] in prompt and ids["N3.3.1"][0] in prompt and M1 in prompt)
        sec = prompt[prompt.index("GROUP PROGRESSOR"):]
        check("the mistake detected at the last review is flagged and listed before the other Progressor mistakes", "DETECTED at the last review in 2 child(ren)" in sec and sec.index(M2) < sec.index(M1), sec[:300])
        check("the Progressor block keeps its two valid questions and drops the two bad ones", [q["question_hi"][:8] for q in blocks["progressor"]["cfu"]] == ["68 + 17 ", "39 + 47:"], blocks["progressor"].get("cfu"))
        check("...with the mistake's Hindi name from the knowledge base", blocks["progressor"]["cfu"][0]["listen_for"][0]["misconception_name_hi"] and blocks["progressor"]["cfu_grounded"] is True)
        check("the Beginner block drops the question that needs a carry (the skill is 'without regrouping') and keeps the others", [q["question_hi"][:8] for q in blocks["beginner"]["cfu"]] == ["21 + 36 ", "47 में क"], blocks["beginner"].get("cfu"))
        check("a model answer that is not a list for the Proficients gives an empty CFU, no crash", blocks["proficient"]["cfu"] == [])
        check("the log says what was dropped and what was kept", "CFU kept:" in log and "dropped" in log, log[-400:])
        check("no question is stored that was not checked: every stored question is in the knowledge base's terms", all(q["kind"] in cfu.KINDS for b in blocks.values() for q in b["cfu"]))

        print("\na skill with no recorded mistakes (N2.3.3 selected)")
        fake2 = FakeMessages({"progressor": [{"kind": "compute", "question_hi": "78 − 35 कितना होगा?", "expected_hi": "43", "listen_for": [], "shows_hi": "बच्चा स्तंभ-दर-स्तंभ घटाता है"},
                                             {"kind": "compute", "question_hi": "64 − 23 कितना होगा?", "expected_hi": "41", "listen_for": lf("N9.9.9-M1", "x"), "shows_hi": "बच्चा घटाव पक्का करता है"}]})
        anthropic.AsyncAnthropic = lambda **kw: SimpleNamespace(messages=fake2)
        with contextlib.redirect_stdout(io.StringIO()):
            await plan_service.generate_dainik_yojana(db, teacher_id, "N2.3.3", "numeracy", TODAY + timedelta(days=1))
        row = await db.fetchrow("SELECT plan_content FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2", teacher_id, TODAY + timedelta(days=1))
        pc2 = json.loads(row["plan_content"]) if isinstance(row["plan_content"], str) else row["plan_content"]
        b2 = {b["teach_group"]: b for b in pc2["rotation_schedule"]["blocks"] if b.get("type") == "teach"}["progressor"]
        check("the prompt tells the model that this skill has no recorded mistakes", "No mistakes are recorded for this skill" in fake2.prompts[-1])
        check("the questions are kept through 'what a right answer shows', marked ungrounded, with the screen note", len(b2["cfu"]) == 2 and b2["cfu_grounded"] is False and all(not q["grounded"] for q in b2["cfu"]) and "दर्ज नहीं" in b2["cfu_note_hi"], b2)
        check("an invented mistake id is removed, not trusted", all(q["listen_for"] == [] for q in b2["cfu"]))

        print("\na readiness skill that is observed, not computed (N0.1.3 selected)")
        eq = {"kind": "choose", "question_hi": "3 फूल और 3 फूल हैं। ज़्यादा, कम या बराबर?", "expected_hi": "बराबर", "listen_for": [], "shows_hi": "बच्चा बराबर की स्थिति पहचानता है"}
        bad = {"kind": "choose", "question_hi": "5 बीज और 3 बीज हैं। ज़्यादा, कम या बराबर?", "expected_hi": "बराबर", "listen_for": [], "shows_hi": "x"}
        cnt = {"kind": "compute", "question_hi": "गिनकर उँगलियों पर दिखाइए: कितने फूल?", "expected_hi": "3", "listen_for": [], "shows_hi": "बच्चा गिनती जानता है"}
        fake4 = FakeMessages({"progressor": [eq, bad, cnt], "beginner": [{"kind": "answer", "question_hi": "गिनकर बताइए: कितने?", "expected_hi": "3", "listen_for": [], "shows_hi": "y"}], "proficient": [dict(eq, kind="answer")]})
        anthropic.AsyncAnthropic = lambda **kw: SimpleNamespace(messages=fake4)
        with contextlib.redirect_stdout(io.StringIO()):
            await plan_service.generate_dainik_yojana(db, teacher_id, "N0.1.3", "numeracy", TODAY + timedelta(days=3))
        row = await db.fetchrow("SELECT plan_content FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2", teacher_id, TODAY + timedelta(days=3))
        pc4 = json.loads(row["plan_content"]) if isinstance(row["plan_content"], str) else row["plan_content"]
        b4 = {b["teach_group"]: b for b in pc4["rotation_schedule"]["blocks"] if b.get("type") == "teach"}
        check("the observed skill keeps its two good questions (the equal comparison and the count with no sum) and drops the wrong comparison", [q["question_hi"][:6] for q in b4["progressor"]["cfu"]] == ["3 फूल ", "गिनकर "], b4["progressor"].get("cfu"))
        check("the other groups keep theirs, so no block is left empty", len(b4["beginner"]["cfu"]) == 1 and len(b4["proficient"]["cfu"]) == 1)
        check("the prompt shows the model that these skills have no recorded mistakes and tells it to still write questions", "No mistakes are recorded for this skill" in fake4.prompts[-1] and "EVERY skill" in fake4.prompts[-1])

        print("\na model that SKIPS the questions: the top-up call (the model wrote none in 4 of about 25 plans)")
        from app.services import ai_budget
        os.environ["CFU_TOPUP"] = "1"
        id_beg, id_prof = ids["N2.3.1"][0], ids["N3.3.1"][0]
        beg_ok = {"kind": "compute", "question_hi": "21 + 36 कितना होगा?", "expected_hi": "57", "listen_for": lf(id_beg, "x")}
        beg_carry = {"kind": "compute", "question_hi": "38 + 47 कितना होगा?", "expected_hi": "85", "listen_for": lf(id_beg, "x")}
        top_beg = [{"kind": "compute", "question_hi": "12 + 34 कितना होगा?", "expected_hi": "46", "listen_for": lf(id_beg, "x")},
                   {"kind": "answer", "question_hi": "52 में कितनी दहाई हैं?", "expected_hi": "5", "listen_for": [], "shows_hi": "बच्चा दहाई पहचानता है"}]
        top_prof = [{"kind": "compute", "question_hi": "286 + 157 कितना होगा?", "expected_hi": "443", "listen_for": lf(id_prof, "343")},
                    {"kind": "choose", "question_hi": "375 + 148: उत्तर 523 है या 423?", "expected_hi": "523", "listen_for": lf(id_prof, "423")}]

        class Seq:
            def __init__(self, replies):
                self.replies, self.calls, self.prompts = list(replies), 0, []

            async def create(self, **kw):
                self.calls += 1
                self.prompts.append(kw["messages"][0]["content"])
                r = self.replies[min(self.calls - 1, len(self.replies) - 1)]
                return SimpleNamespace(content=[SimpleNamespace(type="text", text=r if isinstance(r, str) else json.dumps(r, ensure_ascii=False))], stop_reason="end_turn", usage=SimpleNamespace(input_tokens=6000, output_tokens=9000))

        def plan_with(by_group):
            pl = copy.deepcopy(SAMPLE)
            for b in pl["rotation_schedule"]["blocks"]:
                if b.get("type") == "teach" and b.get("teach_group") in by_group:
                    b["cfu"] = copy.deepcopy(by_group[b["teach_group"]])
            return pl

        async def run(replies, day):
            await db.execute("DELETE FROM ai_usage WHERE school_id = (SELECT id FROM schools WHERE school_code = $1)", school)
            fk = Seq(replies)
            anthropic.AsyncAnthropic = lambda **kw: SimpleNamespace(messages=fk)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                await plan_service.generate_dainik_yojana(db, teacher_id, "N2.3.2", "numeracy", day)
            row = await db.fetchrow("SELECT plan_content FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2", teacher_id, day)
            pc_ = json.loads(row["plan_content"]) if isinstance(row["plan_content"], str) else row["plan_content"]
            rows_ = await db.fetchval("SELECT count(*) FROM ai_usage WHERE school_id = (SELECT id FROM schools WHERE school_code = $1)", school)
            return fk, buf.getvalue(), pc_, {b["teach_group"]: b for b in pc_["rotation_schedule"]["blocks"] if b.get("type") == "teach"}, rows_

        partial = {"progressor": written["progressor"][:2], "beginner": [beg_ok, beg_carry]}                  # progressor fine, beginner 1 valid (a carry is rejected), proficient none
        full = {"progressor": written["progressor"][:2], "beginner": [beg_ok, top_beg[1]], "proficient": top_prof}
        d0 = TODAY + timedelta(days=10)
        fk, log, pc5, bl5, rows5 = await run([plan_with(partial), {"beginner": top_beg, "proficient": top_prof}], d0)
        p2 = fk.prompts[1] if len(fk.prompts) > 1 else ""
        check("blocks with fewer than 2 valid questions get ONE more call, and no other block is asked about", fk.calls == 2 and "GROUP BEGINNER: write exactly 2" in p2 and "GROUP PROFICIENT: write exactly 3" in p2 and "GROUP PROGRESSOR" not in p2, (fk.calls, p2[-700:]))
        check("the top-up call is metered like the plan: two paid calls, two rows", rows5 == 2, rows5)
        check("the request carries what the model needs: the questions already written, why earlier ones were rejected, the recorded mistakes of THAT group's skill", "21 + 36 कितना होगा?" in p2 and "needs a carry" in p2 and "no CFU written" in p2 and id_prof in p2 and "WHAT IS MISSING" in p2, p2[:400])
        check("the new questions are added to the old ones and every block now has at least 2", [q["question_hi"][:7] for q in bl5["beginner"]["cfu"]] == ["21 + 36", "12 + 34"] and len(bl5["proficient"]["cfu"]) == 2 and len(bl5["progressor"]["cfu"]) == 2, {g: len(b.get("cfu") or []) for g, b in bl5.items()})
        check("the stats say which groups were topped up, and how many questions the model wrote in all", pc5["cfu_stats"]["beginner"].get("topped_up") is True and pc5["cfu_stats"]["proficient"].get("topped_up") is True and "topped_up" not in pc5["cfu_stats"]["progressor"] and pc5["cfu_stats"]["beginner"]["written"] == 4, pc5["cfu_stats"])
        fk, log, pc6, bl6, rows6 = await run([plan_with(full)], d0 + timedelta(days=1))
        check("when every block is fine there is NO second call", fk.calls == 1 and rows6 == 1 and not any("topped_up" in s for s in pc6["cfu_stats"].values()), (fk.calls, rows6))
        bad_beg = [{"kind": "compute", "question_hi": "12 + 34 कितना होगा?", "expected_hi": "47", "listen_for": lf(id_beg, "x")}, top_beg[1]]
        fk, log, pc7, bl7, rows7 = await run([plan_with(partial), {"beginner": bad_beg, "proficient": top_prof}], d0 + timedelta(days=2))
        check("the top-up questions go through the SAME checks: a wrong answer in them is dropped (46, not 47) and the right one kept", [q["question_hi"][:7] for q in bl7["beginner"]["cfu"]] == ["21 + 36", "52 में "] and "real result 46" in log, [q["question_hi"][:7] for q in bl7["beginner"]["cfu"]])
        fk, log, pc8, bl8, rows8 = await run([plan_with(partial), '{"beginner" 1'], d0 + timedelta(days=3))
        check("an unreadable top-up reply is survived: the plan is stored, nothing is invented, the call was paid for and metered, and it is NOT asked a third time", fk.calls == 2 and rows8 == 2 and (bl8["proficient"].get("cfu") or []) == [] and "CFU top-up skipped" in log, (fk.calls, rows8))
        real_guard = ai_budget.guard

        async def capped(kind, *a, **k):
            if kind == "plan_repair":
                raise ai_budget.AICapReached("teacher_daily")
            return await real_guard(kind, *a, **k)
        ai_budget.guard = capped
        try:
            fk, log, pc9, bl9, rows9 = await run([plan_with(partial), {"beginner": top_beg}], d0 + timedelta(days=4))
        finally:
            ai_budget.guard = real_guard
        check("when the AI limit is reached the top-up is NOT made, the plan is still generated, and the log says it was skipped", fk.calls == 1 and rows9 == 1 and "CFU top-up skipped" in log, (fk.calls, rows9))
        os.environ["CFU_TOPUP"] = "0"
        fk, log, pc10, bl10, rows10 = await run([plan_with(partial), {"beginner": top_beg}], d0 + timedelta(days=5))
        os.environ["CFU_TOPUP"] = "1"
        check("CFU_TOPUP=0 switches the extra call off: one call, even though blocks are short", fk.calls == 1 and rows10 == 1, (fk.calls, rows10))
        os.environ["CFU_TOPUP"] = "0"

        print("\nthe switch")
        settings.cfu_enabled = False
        try:
            fake3 = FakeMessages(written)
            anthropic.AsyncAnthropic = lambda **kw: SimpleNamespace(messages=fake3)
            with contextlib.redirect_stdout(io.StringIO()):
                await plan_service.generate_dainik_yojana(db, teacher_id, "N2.3.2", "numeracy", TODAY + timedelta(days=2))
            row = await db.fetchrow("SELECT plan_content FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2", teacher_id, TODAY + timedelta(days=2))
            pc3 = json.loads(row["plan_content"]) if isinstance(row["plan_content"], str) else row["plan_content"]
            check("switched off: the prompt has no CFU section", "CHECK FOR UNDERSTANDING" not in fake3.prompts[-1] and "GROUP BEGINNER" not in fake3.prompts[-1])
            check("switched off: nothing the model wrote reaches the plan", not any(k in b for b in pc3["rotation_schedule"]["blocks"] for k in ("cfu", "cfu_grounded", "cfu_note_hi")) and "cfu_stats" not in pc3)
        finally:
            settings.cfu_enabled = True
    finally:
        anthropic.AsyncAnthropic = real_client
        settings.cfu_enabled = True
        await db.execute("DELETE FROM ai_usage WHERE school_id IN (SELECT id FROM schools WHERE school_code = $1)", school)
        await _scratch.remove_class(db, teacher_id, school)
        await db.close()
    if failures:
        print(f"\nFAILED ({len(failures)})")
        sys.exit(1)
    print("\nOK: every CFU question is checked by the code, each group gets its own mistakes, and the switch removes it all")


if __name__ == "__main__":
    asyncio.run(main())
