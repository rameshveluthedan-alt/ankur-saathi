# Deploying Ankur Saathi on Google Cloud

You end up with one address, `https://ankur-saathi-xxxxx-el.a.run.app`, that serves the app and the API over HTTPS, backed by a small
PostgreSQL database, with a nightly reset of the demo. About 60 to 90 minutes the first time. Every command is for **PowerShell**, run from
`C:\dev\Ankur-Saathi`, one line at a time.

**What was and was not tested.** The app served by `app.production`, the rate limit, the database load (`first_setup.sh`) on an empty database, the nightly reset, and the
connection through a unix socket were all tested, including in a real browser against the production build. The `Dockerfile` could not be built where I work (no Docker),
and the `gcloud` commands were checked against Google's reference pages but not run against your project. If a step fails, the troubleshooting table at the end covers the
usual causes, and the error text is what I need to see.

```
Browser --HTTPS--> Cloud Run (the app and the API, one container) --socket--> Cloud SQL (PostgreSQL 15)
                        |  secrets: Secret Manager (database password, AI key, session secret)
Cloud Scheduler --nightly--> Cloud Run job (reset the demo)          Cloud Run job, once (load the database)
```

## 0. Before you start
- A Google Cloud project **with billing enabled** (you have this).
- `gcloud` installed: `gcloud --version` should print a version. If not, install the Google Cloud CLI first.
- A **new Anthropic API key** that has never been in git (ask the organisers; see `docs/AI_BUDGET.md`). You paste it once, in step 4, and it is stored only in Secret Manager.
- Your `backend\.env` (for two values in step 6).

Set these once. **If you close PowerShell, run this block again.**
```powershell
cd C:\dev\Ankur-Saathi
$PROJECT_ID   = "PASTE-YOUR-PROJECT-ID"
$REGION       = "asia-south1"
$SQL_INSTANCE = "ankur-saathi-db"
$SERVICE      = "ankur-saathi"
```
`asia-south1` is Mumbai (`asia-south2` is Delhi). The database region cannot be changed later.

## 1. Sign in and check the project
```powershell
gcloud auth login
gcloud config set project $PROJECT_ID
gcloud billing projects describe $PROJECT_ID --format="value(billingEnabled)"
```
The last command must print `True`.

## 2. Turn on the services, and set a budget alert
```powershell
gcloud services enable compute.googleapis.com run.googleapis.com sqladmin.googleapis.com secretmanager.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com cloudscheduler.googleapis.com
```
Then, in the console, **Billing, then Budgets & alerts, then Create budget**: pick an amount you are comfortable with and add alerts at 50%, 90% and 100% to two email addresses.
A budget only warns, it does not stop spending. The AI spending has its own caps (`docs/AI_BUDGET.md`).

## 3. The database
```powershell
gcloud sql instances create $SQL_INSTANCE --database-version=POSTGRES_15 --edition=ENTERPRISE --tier=db-f1-micro --region=$REGION --storage-size=10GB --storage-auto-increase --backup-start-time=21:30
```
This takes 5 to 10 minutes. `--edition=ENTERPRISE` is needed because newer PostgreSQL versions default to Enterprise Plus, which does not offer this small shared-core tier.
`db-f1-micro` is meant for development and demos, and it is enough here because the app spends its time waiting for the AI, not the database. The backup runs at 03:00 India time.

```powershell
$CONN = gcloud sql instances describe $SQL_INSTANCE --format="value(connectionName)"
$CONN
gcloud sql databases create ankur_saathi --instance=$SQL_INSTANCE
$b = New-Object byte[] 24; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b); $DB_PASSWORD = ($b | ForEach-Object { $_.ToString("x2") }) -join ""
gcloud sql users create ankur --instance=$SQL_INSTANCE --password=$DB_PASSWORD
```
`$CONN` prints like `your-project:asia-south1:ankur-saathi-db`. The password is 48 random letters and digits, so it needs no special handling anywhere.

