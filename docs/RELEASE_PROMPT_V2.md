# Release: prompt v2, the block library and offline plans (`lab/prompt-v2` into `main`)

**For:** the release owner. Written 22 Nov 2026; offline plans added 23 Nov. The lab rule stands: nothing here is run from the lab folder; the release owner merges, runs the
gate and deploys, in `C:\dev\Ankur-Saathi` on `main`. (`docs/LAB_TO_MAIN.md` is the history of an earlier, patch-based move; it does not apply here.)

## What this release carries

- **The branch:** `lab/prompt-v2`, made from `main` at `112b953` (deployed 17 Nov). Count its commits with `git log --oneline main..lab/prompt-v2`.
  `main` has moved since (one docs-only commit, `df270f6`, the roadmap note on EmbeddingGemma), so on 23 Nov the merge is NOT a fast-forward: step 1 makes a merge
  commit (a dry run showed no conflicts). If `git log --oneline lab/prompt-v2..main` prints nothing when you run it, `--ff-only` works as before.
- **Offline plans (23 Nov):** with no connection the teacher can still make a plan for EVERY skill, in both subjects, at 45 / 60 / 90 minutes. While online the phone
  has the server prepare one plan per skill and length (about 300, in batches of at most 25, kept in IndexedDB, refreshed weekly or when the library changes), the
  Plan screen lists the skills it kept when it opens with no connection, Generate opens the prepared plan (📴 label, library note), the worksheets show in the app, and a
  plan made offline is sent when the connection returns. New server routes: `POST /api/offline/prepare` (at most 120 choices a request; no AI, nothing stored) and
  `POST /api/plan/offline` (stores a plan made on a phone, once, by its client id); the quick ⚡ plan online (`source: library`). No database change. Details:
  `docs/OFFLINE.md`.
