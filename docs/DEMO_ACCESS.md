# How reviewers sign in to the demo

The demo holds **fictional data only**, so its passwords are published. Everyone signs in with a **6-character employee code** (three letters and three digits, such as MPT101) and a password. Open the app: the login screen shows a card for each role; tap one to fill in the code and the password, then press Login. **Nobody registers themselves**: accounts are made by the school leader (today, by the operator: see the end of this page).

| Code | Password | What it is |
| --- | --- | --- |
| MPT101 | 4826 | **Demo teacher**: a 30-child multi-grade class (Grades 1 to 3), fictional names, a few days of data |
| MPA101 | 7351 | **School leader** (the head teacher: she teaches too). Looks after the demo school's accounts (the demo teacher, the practice account and the five test teachers): lists them by employee code, unlocks them, resets the practice account's password. Never sees a child's data |
| MPT199 | 3917 | **Practice account**: change its password, reset it as the school leader, lock it out. Nothing else is affected |
| MPT102 to MPT106 | 4826 | **Test teachers** (the role is plain *teacher*: no leader screens), in the same school, each with their own multi-grade class (class numbers 101-110, 201-208, 301-306). Use one each, so you do not overwrite each other's photos or registers |

## Suggested path
0. **What the school leader can do today:** list the school's accounts (each by its employee code, with no child data); reset a teacher's password to a temporary one (shown once); unlock a locked account; and confirm, once, the school's consent statement (a demonstration school carries its own, so you will not be asked). **There is no join code and no registration screen.** Adding teachers from the leader's own screen, one by one or from a CSV file, and reports for the leader and for block and cluster officers, are the next step (`docs/ROADMAP.md`); today the operator makes accounts.
1. **Teacher:** sign in as MPT101 or one of the test teachers. Look at Plan, Progress (the "consider re-assessing" flags, the child list with names) and Review (the observation checklist, the suggested sample).
2. **Password reset:** sign in as the school leader (MPA101), open Profile (the last tab), reset the practice account's password. A temporary password appears once. Sign out, sign in as MPT199 with it: the only screen is "choose a new password" (6 to 12 letters or digits).
3. **A real school's first sign-in:** the school leader sees one screen, once, asking her to confirm a short statement (that the children's parents have been told and have given permission, that photos are not kept and names never go to the AI). It is kept with the date and the exact wording. The demo school carries its own statement ("every child here is fictional"), so you will not see this screen with the demo accounts.

## If the AI limit is reached
The demo's AI use is capped so the credits last through evaluation (`docs/AI_BUDGET.md`). When a limit is reached, a plan for a skill with a
recorded sample is still shown, labelled "sample plan" (the recorded sample plans are N0.1.1, N2.2.1, N2.3.2, L2.3.1, L2.5.1 and L2.7.2); other skills and photo analysis say the limit was reached
and that it resets the next day.

## Why some accounts cannot change their password
The shared demo accounts have a fixed password on purpose: if one reviewer changed it, everyone else would be locked out. The practice account (MPT199) exists so the change and reset flows can still be tried. A new password is 6 to 12 letters or digits (a 6-digit number is fine); the shared demo accounts keep their short published ones.

## For the operator
```
python scripts/migrate_to_employee_codes.py --env-file backend/.env                  # renames accounts made with phone numbers to employee codes and keeps their data; the nightly job runs it first
python scripts/create_test_teachers.py create --count 5 --env-file backend/.env     # the test teachers MPT102 to MPT106, in the demo school
python scripts/auth_admin.py demo-setup       --env-file backend/.env                # passwords and flags; prints this table
python scripts/demo_progress.py seed --end-date YESTERDAY --env-file backend/.env
python scripts/ai_usage.py status --env-file backend/.env                            # before every demo: how much AI budget is left
```
Nightly: `auth_admin.py restore-practice` (puts the practice account right), and re-seed the demo data (flags expire after 14 days). Accounts are made by employee code; `SELF_REGISTRATION` is off unless someone turns it on for a practice database.
If you change a demo password, change it in `pwa/src/screens/LoginScreen.jsx` too: `pwa/tests/demo_accounts.test.mjs` checks that the screen, these guides and the scripts agree. For a real school set `VITE_DEMO_HINT=false`.


## What the Plan screen shows on the demo (seeded every night)
The nightly reset (01:30 IST) records three days of Progressor worksheets for N2.3.2 **and stores yesterday's plan** for the demo teacher (the three groups with their children and skills, and the decisions "recorded" at that review). So when you open **योजना** and choose **N2.3.2**, the panel *"आज हर समूह का कौशल"* shows:
- **Beginners:** yesterday N2.3.1, decision **▲ आगे बढ़ें**: N2.3.2 is suggested ("पिछली समीक्षा में आपके निर्णय से").
- **Progressors:** yesterday N2.3.2, **no decision recorded**: on the last day **6 of the 14 children made a mistake** (rolls 16, 19, 24, 25, 26, 27: the dropped carry four times, the whole ones sum twice) and a third (5) is the threshold, so a **🔄 re-teach is recommended** ("पिछली जाँच के सुझाव से"), with the children's roll numbers and the mistakes named. The box is ticked. Generate the plan: the Progressors' block is the re-teach, with the pace line and the quiet-visit tips, and the top right of the plan lists the groups' skills with "🔄 पुनः शिक्षण".
- **Proficients:** no decision and no evidence: their skill follows the one chosen.
The seeded plan is replaced every night, so the demo tells the same story each day. A plan you generate today becomes "yesterday" at midnight, but the 01:30 reset replaces it with the seeded one.
Check it on your machine: `python scripts\demo_progress.py status` prints what the Plan screen would suggest. `python scripts\demo_progress.py seed --yes` sets it up (it clears the demo teacher's evidence, as the nightly reset does).


## "The Plan screen shows a yesterday I did not expect" (found on the click-through, 24 Oct)
The Plan screen takes the **latest plan stored before today** as "yesterday": a plan you generated yourself counts, exactly like the seeded one. If you generated a plan yesterday (for example while testing), THAT is yesterday: it has no review evidence and no recorded decision, so the panel suggests nothing, and its groups' skills may be whatever you chose. The panel's first line says which plan it reads ("सुझाव 2026-10-23 की योजना…"), and each group's "पिछली योजना (date):" line names that plan's date and says if that group re-taught. (Until 27 Oct this line read "कल:", which looked like yesterday even when the plan was days old.)
To see which plans are stored and which one is used: `python scripts\demo_progress.py status --env-file backend\.env` (it lists the plans of the last 14 days and marks "yesterday").
To bring the demo back to its story: `python scripts\demo_progress.py seed --yes --env-file backend\.env`. It replaces the plan of yesterday with the seeded one and records the three days of worksheets up to yesterday (the nightly reset does the same at 01:30 IST, so in the cloud the demo is right every morning).
