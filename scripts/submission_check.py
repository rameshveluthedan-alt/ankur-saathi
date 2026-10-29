#!/usr/bin/env python3
"""
The gate for the Stage 2 "Source Code" deliverable. READ-ONLY: it changes nothing.

    python scripts/submission_check.py            during the week: FAIL = a real defect, PENDING = a deliverable not made yet
    python scripts/submission_check.py --final    on the freeze day: PENDING also counts as FAIL, and git must be clean, tagged and not past the deadline

What the evaluators' guidelines ask of the repository, and what is checked here:
  * no secrets or API keys committed (the working files AND the whole git history), no .env file, no photos of children's work
  * no personal data of real users (phone numbers other than the published demo ones; real-looking email addresses)
  * a README with setup, how to run locally, tests, deployment; a sample environment file (.env.example) that lists EVERY setting the code reads
  * the README names EVERY external AI service or model the code uses, and says where keys are needed
  * the required documents exist; docs/STATUS.md is a well-formed table
  * no commits after the deadline (`--final`: also a clean working tree and a tag on the frozen commit)

It reuses the rules of scripts/precommit_check.py, so there is one definition of "a secret". It prints file names and line numbers, never a secret.
Exit code 1 when there is a FAIL (and, with --final, a PENDING).
"""
import argparse
import ast
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE)]
import precommit_check as pc                                    # noqa: E402  (one definition of "a secret")

DEADLINE = "2026-11-01T23:59:00+05:30"            # Stage 2 closes on 1 Nov 2026, 11:59 pm (confirm the time zone with the organisers)
SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", "dist", ".pytest_cache"}
BINARY_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".xlsx", ".docx", ".gz", ".zip", ".woff", ".woff2", ".ttf", ".mp4", ".heic", ".tgz"}
NOT_SCANNED = {"package-lock.json", "embeddings.json"}            # a lock file or 150 vectors: nothing to find, and numbers there are not phones
OWN_FILES = {"scripts/precommit_check.py", "scripts/submission_check.py", "backend/tests/test_submission_check.py"}      # they name the patterns they look for
SYMBOLS = "✅🟡❌⏸"

# the AI providers: the module an SDK is imported as / the API host, and the words the README must use to name it
PROVIDERS = {
    "Anthropic": (["anthropic"], ["api.anthropic.com"], ["anthropic", "claude"]),
    "OpenAI": (["openai"], ["api.openai.com"], ["openai"]),
    "Google": (["google.generativeai", "google.genai", "vertexai"], ["generativelanguage.googleapis.com", "aiplatform.googleapis.com"], ["google", "gemini", "vertex"]),
    "Cohere": (["cohere"], ["api.cohere.ai", "api.cohere.com"], ["cohere"]),
    "Voyage": (["voyageai"], ["api.voyageai.com"], ["voyage"]),
    "Mistral": (["mistralai"], ["api.mistral.ai"], ["mistral"]),
    "Groq": (["groq"], ["api.groq.com"], ["groq"]),
    "Hugging Face models (local)": (["sentence_transformers", "transformers", "huggingface_hub"], ["api-inference.huggingface.co"], ["bge-m3", "sentence-transformers", "hugging face", "huggingface"]),
}


class R:
    def __init__(self, level, key, text):
        self.level, self.key, self.text = level, key, text

    def __repr__(self):
        return f"{self.level} {self.key}: {self.text}"


def sh(root: Path, *args):
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout


def is_git(root: Path) -> bool:
    return (root / ".git").exists() and sh(root, "rev-parse", "--is-inside-work-tree")[0] == 0


def list_files(root: Path):
    """The files that are, or with `git add .` WOULD be, in the repository. Without git: every file on disk (minus caches and dependencies)."""
    if is_git(root):
        tracked = sh(root, "ls-files")[1].splitlines()
        others = sh(root, "ls-files", "--others", "--exclude-standard")[1].splitlines()
        return [p for p in dict.fromkeys(tracked + others) if p and (root / p).is_file()], True
    out = []
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        out += [os.path.relpath(os.path.join(d, f), root).replace("\\", "/") for f in files]
    # Without git there are no ignore rules to consult, so a .env on disk is the owner's LOCAL configuration, not repository content: it is reported as a warning (see run_checks), not scanned as a defect
    return [p for p in out if not (re.search(r"(^|/)\.env(\.[^/]*)?$", p) and not pc.ALLOWED_ENV.search(p))], False


