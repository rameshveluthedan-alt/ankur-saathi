# The re-teach block

When the teacher's last review found mistakes, the next plan starts with a short **re-teach (5 minutes)**, and the group it is for is taught first.

## Where the mistakes come from
`previous_review_feedback` (plan_service.py): the misconceptions detected at the teacher's **most recent review within the last 7 days, in the same subject**.
A Friday review feeds a Monday plan; a numeracy review never produces a literacy re-teach; a review with no mistakes means no re-teach.

## Which group it is for (fixed 20 Oct)
`build_reteach_items` finds, for each mistake, the children who made it at that review and the group each is in **now** (their current level). `choose_reteach_group` (prompts/orchestrate.py) then picks:
1. the group with the **most** of those children;
2. on a tie, the group **furthest behind** (Beginner, then Progressor, then Proficient);
3. if none of the children can be placed in a group (a level changed since), the **Progressors**, because today's skill is theirs.

With several mistakes, `pick_priority_group` adds the children up **by group**: the group with most children overall is taught first.
Before the fix the group was written in as "progressor" for every mistake, so the Progressors were always taught first after any mistake, whoever had made it.

## What the plan says
- The model is told, per mistake, which group the re-teach is FOR and that the group is taught first.
- The **code** (not the model) fills in the re-teach block (`stamp_reteach_block`):
  - `teach_group`, so the screen says **"पुनः शिक्षण: शुरुआती (Re-teach: Beginner)"**;
  - `affected_rolls`: the roll numbers of the children of that group who made the mistake ("👥 जिन बच्चों के लिए: रोल 25, 27"). Roll numbers go to the plan only, never to the AI;
  - `other_groups_hi`: what the other two groups do during the 5 minutes. The model leaves this out for a re-teach block, so nobody was told what two thirds of the class do; the text is copied from the next
    teach block (the other groups start that independent work during the re-teach). Work the model did write is kept.
  An older stored plan without these fields still shows the plain label.
- With no re-teach, the Beginners go first, as before, and the intervention template is used proactively ("preteach").

## In the demo
The nightly reset (`scripts/nightly_reset.py`) seeds progress up to yesterday, and the seeded last day includes carry mistakes made by Progressors. So **the demo teacher's plan always opens with a re-teach for the
Progressors, and the Progressors are taught first**. That is the feature working, not a rename of the Beginner block (which is still taught, later).

## Open design question (for Vaishnavi)
The re-teach talking points repeat the whole next lesson (I Do with sticks, We Do, You Do on the same skill) inside 5 minutes, addressed to the whole group, and then the Progressor block teaches it again.
A re-teach is better as a short, targeted fix of the specific mistake (for example: find the missing carry in a wrong worked example), for the children listed above rather than the whole group.
This needs a change to the prompt, which cannot be tested without the real model, so it waits for her decision.

Tests: `backend/tests/test_reteach_lookback.py` (where the mistakes come from) and `backend/tests/test_reteach_group.py` (which group, and what the plan and the model get).