## 4. The secrets
Secret Manager keeps the three values the app must not have in a file. This helper writes each value to a temporary file **without a trailing newline** (a newline would silently
become part of the password), uploads it, and deletes the file:
```powershell
function New-Secret($name, $value) { $f = Join-Path $env:TEMP "$name.txt"; [IO.File]::WriteAllText($f, $value); gcloud secrets create $name --data-file=$f --replication-policy=automatic; Remove-Item $f }
```
```powershell
New-Secret "ankur-db-password" $DB_PASSWORD
$s = New-Object byte[] 32; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($s); New-Secret "ankur-session-secret" (($s | ForEach-Object { $_.ToString("x2") }) -join "")
$sec = Read-Host "Paste the NEW Anthropic API key" -AsSecureString
$key = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
New-Secret "ankur-anthropic-key" $key
$key = $null; $DB_PASSWORD = $null
```
Each `New-Secret` should print `Created secret [...]`. The key is not shown on screen when you paste it.

## 5. Let the app read them
```powershell
$PROJECT_NUMBER = gcloud projects describe $PROJECT_ID --format="value(projectNumber)"
$SA = "$PROJECT_NUMBER-compute@developer.gserviceaccount.com"
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SA" --role="roles/cloudsql.client"
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SA" --role="roles/cloudbuild.builds.builder"
foreach ($n in "ankur-db-password","ankur-session-secret","ankur-anthropic-key") { gcloud secrets add-iam-policy-binding $n --member="serviceAccount:$SA" --role="roles/secretmanager.secretAccessor" }
```
`$SA` is the project's default service account. The app, the build and the jobs all run as it, which is fine for one demo project. The `cloudbuild` role avoids a common failure on the
first deploy in newer projects, where the build runs as this account.

## 6. The settings file
The settings that are not secret live in `deploy\cloudrun-env.yaml`. **Three of them must match your own `backend\.env`**, because the app's built-in defaults are different, and
`CLAUDE_MAX_TOKENS` in particular: the default is 8000 and a plan needs about 13,000, so with the default every plan fails in the cloud while working on your machine.
```powershell
Select-String -Path backend\.env -Pattern "^CLAUDE_"
```
This prints your model settings (it does not print the key). Compare with these lines in `deploy\cloudrun-env.yaml` and edit the file if they differ: `CLAUDE_MODEL`,
`CLAUDE_VISION_MODEL`, `CLAUDE_MAX_TOKENS`. Then fill in the database connection name:
```powershell
(Get-Content deploy\cloudrun-env.yaml) -replace "PROJECT:REGION:INSTANCE", $CONN | Set-Content -Encoding ascii deploy\cloudrun-env.generated.yaml
Select-String -Path deploy\cloudrun-env.generated.yaml -Pattern "DB_HOST|CLAUDE_"
```
`DB_HOST` must now read `/cloudsql/` followed by your connection name. The generated file holds no secrets, but it is generated, so keep it out of git: add the line
`deploy/cloudrun-env.generated.yaml` to `.gitignore` (edit it in VS Code and save as UTF-8). If it is already committed, `git rm --cached deploy/cloudrun-env.generated.yaml` and commit.

**6b. Check the packages (2 minutes, and it saves a failed 10-minute build).** The container installs packages from **your** `backend\requirements.txt`. This builds a clean environment from
that file and checks that every package the production code uses is there, including ones imported only when a feature runs (Pillow, for photos):
```powershell
python -m venv $env:TEMP\reqtest
& $env:TEMP\reqtest\Scripts\python.exe -m pip install -q -r backend\requirements.txt tzdata openpyxl
& $env:TEMP\reqtest\Scripts\python.exe scripts\check_imports.py
```
It must end with `OK: every package the code imports is installed.` If it says `NOT READY`, add the package it names to `backend\requirements.txt` and run the last two lines again. (`tzdata` and `openpyxl` are
added by the Dockerfile itself, so they need not be in the file.)

## 7. Deploy
```powershell
gcloud run deploy $SERVICE --source . --region $REGION --allow-unauthenticated --add-cloudsql-instances $CONN --env-vars-file deploy\cloudrun-env.generated.yaml --set-secrets "DB_PASSWORD=ankur-db-password:latest,SESSION_SECRET=ankur-session-secret:latest,ANTHROPIC_API_KEY=ankur-anthropic-key:latest" --timeout=300 --min-instances=0 --max-instances=3 --memory=1Gi --cpu=1 --concurrency=20
```
- The first time it asks to create an Artifact Registry repository: answer `Y`.
- It builds the container in Google's cloud (5 to 10 minutes) and prints `Service URL: https://...`.
- `--timeout=300` lets a plan take up to 5 minutes (they take 60 to 80 seconds). `--max-instances=3` caps cost and protects the database. `--min-instances=0` means the first visit after
  a quiet period takes a few seconds longer; step 11 shows how to change that for the days jurors are testing.
