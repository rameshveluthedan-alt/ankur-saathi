# Which children to photograph: systematic sampling

A large group does not have to be photographed in full every day. The app suggests a sample, chosen by code, not by the AI.

## The method

1. Sort the group's roll numbers.
2. Interval k = group size / sample size (14 children, sample of 6: k = 2.33).
3. Pick a start point between 0 and k, then take every k-th child after it, so the picks are spread evenly across the roll list.
4. The start point moves a little each day (in golden-ratio steps), so the sample changes from day to day and every child gets a turn.
5. The same group on the same day always gets the same sample, so the plan, the Review screen and the teacher's records agree. The three groups of one class start at different points.

Code: `backend/app/services/sampling.py`. Tests: see `/tmp` in the build log, or rerun the checks in that file's docstring.

## Defaults

- A group of **8 or fewer** is photographed in full.
- A larger group: **40% of the group, never fewer than 6** (14 children: 6; 20: 8; 30: 12). The teacher can switch to "Everyone".
- An **absent** sampled child is replaced by the nearest child on the roll list who is not already in the sample, which keeps the spread.

## What was measured (simulation on the method itself)

- Every child has been in the sample within **about 3 days**, and over 120 days each child was picked within one or two times of a perfectly fair share.
- The biggest gap between two neighbouring picks is about 1.2 times the interval.
- A child reaches **three analyses after about 6 to 7 school days** (worst 8), against 3 days when everyone is photographed.

## What a sample can and cannot tell you

- It gives a **rough picture of the group**. With the default sizes the group's average accuracy could be off by about **19 points for 6 of 14, 17 for 8 of 20, 13 for 12 of 30** (95%, assuming children's accuracies spread about 0.30; this is an assumption, not a measurement). That is enough to decide to re-teach or move on when the picture is clear (for example 35% against 85%), and not when it is close to the line.
- It does **not** give every child's level, and it does not need to: levels change only through an assessment (`docs/LEVELS.md`), never from daily results. Sampling only affects how quickly a "consider re-assessing" flag can appear: a child reaches 3 analyses after about 6 to 7 school days, against 3 when everyone is photographed.
- Choose "Everyone" for the first days of a new skill, or when you want to see every child's work.

## Not built

- Priority picks: always including children who have no recent daily evidence, or whose last flag is still open. They would make the flags appear sooner, at the cost of a sample that is no longer purely systematic.
