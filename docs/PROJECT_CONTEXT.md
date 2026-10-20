# Ankur Saathi: project context

Last updated 20 Oct 2026, after bundle v25b. Attach this at the start of any new session. It holds facts and decisions, never secrets.

## Working rules for the assistant (read first)
1. **Never ship a whole `config.py`, `main.py` or `database.py`.** The user hand-edited these on their own machine (16 Oct: explicit `DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME`
   fields because URL parsing failed on their Windows setup; `main.py` prints `db_host:db_port/db_name`). The assistant's working copy never had those edits, so shipping
   the files overwrote them twice. Give the lines to ADD, or ask for the user's version first. (`config.py` v25b now accepts both styles.)
2. **Search `/mnt/transcripts` (grep) before asking the user something, and before changing anything risky.** The conversation is compacted regularly and the summary drops facts.
3. The user works on **Windows** (`C:\dev\Ankur-Saathi`, PowerShell, Python 3.11 in `backend\venv`, local PostgreSQL). Give PowerShell commands; use `psql -P pager=off`
   (the pager once hid output); set `$env:PGCLIENTENCODING = "UTF8"` for Hindi.
4. Never print or store secrets (the user once pasted an error that contained their DB password). Hindi text can be cut mid-character by `cut`/`head`: read through Python.
5. Tests of OTHER features run with `AUTH_MODE=off`; sign-in is enforced by default. Test data is removed afterwards and tests must not delete real rows.

## The project
AI teaching companion for foundational literacy and numeracy (FLN), multi-grade classes in Madhya Pradesh. Teacher picks a skill, gets a daily plan for three groups
(Beginner / Progressor / Proficient), photographs worksheets, sees analysis. Hackathon: ShikshaNext + Anthropic + CSF. Also an MIT Solve 2027 application.
- **Build Stage submission: 1 Nov 2026. No commits after 1 Nov.** Jury window 1 to 10 Nov (results about 10 Nov). MIT Solve: 6 Nov 2026, 12 noon ET (10:30 pm IST): submit by 4 Nov.
- Environment variables on the host are not commits, so spending caps and switches are settings, not code.

## Credits (organisers' terms)
- **USD 500 received 15 Oct 2026**, valid until **20 Nov 2026** (keys disabled after; unused credit lost). If shortlisted after the pilot phase (10 Nov): extra USD 500 for
  improving the product and preparing the demo by 17 Nov.
- Only through Anthropic's own API or Claude Code, not AWS Bedrock or Google Vertex; for hackathon prototypes only; not transferable. They do not cover claude.ai chat.
- Keep enough for evaluators and the demo. The organisers are told at 80% of the allocation.
- About USD 1.50 had been spent by 20 Oct (6 real plans, 1 photo test): `AI_SPEND_OFFSET_USD=3` covers it.
- Real school data and real children's photos need the team's OWN Anthropic account, not these credits.

## Models and costs
- **Plans and photos: `claude-sonnet-5-5`** (decided 16 Oct: Sonnet 5.5 for daily work and Vision). Fable 5.1 skipped (extra safety guardrails not needed). Opus 5.5 was suggested for
  demo day on 16 Oct; **withdrawn 20 Oct** (it assumed 2 to 4 cents a plan; real is 12 to 14 cents on Sonnet).
- **Prices: $2 per million input, $10 per million output tokens** (Sonnet 5.5, from the pricing pages, 18 Oct). Observed plan cost **11.8 to 14.4 cents**; output is about 94% of it.
  Re-check the prices if the model changes. `scripts/ai_usage.py calibrate` compares the meter with actual spend.
- **Thinking is set low on purpose** (`CLAUDE_THINKING_BODY = between_tools`): at default effort thinking used the whole 16,000-token budget and the plan was never written.
  Do not raise it without testing 3 plans.
- Pending experiment: Haiku 5.5 for photo reading, judged by the scored photo test.

## Decisions made
- **Levels** change ONLY through an assessment (baseline, periodic, or re-assessing one child). Daily results never change a level; they only raise a "consider re-assessing"
  flag. The periodic-assessment screens, a history of rounds and "re-assess one child" are **not built yet**. (`docs/LEVELS.md`)
- **Re-teach context** comes from the most recent review within a week, same subject. **Sampling:** systematic, rotating start, 40% of groups over 8 (`docs/SAMPLING.md`).
- **Register:** CSV or Excel upload, optional names; class numbers carry the grade when rolls repeat (Grade 3 roll 5 = 305). (`docs/REGISTER.md`)
- **Names** are teacher-only, in their own table, never sent to the AI, never in the officer report; enforced by tests. (`docs/PRIVACY.md`)
- **Sign-in:** phone + PIN, signed 12-hour tokens on every route, a school admin resets PINs (temporary PIN shown once), first teacher of a new school is its admin and gets a
  join code. Real use needs HTTPS and a per-address rate limit. (`docs/AUTH.md`)
