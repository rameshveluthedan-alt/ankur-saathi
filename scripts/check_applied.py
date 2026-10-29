"""
Which of the recent bundles are in this working copy? Prints OK or MISSING for each, with the bundle that holds it, and what to do about it.

    python scripts\\check_applied.py

It looks for a marker in each file (a function name or a sentence that every later version of the file still contains), so a bundle that was extracted, and then overwritten by an OLDER bundle, shows up as MISSING.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

# (bundle, what it is, file, marker or None = the file must exist)
CHECKS = [
    ("v27l", "tolerant JSON and one retry", "backend/app/services/model_json.py", None),
    ("v27s", "the CFU top-up call", "backend/app/services/plan_service.py", "async def topup_cfu"),
    ("v27t", "spot-error verdicts", "backend/app/services/cfu.py", "def _verdict"),
    ("v28a", "each group's skill: the proposal", "backend/app/services/group_skills.py", "async def propose"),
    ("v28b", "the re-teach as the group's main block", "prompts/orchestrate.py", "RETEACH_MAIN_RULES"),
    ("v28b", "the re-teach as the group's main block", "backend/app/services/plan_service.py", "def stamp_reteach_main"),
    ("v28c", "the teachers' review: two show-me questions per group", "backend/app/services/cfu.py", "MIN_ITEMS, MAX_ITEMS = 2, 2"),
    ("v28c", "the teachers' review: the routine on the lesson screen", "pwa/src/screens/YojanaScreen.jsx", "20 सेकंड"),
    ("v28d", "try_reteach.py reads backend/.env", "scripts/try_reteach.py", "os.chdir"),
    ("v28e", "a wrong answer that is a right answer in the lesson", "backend/app/services/cfu.py", "def _lesson_results"),
    ("v28e", "no kit-limit sentence in the script", "prompts/orchestrate.py", "NEVER explain the kit size"),
    ("v28f", "vague 'listen for' removed", "backend/app/services/cfu.py", "def _without_vague_listen"),
    ("v28f", "no person who 'did' something", "prompts/cfu_prompt.py", "No PERSON at all"),
    ("v28g", "the Plan screen's per-group panel", "pwa/src/screens/PlanScreen.jsx", "GroupSkillsPanel"),
    ("v28g", "the ladder endpoint", "backend/app/api/routes.py", "/plan/ladder/"),
    ("v28h", "the app's recommendation from the evidence", "backend/app/services/group_skills.py", "def recommend"),
    ("v28h", "the recommendation on the panel", "pwa/src/components/GroupSkillsPanel.jsx", "recommendation"),
    ("v28i", "which skills a group may take", "backend/app/services/group_skills.py", "async def allowed_skills"),
    ("v28i", "a re-teach is the same skill as yesterday", "backend/app/services/plan_service.py", "check_reteach_same_skill"),
    ("v28i", "the panel offers only sensible skills", "pwa/src/components/GroupSkillsPanel.jsx", "skillChoices"),
    ("v28j", "each group's skill at the top right", "pwa/src/services/planSummary.js", None),
    ("v28j", "each group's skill at the top right", "pwa/src/screens/YojanaScreen.jsx", "PlanGroupSkills"),
    ("v28k", "the re-teach block's label", "pwa/src/services/reteachInfo.js", None),
    ("v28k", "the re-teach block's label", "pwa/src/screens/YojanaScreen.jsx", "ReteachNote"),
    ("v28o", "the demo seeds yesterday's plan", "scripts/demo_progress.py", "def seed_yesterday_plan"),
    ("v28o", "the log lists what the model wrote", "backend/app/services/cfu.py", "_STAMPED_BY_CODE"),
    ("v28o", "the runbook updates the nightly job after a redeploy", "deploy/DEPLOY.md", "jobs update ankur-nightly"),
    ("v28q", "a group is never ahead of / behind the day's skill (server)", "backend/app/services/group_skills.py", "def fits_day"),
    ("v28q", "a group is never ahead of / behind the day's skill (screen)", "pwa/src/services/groupSkills.js", "fitsDay"),
    ("v28r", "yesterday's re-teach is remembered (server)", "backend/app/services/group_skills.py", "def reteached_groups"),
    ("v28r", "yesterday's re-teach is shown (screen)", "pwa/src/components/GroupSkillsPanel.jsx", "previous-reteach"),
    ("v28r", "status lists the stored plans", "scripts/demo_progress.py", "Plans stored for the last 14 days"),
    ("v28s", "the group panel is a drawer in the bottom bar", "pwa/src/components/GroupSkillsDrawer.jsx", None),
    ("v28s", "the group panel is a drawer in the bottom bar", "pwa/src/screens/PlanScreen.jsx", "GroupSkillsDrawer"),
    ("v28s", "the real-screen test", "pwa/tests/plan_screen.dom.test.mjs", None),
    ("v28t", "tapping the tab you are on takes that screen back to its start", "pwa/src/services/tabs.js", None),
    ("v28t", "tapping the tab you are on takes that screen back to its start", "pwa/src/App.jsx", "tabTap"),
    ("v28t", "the Plan screen goes back to choosing a skill", "pwa/src/screens/PlanScreen.jsx", "TAB_RESELECT_EVENT"),
    ("v28u", "the re-teach box is the decision and the skill follows it", "pwa/src/services/groupSkills.js", "export function toggleReteach"),
    ("v28u", "the re-teach box is the decision and the skill follows it", "pwa/src/components/GroupSkillsPanel.jsx", "toggleReteach"),
    ("v30b", "the evaluator guide: a time-based opening, Three ways to record (observed, photo, reading-aloud) and a two-day flow", "docs/EVALUATOR_GUIDE.md", "Three ways to record"),
    ("v30a", "sign in by employee code and password: the new login screen with a card for each role", "pwa/src/screens/LoginScreen.jsx", "employee-code"),
    ("v30a", "the school leader confirms the school's consent once, at her first sign-in", "pwa/src/screens/ConsentGate.jsx", "consent-gate"),
    ("v30a", "the leader's Profile: accounts by employee code, no join code", "pwa/src/screens/AccountScreen.jsx", "teacher-code"),
    ("v30a", "employee codes and the 6 to 12 character password rules", "backend/app/services/auth_service.py", "def normalise_code"),
    ("v30a", "self-registration is closed unless a practice database turns it on", "backend/app/api/auth_routes.py", "registration_closed"),
    ("v30a", "a registration accepts an employee code", "backend/app/services/register_service.py", "Enter an employee code"),
    ("v30a", "the demo accounts are named in ONE place", "scripts/demo_accounts.py", "DEMO_TEACHER"),
    ("v30a", "the migration to employee codes, scoped to the demo school and the old test schools", "scripts/migrate_to_employee_codes.py", "OLD_TEST_SCHOOL_PREFIX"),
    ("v30a", "the nightly job converts the accounts first", "scripts/nightly_reset.py", "migrate_to_employee_codes.py"),
    ("v30a", "7-day sessions and registration closed in the cloud settings", "deploy/cloudrun-env.yaml", 'SESSION_HOURS: "168"'),
    ("v30a", "the demo teacher of a fresh database has its employee code", "db/seeds/classroom/01_profile.sql", "MPT101"),
    ("v30a", "the sign-in document describes employee codes and the school leader", "docs/AUTH.md", "employee code"),
    ("v30a", "the accounts test: both old layouts convert and no other school's account is touched", "backend/tests/test_test_teachers.py", "MPT150"),
    ("v30a", "the login screen is tested in a simulated browser", "pwa/tests/login.dom.test.mjs", "employee-code"),
    ("v29z", "how the skills relate to NCF-FS (2022), proposed by AI and awaiting an educator", "docs/NCF_FS_COMPARISON.md", "not yet confirmed by an educator"),
    ("v29z", "the coverage document says the NIPUN alignment is AI-proposed, not confirmed", "docs/COVERAGE.md", "proposed by AI and not yet confirmed by an educator"),
    ("v29y", "the login screen lists every demo role (the test school admin until v30a, which has no separate admin)", "pwa/src/screens/LoginScreen.jsx", "MPA101"),
    ("v29y", "every published single-number account is on the login screen (a test compares it with the access guide)", "pwa/tests/demo_accounts.test.mjs", None),
    ("v29x", "the school's consent confirmation: a table created on first use, kept with the exact wording", "db/schema/13_school_consent.sql", "CREATE TABLE IF NOT EXISTS school_consents"),
    ("v29x", "a new school is created only with the confirmation, and the record is kept in the same transaction", "backend/app/services/register_service.py", "ConsentRequired"),
    ("v29x", "the wording, the record, the admin's confirmation and the demo statement", "backend/app/services/auth_service.py", "CONSENT_VERSION"),
    ("v29x", "the admin route to confirm consent", "backend/app/api/auth_routes.py", "/admin/school/consent"),
    ("v29x", "the consent wording, the same as the server's (a test compares them)", "pwa/src/services/consent.js", "CONSENT"),
    ("v29x", "the school's consent is confirmed by its leader (on the sign-up form until v30a, at her first sign-in since)", "pwa/src/screens/ConsentGate.jsx", "consent-gate"),
    ("v29x", "the admin's Profile shows the confirmation or a button to give it", "pwa/src/screens/AccountScreen.jsx", "consent-row"),
    ("v29x", "the consent rules are tested (backend, screens)", "backend/tests/test_consent.py", None),
    ("v29x", "the consent screens are tested in a simulated browser", "pwa/tests/consent.dom.test.mjs", None),
    ("v29w", "the gate prints its results in aligned columns, however long a key is", "scripts/submission_check.py", "def format_lines"),
    ("v29w", "the evaluator guide has the repository address (GitHub)", "docs/EVALUATOR_GUIDE.md", "github.com/rameshveluthedan-alt/ankur-saathi"),
    ("v29v", "the Hindi style check flags the old Tens | Ones box word only in a place-value sentence (खाना = food, खाने = to eat)", "backend/tests/test_hindi_style.py", "def frame_left"),
    ("v29u", "EVERY recorded plan must be read and signed, with warnings or without (the tool and the gate)", "scripts/review_sample_plans.py", "not yet read"),
    ("v29t", "the review page carries a checklist for the reader (Hindi, answers, the skill, the story, no names, the warnings)", "scripts/review_sample_plans.py", "What to check"),
    ("v29s", "a recorded plan is read as a page (as a teacher will see it) and signed by a tool, not by hand", "scripts/review_sample_plans.py", "def as_teacher_sees"),
    ("v29s", "the reading and signing of recorded plans is tested (nothing left out of the page)", "backend/tests/test_review_sample_plans.py", None),
    ("v29r", "every generated plan is also written to docs/batch/plans (a paid-for plan is never lost)", "scripts/batch_generate.py", "raw_plan_record"),
    ("v29r", "the raw record of a plan, and a fake-model plan is refused by the gate", "backend/app/services/ai_budget.py", "def raw_plan_record"),
    ("v29q", "a recorded plan can be kept WITH its warnings (--accept-warnings); the notes never reach a teacher", "backend/app/services/ai_budget.py", "def mark_for_review"),
    ("v29q", "the batch tool has --accept-warnings", "scripts/batch_generate.py", "--accept-warnings"),
    ("v29q", "a recorded plan kept with warnings must be signed by its reader (the gate)", "scripts/submission_check.py", "sample_plans_review"),
    ("v29q", "the recorded-plan rules are tested", "backend/tests/test_sample_plans.py", None),
    ("v29p", "recording a sample plan: one skill per run, the value attached with '=', and a PowerShell loop", "db/seeds/sample_plans/README.md", "foreach ($s in"),
    ("v29o", "reading aloud is a stopwatch, not a microphone: the screens say no audio is recorded", "pwa/src/screens/ReviewScreen.jsx", "कोई आवाज़ रिकॉर्ड नहीं होती"),
    ("v29o", "the app cannot record sound (a code check)", "pwa/tests/no_audio.test.mjs", None),
    ("v29o", "daily review by observation, voice only for the periodic assessments (a design decision)", "docs/ROADMAP.md", "Assessment modes: daily and periodic"),
    ("v29o", "the gate compares the recorded plans in the folder with the ones the guide names", "scripts/submission_check.py", "sample_plans_extra"),
    ("v29o", "the evaluator guide: observation, reading aloud and Hindi plans among the five sample inputs", "docs/EVALUATOR_GUIDE.md", "No audio is recorded"),
    ("v29n", "the Hindi style check flags 'को दो' only at the end of a clause: दो before a noun is the number two", "backend/tests/test_hindi_style.py", "GIVE_LEFT"),
    ("v29n", "the batch tool is shown with the right options and the recorded-sample choice is explained", "db/seeds/sample_plans/README.md", "there is no --env-file option"),
    ("v29m", "the production test writes its fake files byte for byte (Windows would add carriage returns)", "backend/tests/test_production_app.py", 'newline=""'),
    ("v29m", "the link case of the runner test skips where links are not allowed (Windows without Developer Mode)", "backend/tests/test_run_tests.py", "can_link"),
    ("v29l", "the test runner checks its Python, switches to backend/venv by itself, and explains failures grouped by reason", "scripts/run_tests.py", "def choose_interpreter"),
    ("v29l", "the runner's choice of Python is tested (incl. a virtual environment that is a link)", "backend/tests/test_run_tests.py", "LINK to the system one"),
    ("v29k", "the app knows when it is offline: a probe no cache answers, the browser's flag, a failed request", "pwa/src/services/network.js", "export async function probe"),
    ("v29k", "a missing network becomes one clear sentence; the offline copies are prepared and removed at sign-in and sign-out", "pwa/src/services/api.js", "prepareOfflineCopy"),
    ("v29k", "the private offline copies never outlive the signed-in person", "pwa/src/services/offlineCache.js", "PRIVATE_CACHES"),
    ("v29k", "the offline notice", "pwa/src/components/OfflineBanner.jsx", "data-testid=\"offline-banner\""),
    ("v29k", "the service worker keeps worksheets, answers from its copy after 6 s, and the skill-list rule comes first", "pwa/vite.config.js", "worksheet-cache"),
    ("v29k", "a smaller photo on a phone with 2 GB of memory or less", "pwa/src/utils/imageCompress.js", "export function compressionSettings"),
    ("v29k", "the server compresses what it sends", "backend/app/production.py", "GZipMiddleware, minimum_size"),
    ("v29k", "the offline behaviour is tested (no browser)", "pwa/tests/offline.test.mjs", None),
    ("v29k", "the offline behaviour is documented", "docs/OFFLINE.md", "How the app knows it is offline"),
    ("v29j", "the evaluator guide: sign-ins, five sample inputs, the frozen version (freeze-day markers)", "docs/EVALUATOR_GUIDE.md", "FILL ON FREEZE"),
    ("v29j", "the roadmap: roles above the school, onboarding, data rules (a design sketch)", "docs/ROADMAP.md", "closer to the child"),
    ("v29j", "the gate checks the evaluator guide and refuses --final while freeze-day markers remain", "scripts/submission_check.py", "guide_placeholders"),
    ("v29i", "the test accounts: ONE test school, its admin and plain teachers (`normalise` converts the old layout)", "scripts/create_test_teachers.py", "def cmd_normalise"),
    ("v29i", "the nightly job puts the test accounts in order (a step that cannot stop the reset)", "scripts/nightly_reset.py", "create_test_teachers.py"),
    ("v29i", "the test accounts are tested (old layout converted, nothing else touched)", "backend/tests/test_test_teachers.py", None),
    ("v29i", "the access guide: the school leader and what she can do today (it described the test school admin until v30a)", "docs/DEMO_ACCESS.md", "School leader"),
    ("v29i", "the usage job is created with arguments that survive PowerShell", "deploy/DEPLOY.md", "^@^/srv/scripts/ai_usage.py@status"),
    ("v29h", "the README is the real one: run it locally, every AI service, tests, deploy", "README.md", "How AI is used"),
    ("v29h", "the status document: what is built, against the proposal", "docs/STATUS.md", None),
    ("v29h", "the sample environment file lists every setting the code reads", "backend/.env.example", "SEMANTIC_RETRIEVAL"),
    ("v29h", "the model defaults match the demo (claude-sonnet-5-5, 24000 tokens)", "backend/app/core/config.py", 'claude_model: str = "claude-sonnet-5-5"'),
    ("v29h", "a key that is only in .env is not reported missing at startup", "backend/app/production.py", "_s.anthropic_api_key"),
    ("v29h", "the database setup creates the database through the connection you give, and fails loudly", "db/setup.sh", "ADMIN_URL"),
    ("v29h", "scripts and test helpers find the .env the app reads", "scripts/anchor_common.py", "def default_env_file"),
    ("v29h", "the test runner (return code, tracebacks, skips)", "scripts/run_tests.py", "def resolve_env_file"),
    ("v29h", "the submission gate for the source-code deliverable", "scripts/submission_check.py", "def run_checks"),
    ("v29h", "the gate is tested", "backend/tests/test_submission_check.py", None),
    ("v29h", "the database helper is tested", "backend/tests/test_db_params.py", None),
    ("v29h", "the runner is tested", "backend/tests/test_run_tests.py", None),
    ("v29h", "the privacy notes cover teachers' sign-in: employee codes and passwords (they covered phone numbers and PINs until v30a)", "docs/PRIVACY.md", "Teachers' employee codes and passwords"),
    ("v29g", "semantic retrieval: the migration (vector 1024, the skills column)", "db/schema/12_embeddings_1024.sql", None),
    ("v29g", "semantic retrieval: the tier, the switch and the fallbacks", "prompts/orchestrate.py", "def semantic_enabled"),
    ("v29g", "the embeddings are computed OFFLINE with an open-weights model (BAAI/bge-m3), into one file", "scripts/embed_content.py", "BAAI/bge-m3"),
    ("v29g", "the loader: no model, only fresh vectors, safe without pgvector", "scripts/load_embeddings.py", "def apply"),
    ("v29g", "the texts and fingerprints (an anchor is embedded from its own content only)", "scripts/embedding_texts.py", "def anchor_text(row: dict)"),
    ("v29g", "the evidence script (recovery test against a random baseline, blind A/B, from the file)", "scripts/eval_semantic.py", "def vectors_from_file"),
    ("v29g", "the nightly job loads the embeddings", "scripts/nightly_reset.py", "load_embeddings.py"),
    ("v29g", "the semantic retrieval is tested", "backend/tests/test_semantic_retrieval.py", None),
    ("v29g", "semantic retrieval is documented", "docs/SEMANTIC_RETRIEVAL.md", None),
    ("v29g", "the old OpenAI embeddings script is a pointer only", "scripts/populate_embeddings.py", "REPLACED"),
    ("v29g", "how many Generates needed a second call", "scripts/plan_retries.py", "def find_retries"),
    ("v29f", "one closing bracket too many is removed instead of asking the model again", "backend/app/services/model_json.py", "def repair_stray_closers"),
    ("v29f", "the stray-bracket repair is tested (it never turns a reply into a different plan)", "backend/tests/test_model_json_closers.py", None),
    ("v29e", "a show-me cannot be two wrong right-or-wrong lines (a child guesses)", "backend/app/services/cfu.py", "def _is_wrong_line"),
    ("v29e", "...and the CFU rules ask for a question the child works out", "prompts/cfu_prompt.py", "WORK OUT an answer"),
    ("v29e", "the guessable-question rule is tested", "backend/tests/test_cfu_guessable.py", None),
    ("v29d", "a two-digit addition skill never reaches 100: the show-me rules", "backend/app/services/cfu.py", "max_result"),
    ("v29d", "...and the worksheet repair replaces a total of 100 or more", "backend/app/services/plan_service.py", "three-digit numbers are a later"),
    ("v29d", "the number range note in the plan prompt", "prompts/orchestrate.py", "def range_note"),
    ("v29d", "the I Do uses the SAME sum for the wrong and the right working", "prompts/orchestrate.py", "do the SAME sum again correctly"),
    ("v29d", "the show-me avoids results already on the board", "prompts/cfu_prompt.py", "already written on the board"),
    ("v29d", "the two-digit limit is tested", "backend/tests/test_two_digit_limit.py", None),
    ("v29c", "two questions of one group never share a right answer", "backend/app/services/cfu.py", "def right_answer"),
    ("v29c", "the top-up is told which answers are taken", "prompts/cfu_prompt.py", "The right answers of the questions above"),
    ("v29c", "the You Do points to the worksheet, and no sum is repeated", "prompts/orchestrate.py", "do NOT write problems of your own"),
    ("v29c", "the board problems are separate lines", "pwa/src/components/BoardWork.jsx", "gridTemplateColumns"),
    ("v29c", "the answers check is tested", "backend/tests/test_cfu_answers.py", None),
    ("v29b", "the listen-for wrong answers are computed and checked by code", "backend/app/services/cfu.py", "def verified_listen"),
    ("v29b", "the listen-for check is tested", "backend/tests/test_cfu_listen_for.py", None),
    ("v29a", "the carry strip is a tab above the tens column (no empty box; the other headers grow)", "backend/app/templates/worksheet.html", "pv-header-tall"),
    ("v29a", "the board-work line under the You Do", "pwa/src/screens/YojanaScreen.jsx", "BoardWork"),
    ("v29a", "the board-work line reads the worksheet itself", "pwa/src/services/boardWork.js", "export function boardProblems"),
    ("v28z", "yesterday's skill is offered only as a re-teach, plain only while it is the current choice", "pwa/src/services/groupSkills.js", "export function visibleChoices"),
    ("v28z", "the model is told the truth when a group is on yesterday's skill as a normal lesson", "prompts/orchestrate.py", "NORMAL lesson"),
    ("v28y", "one dropdown holds both decisions (skill and re-teach)", "pwa/src/services/groupSkills.js", "export function chooseOption"),
    ("v28y", "one dropdown holds both decisions (skill and re-teach)", "pwa/src/components/GroupSkillsPanel.jsx", "restore-suggestion"),
    ("v28x", "curated skill bridges: the loader", "scripts/load_bridges.py", None),
    ("v28x", "curated skill bridges: the app consults them first", "backend/app/services/group_skills.py", "async def curated_pick"),
    ("v28x", "curated skill bridges: the table", "db/schema/11_skill_bridges.sql", None),
    ("v28x", "curated skill bridges: the nightly job loads them without stopping the reset", "scripts/nightly_reset.py", "fatal=False"),
    ("v28x", "curated skill bridges: the starter proposals", "db/seeds/content/07_skill_bridges.starter.csv", None),
    ("v28l", "the front-end tests run on Windows", "pwa/tests/group_skills.test.mjs", "pathToFileURL"),
    ("v28l", "the front-end tests run on Windows", "pwa/tests/plan_summary.test.mjs", "pathToFileURL"),
    ("v28l", "the front-end tests run on Windows", "pwa/tests/reteach_note.test.mjs", "pathToFileURL"),
]


def kind_of(bundle, rel):
    """older: a bundle before the v28 series. current: any file of the v28 series (the one package v28p-current holds the current version of all of them)."""
    return "older" if bundle.startswith("v27") else "current"


VERSION = "v30b, 28 Oct: lists the bundles v27l to v30b; v30b-current = v30a-current + the guide section Three ways to record and the two-day flow"


def main():
    status, why, kinds = {}, {}, {}
    for bundle, what, rel, marker in CHECKS:
        p = ROOT / rel
        if not p.exists():
            ok, note = False, f"{rel}: the file is not there"
        elif marker is None:
            ok, note = True, ""
        else:
            ok = marker in p.read_text(encoding="utf-8", errors="replace")
            note = "" if ok else f"{rel}: does not contain '{marker}' ({what})"
        status[bundle] = status.get(bundle, True) and ok
        if not ok:
            why.setdefault(bundle, []).append(note)
            kinds.setdefault(kind_of(bundle, rel), set()).add(bundle)
    print(f"check_applied.py ({VERSION})")
    print(f"Working copy: {ROOT}\n")
    for bundle in sorted(status):
        print(f"  {bundle:<5} {'OK' if status[bundle] else 'MISSING'}")
        for note in why.get(bundle, []):
            print(f"          - {note}")
    # the packages: v28p-current holds the current version of every file of the v28 series, so it is 'in' when every v28 row is OK
    series = [b for b in status if b.startswith("v28")]
    package_ok = all(status[b] for b in series)
    print(f"\n  PACKAGE v30b-current (every file of v28a to v30b, current):  {'OK' if package_ok else 'BEHIND'}")
    print()
    if not kinds:
        print("Everything listed is in this working copy.")
        return 0
    if "current" in kinds:
        print("Something of the v28 series is behind (or was put back by an older bundle). Apply v30b-current.tar.gz ONCE: it holds the current version of every file of the series, so the order does not matter.")
        print("    tar -xzf <downloads>\\v30b-current.tar.gz -C <this folder>")
        print("  and do NOT extract v28a to v30a afterwards: each holds older copies of some of the same files and would put them back.")
    if "older" in kinds:
        print(f"Older bundles missing: {', '.join(sorted(kinds['older']))}. Apply each, oldest first, with  tar -xzf <downloads>\\<bundle>.tar.gz -C <this folder>")
    print("Run this check again afterwards: python scripts\\check_applied.py")
    return 1


if __name__ == "__main__":
    sys.exit(main())
