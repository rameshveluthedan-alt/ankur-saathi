# The AI budget

The hackathon credits are a fixed pool, and the product has to be usable by evaluators until the end of it. So every call to the AI is
**metered** and **capped**, and when a cap is reached the demo keeps working as far as it honestly can.

## The terms we work within (from the organisers)
- **$500** received on 15 Oct 2026, valid until **20 Nov 2026**; unused credit is lost, and the keys stop working after that date.
- Credits may be used only through **Anthropic's own API** (not AWS Bedrock or Google Vertex), only for building and testing hackathon prototypes,
  and cannot be transferred. Hosting the app on Google Cloud is fine as long as it calls Anthropic's API directly.
- The organisers are told at **80%** of the allocation. We want to know long before that (see `status`).
- If shortlisted after the pilot phase (10 Nov): an extra **$500** for improving the product and preparing the demo by 17 Nov.
- For a real school pilot with children's photos, use your own organisation's account, not these credits.

## What is enforced (code: `backend/app/services/ai_budget.py`)
| Rule | Default | What happens when it is hit |
| --- | --- | --- |
| The reserve | $250 held back until 1 Nov | Development cannot spend into it. From 1 Nov it is released, down to a $10 final margin |
| Global daily cap (all users, India day) | $20 | The kill switch. 10 evaluation days x $20 = $200, inside the $240 evaluation budget |
| School daily cap | $10 | Stops that school only |
| Teacher daily cap | $3 | Stops that teacher only |
| Shared demo account (fixed PIN) | $8 | Higher, because many reviewers use one account |
| `AI_ENABLED=false` | on | Every live call stops (recorded plans are still served) |
| After `AI_CREDIT_EXPIRES` | 20 Nov | No call is made |
| Operator mode (the batch run) | | Skips the daily caps, never the total budget or the reserve |

**Plans:** when a limit stops a plan, a **recorded plan for the same skill** (`db/seeds/sample_plans/<skill>.json`, a real earlier output) goes
through exactly the same checks and repairs as a fresh one, is built for the teacher's own groups, and is labelled "sample plan". A skill with
no recorded plan says why it cannot run and which skills do have samples. **Photos** cannot be faked: the analysis says the limit was reached.

**Metering:** every call records its tokens (per teacher and school). A reply that cannot be read is still counted, because it was paid for.
Money is computed from tokens with the **current prices in the settings**, so correcting a price corrects every past estimate.

## The prices are an assumption until checked
The defaults ($2 per million input tokens, $10 per million output) are the batch script's old estimates, and the "about 12 cents a plan" figure rests on them.
Take the real per-million prices for your model from Anthropic's pricing page, set `AI_PRICE_INPUT_PER_MTOK` and `AI_PRICE_OUTPUT_PER_MTOK`, and
if the organisers can tell you what was actually spent over a period, `scripts/ai_usage.py calibrate --actual-usd X` says how far off the prices are.

## A suggested split of the $500
| | Amount | Notes |
| --- | --- | --- |
| Already spent before the meter | about $3 | an estimate (`AI_SPEND_OFFSET_USD`): adjust it |
| Build and test, now to 31 Oct | up to $247 | includes the 101-skill batch run and the scored photo test |
| Evaluators, 1 to 20 Nov | $240 | the reserve, less the margin |
| Final margin | $10 | never spent |

If the extra $500 is granted: set `AI_ALLOCATION_USD=1000` (and `AI_RESERVE_USD` if a new reserve is wanted) and restart.

## Operator commands
```
python scripts/ai_usage.py status    --env-file backend/.env      # spent, remaining, usable now, today by account, warnings at 50/70/80%
python scripts/ai_usage.py schedule  --env-file backend/.env      # the phases and the daily budget each affords
python scripts/ai_usage.py calibrate --env-file backend/.env --actual-usd 12.40
python scripts/batch_generate.py --save-samples                          # the 101-skill run, saving each clean plan as a recorded sample (it reads backend/.env itself: there is no --env-file option)
```
Run `status` daily, and every time before a demo. After 70%, check `schedule` and lower the caps if the evaluation budget is at risk.

## Tests
`backend/tests/test_ai_budget_rules.py` (arithmetic), `test_ai_budget_flow.py` (every cap, the reserve, the fallback and the API answers on a
scratch school; it only deletes its own rows), and `test_ai_calls_are_metered.py` (fails if any paid call is added without being checked and
metered, or if the old unmetered call becomes reachable).

## Not built
- Plan generation in the background (so a dropped connection during the 60 to 80 seconds does not waste a paid plan).
- An automatic comparison of a cheaper model on photo reading, which should be judged with the scored photo test.
- A limit per network address, and an email or message when 50/70/80% is crossed (today you run `status`).
- Recorded plans for all 101 skills: only six are kept on purpose (N0.1.1, N2.2.1, N2.3.2, L2.3.1, L2.5.1 and L2.7.2): the demo skill for each way of recording a review (photo, observation, reading aloud) and two Hindi plans. `scripts/submission_check.py` compares this list with the folder `db/seeds/sample_plans`.