- The service is public, because jurors must reach it. Every API route except sign-in and a few public ones needs a signed session, and sign-in, registration and PIN change are rate limited.

At this point the app answers but the database is empty.

## 8. Load the database (once)
This runs `deploy/first_setup.sh` inside the same container image, as a job, so you need no database tools on your own machine.
```powershell
$IMAGE = gcloud run services describe $SERVICE --region $REGION --format="value(spec.template.spec.containers[0].image)"
gcloud run jobs create ankur-setup --image=$IMAGE --region=$REGION --set-cloudsql-instances=$CONN --env-vars-file=deploy\cloudrun-env.generated.yaml --set-secrets="DB_PASSWORD=ankur-db-password:latest" --command=bash --args=/srv/deploy/first_setup.sh --task-timeout=1800s --max-retries=0 --memory=1Gi
gcloud run jobs execute ankur-setup --region=$REGION --wait
```
It creates the schema, loads the 101 skills and the content, makes the five test teachers and the demo accounts, and seeds the demo progress. **Run it once.** Running it again on a
filled database would fail part-way. A line `extension "vector" is not available` would not be a problem: the loader then uses plain columns, as it does on your machine.
To read the output (it prints the demo accounts and PINs):
```powershell
gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="ankur-setup"' --limit=60 --format="value(textPayload)" --freshness=1h
```

## 9. Try it
```powershell
$URL = gcloud run services describe $SERVICE --region $REGION --format="value(status.url)"
$URL
curl.exe -s "$URL/health"
```
`/health` should answer `{"status":"ok",...}`. Open `$URL` in a browser, sign in with `9876543210` and PIN `4826`, and generate one plan for **N2.3.2**. That costs about 12 to 14 cents and
proves the AI key, the models and the token setting all work in the cloud. Then check the log for warnings:
```powershell
gcloud run services logs read $SERVICE --region=$REGION --limit=40
```
**Check the icons and "Install":** open `$URL/ankur-saathi-icon-192.png`, which must show a green square with a sprout (not an error or a web page). Then in Chrome press F12, open
**Application, then Manifest**: it lists both icons and an "Installability" section. On a phone, Chrome's menu then offers **Install app** (the app also works offline once opened).
The first lines of a start-up should show `Database pool ready.` and no `WARNING`. A warning about `CLAUDE_MAX_TOKENS`, `ANTHROPIC_API_KEY` or `SESSION_SECRET` means step 4 or 6 is incomplete.

## 10. The nightly reset of the demo
```powershell
gcloud run jobs create ankur-nightly --image=$IMAGE --region=$REGION --set-cloudsql-instances=$CONN --env-vars-file=deploy\cloudrun-env.generated.yaml --set-secrets="DB_PASSWORD=ankur-db-password:latest" --command=python --args=/srv/scripts/nightly_reset.py --task-timeout=600s --max-retries=1 --memory=512Mi
gcloud run jobs add-iam-policy-binding ankur-nightly --region=$REGION --member="serviceAccount:$SA" --role="roles/run.invoker"
gcloud scheduler jobs create http ankur-nightly-reset --location=$REGION --schedule="30 1 * * *" --time-zone="Asia/Kolkata" --uri="https://run.googleapis.com/v2/projects/$PROJECT_ID/locations/$REGION/jobs/ankur-nightly:run" --http-method=POST --oauth-service-account-email=$SA
gcloud scheduler jobs run ankur-nightly-reset --location=$REGION
```
It runs every night at 01:30 India time: it puts the "Change PIN" practice account back and re-seeds the demo teacher's progress up to yesterday. The last command runs it once now.
Check it with `gcloud run jobs executions list --job=ankur-nightly --region=$REGION` (the latest should say succeeded).

## 11. Day to day

