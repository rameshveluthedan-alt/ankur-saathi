"""
The 0 to 99 number names, checked against an independent published list (Bharat Discovery, "हिन्दी संख्याएँ", read 18 Oct 2026).
Run: python backend/tests/test_hindi_numbers_reference.py
Every name in the reference must be READ correctly by our parser; our generator must write the same name or a known variant spelling.
"""

import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):          # a pipe on Windows uses a legacy code page that cannot print Hindi
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.services import hindi_numbers as hn

REFERENCE = ("शून्य एक दो तीन चार पाँच छह सात आठ नौ दस ग्यारह बारह तेरह चौदह पन्द्रह सोलह सत्रह अठारह उन्नीस बीस इक्कीस बाईस तेईस चौबीस पच्चीस छब्बीस सत्ताईस अट्ठाईस उनतीस तीस "
             "इकतीस बत्तीस तैंतीस चौंतीस पैंतीस छत्तीस सैंतीस अड़तीस उनतालीस चालीस इकतालीस बयालीस तैंतालीस चौवालीस पैंतालीस छियालीस सैंतालीस अड़तालीस उनचास पचास "
             "इक्यावन बावन तिरेपन चौवन पचपन छप्पन सत्तावन अट्ठावन उनसठ साठ इकसठ बासठ तिरेसठ चौंसठ पैंसठ छियासठ सड़सठ अड़सठ उनहत्तर सत्तर इकहत्तर बहत्तर तिहत्तर चौहत्तर पचहत्तर "
             "छिहत्तर सतहत्तर अठहत्तर उनासी अस्सी इक्यासी बयासी तिरासी चौरासी पचासी छियासी सत्तासी अट्ठासी नवासी नब्बे इक्यानबे बानबे तिरानबे चौरानबे पंचानबे छियानबे सत्तानबे अट्ठानबे निन्यानबे").split()
assert len(REFERENCE) == 100
unread = [(i, w) for i, w in enumerate(REFERENCE) if hn.value_of([w]) != i]
same = [i for i in range(100) if hn._n(hn.name(i)) == hn._n(REFERENCE[i])]
variant = [i for i in range(100) if i not in same]
print(f"reference names our parser reads wrongly: {unread or 'none'}")
print(f"generator writes exactly the reference name for {len(same)} of 100; a variant spelling for {len(variant)}:")
print("   ", "; ".join(f"{i}: ours {hn.name(i)} / reference {REFERENCE[i]}" for i in variant))
assert not unread, "the parser misreads a reference name"


# ── second independent reference: the Hindi cell of NIT Hamirpur (nith.ac.in/library/hindi/hindi_count.php, read 18 Oct 2026) ──
NIT = ("एक दो तीन चार पांच छः सात आठ नौ दस ग्यारह बारह तेरह चौदह पंद्रह सोलह सत्रह अट्ठारह उन्निस बीस इक्कीस बाईस तेईस चौबीस पच्चीस छब्बीस सत्ताईस अट्ठाईस उनतीस तीस "
       "इकतीस बत्तीस तैंतीस चौंतीस पैंतीस छ्त्तीस सैंतीस अड़तीस उनतालीस चालीस इकतालीस बयालीस तैंतालीस चौंतालीस पैंतालीस छियालीस सैंतालीस अड़तालीस उनचास पचास "
       "इक्याबन बावन तिरेपन चौबन पचपन छप्पन सत्तावन अट्ठावन उनसठ साठ इकसठ बासठ तिरसठ चौंसठ पैंसठ छियासठ सड़सठ अड़सठ उनहत्तर सत्तर इकहत्तर बहत्तर तिहत्तर चौहत्तर पचहत्तर "
       "छिहत्तर सतहत्तर अठहत्तर उनासी अस्सी इक्यासी बयासी तिरासी चौरासी पचासी छियासी सतासी अठासी नवासी नब्बे इक्यानबे बानवे तिरानवे चौरानवे पचानवे छियानवे सत्तानवे अट्ठानवे निन्यानवे").split()
assert len(NIT) == 99
NIT_TYPOS = {"छ्त्तीस"}                       # the page itself misspells 36; we deliberately do not accept it
unread_nit = [(i, w) for i, w in enumerate(NIT, start=1) if hn.value_of([w]) != i and w not in NIT_TYPOS]
print(f"NIT Hamirpur words our parser reads wrongly (the page's typo for 36 excluded): {unread_nit or 'none'}")
assert not unread_nit

# ── the bug a spelling variant once caused: a CORRECT problem must never be changed ──
def _sheet(text, ans):
    return {"anchor": {}, "prep_hi": [], "rotation_schedule": {"blocks": []},
            "worksheets": {"proficient": {"problems": [{"number": 1, "problem_hi": text, "answer": str(ans)}], "required_count": 1}}}
for text, ans in (("पांच हज़ार सात = ___", 5007), ("पाँच हज़ार सात = ___", 5007), ("अट्ठारह सौ पाँच = ___", 1805), ("सात हज़ार पांच सौ बीस = ___", 7520),
                  ("इक्याबन लिखिए", 51), ("सतासी लिखिए", 87), ("पचानवे लिखिए", 95), ("उनचास लिखिए", 49)):
    p = _sheet(text, ans)
    assert not hn.repair_place_value(p) and p["worksheets"]["proficient"]["problems"][0]["problem_hi"] == text, f"a correct problem was changed: {text}"
p = _sheet("पांचो हज़ार सात = ___", 5007)                       # an unknown word in front: flagged, never rewritten
assert not hn.repair_place_value(p) and hn.find_number_word_errors(p)
p = _sheet("आठ सौ पाँच = ___", 850)                             # a real mistake in a simple problem IS fixed
assert hn.repair_place_value(p) and hn.phrases(p["worksheets"]["proficient"]["problems"][0]["problem_hi"])[0]["value"] == 850
print("correct problems unchanged, unknown words flagged not rewritten, real mistakes fixed: OK")
