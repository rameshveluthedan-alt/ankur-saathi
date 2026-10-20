#!/usr/bin/env python3
"""
Run this BEFORE `git commit`:   python scripts/precommit_check.py
Puzzled about why .env is or is not ignored?:   python scripts/precommit_check.py --explain

It looks at what is staged (`git add`) and refuses (exit code 1) if anything must never be in git:
  * an environment file (.env, but not .env.example), a private key, a virtual environment, node_modules, compiled files;
  * an API key, a session secret or a database password with a real value in an added line;
  * an environment file on disk that git is not ignoring (one `git add .` away from being committed).
It WARNS (and exits 0) about things to look at: photos (children's work must never be committed), and files over 5 MB.

It prints file names and line numbers, never the secret itself. Needs only Python and git.
"""

import os
import re
import subprocess
import sys

BIG = 5 * 1024 * 1024
FORBIDDEN_PATH = [
    (r"(^|/)\.env(\.[^/]*)?$", "an environment file (it holds passwords and keys)"),
    (r"(^|/)(venv|\.venv|env)/", "a Python virtual environment"),
    (r"(^|/)node_modules/", "node_modules"),
    (r"(^|/)__pycache__/|\.pyc$", "compiled Python files"),
    (r"\.(pem|key|p12|pfx)$|(^|/)id_(rsa|ed25519)", "a private key"),
    (r"(^|/)\.aws/|(^|/)credentials\.json$|service[-_]account.*\.json$", "a cloud credential file"),
]
ALLOWED_ENV = re.compile(r"\.env\.(example|sample|template)$")
PHOTO = re.compile(r"\.(jpe?g|png|heic|webp|tiff?)$", re.I)
PHOTO_OK = re.compile(r"(^|/)(pwa/public|pwa/src/assets|docs/screenshots)/|(^|/)(icon|logo|favicon)[^/]*\.(png|jpg|jpeg|webp)$", re.I)
SECRET_PATTERNS = [
    (re.compile(r"sk-ant-[A-Za-z0-9_\-]{16,}"), "an Anthropic API key"),
    (re.compile(r"\b(ANTHROPIC_API_KEY|OPENAI_API_KEY|VOYAGE_API_KEY|SESSION_SECRET|DB_PASSWORD|POSTGRES_PASSWORD)\s*[=:]\s*['\"]?([^\s'\"#]{6,})"), "a key or password"),
    (re.compile(r"postgres(?:ql)?://[^:/\s@]+:([^@\s]{3,})@"), "a database password in a connection URL"),
]
PLACEHOLDER = re.compile(r"change[-_ ]?me|your[-_]|<.*>|xxx|\.\.\.|dummy|example|placeholder|long-random|secret-here|os\.environ|\$\{|%\(|get_settings|settings\.|\bNone\b|\bnull\b", re.I)


# a value that is itself a dummy, as in `postgresql://user:password@localhost/db` in an example file
DUMMY_VALUE = re.compile(r"^(password|passwd|pass|pwd|secret|postgres|user|username|test|root|admin|yourpassword|mypassword)$", re.I)


def git(*args):
    r = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        sys.exit(f"git {' '.join(args)} failed: {r.stderr.strip()[:200]}")
    return r.stdout


def explain():
    """`--explain`: say, for every environment file on disk, whether git tracks it, ignores it (and by which rule), or would take it. Prints no secrets."""
    root = git("rev-parse", "--show-toplevel").strip()
    os.chdir(root)
    print(f"Git repository root: {root}")
    print(f"You are running this from: {os.getcwd()}  (the repository root, because the script moved there)")
    rules = []
    for dirpath, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "venv", ".venv", "__pycache__", "dist")]
        if ".gitignore" in files:
            gp = os.path.relpath(os.path.join(dirpath, ".gitignore"), ".").replace("\\", "/")
            raw = open(gp, "rb").read()
            enc = "UTF-16 (git IGNORES this file)" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") or b"\x00" in raw[:4] else ("UTF-8 with a BOM" if raw[:3] == b"\xef\xbb\xbf" else "UTF-8/ASCII")
            lines = [l.strip() for l in raw.decode("utf-8-sig", "replace").splitlines()]          # utf-8-sig drops a byte-order mark, which would hide the first rule
            env_lines = [l for l in lines if re.search(r"(^|/|\*)\.env", l) and not l.startswith("#")]      # rules about .env files, not 'venv/' 
            print(f"\n{gp}: {len(lines)} lines, saved as {enc}")
            for l in env_lines:
                hint = ""
                if l.endswith("/"):
                    hint = "   <-- a trailing / means FOLDERS ONLY: it does not match a file named .env. Write it as: .env"
                elif l.startswith("/") and dirpath == ".":
                    hint = "   <-- a leading / anchors to this folder only: it does not match backend/.env. Write it as: .env  (or backend/.env)"
                print(f"   rule mentioning env: {l!r}{hint}")
                rules.append(l)
            if not env_lines:
                print("   (no rule mentions env)")
    found = []
    for dirpath, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "venv", ".venv", "__pycache__", "dist")]
        for f in files:
            if re.fullmatch(r"\.env(\.[A-Za-z]+)?", f) and not ALLOWED_ENV.search(f):
                found.append(os.path.relpath(os.path.join(dirpath, f), ".").replace("\\", "/"))
    print("\nEnvironment files on disk:" + ("" if found else " none found (is the file really named .env? Windows can hide an extension such as .env.txt)"))
    for p in found:
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", p], capture_output=True).returncode == 0
        r = subprocess.run(["git", "check-ignore", "-v", "--no-index", p], capture_output=True, text=True, encoding="utf-8", errors="replace")
        rule = r.stdout.strip().split("\t")[0] if r.stdout.strip() else ""
        if tracked:
            print(f"  {p}: TRACKED by git (ignore rules do not apply). Run: git rm --cached {p}")
        elif rule:
            print(f"  {p}: IGNORED, by {rule}.  Safe.  (If `git check-ignore -v {p}` printed nothing for you, run it as its own command, not on the same line as another)")
        else:
            print(f"  {p}: NOT IGNORED and untracked: `git add .` WOULD take it. Fix the rule above, or add this line to .gitignore:  {p}")
    return 0


