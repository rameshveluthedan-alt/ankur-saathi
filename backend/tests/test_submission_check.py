"""
The gate for the Stage 2 source-code deliverable must catch what it is meant to catch, and stay quiet about what is fine.

    cd backend && python tests/test_submission_check.py        (no database, no network; the git checks need `git` and are skipped without it)

Each case builds a small throwaway repository, plants ONE defect, and checks that exactly that check fails. The last case runs the checker on THIS repository,
so the gate is part of the test suite: a leaked key, a missing setting in .env.example or a stale README line fails the build.
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path[:0] = [str(ROOT / "scripts")]
import submission_check as sc

failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


STATUS_ROWS = "\n".join(f"| ✅ | promise number {i} | where it stands |" for i in range(45))
GOOD = {
    "README.md": """# Demo app
Live demo: https://demo-123.asia-south1.run.app
## How AI is used
Anthropic Claude writes the plan; `ANTHROPIC_API_KEY` is the only key.
## Run it locally
Copy backend/.env.example to backend/.env. See [status](docs/STATUS.md).
## Tests
python scripts/run_tests.py
## Deploy
See [deploy/DEPLOY.md](deploy/DEPLOY.md).
""",
    "backend/.env.example": "DEBUG=true\nDATABASE_URL=\nCLAUDE_MODEL=claude-sonnet-5-5\nCLAUDE_VISION_MODEL=claude-sonnet-5-5\nCLAUDE_MAX_TOKENS=24000\n# SEMANTIC_RETRIEVAL=off\n",
    "backend/app/core/config.py": "class Settings(BaseSettings):\n    debug: bool = True\n    database_url: str = \"\"\n    claude_model: str = \"claude-sonnet-5-5\"\n    claude_vision_model: str = \"claude-sonnet-5-5\"\n    claude_max_tokens: int = 24000\n",
    "backend/app/services/plan.py": "import os\nimport anthropic\nMODE = os.environ.get('SEMANTIC_RETRIEVAL', 'off')\n",
    "deploy/cloudrun-env.yaml": "CLAUDE_MODEL: \"claude-sonnet-5-5\"\nCLAUDE_VISION_MODEL: \"claude-sonnet-5-5\"\nCLAUDE_MAX_TOKENS: \"24000\"\n",
    "deploy/DEPLOY.md": "# deploy\n",
    "docs/DEMO_ACCESS.md": "| 9876543210 | 4826 |\n| 9876500000 | 7351 |\n| 9000000101 to 9000000105 | 4826 |\n",
    "docs/PRIVACY.md": "# privacy\n",
    "docs/STATUS.md": "# Status\n\n| | Promise | Where it stands |\n|---|---|---|\n" + STATUS_ROWS + "\n",
    "docs/EVALUATOR_GUIDE.md": "# Evaluator guide\nhttps://demo-123.asia-south1.run.app\n| Teacher | 9876543210 | 4826 |\n| Admin | 9876500000 | 7351 |\n## Five sample inputs\n1. x\n- these skills still show a recorded sample plan: N2.3.2 and N0.1.1\n## Frozen version\ncommit abc\n",
    "db/seeds/sample_plans/N2.3.2.json": '{"_reviewed_by": "Test reader, 2026-10-25"}\n', "db/seeds/sample_plans/N0.1.1.json": '{"_reviewed_by": "Test reader, 2026-10-25"}\n',
    "Dockerfile": "FROM python:3.11-slim\n",
}


def make(changes=None, remove=()):
    d = Path(tempfile.mkdtemp(prefix="subcheck_"))
    files = dict(GOOD)
    files.update(changes or {})
    for r in remove:
        files.pop(r, None)
    for rel, text in files.items():
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return d


def run(changes=None, remove=(), final=False, **kw):
    d = make(changes, remove)
    try:
        return sc.run_checks(d, final=final, **kw)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def has(res, level, key, text=None):
    return any(r.level == level and r.key == key and (text is None or text in r.text) for r in res)


print("a clean repository")
res = run()
check("a clean repository has no FAIL and no PENDING (only the 'not a git repository' warning)", not any(r.level in ("FAIL", "PENDING") for r in res) and has(res, "WARN", "git_state"), [r for r in res if r.level in ("FAIL", "PENDING")])
check("...and every check named in the guidelines ran", {r.key for r in res} >= {"files_forbidden", "files_photos", "secrets", "personal_phone", "personal_email", "env_example", "env_models", "readme_sections", "readme_stale", "readme_ai", "readme_links", "docs_required", "status_table"})

print("\nsecrets, keys, photos, personal data")
KEY = "sk-ant-api03-" + "abcdefghijklmnopqrstuvwxyz0123456789"
res = run({"backend/app/x.py": f'KEY = "{KEY}"\n'})
check("an Anthropic key in a file is caught, with its place and without its value", has(res, "FAIL", "secrets", "backend/app/x.py:1") and all(KEY not in r.text for r in res))
res = run({"backend/app/y.py": "DB_PASS" + "WORD = " + '"hunter2hunter2"\n'})        # built at run time: this file must itself pass scripts/precommit_check.py
check("a database password with a real value is caught", has(res, "FAIL", "secrets"))
res = run({"backend/app/z.py": 'DB_PASSWORD = os.environ["DB_PASSWORD"]\nSESSION_SECRET = "change-me-to-a-long-random-string"\n'})
check("a placeholder or a reference is NOT a secret (the rule is the pre-commit scanner's)", not has(res, "FAIL", "secrets"))
res = run({"backend/.env": "ANTHROPIC_API_KEY=abc\n"})
check("without git a .env on disk is a warning, and .env.example is never a defect (the git cases are below)", has(res, "WARN", "env_on_disk") and not has(res, "FAIL", "files_forbidden") and not has(run(), "FAIL", "files_forbidden"))
res = run({"docs/worksheet.jpg": "x"})
check("a photo outside the icons is caught (children's work must never be committed)", has(res, "FAIL", "files_photos", "docs/worksheet.jpg"))
check("...but an app icon is fine", not has(run({"pwa/public/icon-192.png": "x"}), "FAIL", "files_photos"))
check("a real-looking phone number is caught", has(run({"docs/notes.md": "call 9812345670 about it"}), "FAIL", "personal_phone"))
check("the published demo numbers, the test-teacher range and obviously fake numbers are fine", not has(run({"docs/notes.md": "9876543210 9000000104 9999999999 9123456789 9898989898"}), "FAIL", "personal_phone"))
check("a real-looking email address is caught; example.com and a service-account placeholder are fine", has(run({"docs/c.md": "write to a.person@gmail.com"}), "FAIL", "personal_email") and not has(run({"docs/c.md": "a@example.com PROJECT_NUMBER-compute@developer.gserviceaccount.com"}), "FAIL", "personal_email"))
check("numbers in a lock file or the embeddings file are not scanned as phones", not has(run({"pwa/package-lock.json": "9812345670", "db/seeds/content/embeddings.json": "9812345670"}), "FAIL", "personal_phone"))
check("the fake-number rule: realistic numbers stay flagged", [sc.looks_fake(n) for n in ("9812345670", "8004912736", "7355013298", "9456123780")] == [False] * 4 and [sc.looks_fake(n) for n in ("9999999999", "9876543210", "9123456789")] == [True] * 3)

print("\nthe sample environment file")
res = run({"backend/app/services/more.py": "import os\nX = os.environ.get('A_NEW_SETTING')\n"})
check("a setting the code reads but .env.example lacks is NAMED", has(res, "FAIL", "env_example", "A_NEW_SETTING"))
res = run({"backend/.env.example": GOOD["backend/.env.example"] + "# A_NEW_SETTING=1\n", "backend/app/services/more.py": "import os\nX = os.environ.get('A_NEW_SETTING')\n"})
check("...and once it is declared (even commented) the check passes", not has(res, "FAIL", "env_example"))
res = run({"backend/app/core/config.py": GOOD["backend/app/core/config.py"] + "    new_field: int = 1\n"})
check("a new field of the settings class counts as a setting (upper-cased)", has(res, "FAIL", "env_example", "NEW_FIELD"))
check("a stale entry in .env.example is a warning, not a failure; a VITE_ setting is allowed", has(run({"backend/.env.example": GOOD["backend/.env.example"] + "OLD_THING=1\n# VITE_X=1\n"}), "WARN", "env_example_extra", "OLD_THING") and "VITE_X" not in str([r for r in run({"backend/.env.example": GOOD["backend/.env.example"] + "# VITE_X=1\n"}) if r.key == "env_example_extra"]))
check("an embedding API or OpenAI left in .env.example is caught", has(run({"backend/.env.example": GOOD["backend/.env.example"] + "EMBEDDING_API_KEY=\n"}), "FAIL", "env_example_stale"))
check("a model name that differs between config, .env.example and the cloud template is caught", has(run({"backend/.env.example": GOOD["backend/.env.example"].replace("claude-sonnet-5-5", "claude-sonnet-4-6", 1)}), "FAIL", "env_models"))
check("a token limit that differs (8000 here, 24000 there) is caught", has(run({"backend/.env.example": GOOD["backend/.env.example"].replace("24000", "8000")}), "FAIL", "env_models"))
check("a variable in the cloud template that .env.example does not list is caught", has(run({"deploy/cloudrun-env.yaml": GOOD["deploy/cloudrun-env.yaml"] + "SOME_FLAG: \"1\"\n"}), "FAIL", "env_template", "SOME_FLAG"))

print("\nthe README")
check("a README without the AI section is caught", has(run({"README.md": GOOD["README.md"].replace("## How AI is used", "## Models")}), "FAIL", "readme_sections", "how AI is used"))
check("a README without a tests section is caught", has(run({"README.md": GOOD["README.md"].replace("## Tests", "## Checks")}), "FAIL", "readme_sections", "tests"))
check("a README that does not mention .env.example, the key variable or the status page is caught", all(has(run({"README.md": GOOD["README.md"].replace(a, "x")}), "FAIL", "readme_sections", b) for a, b in ((".env.example", ".env.example"), ("ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"), ("docs/STATUS.md", "docs/STATUS.md"))))
for phrase, label in (("Week 1 Deliverables", "the Week 1 heading"), ("uvicorn app:app --reload", "the old start command"), ("python scripts/populate_embeddings.py", "the old embedding script"), ("Names exist only in IndexedDB on the teacher's device", "the old claim about names")):
    check(f"out-of-date README text is caught: {label}", has(run({"README.md": GOOD["README.md"] + "\n" + phrase + "\n"}), "FAIL", "readme_stale"))
res = run({"backend/app/services/other.py": "import openai\n"})
check("an AI SDK imported in the code but not named in the README is caught, with where it is used", has(res, "FAIL", "readme_ai", "OpenAI (used in backend/app/services/other.py)"))
res = run({"scripts/call.py": "URL = 'https://api.cohere.ai/v1/embed'\n"})
check("an AI API host in the code but not named in the README is caught too", has(res, "FAIL", "readme_ai", "Cohere"))
res = run({"scripts/embed.py": "def f():\n    from sentence_transformers import SentenceTransformer\n"})
check("a local model library (imported inside a function) must be named in the README", has(res, "FAIL", "readme_ai", "Hugging Face"))
check("...and naming it (bge-m3) satisfies the check", not has(run({"scripts/embed.py": "def f():\n    from sentence_transformers import SentenceTransformer\n", "README.md": GOOD["README.md"] + "\nOffline: BAAI/bge-m3.\n"}), "FAIL", "readme_ai"))
check("an AI SDK in a TEST file is not a service the app uses", not has(run({"backend/tests/test_x.py": "import openai\n"}), "FAIL", "readme_ai"))
check("a link to a file that does not exist is caught", has(run({"README.md": GOOD["README.md"] + "\nSee [it](docs/NOPE.md).\n"}), "FAIL", "readme_links", "docs/NOPE.md"))
check("an external link and an anchor are not checked as files", not has(run({"README.md": GOOD["README.md"] + "\n[a](https://example.com/x) [b](#tests)\n"}), "FAIL", "readme_links"))
check("a README without the live demo link is a warning", has(run({"README.md": GOOD["README.md"].replace("https://demo-123.asia-south1.run.app", "soon")}), "WARN", "readme_demo_url"))

print("\nthe required documents and the exit code")
for rel in ("docs/DEMO_ACCESS.md", "docs/STATUS.md", "docs/PRIVACY.md", "deploy/DEPLOY.md", "Dockerfile"):
    check(f"a missing {rel} is a FAIL", has(run(remove=(rel,)), "FAIL", "docs_required", rel))
res = run(remove=("docs/EVALUATOR_GUIDE.md",))
check("a missing evaluator guide is PENDING, not a FAIL, during the week", has(res, "PENDING", "docs_evaluator") and sc.exit_code(res, final=False) == 0)
check("...and with --final it makes the exit code 1", sc.exit_code(res, final=True) == 1)
check("a FAIL makes the exit code 1 in both modes", sc.exit_code(run({"docs/c.md": "write to a.person@gmail.com"}), False) == 1 and sc.exit_code(run({"docs/c.md": "write to a.person@gmail.com"}), True) == 1)
check("a guide that lacks the link, the sign-ins or a section is caught, naming what is missing", has(run({"docs/EVALUATOR_GUIDE.md": "# guide\n"}), "FAIL", "guide_content", "Sample inputs") and has(run({"docs/EVALUATOR_GUIDE.md": "# guide\n"}), "FAIL", "guide_content", "live link"))
res = run({"docs/EVALUATOR_GUIDE.md": GOOD["docs/EVALUATOR_GUIDE.md"] + "commit: [FILL ON FREEZE: commit hash]\n[FILL ON FREEZE: the video]\n"})
check("unfilled FILL ON FREEZE markers are PENDING during the week (counted, exit code 0) ...", has(res, "PENDING", "guide_placeholders", "2 'FILL ON FREEZE'") and sc.exit_code(res, final=False) == 0 and not has(res, "FAIL", "guide_content"))
check("... and make --final fail (the exit code is 1) until they are filled", sc.exit_code(res, final=True) == 1)
print("the recorded plans match what the guide says")
check("the folder holds exactly the plans the guide names: PASS", has(run(), "PASS", "sample_plans", "N0.1.1, N2.3.2"))
res = run(remove=("db/seeds/sample_plans/N0.1.1.json",))
check("a plan the guide names but the folder lacks is PENDING, names it and gives the command that records it", has(res, "PENDING", "sample_plans", "N0.1.1") and has(res, "PENDING", "sample_plans", "batch_generate.py --only N0.1.1 --save-samples") and sc.exit_code(res, final=False) == 0)
check("...and --final refuses until it is recorded", sc.exit_code(res, final=True) == 1)
res = run({"db/seeds/sample_plans/N0.5.1.json": "{}\n"})
check("a plan in the folder that the guide does not name (it would be offered to teachers) is PENDING and says how to move it out", has(res, "PENDING", "sample_plans_extra", "N0.5.1") and has(res, "PENDING", "sample_plans_extra", "git mv") and sc.exit_code(res, final=True) == 1)
res = run({"docs/EVALUATOR_GUIDE.md": GOOD["docs/EVALUATOR_GUIDE.md"].replace("recorded sample plan", "something else")})
check("a guide that does not say which skills have a recorded plan is a FAIL (the folder cannot be checked against it)", has(res, "FAIL", "sample_plans", "ONE line"))
res = run(remove=("db/seeds/sample_plans/N2.3.2.json", "db/seeds/sample_plans/N0.1.1.json"))
check("a repository with no recorded-plans folder at all is not asked about it (there is nothing to compare)", not any(r.key in ("sample_plans", "sample_plans_extra") for r in res), [r.key for r in res])
print("the printed lines")
lines = sc.format_lines([sc.R("PASS", "secrets", "ok"), sc.R("PENDING", "guide_placeholders", "docs/EVALUATOR_GUIDE.md still has 9 places"), sc.R("PENDING", "sample_plans_review", "2 recorded plans are unsigned")])
import re as _re
parsed = [_re.match(r"^  (\S+)\s+(\S+)\s{2,}(.*)$", l) for l in lines]
check("every line splits into level, key and message, however long the key (the 18- and 19-letter keys used to run into their messages)", all(parsed) and [m.group(2) for m in parsed] == ["secrets", "guide_placeholders", "sample_plans_review"] and parsed[1].group(3).startswith("docs/EVALUATOR_GUIDE.md") and parsed[2].group(3).startswith("2 recorded"), lines)
check("the messages start in the same column on every line", len({l.index(m.group(3)) for l, m in zip(lines, parsed)}) == 1, [l.index(m.group(3)) for l, m in zip(lines, parsed)])
check("an empty list prints nothing and does not fail", sc.format_lines([]) == [])

print("a plan made by the fake model must never be in the folder")
res = run({"db/seeds/sample_plans/N0.1.1.json": '{"anchor": {}, "_stub": true, "_reviewed_by": null}\n'})
check("a _stub plan in db/seeds/sample_plans is a FAIL that says it came from the fake model", has(res, "FAIL", "sample_plans", "FAKE model") and sc.exit_code(res, final=False) == 1)

print("a recorded plan kept WITH warnings must be signed by the person who read it")
unreviewed = '{"anchor": {}, "_recorded_warnings": ["worksheets.proficient problem 5 repeats wording from the lesson or anchor"], "_reviewed_by": null}\n'
res = run({"db/seeds/sample_plans/N0.1.1.json": unreviewed})
check("kept with warnings and nobody's name against them: PENDING, names the plan and says what to do (read it, set _reviewed_by)", has(res, "PENDING", "sample_plans_review", "N0.1.1") and has(res, "PENDING", "sample_plans_review", "review_sample_plans.py sheet") and has(res, "PENDING", "sample_plans_review", "review_sample_plans.py sign") and sc.exit_code(res, final=False) == 0)
check("...and --final refuses until it is signed", sc.exit_code(res, final=True) == 1)
signed = unreviewed.replace('"_reviewed_by": null', '"_reviewed_by": "Vaishnavi, 26 Oct 2026"')
res = run({"db/seeds/sample_plans/N0.1.1.json": signed})
check("once _reviewed_by holds a name it is not asked about again", not any(r.key == "sample_plans_review" for r in res) and has(res, "PASS", "sample_plans"), [(r.key, r.level) for r in res if "sample" in r.key])
res = run({"db/seeds/sample_plans/N0.1.1.json": '{"anchor": {}}\n'})
check("a plan with NO warnings but no signature is PENDING too: the checks do not read Hindi, a person must (it says who is waiting and how)", has(res, "PENDING", "sample_plans_review", "N0.1.1") and has(res, "PENDING", "sample_plans_review", "have not been read and signed") and not has(res, "PENDING", "sample_plans_review", "also carry warnings") and sc.exit_code(res, final=True) == 1)
check("a plan that also carries warnings says so: it names the plan and says the warnings are written inside the file", has(run({"db/seeds/sample_plans/N0.1.1.json": unreviewed}), "PENDING", "sample_plans_review", "(N0.1.1 also carry warnings, written inside the file)"))
check("signed plans (the fixture's own) are not asked about", not any(r.key == "sample_plans_review" for r in run()))
res = run({"db/seeds/sample_plans/N0.1.1.json": "{ this is not json"})
check("a recorded plan that is not valid JSON is a FAIL naming the file (the app would silently find no recorded plan for it)", has(res, "FAIL", "sample_plans", "N0.1.1.json is not valid JSON"))
check("a filled-in guide passes both", has(run(), "PASS", "guide_placeholders") and has(run(), "PASS", "guide_content"))
check("a status table with too few rows is caught", has(run({"docs/STATUS.md": "| ✅ | a | b |\n| ❌ | c | d |\n"}), "FAIL", "status_table"))
check("a status table counts each symbol", has(run(), "PASS", "status_table", "45 rows"))

print("\ngit: the deadline, the freeze and the history")
if not shutil.which("git"):
    print("  SKIPPED the git checks: git is not installed here")
else:
    def git(d, *a, env=None):
        e = dict(os.environ, **(env or {}))
        e.update(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")
        return subprocess.run(["git", "-C", str(d), *a], capture_output=True, text=True, env=e)

    def repo(extra=None, commit_date=None):
        d = make(extra)
        git(d, "init", "-q")
        git(d, "add", "-A")
        git(d, "commit", "-q", "-m", "first", env={"GIT_COMMITTER_DATE": commit_date, "GIT_AUTHOR_DATE": commit_date} if commit_date else None)
        return d
    d = repo()
    res = sc.run_checks(d, final=False)
    check("a committed clean repository: no FAIL, a clean tree, the commit is shown", not any(r.level == "FAIL" for r in res) and has(res, "PASS", "git_clean") and has(res, "INFO", "git_head"), [r for r in res if r.level == "FAIL"])
    res_final = sc.run_checks(d, final=True)
    check("--final without a tag on the frozen commit fails", has(res_final, "FAIL", "git_tag"))
    git(d, "tag", "submission-stage2")
    res_final = sc.run_checks(d, final=True)
    check("...and with the tag it passes (and the tag is shown)", has(res_final, "PASS", "git_tag", "submission-stage2") and sc.exit_code(res_final, True) == 0, [r for r in res_final if r.level in ("FAIL", "PENDING")])
    (d / "notes.txt").write_text("uncommitted", encoding="utf-8")
    check("an uncommitted file is a warning during the week and a FAIL in --final", has(sc.run_checks(d, final=False), "WARN", "git_clean") and has(sc.run_checks(d, final=True), "FAIL", "git_clean"))
    (d / "notes.txt").unlink()
    check("a commit after the deadline is caught (here the deadline is in the past)", has(sc.run_checks(d, final=False, deadline="2000-01-01T00:00:00+00:00"), "FAIL", "git_deadline"))
    check("a commit before the deadline is fine", has(sc.run_checks(d, final=False, deadline="2099-01-01T00:00:00+00:00"), "PASS", "git_deadline"))
    old = repo(commit_date="2026-10-20T10:00:00+05:30")
    check("a commit dated 20 Oct passes the 1 Nov deadline", has(sc.run_checks(old, final=False), "PASS", "git_deadline"))
    late = repo(commit_date="2026-11-02T10:00:00+05:30")
    check("a commit dated 2 Nov fails the 1 Nov deadline", has(sc.run_checks(late, final=False), "FAIL", "git_deadline"))
    # a secret that was committed and later deleted is STILL in the history
    h = repo({"backend/.env": "X=1\n"})
    check("a .env file that is COMMITTED is a FAIL", has(sc.run_checks(h, history=False), "FAIL", "files_forbidden", "backend/.env "))
    git(h, "rm", "-q", "--cached", "backend/.env")
    (h / "backend" / ".env").unlink()
    git(h, "commit", "-q", "-m", "remove the env file")
    check("an .env file committed once and removed later is still found in the history", has(sc.run_checks(h), "FAIL", "history", "env file"))
    k = repo({"backend/app/k.py": f'KEY = "{KEY}"\n'})
    git(k, "rm", "-q", "backend/app/k.py")
    git(k, "commit", "-q", "-m", "remove the key")
    res = sc.run_checks(k)
    check("a key committed once and removed later is still found in the history (and the working files are clean)", has(res, "FAIL", "history", "Anthropic") and has(res, "PASS", "secrets"))
    check("--no-history skips that search", not any(r.key == "history" for r in sc.run_checks(k, history=False)))
    nogit = make()
    check("--final outside a git repository fails", has(sc.run_checks(nogit, final=True), "FAIL", "git_state"))
    # a .env on disk: harmless where git ignores it, a defect where git would take it, only a warning where there is no git to ask
    plain = make({"backend/.env": "DB_NAME=mine\nANTHROPIC_API_KEY=local-key-for-me\n"})
    res = sc.run_checks(plain)
    check("WITHOUT git a .env on disk is a warning (your own local configuration), not a FAIL, and is not scanned for secrets", has(res, "WARN", "env_on_disk", "backend/.env") and not has(res, "FAIL", "files_forbidden") and not has(res, "FAIL", "secrets"), [r for r in res if r.level in ("FAIL", "WARN")])
    g = repo({"backend/.env": "DB_NAME=mine\n"})
    git(g, "rm", "-q", "--cached", "backend/.env")
    check("WITH git, a .env that git is NOT ignoring (one `git add .` away from being committed) is a FAIL", has(sc.run_checks(g, history=False), "FAIL", "files_forbidden", "backend/.env"))
    (g / ".gitignore").write_text(".env\n", encoding="utf-8")
    git(g, "add", ".gitignore")
    git(g, "commit", "-q", "-m", "ignore env")
    check("...and once .env is git-ignored it is fine", not has(sc.run_checks(g, history=False), "FAIL", "files_forbidden"))
    shutil.rmtree(plain, ignore_errors=True)
    shutil.rmtree(g, ignore_errors=True)
    for x in (d, old, late, h, k, nogit):
        shutil.rmtree(x, ignore_errors=True)

print("\nthis repository")
res = sc.run_checks(ROOT, final=False)
fails = [r for r in res if r.level == "FAIL"]
check("THIS repository has no FAIL (a key, a stale README line, a setting missing from .env.example... would fail the build)", not fails, fails)
check("this repository's .env.example lists every setting the code reads", has(res, "PASS", "env_example"))
check("this repository's README names every AI service the code uses", has(res, "PASS", "readme_ai"))

if failures:
    print(f"\nFAILED ({len(failures)})")
    sys.exit(1)
print("\nOK: the gate catches each defect it exists for, stays quiet about what is fine, and this repository passes it")
