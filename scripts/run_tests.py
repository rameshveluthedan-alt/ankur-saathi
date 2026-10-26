#!/usr/bin/env python3
"""
Run every backend test suite, and say for EACH: its return code, how many checks passed and failed, whether it crashed (a traceback) and whether a part was SKIPPED.
A suite is only "OK" when the return code is 0 AND nothing failed AND nothing crashed: a count of passing checks alone can hide a crash after them.

    python scripts/run_tests.py --env-file backend/.env                 every backend suite (they need the database made by db/setup.sh)
    python scripts/run_tests.py --env-file backend/.env --only cfu,auth     only suites whose name contains one of these words
    python scripts/run_tests.py --env-file backend/.env --pwa           and the front-end tests (run `npm install` in pwa first)

It needs the backend's packages. If the Python you start it with does not have them (for example the system Python, with no virtual environment active), it uses backend/venv by itself
when that exists, and otherwise says exactly what to activate or install: it never prints one traceback per suite for a mistake like that.

Exit code 0 when everything is OK, 1 otherwise. The tests never call the AI and never write to your data: they work inside transactions that are rolled back,
or on rows they remove again.
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def judge(returncode: int, text: str) -> dict:
    """What a suite's output says. Pure, so it is tested."""
    lines = text.splitlines()
    ok = sum(1 for l in lines if re.match(r"\s*OK\b", l) and not l.strip().startswith("OK:"))
    fail = sum(1 for l in lines if re.match(r"\s*FAIL\b", l))
    crashed = any("Traceback (most recent call last)" in l for l in lines)
    skipped = [l.strip() for l in lines if "SKIPPED" in l]
    good = returncode == 0 and fail == 0 and not crashed
    return {"ok": ok, "fail": fail, "crashed": crashed, "skipped": skipped, "returncode": returncode, "good": good}


# What the backend's tests import (the names in backend/requirements.txt). A Python without them cannot run most suites: the runner says so in one sentence instead of printing a traceback
# per suite (found on the first run on a real machine: the system Python was used, not the backend's virtual environment).
BACKEND_MODULES = ["fastapi", "uvicorn", "multipart", "asyncpg", "pydantic_settings", "anthropic", "httpx", "jinja2", "dateutil", "PIL"]
# Installed next to them by the README, but NOT needed to run the suites: a note, never a refusal.
OPTIONAL_MODULES = {"openpyxl": "reads Excel class registers", "tzdata": "India time on Windows"}
INSTALL_HINT = "pip install -r backend/requirements.txt openpyxl tzdata"


def missing_modules(python, modules=None):
    """Which of the backend's packages the given Python cannot import. [] when all can."""
    names = modules or BACKEND_MODULES
    code = "import importlib.util as u, sys; print(' '.join(m for m in sys.argv[1:] if u.find_spec(m) is None))"
    try:
        r = subprocess.run([python, "-c", code, *names], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.SubprocessError):          # a Python that cannot start is never "fine": everything counts as missing
        return list(names)
    return r.stdout.split() if r.returncode == 0 else list(names)


def find_venv_python(root):
    """The backend's virtual environment, where the README creates it (backend/venv; backend/.venv also): its Python, or None."""
    for rel in ("backend/venv/Scripts/python.exe", "backend/venv/bin/python", "backend/.venv/Scripts/python.exe", "backend/.venv/bin/python"):
        p = Path(root) / rel
        if p.is_file():
            return str(p)
    return None


def choose_interpreter(current, venv_python, missing=missing_modules):
    """(python to use, a note or '', an error or None). Use the current Python if it has the backend's packages; else the backend's virtual environment if that has them; else an error that says what to do."""
    lacking = missing(current)
    if not lacking:
        return current, "", None
    # compared as GIVEN, not with symlinks followed: a virtual environment's Python is a link to the system Python, so resolving both made them look identical and the switch never happened
    if venv_python and os.path.abspath(venv_python) != os.path.abspath(current) and not missing(venv_python):
        return venv_python, f"This Python ({current}) lacks {', '.join(lacking)}: using the backend's virtual environment instead ({venv_python}).", None
    activate = "backend\\venv\\Scripts\\Activate.ps1 (PowerShell)  or  source backend/venv/bin/activate (Linux, macOS)"
    return None, "", (f"This Python ({current}) cannot import: {', '.join(lacking)}.\n"
                      f"These are the backend's packages. Either activate the backend's virtual environment first:  {activate}\n"
                      f"or install them here:  {INSTALL_HINT}\nThen run this again.")


def reason_of(output, limit=3):
    """Why a suite is a PROBLEM, in one or two lines: its failing checks, or the last line of its traceback."""
    lines = [l.rstrip() for l in output.splitlines() if l.strip()]
    fails = [l.strip() for l in lines if re.match(r"\s*FAIL\b", l)]
    if fails:
        return fails[:limit]
    if any("Traceback (most recent call last)" in l for l in lines):
        tail = [l.strip() for l in lines if not l.startswith(" ")]
        return [tail[-1]] if tail else ["crashed (no message)"]
    return ["exit code was not 0 (no message)"]


