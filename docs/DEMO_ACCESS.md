# How reviewers sign in to the demo

The demo holds **fictional data only**, so its PINs are published. Open the app: the login screen lists these accounts, and
tapping one fills in the phone number and PIN.

| Phone | PIN | What it is |
| --- | --- | --- |
| 9876543210 | 4826 | **Demo teacher**: a 30-child multi-grade class (Grades 1 to 3), fictional names, a few days of data |
| 9876500000 | 7351 | **Demo school admin**: lists the school's accounts, shows the join code, resets the "Change PIN" account's PIN |
| 9000000199 | 3917 | **"Change PIN" account (पिन बदलना)**: change its PIN, reset it as the admin, lock it out. Nothing else is affected |
| 9000000101 to 9000000105 | 4826 | **Test teachers**, each with their own multi-grade class (class numbers 101-110, 201-208, 301-306). Use one each, so you do not overwrite each other's photos or registers |

## Suggested path
1. **Teacher:** sign in as 9876543210 or one of the test teachers. Look at Plan, Progress (the "consider re-assessing" flags, the
   child list with names) and Review (the observation checklist, the suggested sample).
2. **PIN reset:** sign in as the admin (9876500000), open Profile (the last tab), reset the "Change PIN" account's PIN. A temporary PIN appears once.
   Sign out, sign in as 9000000199 with it: the only screen is "choose a new PIN".
3. **A new school:** choose "New teacher? Register" with any new phone number and school code: you become that school's admin and
   see its join code. Registering into the demo school needs its join code: **DEMO26**.

## If the AI limit is reached
The demo's AI use is capped so the credits last through evaluation (`docs/AI_BUDGET.md`). When a limit is reached, a plan for a skill with a
recorded sample is still shown, labelled "sample plan" (try **N2.2.1** or **N2.3.2**); other skills and photo analysis say the limit was reached
and that it resets the next day.

## Why some accounts cannot change their PIN
The shared demo accounts have a fixed PIN on purpose: if one reviewer changed it, everyone else would be locked out. The PIN
practice account exists so the change and reset flows can still be tried.

## For the operator
```
python scripts/create_test_teachers.py create --count 5 --env-file backend/.env
python scripts/auth_admin.py demo-setup       --env-file backend/.env     # PINs, flags and the join code; prints this table
python scripts/demo_progress.py seed --end-date YESTERDAY --env-file backend/.env
python scripts/ai_usage.py status --env-file backend/.env                 # before every demo: how much AI budget is left
```
Nightly: `auth_admin.py restore-practice` (puts the "Change PIN" account right), and re-seed the demo data (flags expire after 14 days).
If you change a demo PIN, change it in `pwa/src/screens/LoginScreen.jsx` too. For a real school set `VITE_DEMO_HINT=false`.