### After EVERY redeploy: point the nightly job at the new image
The job `ankur-nightly` was created with a FIXED copy of the image (`--image=$IMAGE`). Redeploying the app builds a new image but does **not** change the job, so without this step the nightly reset keeps running the OLD code
(for example the old demo seed, without yesterday's plan that the Plan screen suggests from).
```powershell
$IMAGE = gcloud run services describe $SERVICE --region $REGION --format="value(spec.template.spec.containers[0].image)"
gcloud run jobs update ankur-nightly --image=$IMAGE --region=$REGION
gcloud scheduler jobs run ankur-nightly-reset --location=$REGION
gcloud run jobs executions list --job=ankur-nightly --region=$REGION
```
The last command should show the newest execution as succeeded. (The one-off `ankur-setup` job was deleted after the first setup and is not touched.)
**See the AI budget** (run it daily, and before a demo). It uses a one-off job:
```powershell
gcloud run jobs create ankur-usage --image=$IMAGE --region=$REGION --set-cloudsql-instances=$CONN --env-vars-file=deploy\cloudrun-env.generated.yaml --set-secrets="DB_PASSWORD=ankur-db-password:latest" --command=python --args=/srv/scripts/ai_usage.py,status --task-timeout=300s --max-retries=0
gcloud run jobs execute ankur-usage --region=$REGION --wait
gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="ankur-usage"' --limit=40 --format="value(textPayload)" --freshness=15m
```
**Release a change** (after committing): run the step 7 command again. The environment variables and secrets stay. If the change adds a database file, tell me and I will give you the command.

**While jurors are testing (1 to 10 November): keep one container warm,** so nobody waits for a start-up:
```powershell
gcloud run services update $SERVICE --region=$REGION --min-instances=1
```
and set it back to `0` afterwards. A warm container is billed even when idle.

**Replace the AI key** (for example after the organisers issue a new one):
```powershell
$sec = Read-Host "Paste the NEW key" -AsSecureString
$key = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
$f = Join-Path $env:TEMP "k.txt"; [IO.File]::WriteAllText($f, $key); gcloud secrets versions add ankur-anthropic-key --data-file=$f; Remove-Item $f; $key = $null
gcloud run services update $SERVICE --region=$REGION --update-env-vars=KEY_ROTATED=1
```
(The second command makes Cloud Run start new containers, which read the `latest` secret.)

**Roll back** a bad release: `gcloud run revisions list --service=$SERVICE --region=$REGION`, then
`gcloud run services update-traffic $SERVICE --region=$REGION --to-revisions=REVISION-NAME=100`.

**Costs.** The database instance is billed for every hour it exists, whether or not anyone uses the app. Cloud Run is billed while it handles requests (and for idle warm containers).
Check the figures in Google's pricing calculator for your region, and keep the budget alert from step 2. The AI credit is separate.

## When something goes wrong
| What you see | Likely cause and fix |
| --- | --- |
| The deploy fails with a permission or storage error during the build | Step 5 was not completed, or has not taken effect yet. Run step 5 again, wait a minute, deploy again. |
| `... allUsers ... blocked by an organization policy` | Your Google account belongs to an organisation that forbids public services. A personal Google account does not have this. Ask whoever administers the organisation. |
| The page loads but sign-in says something went wrong | `gcloud run services logs read $SERVICE --region=$REGION --limit=60`. Usually the database: check `DB_HOST` in the generated file starts with `/cloudsql/`, and that step 8 ran. |
| Every plan fails, but sign-in works | `CLAUDE_MAX_TOKENS` is still 8000 (step 6), or the AI key is wrong. The start-up log names both. |
| "AI limit reached" in the app | A spending cap, working as designed (`docs/AI_BUDGET.md`). Run the usage job in step 11. |
| Sign-in answers "too many attempts" | The rate limit (20 sign-ins a minute per address). Wait the time it says. |
| A job fails | `gcloud run jobs executions list --job=ankur-setup --region=$REGION`, then read its log with the `gcloud logging read` command shown in that step. |
| The page looks old after a release | The browser kept the old version for one visit. Reload twice, or clear the site data. |
| `first_setup.sh: line 2: set: -: invalid option` | The script had Windows line endings. The Dockerfile removes them, so this means the image was built without the `sed` line. Rebuild with step 7. |

## When the judging is over
Delete what costs money. This removes everything, including the database and its data:
```powershell
gcloud scheduler jobs delete ankur-nightly-reset --location=$REGION --quiet
gcloud run jobs delete ankur-nightly --region=$REGION --quiet
gcloud run jobs delete ankur-setup --region=$REGION --quiet
gcloud run jobs delete ankur-usage --region=$REGION --quiet
gcloud run services delete $SERVICE --region=$REGION --quiet
gcloud sql instances delete $SQL_INSTANCE --quiet
```
The hackathon credit ends on 20 November, and the AI key stops working then (`docs/AI_BUDGET.md`).