def summarise(problems):
    """problems: [(suite, output)]. {reason: [suites]}, so 22 suites that crash for ONE reason are shown as one line."""
    groups = {}
    for name, out in problems:
        for why in reason_of(out):
            groups.setdefault(why, []).append(name)
    return groups


def resolve_env_file(path):
    """The --env-file as an ABSOLUTE path, relative to where the user typed it. The tests run with backend/ as their working folder, where `backend/.env` would not exist: passing the
    path on as typed made every test silently fall back to a default database. None if no file was given; raises FileNotFoundError if it does not exist."""
    if not path:
        return None
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        raise FileNotFoundError(f"the env file {path} was not found (looked for {p})")
    return str(p)


def run(cmd, cwd, env, timeout):
    try:
        r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, f"Traceback (most recent call last): timed out after {timeout} s"


def main() -> int:
    ap = argparse.ArgumentParser(description="Run every backend test suite.", epilog=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--env-file", default=None, help="the .env with the database settings (e.g. backend/.env)")
    ap.add_argument("--only", help="comma-separated words: run only suites whose name contains one")
    ap.add_argument("--pwa", action="store_true", help="also run the front-end tests (pwa/tests/*.test.mjs)")
    ap.add_argument("--timeout", type=int, default=900, help="seconds allowed per suite")
    args = ap.parse_args()

    try:
        args.env_file = resolve_env_file(args.env_file)
    except FileNotFoundError as e:
        print(f"ERROR: {e}. Run this from the repository root, for example:  python scripts/run_tests.py --env-file backend/.env")
        return 2
    python, note, error = choose_interpreter(sys.executable, find_venv_python(ROOT))
    if error:
        print(error)
        return 2
    if note:
        print(note + "\n")
    lacking_optional = missing_modules(python, list(OPTIONAL_MODULES))
    if lacking_optional:
        print("Not installed (optional, the suites still run): " + "; ".join(f"{m} ({OPTIONAL_MODULES[m]})" for m in lacking_optional) + f".  To add them:  pip install {' '.join(lacking_optional)}\n")
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")          # UTF-8 mode: reading a file never depends on the Windows code page (Hindi text)
    env.setdefault("ANTHROPIC_API_KEY", "test-key-never-sent")           # the suites never call the AI; some import code that wants a key to exist
    suites = sorted((ROOT / "backend" / "tests").glob("test_*.py"))
    if args.only:
        words = [w.strip() for w in args.only.split(",") if w.strip()]
        suites = [s for s in suites if any(w in s.stem for w in words)]
    if not suites:
        print("No test suites found.")
        return 1

    problems, skipped_any = [], []
    print(f"{'suite':<34}{'result':<9}{'rc':>3}  {'checks':>7} {'failing':>8}  notes")
    for s in suites:
        cmd = [python, str(s)] + (["--env-file", args.env_file] if args.env_file else [])
        rc, out = run(cmd, ROOT / "backend", env, args.timeout)
        j = judge(rc, out)
        notes = ("CRASHED (traceback)" if j["crashed"] else "") + ("; " if j["crashed"] and j["skipped"] else "") + ("part SKIPPED" if j["skipped"] else "")
        print(f"{s.stem:<34}{'OK' if j['good'] else 'PROBLEM':<9}{rc:>3}  {j['ok']:>7} {j['fail']:>8}  {notes}")
        if not j["good"]:
            problems.append((s.stem, out))
        if j["skipped"]:
            skipped_any.append((s.stem, j["skipped"][0]))

    if args.pwa:
        pwa = ROOT / "pwa"
        print()
        if not (pwa / "node_modules").exists():
            print("Front-end tests SKIPPED: run `npm install` in pwa first.")
        else:
            for t in sorted((pwa / "tests").glob("*.test.mjs")):
                rc, out = run(["node", str(t)], pwa, env, args.timeout)
                if re.search(r"Cannot find package '(jsdom|esbuild)'", out):
                    print(f"{t.name:<34}{'SKIPPED':<9}{rc:>3}  needs `npm install --no-save jsdom` in pwa")
                    continue
                j = judge(rc, out)
                print(f"{t.name:<34}{'OK' if j['good'] else 'PROBLEM':<9}{rc:>3}  {j['ok']:>7} {j['fail']:>8}  {'CRASHED (traceback)' if j['crashed'] else ''}")
                if not j["good"]:
                    problems.append((t.name, out))

    print()
    for name, why in skipped_any:
        print(f"SKIPPED part of {name}: {why[:150]}")
    if problems:
        print(f"\n{len(problems)} suite(s) with a PROBLEM. Why (grouped):")
        for why, names in summarise(problems).items():
            print(f"  {why[:200]}\n      {len(names)} suite(s): {', '.join(names[:6])}{' ...' if len(names) > 6 else ''}")
        print("\nTo see one in full:  python backend/tests/<suite>.py --env-file backend/.env")
        return 1
    print(f"All {len(suites)} backend suite(s) OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
