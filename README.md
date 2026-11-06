# Ankur Saathi (अंकुर साथी)

**AI-powered daily differentiated instruction for every FLN classroom.**
AI for Foundational Learning Hackathon 2026 · Challenge #1: Classroom Complexity

| | |
|---|---|
| **Live demo** | https://ankur-saathi-434145152242.asia-south1.run.app |
| **3-minute video** | https://youtu.be/fSvoh9tDXY4 |
| **Test accounts and a guided path** | [docs/DEMO_ACCESS.md](docs/DEMO_ACCESS.md) (the demo holds fictional data only) |
| **What is built, against the original proposal** | [docs/STATUS.md](docs/STATUS.md) |

> **Status: early piloting.** Ankur Saathi is a prototype and the code will change. Its skill ladder, its mapping to NIPUN Bharat outcomes, the content bank and the generated plans have not been reviewed or approved by government curriculum experts, and AI-generated plans can contain mistakes. It is not an official government product. See the Licence section at the end.

## What it does

One teacher, 60 or more children at three different levels, about 90 minutes. No tool helps her teach each group at its own level.

The teacher picks the day's skill on her phone. Ankur Saathi sorts the children into **Beginners, Progressors and Proficients** for that subject and, in about a minute, writes a complete **Dainik Yojana** (daily plan):

- a whole-class **anchor activity** (a short shared story or situation);
- three levelled **teaching scripts** (I Do, We Do, You Do) with talking points and quick "show me" questions to check understanding;
- three printable **worksheets** with a roll-number answer grid, and a line to copy on the board where there is no printer;
- a **rotation schedule** with transition scripts, peer monitors and activities for the groups working alone;
- a one-page **printed plan** and a **paper tick sheet**, for a teacher who records during the lesson without her phone in hand.

After class the **Review** has three steps: her own **first judgment** for each group (Advance, Re-teach or Not sure) before the AI reads anything; **the children's work**, checked by a photo of the worksheet, a quick tap per child, or a one-minute reading count; and a **final decision** with the day's evidence in front of her. That evidence shapes tomorrow's plan (a group that struggled is re-taught). A **class summary** gives the teacher the children to look at and the next step; a **mentor report** (roll numbers only, with talking points from fixed rules) gives a visiting officer something to talk through with her. **The AI proposes, the teacher decides.** The interface is Hindi first. Only the teacher uses a phone; no child uses a device.

## How AI is used

**Every external AI service and model, and where a key is needed:**

| Service | Model | Where in the code | What it does | Key |
|---|---|---|---|---|
| **Anthropic Claude** (text) | `claude-sonnet-5-5` (`CLAUDE_MODEL`) | `backend/app/services/plan_service.py`, `prompts/orchestrate.py` | Writes the daily plan as JSON inside the context the knowledge layers give it. One call per plan; a second call only when the first reply cannot be read; a short extra call to replace dropped "show me" questions. | `ANTHROPIC_API_KEY` |
| **Anthropic Claude** (vision) | `claude-sonnet-5-5` (`CLAUDE_VISION_MODEL`) | `backend/app/services/review_service.py`, `prompts/vision_analysis.py` | Reads photos of worksheets by roll number and classifies mistakes against the misconception list. The teacher has already recorded her own decision. | same key |
| **BAAI/bge-m3** (open weights, MIT licence), **offline only** | `BAAI/bge-m3` | `scripts/embed_content.py` | Run once on a laptop to compute vectors for the content bank and the skills. The vectors are stored in `db/seeds/content/embeddings.json` and loaded into PostgreSQL. **The running app never loads or calls a model for this.** | none |

**The only key the app needs is `ANTHROPIC_API_KEY`.** It is read on the server (Secret Manager in the cloud, `backend/.env` locally) and is never sent to the browser. There is no other AI service, no embedding API, no analytics and no third-party script. With `AI_ENABLED=false` the app makes no AI call at all and serves recorded sample plans for six skills (N0.1.1, N2.2.1, N2.3.2, L2.3.1, L2.5.1, L2.7.2).

