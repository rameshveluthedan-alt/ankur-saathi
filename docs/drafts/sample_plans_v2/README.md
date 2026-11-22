# Recorded plans, prompt v2: drafts for the education lead (22 Nov 2026)

New versions of the six recorded plans (`db/seeds/sample_plans`: N2.3.2, N2.2.1, N0.1.1, L2.7.2, L2.5.1, L2.3.1), made with prompt v2 at 90
minutes (Sonnet 5.5, $0.79 for the six) through the app's own pipeline and checks. **The six in use were read and signed by Vaishnavi**
(26 Oct to 15 Nov), so they stay in use; a draft replaces one only after she has read and signed it.

A recorded plan is the LAST fallback: when the AI is off, the block library builds the plan first, and a recorded plan is used only when the
library cannot (a missing or damaged piece). The nightly demo reset also uses N2.3.2 as the demo class's "yesterday".

    python scripts/review_sample_plans.py --dir docs/drafts/sample_plans_v2 list                         which drafts are read and signed
    python scripts/review_sample_plans.py --dir docs/drafts/sample_plans_v2 sheet                        a page per unsigned draft (docs/batch/review/<skill>.html)
    python scripts/review_sample_plans.py --dir docs/drafts/sample_plans_v2 sign N2.3.2 --by "Vaishnavi"
    python scripts/review_sample_plans.py --dir docs/drafts/sample_plans_v2 promote N2.3.2              the signed draft becomes the recorded plan

`promote` refuses a draft nobody has signed. The checks' warnings are inside each file (`_recorded_warnings`) and at the top of its page:
N2.2.1 (sticks not in the preparation list; a Proficient problem repeats a number of the lesson), L2.7.2 and L2.3.1 (an independent-practice
passage not named in what the other groups do), N0.1.1 (a show-me question names आकार beside shapes: read, and it is right: big circle, small
circle, big square, sorted by size, expected 2). N2.3.2 and L2.5.1 have none, but every plan must still be read.

**Corrected before review (22 Nov, after an AI-assisted read of the drafts),** each listed in the file (`_edits_before_review`) and at the top
of its page: two self-corrections the model left in the text (N2.3.2's anchor, N2.2.1's We Do); N2.2.1's Proficient problem 1 used the
lesson's own number (3,452 -> 4,573, its words from the app's number-word code) and the sticks were missing from its preparation list;
L2.7.2's no-space example had an extra 'से' and its preparation list contradicted itself; L2.3.1 'प्रतिक्षा' -> 'प्रतीक्षा'; N0.1.1 an
activity length that did not match its block. Left for the reader: the independent-practice passages on the preparation lists of L2.7.2 and
L2.3.1 that no group is sent to, and 'पैसे' for rupee prices in N2.3.2. N2.3.2 is a normal teaching plan ON PURPOSE: the demo uses it as
the demo class's yesterday, and today's re-teach is what the app suggests from that day's worksheets.
