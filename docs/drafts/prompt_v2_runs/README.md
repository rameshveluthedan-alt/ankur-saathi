# Prompt v2: the real-model test plans (19-20 Nov 2026, lab)

Twelve plans made by the real model (Claude Sonnet 5.5) with the prompt v2 rebuild on branch `lab/prompt-v2`: four skill shapes at the three
session lengths. They were made through the app's own pipeline (`plan_service.generate_dainik_yojana`), so every code check and repair has run
on them, on a scratch class of 30 in the lab database (rolls 1-8 Beginners, 9-20 Progressors, 21-30 Proficients; no names).

| File | Skill | Shape |
|---|---|---|
| `N2.3.2_45/60/90.plan.json` | N2.3.2 addition with carry (Beginners N2.3.1, Proficients N3.3.1) | written maths: 3 + N worksheets |
| `L2.7.2_45/60/90.plan.json` | L2.7.2 writing connected sentences | writing: composition and formation sheets |
| `L2.5.1_45/60/90.plan.json` | L2.5.1 reading aloud | fluency sheets |
| `N0.1.1_45/60/90.plan.json` | N0.1.1 sorting by one attribute | observed: a task to watch |

- `CHECKS_201126.txt`: what each plan was checked for (block minutes, the 3 + N sheet, each group's own mistakes, the You Do range, banned
  Hindi forms, the show-me questions kept, the cost of each call, the cache read) and the result. No plan broke a v2 rule.
- The 45-minute plans follow the team's split (anchor 5, Beginners 16, Progressors 14, Proficients 7, transitions 2 + 1).
- `L2.7.2_45`, `L2.5.1_45` and `N0.1.1_45` were made again on 20 Nov, after an AI-assisted review of the first twelve found real problems:
  a gendered first person inside the teacher's quoted words ('मैं ... छाँटूँगी'), a self-correction in a script ('चुपके से... यानी शांति से'),
  an English word in Devanagari ('ट्रंग ट्विस्टर'), a length other than the block's ('about 25 minutes' in a 13-minute block), and 45-minute
  You Do tasks that could not fit in 5 minutes. The fixes: the prompt rules; code that rewrites the teacher's quoted 'मैं' sentences to the
  'हम' form and flags any left; a short You Do (and a short fluency You Do) only STARTS the task; 0-minute blocks and unknown group keys removed.
- **Nine were made again on 21 Nov with the final code** (after the second AI-assisted review; this file said "all 12" until 22 Nov, but the
  three 45-minute plans of L2.5.1, L2.7.2 and N0.1.1 were still the 20 Nov ones): every session adds up exactly (45 / 60 / 90), no 0-minute
  block, no stray keys, every block has its show-me questions, no gendered 'मैं', no self-correction. The second review also found an 'odd one
  out' item with no single answer (now dropped by code) and photo samples listed for practice-only sheets (now empty).
- **22 Nov, the third AI-assisted review:** (1) an example that is the answer ('जैसे 3, 1, 2' when the answer is 3, 1, 2) is now removed by
  code; (2) आकार (size) vs आकृति (shape) in N0.1.1 ('गोल ... चौकोर ... मेरा नियम है आकार'): a prompt rule and a check that flags it (it is a
  meaning, not a word, so code cannot repair it); (3) 'मैं' with a verb already plural in a quote becomes 'हम'; (4) a group addressed in an
  instruction takes the respectful plural ('समूह ... जाएँ', not 'जाए'). The three stale 45-minute plans were made again with this code ($0.42,
  `CHECKS_221126.txt`); the code-only clean-ups (1), (3), (4) were applied to the other nine stored files, without changing the model's own
  words otherwise. The three plans the checks still flagged (N0.1.1_60, N0.1.1_90: आकार / आकृति; N2.3.2_45: 'पैसे', 'दहाई ऊपर दहाई के
  नीचे') were then made again ($0.44, appended to `CHECKS_221126.txt`): every आकार in them now means size. One flag remains in N0.1.1_60
  (an I Do that shows things differing in colour, size AND shape, then sorts by colour or size): read and found correct, a cautious flag.
- **22 Nov, the fourth AI-assisted review** (found the set ready for the pilot) named three small items, now repaired by code and applied to
  the stored files: a gendered verb in a quote with the subject left out ('इसे यहाँ रखता हूँ' -> 'रखते हैं'); 'finish in the next block' in
  the session's LAST block (-> 'अगली कक्षा में'; also in L2.5.1_45, which the review missed); 'शिक्षक हर कहानी बोलकर सुनाएँगे' on a
  reading-aloud sheet, where the children read one passage themselves (removed; also in L2.5.1_60). No new AI call.
- Open for the education lead (teaching, not code): N0.1.1's three groups on one skill (Proficients sort by a second rule); the board load in
  45-minute plans; 'कठिन शब्द' for Beginners' warm-up words; 'पैसे' for rupee prices; the आकार / आकृति convention.
- `CHECKS_201126.txt` covers the other six; `CHECKS_221126.txt` the six plans made on 22 Nov (L2.5.1_45, L2.7.2_45, N0.1.1_45, then N0.1.1_60, N0.1.1_90, N2.3.2_45).
- Cost of all the runs: about $4.65 (34 plans, twenty-two of them repeats).

**To read them on screen** (lab only, AI off): `C:\dev\ankur-scratch\v2_run\load_for_review.py` loads them into six review accounts
(V245NA ... V290NB, password 4826), dated the day it is run. `tools/make_review_html.py` writes `REVIEW_PLANS_v2.html`, a readable copy of all 12.

These are for review (the team and the education lead). They are not recorded sample plans: nothing in the app reads this folder.
