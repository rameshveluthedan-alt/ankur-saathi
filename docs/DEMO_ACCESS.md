# How reviewers sign in to the demo

The demo holds **fictional data only**, so its PINs are published. Open the app: the login screen lists these accounts, and
tapping one fills in the phone number and PIN.

| Phone | PIN | What it is |
| --- | --- | --- |
| 9876543210 | 4826 | **Demo teacher**: a 30-child multi-grade class (Grades 1 to 3), fictional names, a few days of data |
| 9876500000 | 7351 | **Demo school admin** (the demo school: the demo teacher and the "Change PIN" account): lists the school's accounts, shows the join code, resets the "Change PIN" account's PIN |
| 9000000100 | 7351 | **Test school admin** (the test school: the five test teachers below): lists their accounts and shows the school's join code. The test teachers' PINs are fixed, so it cannot reset them |
| 9000000199 | 3917 | **"Change PIN" account (पिन बदलना)**: change its PIN, reset it as the admin, lock it out. Nothing else is affected |
| 9000000101 to 9000000105 | 4826 | **Test teachers** (the role is plain *teacher*: no admin screens), all in the test school, each with their own multi-grade class (class numbers 101-110, 201-208, 301-306). Use one each, so you do not overwrite each other's photos or registers |

## Suggested path
0. **What the admin can do today:** see the school's code and join code and make a new join code; list the school's accounts (only the last four digits of each phone number); reset a teacher's PIN to a temporary one (shown once); unlock a locked account. **Teachers register themselves** with the join code, **each teacher enrols her own class** by uploading a register, and a teacher picks her own grades. There are no admin screens yet for enrolling teachers or children, assigning classes or viewing reports (`docs/STATUS.md`).
1. **Teacher:** sign in as 9876543210 or one of the test teachers. Look at Plan, Progress (the "consider re-assessing" flags, the
   child list with names) and Review (the observation checklist, the suggested sample).
2. **PIN reset:** sign in as the admin (9876500000), open Profile (the last tab), reset the "Change PIN" account's PIN. A temporary PIN appears once.
   Sign out, sign in as 9000000199 with it: the only screen is "choose a new PIN".
3. **A new school:** choose "New teacher? Register" with any new phone number and school code: you become that school's admin and
   see its join code. Creating a school asks you to **confirm a short statement** (that the children's parents have been told and have given permission, that photos are not kept and names never go to the AI): tick the box under the join code field. Joining an existing school asks for nothing, because that school confirmed it when it was created. Registering into the demo school needs its join code: **DEMO26**. The admin's Profile shows the school's confirmation, or a button to confirm it for a school created earlier.

## If the AI limit is reached
The demo's AI use is capped so the credits last through evaluation (`docs/AI_BUDGET.md`). When a limit is reached, a plan for a skill with a
recorded sample is still shown, labelled "sample plan" (the recorded sample plans are N0.1.1, N2.2.1, N2.3.2, L2.3.1, L2.5.1 and L2.7.2); other skills and photo analysis say the limit was reached
and that it resets the next day.

## Why some accounts cannot change their PIN
The shared demo accounts have a fixed PIN on purpose: if one reviewer changed it, everyone else would be locked out. The PIN
practice account exists so the change and reset flows can still be tried.

## For the operator
```
python scripts/create_test_teachers.py create --count 5 --env-file backend/.env     # the test school, its admin 9000000100, and the five teachers
python scripts/create_test_teachers.py normalise --env-file backend/.env            # converts accounts made by an older version (each teacher alone in a school, so each an admin); the nightly job runs it
python scripts/auth_admin.py demo-setup       --env-file backend/.env     # PINs, flags and the join code; prints this table
python scripts/demo_progress.py seed --end-date YESTERDAY --env-file backend/.env
python scripts/ai_usage.py status --env-file backend/.env                 # before every demo: how much AI budget is left
```
Nightly: `auth_admin.py restore-practice` (puts the "Change PIN" account right), and re-seed the demo data (flags expire after 14 days).
If you change a demo PIN, change it in `pwa/src/screens/LoginScreen.jsx` too. For a real school set `VITE_DEMO_HINT=false`.


## What the Plan screen shows on the demo (seeded every night)
The nightly reset (01:30 IST) records three days of Progressor worksheets for N2.3.2 **and stores yesterday's plan** for the demo teacher (the three groups with their children and skills, and the decisions "recorded" at that review). So when you open **योजना** and choose **N2.3.2**, the panel *"आज हर समूह का कौशल"* shows:
- **Beginners:** yesterday N2.3.1, decision **▲ आगे बढ़ें**: N2.3.2 is suggested ("आपके कल के निर्णय से").
- **Progressors:** yesterday N2.3.2, **no decision recorded**: on the last day **6 of the 14 children made a mistake** (rolls 16, 19, 24, 25, 26, 27: the dropped carry four times, the whole ones sum twice) and a third (5) is the threshold, so a **🔄 re-teach is recommended** ("कल की जाँच के सुझाव से"), with the children's roll numbers and the mistakes named. The box is ticked. Generate the plan: the Progressors' block is the re-teach, with the pace line and the quiet-visit tips, and the top right of the plan lists the groups' skills with "🔄 पुनः शिक्षण".
- **Proficients:** no decision and no evidence: their skill follows the one chosen.
The seeded plan is replaced every night, so the demo tells the same story each day. A plan you generate today becomes "yesterday" at midnight, but the 01:30 reset replaces it with the seeded one.
Check it on your machine: `python scripts\demo_progress.py status` prints what the Plan screen would suggest. `python scripts\demo_progress.py seed --yes` sets it up (it clears the demo teacher's evidence, as the nightly reset does).


## "The Plan screen shows a yesterday I did not expect" (found on the click-through, 24 Oct)
The Plan screen takes the **latest plan stored before today** as "yesterday": a plan you generated yourself counts, exactly like the seeded one. If you generated a plan yesterday (for example while testing), THAT is yesterday: it has no review evidence and no recorded decision, so the panel suggests nothing, and its groups' skills may be whatever you chose. The panel's first line says which plan it reads ("सुझाव 2026-10-23 की योजना…"), and each group's "कल:" line says if that group re-taught.
To see which plans are stored and which one is used: `python scripts\demo_progress.py status --env-file backend\.env` (it lists the plans of the last 14 days and marks "yesterday").
To bring the demo back to its story: `python scripts\demo_progress.py seed --yes --env-file backend\.env`. It replaces the plan of yesterday with the seeded one and records the three days of worksheets up to yesterday (the nightly reset does the same at 01:30 IST, so in the cloud the demo is right every morning).