**What stands between the model and the teacher** (data input, processing, guardrails, evaluation, output):

1. **Input is constrained.** Claude never writes from its own knowledge alone. Layer 1 (a deterministic curriculum database) says what to teach, in what order and what mistakes to expect; Layer 2 (a curated content bank) supplies the stories and templates to adapt.
2. **Code checks the output.** Every sum, answer key and number range is recomputed by code; "show me" questions with a wrong or guessable answer are dropped; unreadable model output is repaired or asked for again; worksheet numbers are repaired to the skill's range. In one real run these checks dropped 6 of 9 first-pass questions.
3. **The teacher decides.** Her Advance/Re-teach choice is recorded before any photo analysis; she can change any group's skill; a child's level changes only through an assessment, never from one day's result.
4. **Children's names never reach the AI.** Only roll numbers and handwritten answers do (a test fails the build if code that builds an AI request reads the names table). Photos are processed in memory and never stored.
5. **Spending is capped.** Every call is metered and limited per teacher, per school and overall ([docs/AI_BUDGET.md](docs/AI_BUDGET.md)).

## Run it locally

### What you need
- **Python 3.11** and **Node.js 20 or newer**
- **PostgreSQL 14 or newer** (the `psql` command must work). The optional `pgvector` extension is only needed for the semantic retrieval switch.
- **Git Bash** (on Windows) or any Linux/macOS shell, to run `db/setup.sh`
- An **Anthropic API key** to generate plans and read photos. Without one you can still sign in and browse everything else.

### 1. Get the code and install the backend
```bash
git clone https://github.com/rameshveluthedan-alt/ankur-saathi.git
cd ankur-saathi
python -m venv backend/venv
source backend/venv/bin/activate            # Windows PowerShell: backend\venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt openpyxl tzdata
```
(`openpyxl` reads Excel class registers; `tzdata` gives Windows the time-zone database.)

### 2. Create the database
```bash
bash db/setup.sh postgresql://postgres:PASSWORD@localhost/ankur_saathi
```
If your password contains characters such as `@`, `:`, `/`, `#` or `%`, write them percent-encoded in the URL (`@` becomes `%40`). The setup may print one line, `extension "vector" is not available`: that is the optional pgvector extension, and it is safe to ignore.

This creates the database, the schema and all seed data: 101 skills (53 numeracy, 48 Hindi literacy) from Balvatika to Grade 3, the prerequisite graph, the misconception list, the content bank, a representative Madhya Pradesh weekly plan and a fictional demo class. If `pgvector` is not installed it says so and continues; everything works except the optional semantic switch.

### 3. Configure
```bash
cp backend/.env.example backend/.env        # Windows: Copy-Item backend\.env.example backend\.env
```
Open `backend/.env` and set **`DB_PASSWORD`** and **`ANTHROPIC_API_KEY`**. Every other setting has a sensible default and is described in the file. **Never commit `.env`.**

### 4. Create the demo accounts
Run these from the repository root:
```bash
python scripts/auth_admin.py demo-setup --env-file backend/.env
python scripts/create_test_teachers.py create --count 5 --env-file backend/.env
python scripts/demo_progress.py seed --yes --env-file backend/.env
```
The first command prints the accounts (they are also in [docs/DEMO_ACCESS.md](docs/DEMO_ACCESS.md)); the last gives the demo class a few days of fictional evidence.