def looks_fake(number: str) -> bool:
    """A number nobody owns: one or two distinct digits (9999999999, 9898989898), or a run (9876543210, 9123456789), or mostly zeros. Test fixtures use these on purpose."""
    d = [int(c) for c in number]
    steps = {b - a for a, b in zip(d[1:], d[2:])}                  # the run may follow the leading 9 / 8 / 7 / 6: 9123456789
    return len(set(d)) <= 2 or steps <= {1} or steps <= {-1} or number.rstrip("0") != number and len(number.rstrip("0")) <= 4


def read_text(path: Path):
    if path.suffix.lower() in BINARY_EXT or path.name in NOT_SCANNED:
        return None
    try:
        if path.stat().st_size > 1_500_000:
            return None
        raw = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in raw[:2048]:
        return None
    return raw.decode("utf-8", "replace")


# ---------------------------------------------------------------------------------------------------------------- the variables the code reads
def code_variables(root: Path) -> set:
    """Every environment variable the code reads: the settings fields (upper-cased) and every os.environ / getenv name outside the tests."""
    found = set()
    cfg = root / "backend" / "app" / "core" / "config.py"
    if cfg.exists():
        tree = ast.parse(cfg.read_text(encoding="utf-8"))
        for c in tree.body:
            if isinstance(c, ast.ClassDef) and c.name == "Settings":
                found |= {n.target.id.upper() for n in c.body if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)}
    rx = re.compile(r"os\.environ(?:\.get)?\(?\[?\s*[\"']([A-Z][A-Z0-9_]{2,})[\"']|getenv\(\s*[\"']([A-Z][A-Z0-9_]{2,})[\"']")
    for sub in ("backend/app", "prompts", "scripts"):
        for p in (root / sub).rglob("*.py") if (root / sub).exists() else []:
            if "tests" in p.parts or "__pycache__" in p.parts:
                continue
            for m in rx.finditer(p.read_text(encoding="utf-8", errors="replace")):
                found.add(m.group(1) or m.group(2))
    return found


def declared_variables(path: Path) -> set:
    return set(re.findall(r"^#?\s*([A-Z][A-Z0-9_]{2,})=", path.read_text(encoding="utf-8", errors="replace"), re.M)) if path.exists() else set()


def ai_providers_used(root: Path) -> dict:
    """{provider: first place it is used}: an SDK import, or its API host in the code."""
    used = {}
    for sub in ("backend/app", "prompts", "scripts", "pwa/src"):
        base = root / sub
        if not base.exists():
            continue
        for p in list(base.rglob("*.py")) + list(base.rglob("*.js")) + list(base.rglob("*.jsx")):
            if any(x in p.parts for x in ("tests", "__pycache__", "node_modules")) or str(p.relative_to(root)).replace("\\", "/") in OWN_FILES:
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
            rel = str(p.relative_to(root)).replace("\\", "/")
            mods = set()
            if p.suffix == ".py":
                try:
                    for n in ast.walk(ast.parse(text)):
                        if isinstance(n, ast.Import):
                            mods |= {a.name for a in n.names}
                        elif isinstance(n, ast.ImportFrom) and n.module:
                            mods.add(n.module)
                except SyntaxError:
                    pass
            for name, (modules, hosts, _) in PROVIDERS.items():
                if name in used:
                    continue
                if any(m == mod or m.startswith(mod + ".") for m in mods for mod in modules) or any(h in text for h in hosts):
                    used[name] = rel
    return used


