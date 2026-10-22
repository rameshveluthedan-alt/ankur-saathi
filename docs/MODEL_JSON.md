# When the model's reply is not valid JSON

A plan costs about 12 cents and **the reply is paid for before it is read**. On 22 Oct a real run of N0.2.2 lost a whole plan to one malformed reply (`Expecting ':' delimiter`, character 14,627), with no hint of the cause.

## What happens now (`backend/app/services/model_json.py`, used by `plan_service.py`)
1. The reply is parsed as it is.
2. If that fails: raw line breaks inside text are accepted, and **unescaped double quotes inside a text value are escaped**. The commonest slip in Hindi text is `"बच्चा "एक" बोलता है"`.
   A quote ends a string only if what follows is valid JSON (a colon, a closing bracket, or a comma then the start of a key or value). **A key is never repaired**: a key with no colon stays an error, instead of becoming valid JSON with a merged key.
3. If it still cannot be read, **the model is asked once more**. The AI limit is checked again first, and **both calls are metered** (both were paid for). Never more than two calls.
4. If the second reply also fails, the error says where and what: `the model's reply is not valid JSON (Expecting ':' delimiter at character 14627 of 15210). Around it: '...'`.

Log lines to look for: `Model JSON: escaped N unescaped double quote(s) inside text` (repaired, no extra cost), `Model JSON problem (attempt 1 of 2): ...` then `Asking the model again` (a second paid call).

## Known limit
An inner quote followed by `, "` looks like structure, and two quoted words side by side (`"एक" "दो"`) look like a missing comma: some slips cannot be repaired and fall through to the retry. A repaired reply still goes through every check a plan goes through.

## The prompt
The check-for-understanding rules now say never to use the double quote character inside a text value (use single quotes): the CFU section quotes words more than the rest of the plan.

Tests: `backend/tests/test_model_json.py` (the parser, and the pipeline with a stand-in model: repaired, asked once more, stopped after two, both metered, no second call when the AI limit is reached).