- **In it:** prompt v2 (the cached system block, each group's own mistakes, the 3 + N worksheet, the pace per block); the 45 / 60 / 90-minute
  session lengths, with the line under "आज का समय" describing each; the block library (`db/seeds/library/`, 880 checked pieces) and the assembler,
  used FIRST when the AI is off; the pilot-account commands (`scripts/auth_admin.py create-school` with `--block`, `--district`, `--printer`);
  the fixes from four AI-assisted reviews of the 12 test plans (`docs/drafts/prompt_v2_runs/README.md`).
- **The database:** nothing to run by hand. The two new columns of `ai_usage` (`cache_read_tokens`, `cache_write_tokens`) are added by the app
  itself the first time it records a call (`ADD COLUMN IF NOT EXISTS`, `backend/app/services/ai_budget.py`); `db/schema/10_ai_usage.sql` has them too.
- **Settings:** `deploy/cloudrun-env.yaml` gained two lines (`AI_PRICE_CACHE_READ_PER_MTOK`, `AI_PRICE_CACHE_WRITE_PER_MTOK`), so the generated file
  must be made again (step 3). Unchanged and right: `CLAUDE_MODEL` (Sonnet 5.5), `CLAUDE_MAX_TOKENS` 24000 (the largest v2 plan used about 14,600
  output tokens), `AI_CREDIT_EXPIRES` 2026-11-30. `LIBRARY_FALLBACK` and `PLAN_SOURCE` are not set on live: their defaults are right.
- **The library files ship in the image:** the Dockerfile copies `db/`, and `.dockerignore` drops only CSV files (except the skill bridges).

## Steps (PowerShell, in `C:\dev\Ankur-Saathi`)

**1. The guard lines, then the merge**
```powershell
cd C:\dev\Ankur-Saathi
git branch --show-current      # must print: main
git status --short             # must print nothing
git merge --no-edit lab/prompt-v2     # a merge commit (main has one docs-only commit the branch lacks); if it stops on a conflict, stop and look
git log --oneline -3                  # the merge commit, then the newest commit of lab/prompt-v2 below it
```
The EmbeddingGemma roadmap note is already on `main` (`df270f6`), so no cherry-pick is needed.

**2. The gate.** In a SEPARATE PowerShell window, so the tests can never use the real key:
```powershell
cd C:\dev\Ankur-Saathi
$env:ANTHROPIC_API_KEY = "sk-dummy-never-used"
python scripts\run_tests.py --env-file backend\.env --pwa
cd pwa; npm run build; cd ..
```
- Expected to fail: `test_submission_check` only (commits after the 1 Nov deadline).
- May fail: `test_demo_seed`, which depends on the date and on what the local database holds (it failed in the lab on 22 Nov because a
  demo-seed plan from an earlier night sat on the date it picks).
- Anything else: stop, and look at it before deploying.

**3. Make the settings file again** (`deploy/DEPLOY.md` section 6). Set the variable block of section 0 and `$CONN` (section 3) first.
```powershell
(Get-Content deploy\cloudrun-env.yaml) -replace "PROJECT:REGION:INSTANCE", $CONN | Set-Content -Encoding ascii deploy\cloudrun-env.generated.yaml
Select-String -Path deploy\cloudrun-env.generated.yaml -Pattern "DB_HOST|CLAUDE_|AI_PRICE_CACHE"
```
`DB_HOST` must start with `/cloudsql/`, and both `AI_PRICE_CACHE_*` lines must be there.

**4. Deploy** (`deploy/DEPLOY.md` section 7, the same command as before)
```powershell
gcloud run deploy $SERVICE --source . --region $REGION --allow-unauthenticated --add-cloudsql-instances $CONN --env-vars-file deploy\cloudrun-env.generated.yaml --set-secrets "DB_PASSWORD=ankur-db-password:latest,SESSION_SECRET=ankur-session-secret:latest,ANTHROPIC_API_KEY=ankur-anthropic-key:latest" --timeout=300 --min-instances=0 --max-instances=3 --memory=1Gi --cpu=1 --concurrency=20
```

**5. Point the jobs at the new image** (`deploy/DEPLOY.md` section 11). Without this the nightly demo reset keeps running the OLD code.
```powershell
$IMAGE = gcloud run services describe $SERVICE --region $REGION --format="value(spec.template.spec.containers[0].image)"
gcloud run jobs update ankur-nightly --image=$IMAGE --region=$REGION
gcloud run jobs update ankur-usage --image=$IMAGE --region=$REGION
gcloud scheduler jobs run ankur-nightly-reset --location=$REGION
gcloud run jobs executions list --job=ankur-nightly --region=$REGION     # the newest: succeeded
```

**6. Smoke test on the live app** (real credits: about $0.13 a plan, some $0.50 in all)
- **Plan screen:** the time choice offers 45 / 60 / 90, and the line under "आज का समय" changes with it
  (45: "एंकर 5 मिनट · समूहों को 16, 14 और 7 मिनट · वर्कशीट (गणित और पठन): 3 मुख्य + 1 अतिरिक्त सवाल").
- **One plan at 45 minutes:** blocks of 5, 16, 2, 14, 1 and 7 minutes; one show-me question per block; each worksheet 3 core + 1 extra.
- **One plan at 60 minutes:** 3 core + 2 extra; two show-me questions per block.
- **Review:** the three steps; the tick sheet and the printed plan, printed.
- **Offline plans (needs no AI credit):**
  - Sign in as a demo teacher and open the Plan screen; wait for "✓ ऑफ़लाइन योजना तैयार" (about 300 plans, fetched in batches of 25, so a minute or two; longer on a slow connection).
  - Cut the network (airplane mode, or DevTools → Network → Offline). The banner appears; the skills still list; the prepared ones are ready.
  - Pick a skill, press "आज की योजना बनाएँ": the plan opens with the 📴 "बिना इंटरनेट के बनी योजना" label, and 📝 opens each worksheet in the app
    (an observed sheet shows its "what to look for" as three ✓ / ~ / ✗ lines).
  - Restore the network: the plan is sent by itself (the teacher is told). Check the Teach screen shows the stored plan.
  - Repeat in Hindi (हिंदी), and once at 45 and 60 minutes. Online, the ⚡ quick plan answers in seconds with the library label.
  - Sign out with a plan not yet sent: the app warns first.
  - Not tested on a real budget Android phone (1 to 2 GB): worth one try on a spare phone.
- **The AI budget:** `gcloud run jobs execute ankur-usage --region=$REGION --wait`, then read its log as in section 11: the new calls are there,
  and after the first plan they show cache reads.

**7. If anything is wrong: roll back** (`deploy/DEPLOY.md` section 11)
```powershell
gcloud run revisions list --service=$SERVICE --region=$REGION
gcloud run services update-traffic $SERVICE --region=$REGION --to-revisions=PREVIOUS-REVISION=100
```
A rollback does not touch the database; the two new columns are harmless to the old code.

**8. Push `main`** once the smoke test passes: `git push origin main`.

## Worth knowing

- **After 30 Nov** (`AI_CREDIT_EXPIRES`) AI calls are refused: plans come from the block library, built by code, with the label
  "🧩 तैयार हिस्सों से बनी योजना" (AI-drafted pieces, not yet reviewed); photo marking stops. With no library piece for a choice, the six recorded
  plans are the fallback, as before.
- **The education lead's review:** the new Hindi on her list (`docs/HANDOVER.md`, item 3) goes live with this release; her OK before the pilot
  teachers start is worth having.
- **Pilot accounts** (`docs/AUTH.md`, "Real accounts"): `create-school` must run against the LIVE database. A one-off Cloud Run job would print the
  temporary passwords into Cloud Logging; running the script from your own machine through the Cloud SQL Auth Proxy keeps them on your screen only.
- **`--min-instances` stays 0.** Set it to 1 only while people are testing, and back to 0 afterwards (a warm container is billed when idle).
