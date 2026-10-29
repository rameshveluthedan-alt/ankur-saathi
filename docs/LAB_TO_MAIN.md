# Moving the lab work into main

**For:** the release owner (Ramesh). The lab rule stands: the lab never touches `main`; the release owner packages, applies, runs the gate and deploys, in
`C:\dev\Ankur-Saathi` on `main`. Full detail of every change: `docs/LAB_UI_HANDOVER.md`.

## What moves

- **The lab commits** on `lab/experiments` since `main` at `4e17b06` (Release candidate 3). Count them with `git log --oneline main..lab/experiments`, and see the files with `git diff --stat main..lab/experiments` (a fixed number here would go out of date with every lab commit).
- **The first lab commit is not UI work.** `dce44f3` ("WIP snapshot before UI work: employee-code sign-in, consent gate, login rework", 39 files) is a
  snapshot of the sign-in work: `auth_service.py`, `auth_routes.py`, `register_service.py`, `config.py`, `LoginScreen.jsx`, `ConsentGate.jsx`, `ChangePinScreen.jsx`,
  the account scripts, `DEPLOY.md`, `cloudrun-env.yaml` and their tests. **If main already has the sign-in work in its own form (v30b), leave this commit out**
  (see step 1). Everything after it is the UI work in `docs/LAB_UI_HANDOVER.md`.
- **No database migration.** The UI work only updates the comment in `db/schema/09_auth.sql` (the event list); the snapshot also changes the seed
  `db/seeds/classroom/01_profile.sql`.
- **Two new read-only server routes:** `GET /progress/mentor/{teacher}` (the mentor report) and `GET /progress/class-summary/{teacher}` (the class summary).
  One new audit event name: `class_summary_view` (each opening of the class summary is logged).
- **The AI prompt is unchanged.** The prompt work is drafts only, in `docs/drafts/`.

## Steps

1. **Package (in the lab folder):**
   - **the UI work only** (main already has its own sign-in work): one file per commit, `git format-patch dce44f3..lab/experiments -o C:\dev\lab-patches`;
     or one file, `git diff dce44f3 lab/experiments > C:\dev\lab.patch`.
   - **everything, the sign-in snapshot included** (only if main does NOT have the sign-in work): `git format-patch main..lab/experiments -o C:\dev\lab-patches`.
   - Never `git diff main..lab/experiments` for the UI work alone: it carries the snapshot with it.
   - Leave `docs/drafts/` out if the drafts should not ship.
   - **Where the UI work sits on the snapshot's changes** (both changed these files, so they may not apply cleanly onto main's own sign-in version; merge
     them by hand): `pwa/src/App.jsx`, `pwa/src/screens/AccountScreen.jsx`, `ChangePinScreen.jsx`, `ConsentGate.jsx`, `LoginScreen.jsx`, `pwa/src/services/api.js`,
     `backend/app/models/schemas.py`, `pwa/tests/consent.dom.test.mjs`, `demo_accounts.test.mjs`, `login.dom.test.mjs`, `docs/DEMO_ACCESS.md`, `docs/ROADMAP.md`.
2. **Apply (in `C:\dev\Ankur-Saathi`):**
   - `git branch --show-current` must say `main`.
   - `git log 4e17b06..main`: if main has moved since the lab began, expect a few conflicts.
   - `git am C:\dev\lab-patches\*.patch`, or `git apply --3way C:\dev\lab.patch`.
3. **Gate:**
   - `python scripts\run_tests.py --env-file backend\.env --pwa`: all OK (in the lab: 44 backend and 38 front-end suites). Without the snapshot, the sign-in
     tests (`test_auth_flow`, `test_auth_pin`, `test_test_teachers`, `login.dom`, `consent.dom`, `demo_accounts`, and the login part of `ui_review`) follow
     main's own sign-in: a failure there is a merge to check against main's version, not a lab change to copy.
   - `cd pwa; npm run build`.
   - `python scripts\precommit_check.py`, and commit only if it exits 0 on its own (never piped through `tail`).
   - **Do not set `VITE_MOCK_SIGNAL`** for the main build: it is the lab's placeholder for the signal panel.
4. **Deploy:** the two guard lines first, then `deploy/DEPLOY.md` section 7; then **section 11, "After EVERY redeploy"**, to point the nightly job at the new
   image (otherwise the nightly demo reset keeps running the old code).
5. **Smoke test on the deployed app:**
   - a plan at 45 minutes (the time chip says 45);
   - the Review's three steps, and "अभी दर्ज करें" from a teach block's You Do;
   - the tick sheet and the printed plan, printed;
   - the mentor report and the class summary (Class progress → "📄 रिपोर्ट");
   - the phone's Back button inside the Review;
   - the tab names (योजना बनाएँ, आज की योजना, समीक्षा, कक्षा प्रगति);
   - "आज की योजना" after reopening the app the next day (today's plan, never yesterday's).

## Worth knowing

- **The signal panel stays hidden** until the server sends `signal` on each teach block (server work, not in the lab). Nothing breaks without it.
- **Not included:** the 3 + N worksheet and the prompt v2 (`docs/drafts/`): they need the prompt decision and a real-model run on main.
- **Open items** are listed in the handover note's "Open decisions for the team".
