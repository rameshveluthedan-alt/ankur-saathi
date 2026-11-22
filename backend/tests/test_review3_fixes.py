"""
The third review of the prompt-v2 plans (22 Nov 2026), its five points, each with the reviewer's own sentence:
  1. an example that gives the answer away ('जैसे 3, 1, 2' when the answer is 3, 1, 2): removed by code;
  2. आकार (size) vs आकृति (shape) in the sorting skill: a check for the review (and a prompt rule);
  3. 'मैं ... छाँट रहे हैं' (मैं with a verb already plural) and 'रहा/रही हूँ' becoming 'रहा/रहे हैं': rewritten to 'हम ...';
  4. a group addressed in the singular ('शुरुआती समूह ... जाए') next to the plural ('प्रगतिशील समूह ... आएँ'): the plural throughout;
  5. the rules are in the prompt. No database, no AI.

    python backend/tests/test_review3_fixes.py
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
sys.path[:0] = [os.path.join(ROOT, "backend"), os.path.join(ROOT, "prompts")]
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-dummy-never-used")
import hindi_style as hs
from app.services.plan_service import drop_answer_examples

failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


print("1. an example that is an answer on the sheet")
plan = {"worksheets": {"proficient": {"problems": [
    {"number": 3, "problem_hi": "इन वाक्यों को सही क्रम में लिखिए (संख्याएँ लिखें, जैसे 3, 1, 2): 1) 'फिर हमने दीप जलाए।'", "answer": "3, 1, 2"},
    {"number": 4, "problem_hi": "क्रम की संख्याएँ लिखिए, जैसे 2, 3, 1।", "answer": "2, 3, 1"},
    {"number": 5, "problem_hi": "क्रम की संख्याएँ लिखिए, जैसे 1, 2, 3।", "answer": "3, 2, 1"},
    {"number": 6, "problem_hi": "एक बच्चा कोई अंक बोले, जैसे 6, 3, 8, 1, 9।", "answer": "मौखिक"}]}}}
lines = drop_answer_examples(plan)
p = plan["worksheets"]["proficient"]["problems"]
check("the reviewer's L2.7.2_90 item 3: the example goes, the instruction stays", p[0]["problem_hi"] == "इन वाक्यों को सही क्रम में लिखिए (संख्याएँ लिखें): 1) 'फिर हमने दीप जलाए।'", p[0]["problem_hi"])
check("the reviewer's item 4 (Progressors): 'क्रम की संख्याएँ लिखिए।'", p[1]["problem_hi"] == "क्रम की संख्याएँ लिखिए।", p[1]["problem_hi"])
check("an example that is no answer on the sheet is kept (it shows the format)", p[2]["problem_hi"] == "क्रम की संख्याएँ लिखिए, जैसे 1, 2, 3।")
check("a list of numbers that is not an answer is kept", p[3]["problem_hi"].endswith("जैसे 6, 3, 8, 1, 9।"))
check("two repairs reported, and again nothing (idempotent)", len(lines) == 2 and drop_answer_examples(plan) == [], lines)

print("\n2. आकार (size) and आकृति (shape) in the sorting skill")
def blk(**kw):
    return {"rotation_schedule": {"blocks": [kw]}}
i_do_60 = "याद दिलाएँ। फिर 8 चीज़ें लेकर आकार के नियम से छाँटें: 'देखिए, गोल एक तरफ़, चौकोर दूसरी तरफ़।' बोलें: 'मेरा नियम है आकार।'"
cfu_60 = {"question_hi": "बोर्ड पर एक बड़ा तारा, एक छोटा तारा और एक बड़ा गोला बनाएँ। पूछें: 'आकार के नियम से कौन-से दो साथ रहेंगे?'", "expected_hi": "एक उँगली",
          "shows_hi": "बच्चा आकृति के नियम से जोड़ी पहचानता है"}
i_do_90 = "कहें: 'देखिए, हम इन्हें आकार से छाँटते हैं। सारी गोल चीज़ें एक ओर, बाकी दूसरी ओर।'"
cfu_45_ok = {"question_hi": "2 बड़े और 2 छोटे गोले बनाएँ। पूछें: 'इन्हें किस नियम से छाँटा जा सकता है: 1) आकार 2) रंग?'", "expected_hi": "1 (आकार)"}
lib = {"question_hi": "बोर्ड पर बनाएँ: बड़ा गोला, छोटा गोला, बड़ा तिकोना, छोटा तिकोना। 'गोले वाले ढेर में कितनी चीज़ें जाएँगी?'", "expected_hi": "2",
       "shows_hi": "बच्चा आकार के नियम से छाँटता है और बड़े-छोटे को अनदेखा करता है।"}
check("N0.1.1_60 I Do ('गोल ... चौकोर ... मेरा नियम है आकार') is flagged", len(hs.check_size_shape(blk(talking_points={"i_do_hi": i_do_60}), ["N0.1.1"])) == 1)
check("N0.1.1_60 show-me question (big star, small star, big circle 'by आकार') is flagged", len(hs.check_size_shape(blk(cfu=[cfu_60]), ["N0.1.1"])) == 1)
check("N0.1.1_90 I Do ('आकार से ... सारी गोल चीज़ें', which the review missed) is flagged", len(hs.check_size_shape(blk(talking_points={"i_do_hi": i_do_90}), ["N0.1.1"])) == 1)
check("the library piece (circles and triangles, 'आकार के नियम') is flagged", len(hs.check_size_shape(blk(cfu=[lib]), ["N0.1.1"])) == 1)
check("a correct use (big and small circles, the size rule) is NOT flagged", hs.check_size_shape(blk(cfu=[cfu_45_ok]), ["N0.1.1"]) == [])
check("a list naming all three ('रंग, आकार या आकृति') is NOT flagged",
      hs.check_size_shape(blk(talking_points={"we_do_hi": "रंग, आकार या आकृति: गोल और चौकोर चीज़ें दिखाएँ"}), ["N0.1.1"]) == [])
check("geometry ('किस आकार का है: गोला या घन', ordinary Hindi) is not checked",
      hs.check_size_shape(blk(talking_points={"i_do_hi": "पूछें: 'गेंद किस आकार की है: गोला या घन?'"}), ["N0.5.1"]) == [])

print("\n3. 'मैं' with a plural verb, and the paired form")
check("the reviewer's N0.1.1_60 line: 'मैं रंग देखकर छाँट रहे हैं' -> 'हम ...'",
      hs.neutral_quotes("उठाकर कहें, 'देखिए, मैं रंग देखकर छाँट रहे हैं।' लाल एक तरफ़") == ("उठाकर कहें, 'देखिए, हम रंग देखकर छाँट रहे हैं।' लाल एक तरफ़", 1))
check("'मैं छाँट रहा/रही हूँ' -> 'हम छाँट रहे हैं' (was 'रहा/रहे हैं')",
      hs.neutral_quotes("कहें, 'देखिए, मैं रंग देखकर छाँट रहा/रही हूँ।' लाल")[0] == "कहें, 'देखिए, हम रंग देखकर छाँट रहे हैं।' लाल")
check("'मैं दिखाऊँगा/दिखाऊँगी' -> 'हम दिखाएँगे'", hs.neutral_quotes("कहें, 'अब मैं दिखाऊँगा/दिखाऊँगी।'")[0] == "कहें, 'अब हम दिखाएँगे।'")
check("a sentence written for the children keeps its 'मैं'", hs.neutral_quotes("बोर्ड पर लिखें: 'मैं स्कूल जाते हैं।'")[1] == 0)
check("a 'मैं' sentence with no plural verb is left ('मैं पूछूँ?')", hs.neutral_quotes("कहें, 'मैं पूछूँ? बच्चे खेल रहे हैं।'")[0] == "कहें, 'मैं पूछूँ? बच्चे खेल रहे हैं।'")
check("idempotent", hs.neutral_quotes("कहें, 'देखिए, हम रंग देखकर छाँट रहे हैं।'")[1] == 0)

print("\n4. a group addressed in the respectful plural")
script = "यहीं रोक दें और कॉपी बंद करें। शुरुआती समूह अपनी जगह पर वर्कशीट लेकर जाए। प्रगतिशील समूह मेरे पास आएँ। शांति से और बिना शोर किए।"
new, n = hs.polite_group_verbs(script)
check("the reviewer's N0.1.1_45 transition: 'जाए' -> 'जाएँ', 'आएँ' unchanged", n == 1 and "वर्कशीट लेकर जाएँ।" in new and "मेरे पास आएँ।" in new, new)
new, n = hs.polite_group_verbs("प्रगतिशील समूह जोड़ी में अपने ढेर को रंग के नियम से छाँटे और अपना नियम साथी को बताए।")
check("two verbs in one clause: 'छाँटें और ... बताएँ'", n == 2 and new == "प्रगतिशील समूह जोड़ी में अपने ढेर को रंग के नियम से छाँटें और अपना नियम साथी को बताएँ।", new)
check("a story's 'बादल आए' (no समूह) is untouched", hs.polite_group_verbs("एक दिन आसमान में काले बादल आए। फ़सल बच जाएगी।")[1] == 0)
check("'जाएगी' and 'समूह के बच्चे' are untouched", hs.polite_group_verbs("शुरुआती समूह के बच्चे। वर्कशीट दी जाएगी।")[1] == 0)
check("text in quotes after समूह is not reached", hs.polite_group_verbs("दक्ष समूह से कहें: 'बादल आए।'")[1] == 0)
# found by the library re-check: the group is an object, or another subject governs the verb
for s in ("हर बच्चा अपनी कॉपी में लिखी जोड़ियाँ एक बार पढ़कर समूह को सुनाए।",
          "हर बच्चा अपने समूह से एक अंक-कार्ड चुने और वही अंक अपनी स्लेट पर लिखे, फिर उतने ही छोटे गोले बनाए।",
          "जो समूह जल्दी ख़त्म करे, वह कार्ड उल्टा रखकर एक-दूसरे से पूछे।",
          "हर समूह अपनी सबसे अच्छी खोज सबको बताए।",
          "समूह मिलकर पंक्ति पढ़ें और हर बच्चा अपनी स्लेट पर लिखे।"):
    check(f"left alone: {s[:45]}…", hs.polite_group_verbs(s)[1] == 0, hs.polite_group_verbs(s)[0])
check("'बाकी सवाल समूह अगले ब्लॉक में अपनी जगह पर पूरे करे' -> 'करें'",
      hs.polite_group_verbs("बाकी सवाल समूह अगले ब्लॉक में अपनी जगह पर पूरे करे।")[0] == "बाकी सवाल समूह अगले ब्लॉक में अपनी जगह पर पूरे करें।")
check("idempotent", hs.polite_group_verbs(hs.polite_group_verbs(script)[0])[1] == 0)
plan = {"rotation_schedule": {"blocks": [{"type": "transition", "script_hi": script}]}}
hs.soften_plan(plan)
check("soften_plan applies it to a transition script", "लेकर जाएँ।" in plan["rotation_schedule"]["blocks"][0]["script_hi"])
src = open(os.path.join(ROOT, "backend", "app", "services", "library_assembler.py"), encoding="utf-8").read()
check("the library assembler's own transition says 'आएँ'", "शिक्षक के पास आएँ;" in src and "शिक्षक के पास आए;" not in src)

print("\n5. the rules are in the prompt")
import orchestrate
sec = orchestrate.HINDI_STYLE_SECTION
check("the example rule", "never be an answer on the sheet" in sec)
check("the आकार / आकृति rule", "आकार means SIZE" in sec and "आकृति means SHAPE" in sec)
check("the group plural rule", "'शुरुआती समूह अपनी जगह जाएँ'" in sec)

print("\nthe current test plans: what the new code finds")
runs = os.path.join(ROOT, "docs", "drafts", "prompt_v2_runs")
# N0.1.1_60 and _90 were made again on 22 Nov after these checks: _90 has no flag; _60 keeps one cautious flag (an I Do showing things that
# differ in colour, size AND shape, then sorting by colour or size: read, and correct), so only _90 is asserted here
for name, skills in (("L2.7.2_90", None), ("N0.1.1_90", [])):
    path = os.path.join(runs, f"{name}.plan.json")
    if not os.path.isfile(path):
        continue
    d = json.load(open(path, encoding="utf-8"))
    d = d.get("plan", d)
    if skills is None:      # the stored plan had the code's clean-ups applied on 22 Nov: no give-away example is left
        check(f"{name}: no example gives an answer away", drop_answer_examples(d) == [] and "जैसे 3, 1, 2" not in json.dumps(d, ensure_ascii=False))
    else:
        check(f"{name} (made again): no size/shape flag", hs.check_size_shape(d, ["N0.1.1"]) == [], hs.check_size_shape(d, ["N0.1.1"]))

if failures:
    print(f"\nFAILED ({len(failures)})")
    sys.exit(1)
print("\nOK: the third review's five points are handled in code and in the prompt")