# ---------------------------------------------------------------------------------------------------------------------------------- the checks
def run_checks(root: Path, final: bool = False, deadline: str = DEADLINE, history: bool = True) -> list:
    root = Path(root)
    res = []
    add = lambda level, key, text: res.append(R(level, key, text))
    files, git = list_files(root)
    if not git:
        add("FAIL" if final else "WARN", "git_state", "this is not a git repository: only the files on disk were checked (no history, no deadline check). Run it in your clone.")
        local_env = sorted(p for p in (os.path.relpath(os.path.join(d, f), root).replace("\\", "/") for d, _, fs in os.walk(root) for f in fs) if re.search(r"(^|/)\.env(\.[^/]*)?$", p) and not pc.ALLOWED_ENV.search(p) and not any(x in p.split("/") for x in SKIP_DIRS))
        if local_env:
            add("WARN", "env_on_disk", f"{', '.join(local_env)} exists here (your local configuration: not scanned). Make sure it is git-ignored and never committed.")

    # ---- files that must never be there
    forbidden = []
    for p in files:
        for pat, what in pc.FORBIDDEN_PATH:
            if re.search(pat, p) and not pc.ALLOWED_ENV.search(p):
                forbidden.append(f"{p} ({what})")
                break
    add("FAIL" if forbidden else "PASS", "files_forbidden", ("; ".join(forbidden[:6]) + (f" and {len(forbidden) - 6} more" if len(forbidden) > 6 else "")) if forbidden else f"{len(files)} files: no .env file, key file, virtual environment or node_modules")
    photos = [p for p in files if pc.PHOTO.search(p) and not pc.PHOTO_OK.search(p)]
    add("FAIL" if photos else "PASS", "files_photos", f"{len(photos)} image(s) outside the app's icons and screenshots: {', '.join(photos[:5])}. Photos of children's work must never be committed" if photos else "no photos (only app icons and screenshots)")
    big = [p for p in files if (root / p).exists() and (root / p).stat().st_size > pc.BIG]
    if big:
        add("WARN", "files_big", f"{len(big)} file(s) over 5 MB: {', '.join(big[:4])}")

    # ---- secrets in the files
    hits, scanned = [], 0
    for p in files:
        if p in OWN_FILES:
            continue
        text = read_text(root / p)
        if text is None:
            continue
        scanned += 1
        for n, line in enumerate(text.splitlines(), 1):
            for pat, what in pc.SECRET_PATTERNS:
                m = pat.search(line)
                if not m:
                    continue
                value = m.group(m.lastindex) if m.lastindex else m.group(0)
                if pc.PLACEHOLDER.search(line) or pc.PLACEHOLDER.search(value or "") or pc.DUMMY_VALUE.match(value or "") or pc.SECRET_REFERENCE.match(value or ""):
                    continue
                hits.append(f"{p}:{n} looks like {what}")
                break
    add("FAIL" if hits else "PASS", "secrets", ("; ".join(hits[:6]) + " (values hidden)") if hits else f"{scanned} text files scanned: nothing looks like a key or a password")

    # ---- secrets in the history
    if git and history:
        _, names = sh(root, "log", "--all", "--diff-filter=A", "--name-only", "--format=")
        env_hist = sorted({n for n in names.splitlines() if re.search(r"(^|/)\.env(\.[^/]*)?$", n) and not pc.ALLOWED_ENV.search(n)})
        _, keyhist = sh(root, "log", "--all", "-G", r"sk-ant-[A-Za-z0-9_-]{20,}", "--oneline")
        bad = ([f"an env file was committed at some point: {', '.join(env_hist[:3])}"] if env_hist else []) + ([f"{len(keyhist.splitlines())} commit(s) add something shaped like an Anthropic key"] if keyhist.strip() else [])
        add("FAIL" if bad else "PASS", "history", ("; ".join(bad) + ". Rotate the key or password, then clean the history (a later commit does not remove it)") if bad else "the git history holds no .env file and no Anthropic-shaped key")

    # ---- personal data
    allowed = set()
    da = root / "docs" / "DEMO_ACCESS.md"
    if da.exists():
        t = da.read_text(encoding="utf-8")
        allowed |= set(re.findall(r"(?<!\d)\d{10}(?!\d)", t))
        for a, b in re.findall(r"(\d{10})\s*(?:to|-|–)\s*(\d{10})", t):
            allowed |= {str(x) for x in range(int(a), int(b) + 1)}
    allowed |= {"9876543210", "9876500000"}            # the two OLD fictional demo numbers: the migration to employee codes and its test have to name them
    phones, emails = {}, {}
    mail_ok = re.compile(r"example\.(com|org|net)$|noreply|gserviceaccount\.com$|\.invalid$|localhost$", re.I)
    for p in files:
        if p in OWN_FILES:
            continue
        text = read_text(root / p)
        if text is None:
            continue
        for m in re.finditer(r"(?<![\d.])[6-9]\d{9}(?!\d)", text):
            if m.group(0) not in allowed and not m.group(0).startswith("9000000") and not looks_fake(m.group(0)):
                phones.setdefault(m.group(0)[:3] + "xxxxxxx", set()).add(p)
        for m in re.finditer(r"[\w.+-]+@([\w-]+(?:\.[\w-]+)+)", text):
            if not mail_ok.search(m.group(1)) and not re.search(r"[A-Z]{4,}", m.group(0)):
                emails.setdefault(m.group(0), set()).add(p)
    add("FAIL" if phones else "PASS", "personal_phone", ("phone-like numbers that are not the published demo accounts, in: " + "; ".join(sorted({f for v in phones.values() for f in v})[:6])) if phones else "no phone number except the published demo accounts")
    add("FAIL" if emails else "PASS", "personal_email", ("email addresses in: " + "; ".join(sorted({f for v in emails.values() for f in v})[:6])) if emails else "no real-looking email address")

    # ---- the sample environment file
    ex = root / "backend" / ".env.example"
    need = code_variables(root)
    if not ex.exists():
        add("FAIL", "env_example", "backend/.env.example does not exist")
    else:
        have = declared_variables(ex)
        missing = sorted(need - have)
        extra = sorted(v for v in have - need if not v.startswith("VITE_"))
        add("FAIL" if missing else "PASS", "env_example", (f"{len(missing)} setting(s) the code reads are missing from backend/.env.example: {', '.join(missing[:10])}") if missing else f"backend/.env.example lists all {len(need)} settings the code reads")
        if extra:
            add("WARN", "env_example_extra", f"backend/.env.example lists setting(s) the code does not read (stale?): {', '.join(extra)}")
        old = re.findall(r"EMBEDDING_API|OPENAI", ex.read_text(encoding="utf-8"))
        if old:
            add("FAIL", "env_example_stale", "backend/.env.example still mentions an embedding API / OpenAI, which the app no longer uses")
    tpl = root / "deploy" / "cloudrun-env.yaml"
    cfg = root / "backend" / "app" / "core" / "config.py"
    if tpl.exists() and ex.exists() and cfg.exists():
        t = tpl.read_text(encoding="utf-8")
        e = ex.read_text(encoding="utf-8")
        c = cfg.read_text(encoding="utf-8")
        for var, field in (("CLAUDE_MODEL", "claude_model"), ("CLAUDE_VISION_MODEL", "claude_vision_model"), ("CLAUDE_MAX_TOKENS", "claude_max_tokens")):
            vals = {
                "config.py": (re.search(rf"{field}\s*:\s*\w+\s*=\s*[\"']?([\w.\-]+)", c) or [None, None])[1],
                ".env.example": (re.search(rf"^{var}=([\w.\-]+)", e, re.M) or [None, None])[1],
                "cloudrun-env.yaml": (re.search(rf"^{var}:\s*[\"']?([\w.\-]+)", t, re.M) or [None, None])[1],
            }
            if len({v for v in vals.values() if v}) > 1 or None in vals.values():
                add("FAIL", "env_models", f"{var} is not the same in all three places: {vals}")
                break
        else:
            add("PASS", "env_models", "the model names and the token limit agree in config.py, .env.example and deploy/cloudrun-env.yaml")
        in_tpl = set(re.findall(r"^([A-Z][A-Z0-9_]{2,}):", t, re.M))
        notdecl = sorted(in_tpl - declared_variables(ex))
        if notdecl:
            add("FAIL", "env_template", f"deploy/cloudrun-env.yaml sets variable(s) that backend/.env.example does not list: {', '.join(notdecl)}")

    # ---- the README
    rd = root / "README.md"
    if not rd.exists():
        add("FAIL", "readme_sections", "README.md does not exist")
    else:
        r = rd.read_text(encoding="utf-8")
        heads = [l.lstrip("# ").strip().lower() for l in r.splitlines() if l.startswith("#")]
        wanted = {"how to run it locally": r"run it locally|quick start|getting started|how to run", "tests": r"^tests?\b", "deployment": r"^deploy", "how AI is used": r"how ai is used|ai services|ai/llm"}
        absent = [k for k, rx in wanted.items() if not any(re.search(rx, h) for h in heads)]
        for k, ph in ((".env.example", ".env.example"), ("the key variable ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"), ("docs/STATUS.md", "docs/STATUS.md")):
            if ph not in r:
                absent.append(f"a mention of {k}")
        add("FAIL" if absent else "PASS", "readme_sections", ("the README lacks: " + ", ".join(absent)) if absent else "the README has setup / run locally, tests, deployment, the AI services, .env.example and the status link")
        stale = [s for s, rx in (("Week 1 Deliverables", r"Week 1 Deliverables"), ("the old start command `uvicorn app:app`", r"uvicorn app:app\b"), ("populate_embeddings", r"populate_embeddings"), ("EMBEDDING_API_KEY", r"EMBEDDING_API_KEY"), ("names only in IndexedDB", r"IndexedDB on teacher|Names exist only in IndexedDB"))
                 if re.search(rx, r)]
        add("FAIL" if stale else "PASS", "readme_stale", ("the README still contains out-of-date text: " + ", ".join(stale)) if stale else "no out-of-date text (old start command, old embedding script, wrong claim about names)")
        used = ai_providers_used(root)
        low = r.lower()
        unnamed = [f"{n} (used in {w})" for n, w in used.items() if not any(word in low for word in PROVIDERS[n][2])]
        add("FAIL" if unnamed else "PASS", "readme_ai", ("the code uses AI service(s) the README does not name: " + "; ".join(unnamed)) if unnamed else f"the README names every AI service the code uses ({', '.join(sorted(used)) or 'none found'})")
        broken = []
        for m in re.finditer(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", r):
            tgt = m.group(1)
            if re.match(r"[a-z]+:", tgt) or tgt.startswith("#"):
                continue
            if not (root / tgt).exists():
                broken.append(tgt)
        add("FAIL" if broken else "PASS", "readme_links", ("links to files that do not exist: " + ", ".join(sorted(set(broken))[:8])) if broken else "every file the README links to exists")
        if not re.search(r"https://[\w.-]+\.run\.app", r):
            add("WARN", "readme_demo_url", "the README does not show the live demo link (a .run.app address)")

    # ---- the required documents
    for rel, level, why in (("docs/DEMO_ACCESS.md", "FAIL", "test credentials for every role"), ("docs/STATUS.md", "FAIL", "the honest status against the proposal"), ("docs/PRIVACY.md", "FAIL", "where children's data goes"),
                            ("deploy/DEPLOY.md", "FAIL", "how it is deployed"), ("Dockerfile", "FAIL", "how the container is built"), ("docs/EVALUATOR_GUIDE.md", "PENDING", "the evaluators' one-page guide: links, credentials, sample inputs, the frozen commit")):
        if (root / rel).exists():
            add("PASS", "docs_required", f"{rel} exists")
        else:
            add(level, "docs_evaluator" if "EVALUATOR" in rel else "docs_required", f"{rel} is missing ({why})")
    guide = root / "docs" / "EVALUATOR_GUIDE.md"
    if guide.exists():
        g = guide.read_text(encoding="utf-8")
        lacks = [what for what, rx in (("the live link (a .run.app address)", r"https://[\w.-]+\.run\.app"), ("the teacher's sign-in (employee code MPT101)", r"\bMPT101\b"), ("the school leader's sign-in (employee code MPA101)", r"\bMPA101\b"),
                                       ("a 'Sample inputs' section", r"(?im)^#+\s*(\w+\s+){0,3}sample inputs"), ("a 'Frozen version' section", r"(?im)^#+\s*frozen version")) if not re.search(rx, g)]
        add("FAIL" if lacks else "PASS", "guide_content", ("docs/EVALUATOR_GUIDE.md lacks: " + ", ".join(lacks)) if lacks else "the evaluator guide has the live link, the sign-ins, a 'Sample inputs' section and a 'Frozen version' section")
        left = g.count("FILL ON FREEZE")
        if left:
            add("PENDING", "guide_placeholders", f"docs/EVALUATOR_GUIDE.md still has {left} 'FILL ON FREEZE' place(s) (the video, the commit, the tag, the revision, the sample photos...): fill them on the freeze day; --final refuses to pass until they are gone")
        else:
            add("PASS", "guide_placeholders", "the evaluator guide has no unfilled FILL ON FREEZE marker")
        # The recorded plans are what a teacher (or an evaluator) sees when the AI limit is reached, and the app lists every file in db/seeds/sample_plans. So the folder must hold exactly the plans
        # the guide says are there: found on the team's own copy (25 Oct) that the guide said two while the folder held four.
        plans_dir = root / "db" / "seeds" / "sample_plans"
        if plans_dir.is_dir():
            line = next((l for l in g.splitlines() if "recorded sample plan" in l), "")
            named = set(re.findall(r"\b[NL]\d\.\d+\.\d+\b", line))
            have = {p.stem for p in plans_dir.glob("*.json")}
            if not named:
                add("FAIL", "sample_plans", "docs/EVALUATOR_GUIDE.md must say, in ONE line containing the words 'recorded sample plan', which skills have one (for example N2.3.2): the folder db/seeds/sample_plans is shown to teachers and must match it")
            else:
                missing, extra = sorted(named - have), sorted(have - named)
                if missing:
                    add("PENDING", "sample_plans", f"the evaluator guide names a recorded plan for {', '.join(missing)} but db/seeds/sample_plans has none: record it (it reads backend/.env, about 14 cents each; one skill per run, the value attached with '=', so a pasted line cannot lose it):  {'; '.join(f'python scripts/batch_generate.py --only {m} --save-samples --redo --yes --max-cost=1' for m in missing)}   then have the Hindi read")
                if extra:
                    add("PENDING", "sample_plans_extra", f"db/seeds/sample_plans has {', '.join(extra)}, which the evaluator guide does not name. Every file there is offered to teachers when the AI limit is reached: name it in the guide, or move it out (git mv db/seeds/sample_plans/<skill>.json docs/samples/)")
                if not missing and not extra:
                    add("PASS", "sample_plans", f"the recorded plans in db/seeds/sample_plans are exactly the ones the guide names ({', '.join(sorted(named))})")
            # EVERY recorded plan is shown to teachers and evaluators when the AI limit is reached, so each must be read by someone who reads Hindi and then signed (_reviewed_by), with warnings or without:
            # the checks cover sums, structure and repeated wording, not whether the Hindi is natural or the story suits the children. A plan kept WITH warnings also carries them inside the file.
            unsigned, with_warnings = [], []
            for p in sorted(plans_dir.glob("*.json")):
                try:
                    d = json.loads(p.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    add("FAIL", "sample_plans", f"db/seeds/sample_plans/{p.name} is not valid JSON")
                    continue
                if isinstance(d, dict) and d.get("_stub"):
                    add("FAIL", "sample_plans", f"db/seeds/sample_plans/{p.name} was made by the FAKE model (_stub): it is not a real recorded plan and must not be shown to anyone")
                if isinstance(d, dict) and not d.get("_reviewed_by"):
                    unsigned.append(p.stem)
                    if d.get("_recorded_warnings"):
                        with_warnings.append(p.stem)
            if unsigned:
                add("PENDING", "sample_plans_review", f"{len(unsigned)} recorded plan(s) have not been read and signed by a person: {', '.join(unsigned)}" + (f" ({', '.join(with_warnings)} also carry warnings, written inside the file)" if with_warnings else "") + ". Each is shown to teachers and evaluators when the AI limit is reached, so each must be read by someone who reads Hindi: python scripts/review_sample_plans.py sheet (open the pages it writes), then sign (python scripts/review_sample_plans.py sign <skill> --by \"Name\"): never edit the JSON by hand")
    st = root / "docs" / "STATUS.md"
    if st.exists():
        rows = re.findall(rf"^\| ([{SYMBOLS}]) \|", st.read_text(encoding="utf-8"), re.M)
        add("PASS" if len(rows) >= 40 else "FAIL", "status_table", f"docs/STATUS.md has {len(rows)} rows ({', '.join(f'{s} {rows.count(s)}' for s in SYMBOLS if rows.count(s))})" if len(rows) >= 40 else f"docs/STATUS.md has only {len(rows)} well-formed rows (expected 40 or more)")
    emb = root / "db" / "seeds" / "content" / "embeddings.json"
    add("INFO", "embeddings_file", "db/seeds/content/embeddings.json is present" if emb.exists() else "db/seeds/content/embeddings.json is not there (semantic retrieval has no vectors to load; fine while the switch is OFF)")

    # ---- git: the deadline and the freeze
    if git:
        _, head = sh(root, "rev-parse", "--short", "HEAD")
        _, when = sh(root, "log", "-1", "--format=%cI")
        _, branch = sh(root, "rev-parse", "--abbrev-ref", "HEAD")
        _, tags = sh(root, "tag", "--points-at", "HEAD")
        dirty = [l for l in sh(root, "status", "--porcelain")[1].splitlines() if l.strip()]
        add("INFO", "git_head", f"commit {head.strip()} on {branch.strip()}, committed {when.strip()}, tag(s) at HEAD: {', '.join(tags.split()) or 'none'}")
        try:
            late = dt.datetime.fromisoformat(when.strip()) > dt.datetime.fromisoformat(deadline)
        except ValueError:
            late = False
        _, after = sh(root, "log", "--all", "--since", deadline, "--oneline")
        n_after = len([l for l in after.splitlines() if l.strip()]) if not after.startswith("fatal") else 0
        add("FAIL" if (late or n_after) else "PASS", "git_deadline", f"{n_after or 1} commit(s) after the deadline {deadline}" if (late or n_after) else f"no commit after the deadline {deadline}")
        add(("FAIL" if final else "WARN") if dirty else "PASS", "git_clean", f"{len(dirty)} uncommitted or untracked change(s): the evaluators see only what is committed" if dirty else "the working tree is clean")
        if final and not tags.split():
            add("FAIL", "git_tag", "no tag on the frozen commit: run `git tag submission-stage2` and push the tag")
        elif tags.split():
            add("PASS", "git_tag", f"the frozen commit is tagged: {', '.join(tags.split())}")
        _, remotes = sh(root, "remote", "-v")
        add("INFO", "git_remote", ("remote: " + remotes.splitlines()[0].split()[1]) if remotes.strip() else "no git remote is set (the evaluators need read access to a hosted repository)")
    return res


def exit_code(res: list, final: bool) -> int:
    """1 when there is a FAIL, and with --final also when anything is still PENDING."""
    return 1 if any(r.level == "FAIL" or (final and r.level == "PENDING") for r in res) else 0


def format_lines(res) -> list:
    """One line per result, in aligned columns. The key column is as wide as the longest key: it was a fixed 17, and 'guide_placeholders' (18) and 'sample_plans_review' (19) ran into their messages."""
    w = max((len(r.key) for r in res), default=0) + 2
    return [f"  {r.level:<8}{r.key:<{w}}{r.text}" for r in res]


def main() -> int:
    ap = argparse.ArgumentParser(description="The gate for the Stage 2 source-code deliverable.", epilog=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--final", action="store_true", help="the freeze-day mode: PENDING counts as FAIL; git must be clean and tagged")
    ap.add_argument("--root", default=str(HERE.parent), help="the repository (default: this one)")
    ap.add_argument("--deadline", default=DEADLINE, help=f"ISO time of the deadline (default {DEADLINE})")
    ap.add_argument("--no-history", action="store_true", help="skip the git history search (faster on a big repository)")
    args = ap.parse_args()
    res = run_checks(Path(args.root), args.final, args.deadline, history=not args.no_history)
    print(f"Ankur Saathi submission check ({'FINAL' if args.final else 'normal'} mode), repository {Path(args.root).resolve()}\n")
    for line in format_lines(res):
        print(line)
    n = {k: sum(1 for r in res if r.level == k) for k in ("FAIL", "PENDING", "WARN")}
    bad = exit_code(res, args.final)
    print(f"\nRESULT: {n['FAIL']} FAIL, {n['PENDING']} PENDING, {n['WARN']} WARN" + ("" if not bad else ("  <-- fix the FAIL lines" + (" (and the PENDING ones: this is --final)" if args.final and n['PENDING'] else ""))))
    if not bad and not n["PENDING"]:
        print("Everything this check can see is in order. It cannot see: that the live link works, that the video is public, or that the evaluators have read access.")
    return bad


if __name__ == "__main__":
    sys.exit(main())