### 5. Start the backend
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```
Check it: http://localhost:8000/health (it answers `{"status": "ok", ...}`). On Windows, if you send the backend's output to a file, set `PYTHONIOENCODING=utf-8` first, or its start-up message cannot be written.

### 6. Start the app
In a second terminal:
```bash
cd pwa
npm install
npm run dev
```
Open http://localhost:5173 and sign in as the demo teacher: **MPT101 / 4826** (employee code and password). The login screen shows a card for each role: tap one to fill in its code and password.

**To run the built app from the backend alone** (what the cloud does): `cd pwa && npm run build`, then from `backend/` run `uvicorn app.production:app --port 8000` and open http://localhost:8000.

### Optional: semantic retrieval
Where the curated anchors have nothing for a skill, the app can choose the anchor nearest in meaning. It is **off by default** (`SEMANTIC_RETRIEVAL=off`) and needs no key and no model at run time. Evaluated on 31 October: it recovers the curated anchor first 75% of the time (random: 25%), but a blind review of the 9 skills where it differs from today's pick was split (4 for semantic, 5 for today's), so it is **switched off in the submitted version**. See [docs/SEMANTIC_RETRIEVAL.md](docs/SEMANTIC_RETRIEVAL.md).

## Tests
```bash
python scripts/run_tests.py --env-file backend/.env          # every backend suite: return code, checks, tracebacks
python scripts/run_tests.py --env-file backend/.env --pwa    # and the front-end tests (run `npm install` in pwa first)
```
The suites use a fake AI, so keep `AI_ENABLED` at its default (`true`) in `backend/.env` while you run them. The backend suites need the database from step 2 and the backend's packages (run it with the virtual environment from step 1 active; if you forget, the runner uses `backend/venv` by itself, or says exactly what to activate or install). When a suite fails it prints the failing lines, grouped by reason. They cover the plan rules, the check-for-understanding validator, the Hindi style rules, worksheet layout, sign-in and PIN rules, the AI spending caps, the guarantee that names never reach the AI, the skill bridges, the semantic retrieval and the production server. A suite that needs `pgvector` says **SKIPPED** and why when it is missing. Plans have also been generated with the real model for 27 of the 101 skills so far (`docs/batch/batch_results.csv`); the run over all 101 is described in `docs/BATCH_AND_COVERAGE.md` and is still to do.

Before committing: `python scripts/precommit_check.py` (refuses secrets and `.env` files). Before the final submission: `python scripts/submission_check.py --final`.

## Deploy
Google Cloud Run (Mumbai, `asia-south1`) with Cloud SQL for PostgreSQL, Secret Manager for the keys and a nightly job that resets the demo. Every step is in [deploy/DEPLOY.md](deploy/DEPLOY.md); the container is built from the [Dockerfile](Dockerfile) and configured by [deploy/cloudrun-env.yaml](deploy/cloudrun-env.yaml).

## How it is built

```
Teacher's phone: installable web app (React + Vite, service worker)
        │  HTTPS, JSON
        ▼
FastAPI backend ── sign-in, rate limits, AI spending caps
        │
        ├── Layer 1: curriculum knowledge base (PostgreSQL, deterministic lookup)
        │     skills and prerequisites · misconception list · A / PA / NA criteria · state weekly plan
        ├── Layer 2: curated content bank (anchors, passages, intervention templates, materials)
        │     curated match first (exact, related, topic area, loose); optional semantic tier on pgvector
        ▼
Layer 3: Claude, constrained by Layer 1 + Layer 2
        ▼
Code checks: sums · answer keys · number ranges · readable JSON · "show me" questions
        ▼
Dainik Yojana → the app, and printable worksheets
```

How it is deployed:

```mermaid
flowchart LR
  phone["Teacher's phone<br/>installable web app<br/>(a service worker keeps today's plan)"] -- HTTPS --> run["Cloud Run, Mumbai<br/>FastAPI backend"]
  run --> sql[("Cloud SQL for PostgreSQL<br/>knowledge base, content bank,<br/>classes, evidence, plans")]
  run -- "roll numbers and answers,<br/>never names" --> claude["Anthropic Claude API<br/>plans (text), photos (vision)"]
  secrets["Secret Manager<br/>Claude key, database password"] -.-> run
  sched["Cloud Scheduler"] --> job["Cloud Run job, nightly<br/>demo reset, embeddings load"] --> sql
  laptop["A laptop, once<br/>BGE-M3 writes the vectors file"] -.-> job
