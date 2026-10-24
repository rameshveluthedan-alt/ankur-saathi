"""
One closing bracket too many must not cost a second paid call.
Found on the first Generate in the cloud (24 Oct): the model wrote `..."shows_hi":""}]}},{"type":"transition"...` (a teach block closed twice). json.loads failed with "Expecting ',' delimiter" at the stray }, the code threw
away a complete 11,610-token plan, asked again (a second full call: another 60 seconds and 14 cents), and the teacher waited 131 seconds instead of 65.

    cd backend && python tests/test_model_json_closers.py        (no database, no network)
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..")]
from app.services.model_json import parse_model_json, repair_stray_closers, ModelJSONError, STRAY_CLOSER_LIMIT

failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


def compact(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))          # the way the model writes it: no spaces, Hindi as it is


def closers_outside_strings(text):
    out, in_str, esc = [], False, False
    for i, ch in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch in "}]":
            out.append(i)
    return out


def raises(text):
    try:
        parse_model_json(text)
        return False
    except ModelJSONError:
        return True


print("the failure from the log")
GOOD = '{"rotation_schedule":{"blocks":[{"type":"teach","cfu":[{"listen_for":[{"misconception_id":"N2.3.2-M1","wrong_answer_hi":"53"}],"shows_hi":""}]},{"type":"transition","time_start":"0:41","duration_minutes":2}]}}'
BAD = GOOD.replace('"shows_hi":""}]},{"type"', '"shows_hi":""}]}},{"type"')
try:
    json.loads(BAD)
    check("the rebuilt text really fails as plain JSON", False)
except json.JSONDecodeError as e:
    check("the rebuilt text really fails exactly as in the log: Expecting ',' delimiter, AT a } (so the test is of the real failure)", e.msg.startswith("Expecting ',' delimiter") and BAD[e.pos] == "}")
data, note = parse_model_json(BAD)
check("it is read, and it is EXACTLY the plan the model meant (nothing lost, nothing moved)", data == json.loads(GOOD), data)
check("the note says what was done (it is printed in the server log: 'Model JSON: ...')", note == "removed 1 stray closing bracket(s)", note)
check("a valid reply is returned as it came, with no note", parse_model_json(GOOD) == (json.loads(GOOD), ""))

PLAN_FILE = os.path.join(HERE, "..", "..", "db", "seeds", "sample_plans", "N2.3.2.json")
text = GOOD                                    # what the checks below use if the recorded plan is not in this folder
if not os.path.exists(PLAN_FILE):
    print("\n  SKIPPED the real-size checks: db/seeds/sample_plans/N2.3.2.json is not in this folder (they run in the project)")
else:
    print("\na real-size plan (the recorded N2.3.2 plan with a show-me list in every teach block)")
    plan = json.load(open(os.path.join(HERE, "..", "..", "db", "seeds", "sample_plans", "N2.3.2.json"), encoding="utf-8"))
    for b in plan["rotation_schedule"]["blocks"]:
        if b.get("type") == "teach":
            b["cfu"] = [{"kind": "compute", "question_hi": "बोर्ड पर देखें: 56 + 28।", "expected_hi": "84", "listen_for": [{"misconception_id": "N2.3.2-M1", "wrong_answer_hi": "74"}], "shows_hi": ""},
                        {"kind": "spot_error", "question_hi": "49 + 35 = 74। सही या गलत?", "expected_hi": "गलत, 84", "listen_for": [{"misconception_id": "N2.3.2-M1", "wrong_answer_hi": "सही है, 74"}], "shows_hi": ""}]
    text = compact(plan)
    check(f"the plan is a real size ({len(text)} characters, {len(closers_outside_strings(text))} closing brackets)", len(text) > 15000)
    marker = '"shows_hi":""}]}'
    at = text.index(marker) + len(marker)
    broken = text[:at] + "}" + text[at:]
    data, note = parse_model_json(broken)
    check("the failure of the log, in the real plan: one extra } after the first show-me list: the plan comes back identical", data == plan and note == "removed 1 stray closing bracket(s)", note)
    check("an extra } at the very END of the reply ('Extra data') is NOT repaired on purpose: it looks the same as an early stray } that moved a key (found by the property test below); the model is asked again", raises(text + "}"))
    data, note = parse_model_json(text.replace('"shows_hi":""}]}', '"shows_hi":""}]]}', 1))
    check("an extra ] is removed the same way", data == plan and note == "removed 1 stray closing bracket(s)", note)
    two = text.replace('"shows_hi":""}]}', '"shows_hi":""}]}}', 2)
    data, note = parse_model_json(two)
    check("TWO stray brackets in different blocks (two show-me lists closed twice): both removed", data == plan and note == "removed 2 stray closing bracket(s)", note)
    data, note = parse_model_json(text[:at] + "}}}" + text[at:])
    check("three in a row: removed (the limit is a handful: " + str(STRAY_CLOSER_LIMIT) + ")", data == plan and note == "removed 3 stray closing bracket(s)", note)

    print("\nthe safety property: a stray closing bracket NEVER turns into a different plan")
    spots = closers_outside_strings(text)
    repaired = refused = different = 0
    bad_cases = []
    for i in spots:
        variant = text[:i + 1] + text[i] + text[i + 1:]
        try:
            data, _ = parse_model_json(variant)
        except ModelJSONError:
            refused += 1
            continue
        if data == plan:
            repaired += 1
        else:
            different += 1
            bad_cases.append(i)
    check(f"a duplicate of each of the {len(spots)} closing brackets, one at a time: {repaired} repaired to exactly the original, {refused} refused (the caller asks again), {different} turned into a DIFFERENT plan", different == 0, bad_cases[:5])
    check("and most of them ARE repaired (the repair is useful, not only careful)", repaired >= len(spots) * 0.5, (repaired, len(spots)))
    print(f"      (for the record: {repaired} repaired, {refused} refused)")
    # the same, for a stray } or ] put in EVERY other place a model could drop one: before each comma and before each closer, outside strings
    def commas_outside_strings(t):
        out, in_str, esc = [], False, False
        for i, ch in enumerate(t):
            if in_str:
                esc = (not esc) if ch == "\\" else False
                if ch == '"' and not esc:
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch == ",":
                out.append(i)
        return out
    places = sorted(set(commas_outside_strings(text) + spots))
    total = rep2 = ref2 = diff2 = 0
    bad2 = []
    for i in places:
        for stray in "}]":
            variant = text[:i] + stray + text[i:]
            total += 1
            try:
                data, _ = parse_model_json(variant)
            except ModelJSONError:
                ref2 += 1
                continue
            if data == plan:
                rep2 += 1
            else:
                diff2 += 1
                bad2.append((i, stray))
    check(f"a stray }} or ] dropped in front of each of {len(places)} commas and closing brackets ({total} variants): {rep2} repaired exactly, {ref2} refused, {diff2} turned into a DIFFERENT plan", diff2 == 0, bad2[:5])


print("\nwhat is NOT touched")
check("a missing comma is not guessed at", raises('{"a":1 "b":2}') and raises('[{"a":1}{"b":2}]'))
check("a text that is cut off (a missing closing bracket) is not completed", raises(text[:len(text) // 2]) and raises(text[:-1]))
check("a trailing comma is not 'repaired' by removing a bracket", raises('{"a":[1,2,]}') and raises('{"a":1,}'))
check("a stray bracket AND a missing comma: the missing comma stops it, nothing is returned half-repaired", raises('{"a":1 "b":[2]]}'))
inside_a_list = lambda k: '{"a":[{"b":1}' + "}" * k + ']}'
check(f"up to {STRAY_CLOSER_LIMIT} stray brackets in a row (inside a list) are removed; more than that is refused (it should not guess at a reply that broken)", not raises(inside_a_list(STRAY_CLOSER_LIMIT)) and raises(inside_a_list(STRAY_CLOSER_LIMIT + 2)))
check("...and what is returned for the allowed number is the right plan", parse_model_json(inside_a_list(STRAY_CLOSER_LIMIT))[0] == {"a": [{"b": 1}]})
try:
    parse_model_json('{"a":1 "b":2}')
except ModelJSONError as e:
    check("the message is the one the log shows: what, where and the text around it", "not valid JSON" in str(e) and "Around it" in str(e), str(e)[:140])
check("repair_stray_closers on its own: valid text comes back as it is, with 0", repair_stray_closers(GOOD) == (GOOD, 0))
check("...and text whose first error is not a bracket comes back as it is, with 0", repair_stray_closers('{"a":1 "b":2}') == ('{"a":1 "b":2}', 0))

print("\nthe older repairs still work, alone and together with this one")
data, note = parse_model_json('{"a":"बच्चा "एक" बोलता है","b":[1]}')
check("an unescaped double quote inside Hindi text: still escaped", data["a"] == 'बच्चा "एक" बोलता है' and "escaped 2" in note, note)
data, note = parse_model_json('{"a":"बच्चा "एक" बोलता है","b":[{"c":1}}]}')
check("a quote problem AND a stray bracket (inside a list) in the same reply: both repaired, and the note says both", data == {"a": 'बच्चा "एक" बोलता है', "b": [{"c": 1}]} and "removed 1 stray closing bracket(s)" in note and "escaped 2" in note, (data, note))
check("...but a quote problem and a bracket left over at the very END: the bracket is not guessed at, the reply is refused", raises('{"a":"बच्चा "एक" बोलता है","b":[1]}}'))
data, note = parse_model_json('{"a":"x\ny"}')
check("a raw line break inside a string: still accepted", data == {"a": "x\ny"} and "control characters" in note, note)

if failures:
    print(f"\nFAILED ({len(failures)})")
    sys.exit(1)
print("\nOK: one closing bracket too many is removed (and only that), the plan comes back exactly as the model meant it, and no repair ever turns a reply into a different plan")