- **AI budget:** every call metered; reserve $250 until 1 Nov; global daily cap $20; fallback to recorded sample plans (N2.2.1, N2.3.2 so far). (`docs/AI_BUDGET.md`)
- **Hindi style (20 Oct, from Vaishnavi's review of the N2.3.2 PDF):** respectful forms when the teacher speaks to the class (आएँ, रोक दें, दें), no फालतू/चुपचाप, the Tens|Ones frame is
  "दहाई-इकाई का बॉक्स" (decided 20 Oct; not "घर": children are taught with the printed grids) not "खाना", feminine "कितनी दहाई/इकाई". A prompt rule plus a code safety net (`prompts/hindi_style.py`, `docs/HINDI_STYLE.md`); the review PDF renders fine
  (its odd extracted text is only an extraction artefact of shaped Devanagari) and the same wording WAS in the app's plans. OPEN for her: polite forms in printed worksheets (`POLITE_IN_WORKSHEETS`).
- **Copy errors** (a child copying a problem wrongly) are detected in code and not scored. A repeated photo of the same child keeps the earlier result unless Replace is chosen.
- **Capture:** only the channels today's skills need (photo, observed, oral reading), per group.

## Hosting (not built yet)
- **Google Cloud**, a NEW project the user is creating (project ID and region to be sent: Mumbai `asia-south1` or Delhi `asia-south2`). Cloud Run + Cloud SQL (needs `vector` and
  `uuid-ossp`) + Secret Manager + Cloud Scheduler for the nightly reset.
- **Serve the app and the API from ONE Cloud Run service.** Firebase Hosting in front of the API is rejected: its proxy times out at 60 seconds and a plan takes 60 to 80.
- Plan: first throwaway deployment about 22 to 23 Oct, fixes 24 to 28 Oct, final deploy 29 to 30 Oct, freeze 31 Oct. The assistant cannot reach the user's cloud account: it writes files
  and commands, the user runs them.

## Demo accounts (fictional data only; published to jurors; `docs/DEMO_ACCESS.md`)
9876543210 / 4826 demo teacher (30 children) | 9876500000 / 7351 demo school admin | 9000000199 / 3917 the "Change PIN" account, पिन बदलना (PIN changeable; formerly "PIN practice") | 9000000101 to 105 / 4826 test teachers.
Join code for the demo school: DEMO26. Shared accounts have a fixed PIN so one reviewer cannot lock out the others.

## Bundles
Cumulative bundles since v17: **v26-changes-since-v17.tar.gz** (69 files) is the latest (**v26-hindi-style.tar.gz** is only what changed after v25g: 8 files); **v25b-config-fix.tar.gz** is only `config.py` + its test; **v25g-pin-wording.tar.gz** (10 files: the final screens, wording and the operator script) supersedes the small fixes **v25c/v25d/v25e/v25f**, whose content is all in it; before that: **v25c-app-fix** and **v25d-nav-fix** were only `pwa/src/App.jsx` (c: a stored teacher with no token no longer counts as signed in; d: a Profile tab (प्रोफ़ाइल, formerly खाता / Account) in the bottom bar on every screen; e/f: the word खाता is no longer used. Naming rule (UI words): the PAGE is प्रोफ़ाइल / Profile; a login identity is अकाउंट / account ("demo account"); never आईडी, which clashes with children's roll and class numbers; an admin's reset prompt says शिक्षक; Hindi text writes पिन, English text writes PIN). All are already inside the latest v25. Install order after extracting:
`psql -U postgres -d ankur_saathi -f db/schema/06 ... 10_*.sql` (each file once), `db/seeds/classroom/02_child_names.sql`, `python scripts/auth_admin.py demo-setup --env-file backend/.env`,
set `SESSION_SECRET` in `backend/.env`, restart. Delete `docs/LEVEL_CHANGES.md` (replaced by `docs/LEVELS.md`).

## Open items, roughly by priority
1. Hosting files and first deployment. 2. Scored photo test (Stage 2; the 5-photo smoke test passed: 38 of 40 answers read right; includes a few hand-drawn-grid notebook pages and copy
errors). 3. `batch_generate.py --limit 3 --save-samples`, then the rest (recorded plans, coverage labels). 4. Hindi spelling decisions for 13 number names (Vaishnavi; check the Class 1 to 3
textbook the pilot uses). 5. Offline test of the app. 6. Periodic assessment screens (needs round history). 7. MIT Solve application: teacher conversations, business model, hosted link.
8. Background plan generation (a dropped connection wastes a paid plan). 9. Review packs for Vaishnavi (mistakes and prerequisites; NIPUN alignment).
