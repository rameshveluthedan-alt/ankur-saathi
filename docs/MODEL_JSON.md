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


## One closing bracket too many (24 Oct)
**Found on the first Generate in the cloud:** it took **131 seconds** instead of about 65. The log showed TWO full plan calls: the first reply (11,610 tokens) was thrown away and the model was asked again (10,806 tokens). The server log line was `Model JSON problem (attempt 1 of 2): the model's reply is not valid JSON (Expecting ',' delimiter at character 4855 of 19134). Around it: '...,"shows_hi":""}]}},{"type":"transition",...'`: a teach block's closing brace written TWICE (`}]}}` where `}]}` is right: item, show-me list, block). The plan itself was complete and fine. Every Generate that needs the second call costs the same time and money again (about 60 seconds and 14 cents).
**Now** `parse_model_json` tries, after the older repairs, `repair_stray_closers`: when json.loads FIRST fails with `Expecting ',' delimiter` AT a `}` or `]`, that one character is removed and the text is read again (at most `STRAY_CLOSER_LIMIT` = 8 times). The server log then says `Model JSON: removed 1 stray closing bracket(s)` instead of `Model JSON problem`.
**What it does NOT do, on purpose.** The first version also removed a leftover closer at the very END of the text ("Extra data"). The property test (a stray bracket put at every closing bracket, every comma: 1,007 variants of a real-size plan) found one case where that gave a reply that PARSED but was a DIFFERENT plan: the stray `}` had closed `classroom_management` too early, and removing the last `}` left `independent_activities_hi` moved up one level. A leftover bracket at the end looks the same whether it is harmless or the sign of an early one, so that case is refused (the model is asked again, as before). Also refused: a missing comma, a missing bracket, a text that is cut off, a trailing comma, more than 8 strays.
**Measured on the real-size plan:** of 87 duplicated closing brackets, 69 are repaired to EXACTLY the original and 18 are refused; of 920 strays dropped before every comma and closer, 529 are repaired exactly and 391 refused; **none** turned into a different plan.
Tests: `backend/tests/test_model_json_closers.py` (26 checks).
**To watch in the logs:** `Model JSON problem (attempt 1 of 2)` = a plan that took two calls; `Model JSON: removed N stray closing bracket(s)` = a plan saved by this repair. If the first appears often, look at its 'Around it' text: it is the cause.
