"""
A plan costs about 12 cents and the model's reply is paid for before it is read, so one small slip in the JSON (the commonest: an unescaped double quote inside a Hindi string)
must not lose it. The reply is parsed tolerantly; if it still cannot be read, the model is asked ONCE more, with the AI limit checked and both calls metered.

    python tests/test_model_json.py --env-file .env      (the pipeline part needs the database; the parser part does not)
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
from app.services.model_json import ModelJSONError, parse_model_json, repair_inner_quotes

failures = []
SAMPLE = json.load(open(os.path.join(HERE, "..", "..", "db", "seeds", "sample_plans", "N2.3.2.json"), encoding="utf-8"))


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


def fails(text):
    try:
        parse_model_json(text)
        return False
    except ModelJSONError:
        return True


print("the parser")
d, note = parse_model_json('{"a": [1, {"q": "x"}], "b": null}')
check("a valid reply is returned untouched, with no note", d == {"a": [1, {"q": "x"}], "b": None} and note == "")
d, note = parse_model_json('{"a": "बच्चा "एक" बोलता है", "b": 1}')
check("an unescaped double quote inside a Hindi string is repaired, and kept in the text", d == {"a": 'बच्चा "एक" बोलता है', "b": 1} and "escaped 2" in note, (d, note))
d, _ = parse_model_json('{"a": "बोलें "सही" या "गलत" लिखें", "b": [ "x", "y" ]}')
check("several inner quotes in one string are repaired", d["a"] == 'बोलें "सही" या "गलत" लिखें' and d["b"] == ["x", "y"], d)
d, _ = parse_model_json('{"a": "बोलें "सही", फिर लिखें", "b": 2}')
check("an inner quote followed by a comma and more text is repaired (a comma then a letter cannot be structure)", d == {"a": 'बोलें "सही", फिर लिखें', "b": 2}, d)
d, _ = parse_model_json('{"list": ["एक "दो" तीन", "चार"], "k": {"x": "y"}}')
check("quotes that really are structure (in lists and nested objects) are left alone", d == {"list": ['एक "दो" तीन', "चार"], "k": {"x": "y"}}, d)
d, _ = parse_model_json('{"a": "say \\"hi\\"", "b": 1}')
check("quotes that are already escaped are not escaped twice", d == {"a": 'say "hi"', "b": 1}, d)
d, note = parse_model_json('{"a": "line one\nline two"}')
check("a raw line break inside a string is accepted", d == {"a": "line one\nline two"} and "control" in note, (d, note))
check("what cannot be repaired is reported, with the position and the text around it", fails('{"a" 1, "b": 2}'))
check("a KEY is never 'repaired': a key with no colon stays an error instead of becoming a merged key", fails('{"a": "x", "b" "y"}') and fails('{"a" 1, "b": 2}'))
try:
    parse_model_json('{"alpha": "x", "beta" "y"}')
except ModelJSONError as e:
    check("the error names the problem and quotes the text around it", "Expecting ':' delimiter" in str(e) and '"beta"' in str(e) and "character" in str(e), str(e))
real = json.dumps(copy.deepcopy(SAMPLE), ensure_ascii=False)
needle = SAMPLE["rotation_schedule"]["blocks"][0].get("script_hi") or next(b["script_hi"] for b in SAMPLE["rotation_schedule"]["blocks"] if b.get("script_hi"))
broken_plan = copy.deepcopy(SAMPLE)
for b in broken_plan["rotation_schedule"]["blocks"]:
    if b.get("script_hi"):
        b["script_hi"] = 'बच्चे "एक" से "दस" तक गिनें'
        break
text = json.dumps(broken_plan, ensure_ascii=False).replace('\\"एक\\"', '"एक"').replace('\\"दस\\"', '"दस"')
d, note = parse_model_json(text)
check("a whole real plan with two inner quotes in one line is repaired exactly", d == broken_plan and "escaped 4" in note, note)
fixed, n = repair_inner_quotes(real)
check("a valid plan is not changed by the repair step (no false repairs over about 15,000 characters)", n == 0 and fixed == real)


class Replies:
    """A stand-in model that returns the given texts in turn."""
    def __init__(self, texts):
        self.texts, self.calls, self.prompts = list(texts), 0, []

    async def create(self, **kw):
        self.calls += 1
        self.prompts.append(kw["messages"][0]["content"])
        t = self.texts[min(self.calls - 1, len(self.texts) - 1)]
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=t)], stop_reason="end_turn", usage=SimpleNamespace(input_tokens=6000, output_tokens=9000))


async def main():
    import _scratch
    import anthropic
    from app.services import ai_budget, plan_service
    db = await _scratch.connect()
    levels = {1: "beginner", 2: "beginner", 3: "beginner", 4: "progressor", 5: "progressor", 6: "progressor", 7: "proficient", 8: "proficient"}
    teacher_id, school = await _scratch.make_class(db, {r: (lv, lv) for r, lv in levels.items()}, grade="grade_2")
    real_client, real_check = anthropic.AsyncAnthropic, ai_budget.check
    good = json.dumps(SAMPLE, ensure_ascii=False)
    TODAY = date.today()

    async def usage_rows():
        return await db.fetchval("SELECT count(*) FROM ai_usage WHERE school_id = (SELECT id FROM schools WHERE school_code = $1)", school)

    async def generate(texts, day):
        fake = Replies(texts)
        anthropic.AsyncAnthropic = lambda **kw: SimpleNamespace(messages=fake)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            try:
                await plan_service.generate_dainik_yojana(db, teacher_id, "N2.3.2", "numeracy", day)
                err = None
            except Exception as e:
                err = e
        return fake, err, buf.getvalue()

    try:
        print("\nthe pipeline, with a stand-in model")
        fake, err, log = await generate([good], TODAY)
        check("a valid reply: one call, one metered row, no retry", err is None and fake.calls == 1 and await usage_rows() == 1, (err, fake.calls))

        await db.execute("DELETE FROM ai_usage WHERE school_id = (SELECT id FROM schools WHERE school_code = $1)", school)
        slipped = json.dumps(broken_plan, ensure_ascii=False).replace('\\"एक\\"', '"एक"').replace('\\"दस\\"', '"दस"')
        fake, err, log = await generate([slipped], TODAY + timedelta(days=1))
        row = await db.fetchrow("SELECT plan_content FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2", teacher_id, TODAY + timedelta(days=1))
        text = json.dumps(json.loads(row["plan_content"]) if isinstance(row["plan_content"], str) else row["plan_content"], ensure_ascii=False)
        check("a reply with unescaped quotes is repaired: ONE call, the plan is stored, and the log says what was repaired", err is None and fake.calls == 1 and "Model JSON: escaped 4" in log and "एक" in text, (err, fake.calls, log[-200:]))

        await db.execute("DELETE FROM ai_usage WHERE school_id = (SELECT id FROM schools WHERE school_code = $1)", school)
        fake, err, log = await generate(['{"a" 1, "b": 2', good], TODAY + timedelta(days=2))
        check("a reply that cannot be read is followed by ONE more call, and the plan is generated", err is None and fake.calls == 2 and "Asking the model again" in log, (err, fake.calls))
        check("BOTH paid calls are metered", await usage_rows() == 2, await usage_rows())
        check("the second call carries the same prompt", fake.prompts[0] == fake.prompts[1])

        await db.execute("DELETE FROM ai_usage WHERE school_id = (SELECT id FROM schools WHERE school_code = $1)", school)
        fake, err, log = await generate(['{"a" 1', '{"b" 2'], TODAY + timedelta(days=3))
        check("two unreadable replies in a row: it stops after TWO calls (never a loop), with the error and the text around it", isinstance(err, ModelJSONError) and fake.calls == 2 and "Around it" in str(err), (type(err), fake.calls))
        check("...and both were metered, because both were paid for", await usage_rows() == 2, await usage_rows())

        await db.execute("DELETE FROM ai_usage WHERE school_id = (SELECT id FROM schools WHERE school_code = $1)", school)
        calls_to_check = {"n": 0}

        async def check_once_then_capped(*a, **k):
            calls_to_check["n"] += 1
            if calls_to_check["n"] >= 2:
                raise ai_budget.AICapReached("teacher_daily")
            return await real_check(*a, **k)
        ai_budget.check = check_once_then_capped
        fake, err, log = await generate(['{"a" 1'], TODAY + timedelta(days=4))
        ai_budget.check = real_check
        check("if the AI limit is reached before the second call, it is NOT made, and the message says why", isinstance(err, ValueError) and "could not be asked again" in str(err) and fake.calls == 1, (err, fake.calls))
    finally:
        anthropic.AsyncAnthropic, ai_budget.check = real_client, real_check
        await db.execute("DELETE FROM ai_usage WHERE school_id IN (SELECT id FROM schools WHERE school_code = $1)", school)
        await _scratch.remove_class(db, teacher_id, school)
        await db.close()
    if failures:
        print(f"\nFAILED ({len(failures)})")
        sys.exit(1)
    print("\nOK: a slip in the model's JSON is repaired or asked again once, both calls are metered, and a failure says where")


if __name__ == "__main__":
    asyncio.run(main())