def main():
    if "--explain" in sys.argv:
        return explain()
    fails, warns = [], []
    root = git("rev-parse", "--show-toplevel").strip()
    os.chdir(root)
    staged = [l for l in git("diff", "--cached", "--name-only", "--diff-filter=ACMR").splitlines() if l]

    # repo-level problems, checked even when nothing is staged
    env_re = re.compile(r"(^|/)\.env(\.[^/]*)?$")
    for p in git("ls-files").splitlines():
        if env_re.search(p) and not ALLOWED_ENV.search(p):
            n = len([l for l in git("log", "--oneline", "--all", "--", p).splitlines() if l])
            fails.append(f"{p}: is TRACKED by git. Ignore rules never apply to a tracked file, so .gitignore does not protect it. "
                         f"Run `git rm --cached {p}` (the file stays on disk). It is in {n} commit(s) of history: see the notes in the answer about removing it and about rotating the passwords and keys")
    for dirpath, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "venv", ".venv", "__pycache__", "dist")]
        if ".gitignore" in files:
            gp = os.path.relpath(os.path.join(dirpath, ".gitignore"), ".").replace("\\", "/")
            head = open(gp, "rb").read(4)
            if head[:2] in (b"\xff\xfe", b"\xfe\xff") or b"\x00" in head:
                fails.append(f"{gp}: is saved as UTF-16 (PowerShell's > does this). Git silently IGNORES it, so none of its rules work. "
                             f"Re-save it as UTF-8 (the brackets matter: they read the whole file before rewriting it):  (Get-Content {gp}) | Set-Content -Encoding utf8 {gp}")
    if not staged:
        for f in fails:
            print("  FAIL ", f)
        if fails:
            print(f"\nNOT SAFE ({len(fails)} problem(s)). Nothing is staged, but fix these before you commit.")
            return 1
        print("Nothing is staged. Run `git add <files>` first, then this check.")
        return 0

    grouped, photos, bigs = {}, [], []
    for path in staged:
        for pat, what in FORBIDDEN_PATH:
            m = re.search(pat, path)
            if m and not ALLOWED_ENV.search(path):
                # a whole folder (venv, node_modules...) is reported once with a count, not once per file
                key = (what, path[:m.end()].rstrip("/") if what.split()[0] in ("a", "node_modules", "compiled") and "/" in path[:m.end()] else path)
                grouped[key] = grouped.get(key, 0) + 1
        if PHOTO.search(path) and not PHOTO_OK.search(path):
            photos.append(path)
        try:
            if os.path.getsize(path) > BIG:
                bigs.append(f"{path}: {os.path.getsize(path) // (1024 * 1024)} MB, large for git")
        except OSError:
            pass
    for (what, where), n in grouped.items():
        fails.append(f"{where}: {what}" + (f"  ({n} staged files in it: run `git restore --staged {where}`)" if n > 1 else ""))
    if photos:
        shown = ", ".join(photos[:5]) + (f" and {len(photos) - 5} more" if len(photos) > 5 else "")
        warns.append(f"{len(photos)} image(s): {shown}. Photos of children's work must never be committed; an app icon or a screenshot is fine")
    warns += bigs[:5] + ([f"...and {len(bigs) - 5} more large files"] if len(bigs) > 5 else [])

    # added lines only: what this commit would newly put in the history
    diff = git("diff", "--cached", "-U0", "--no-color")
    current, line_no = None, 0
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            line_no = int(m.group(1)) - 1 if m else 0
        elif line.startswith("+") and not line.startswith("+++"):
            line_no += 1
            text = line[1:]
            for pat, what in SECRET_PATTERNS:
                m = pat.search(text)
                if not m:
                    continue
                value = m.group(m.lastindex) if m.lastindex else m.group(0)
                if PLACEHOLDER.search(text) or PLACEHOLDER.search(value or "") or DUMMY_VALUE.match(value or ""):
                    continue
                fails.append(f"{current}:{line_no}: looks like {what} (value hidden)")
                break

    # an env file on disk that git would pick up with `git add .`
    for dirpath, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "venv", ".venv", "__pycache__", "dist")]
        for f in files:
            if re.fullmatch(r"\.env(\.[a-z]+)?", f) and not ALLOWED_ENV.search(f):
                p = os.path.relpath(os.path.join(dirpath, f), ".").replace("\\", "/")
                tracked = subprocess.run(["git", "ls-files", "--error-unmatch", p], capture_output=True).returncode == 0
                if not tracked and subprocess.run(["git", "check-ignore", "-q", p]).returncode != 0:
                    fails.append(f"{p}: exists on disk and git is NOT ignoring it: add `.env` to .gitignore (and check .gitignore is saved as UTF-8)")

    print(f"Checked {len(staged)} staged file(s).")
    for w in warns:
        print("  WARN ", w)
    for f in fails:
        print("  FAIL ", f)
    if fails:
        print(f"\nNOT SAFE TO COMMIT ({len(fails)} problem(s)). Fix them (git restore --staged <file>), then run this again.")
        return 1
    print("\nOK: nothing secret is staged." + (" Look at the warnings above." if warns else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