```

```
backend/app/      FastAPI app: api/ (routes, sign-in), services/ (plan, review, progress, register, AI budget...), core/ (settings, database)
backend/tests/    the backend test suites (python tests/test_X.py --env-file .env)
prompts/          the prompts and rules sent to Claude, the Hindi style rules, the show-me question rules
db/schema/        the database, 01 to 13 (12 = embeddings, optional; 13 = the school's consent, created by the app on first use)
db/seeds/         curriculum, misconceptions, content bank, state plan, demo class, recorded sample plans
pwa/src/          the app: screens (Make plan, Today's plan, Review, Class progress, Profile, class register, printable pages), components, services
scripts/          operator tools: demo accounts, test teachers, nightly reset, AI usage, bridges, embeddings, tests, checks
deploy/           Cloud Run guide, environment template, first-time setup
docs/             one note per design topic (below)
```

**Design decisions**
1. **Three layers.** Structured lookup for what is certain (curriculum, prerequisites, mistakes), curated content for what must be vetted (stories, passages), generation for what must adapt (today's numbers, talking points).
2. **Grouping is per subject.** A child can be a Beginner in numeracy and a Proficient in reading.
3. **Levels change only through an assessment.** Daily evidence changes the plan and raises a "consider re-assessing" flag (docs/LEVELS.md).
4. **Roll numbers, not names, go to the AI.** Names are kept in a separate teacher-only table for the teacher's own screens.
5. **The AI proposes, the teacher decides**, and mistakes are matched to a fixed misconception list, not invented.
6. **Code verifies the AI**, instead of trusting it.

## Privacy and safety
- No child's name is ever sent to the AI; photos are read in memory and never stored; there are no trackers, advertisements or third-party scripts.
- The demo holds **fictional data only**; its passwords are public on purpose.
- Secrets live only in `backend/.env` (git-ignored) or in Secret Manager. `scripts/precommit_check.py` and `scripts/submission_check.py` fail on a key, a password or a `.env` file in the repository.
- What is not done yet (for example consent from each parent: the app records the school's confirmation only) is listed honestly in [docs/PRIVACY.md](docs/PRIVACY.md) and [docs/STATUS.md](docs/STATUS.md).

## Documentation
| | |
|---|---|
| [docs/STATUS.md](docs/STATUS.md) | what is built, against the proposal |
| [docs/EVALUATOR_GUIDE.md](docs/EVALUATOR_GUIDE.md) | one page for evaluators: sign-ins, five sample inputs, the frozen version |
| [docs/DEMO_ACCESS.md](docs/DEMO_ACCESS.md) | test accounts and a guided path |
| [docs/ROADMAP.md](docs/ROADMAP.md) | roles (state, district, school), onboarding and integration: a design sketch |
| [docs/OFFLINE.md](docs/OFFLINE.md) | what works with no network, how the app knows, slow networks, privacy of the copies |
| [docs/AI_BUDGET.md](docs/AI_BUDGET.md) | the AI spending limits |
| [docs/AUTH.md](docs/AUTH.md) | sign-in: employee codes, passwords, the school leader |
| [docs/PRIVACY.md](docs/PRIVACY.md) | where each kind of data goes |
| [docs/LEVELS.md](docs/LEVELS.md) | what changes a child's group |
| [docs/REGISTER.md](docs/REGISTER.md) | enrolling a class |
| [docs/RETEACH.md](docs/RETEACH.md), [docs/GROUP_SKILLS.md](docs/GROUP_SKILLS.md), [docs/BRIDGES.md](docs/BRIDGES.md) | re-teaching, per-group skills, curated skill bridges |
| [docs/CFU.md](docs/CFU.md) | the "show me" questions |
| [docs/WORKSHEETS.md](docs/WORKSHEETS.md), [docs/HINDI_STYLE.md](docs/HINDI_STYLE.md) | worksheets, Hindi style |
| [docs/SEMANTIC_RETRIEVAL.md](docs/SEMANTIC_RETRIEVAL.md) | the optional semantic retrieval |
| [docs/MODEL_JSON.md](docs/MODEL_JSON.md), [docs/SCORING.md](docs/SCORING.md), [docs/SAMPLING.md](docs/SAMPLING.md) | reading model output, scoring, photo sampling |
| [docs/VISION_PHOTO_TEST.md](docs/VISION_PHOTO_TEST.md) | how to test photo analysis on real worksheets |
| [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md) | what we know is not right yet, and why |
| [docs/skill_ladder.csv](docs/skill_ladder.csv) | the whole skill ladder on one sheet, for review (made by `scripts/export_skill_ladder.py`) |
| [docs/LAB_UI_HANDOVER.md](docs/LAB_UI_HANDOVER.md) | the teacher-UI review rounds, change by change, with the tests and the open decisions |

## Terms and abbreviations
| Term | Meaning |
|---|---|
| **FLN** | foundational literacy and numeracy: reading with understanding and basic arithmetic in the early grades |
| **NIPUN Bharat** | the national mission for FLN; its coded learning outcomes are what our skills are mapped to |
| **NCF-FS** | the National Curriculum Framework for the Foundational Stage (2022), for ages 3 to 8 |
| **Lakshya** | a learning target: NIPUN's word for a skill |
| **Beginner / Progressor / Proficient** | the three levels the children are grouped into, per subject |
| **A / PA / NA** | Achieved / Partly achieved / Not achieved: NIPUN's way of recording a skill |
| **Anchor activity** | the whole-class opening story or activity of a plan |
| **I Do / We Do / You Do** | the teacher shows; the group does it together; the child does it alone |
| **TLM** | teaching-learning material, for example bundling sticks |
| **Layer 1 / 2 / 3** | the knowledge base; the content bank; and the AI, which writes the plan inside the first two |
| **R1 / R2** | first-language and second-language literacy |
| **BRC, CRC, BAC, MLO** | block and cluster academic support officers; the titles vary by state |
| **Skill id** | N or L (numeracy or Hindi literacy), then the grade and the skill's place in the ladder: N2.3.2 is a Grade 2 numeracy skill |
| **Roll number** | the school's own number for a child, and the only identifier sent to the AI |
| **PWA** | progressive web app: a web app that installs from a link and keeps what it has loaded for offline use |
| **DPDP Act** | India's Digital Personal Data Protection Act, 2023 |
| **CWPM** | correct words per minute, the measure of reading fluency |
| **Embedding, pgvector** | a list of numbers that stands for the meaning of a text; the PostgreSQL extension that compares them |
| **BGE-M3** | the open-weights model that makes the embeddings, run offline on a laptop |
| **CSV, JSON, API** | a file a spreadsheet opens; a plain-text data format; the way one program calls another |

## Team Beej
Beej (बीज) means seed: the team behind Ankur (अंकुर), the sprout.

- **Vaishnavi**: Education Domain Lead (curriculum knowledge base, misconceptions, Hindi review)
- **Ramesh**: AI and Engineering Lead (orchestration, Claude integration)
- **Arjun**: Data and Architecture Lead (backend, database, infrastructure)

## Licence

The code is released under the MIT Licence (see `LICENSE`). Any third-party material keeps its own licence.

Content: the skill ladder, its mapping to NIPUN Bharat outcomes (proposed with AI help, awaiting expert confirmation), the content bank, and the generated plans and worksheets are work in progress. A teacher should review every plan before use.

Data: the data in the demonstration is fictional. Do not use the software with real children's data without a data-protection review.