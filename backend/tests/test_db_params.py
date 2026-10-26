"""
Which database the scripts and the test helpers connect to (scripts/anchor_common.db_params).

Found by following the README as a stranger: a helper that built its arguments from an EMPTY list ignored --env-file and never looked for .env, so it talked to the default
database while the app under test (which reads .env) used another: "already registered", foreign-key errors. Now, with no --env-file, the helper finds the same .env the app reads,
in the same order as the app (the environment first, then .env); an explicit --env-file still wins over the environment, as the scripts document.

    cd backend && python tests/test_db_params.py        (no database needed)
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import argparse
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent.parent / "scripts")]
import anchor_common as ac

failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


def params(argv, cwd, env):
    """db_params as a script or a test helper would see it: the given arguments, the given working folder, ONLY the given environment variables."""
    ap = argparse.ArgumentParser()
    ac.add_db_args(ap)
    saved_cwd, saved_env = os.getcwd(), dict(os.environ)
    try:
        os.chdir(cwd)
        for k in [k for k in os.environ if k.startswith("DB_")]:
            del os.environ[k]
        os.environ.update(env)
        return ac.db_params(ap.parse_args(argv))
    finally:
        os.chdir(saved_cwd)
        os.environ.clear()
        os.environ.update(saved_env)


def folder(env_text=None, sub=None):
    d = Path(tempfile.mkdtemp(prefix="dbp_"))
    target = d / sub if sub else d
    target.mkdir(parents=True, exist_ok=True)
    if env_text is not None:
        (target / ".env").write_text(env_text, encoding="utf-8")
    return d


ENV = "DB_HOST=filehost\nDB_PORT=6000\nDB_USER=fileuser\nDB_PASSWORD=filepw\nDB_NAME=filedb\n# DB_NAME=commented\n"
print("no --env-file: the .env the app would read is found")
d = folder(ENV)
p = params([], d, {})
check("run from a folder that has a .env (backend/): it is used", (p["host"], p["port"], p["user"], p["password"], p["database"]) == ("filehost", 6000, "fileuser", "filepw", "filedb"), p)
d = folder(ENV, sub="backend")
check("run from the repository root (the .env is in ./backend): it is used", params([], d, {})["database"] == "filedb")
d = folder()
p = params([], d, {})
found = ac.default_env_file()
check("no .env anywhere near: the built-in defaults, as before (the repository's own backend/.env, if it exists here, is not what this checks)", found is not None or (p["host"], p["user"], p["database"]) == ("127.0.0.1", "postgres", "ankur_saathi"), p)
print("\nthe order: the same as the app")
d = folder(ENV)
check("with no --env-file, an environment variable beats the .env (like the app's settings)", params([], d, {"DB_NAME": "fromenv", "DB_PASSWORD": "envpw"}) ["database"] == "fromenv" and params([], d, {"DB_NAME": "fromenv", "DB_PASSWORD": "envpw"})["password"] == "envpw")
check("...and a setting the environment does not have still comes from the .env", params([], d, {"DB_NAME": "fromenv"})["host"] == "filehost")
other = folder("DB_NAME=explicitdb\nDB_PASSWORD=explicitpw\n")
check("an explicit --env-file beats the environment (as the scripts document)", params(["--env-file", str(other / ".env")], d, {"DB_NAME": "fromenv"})["database"] == "explicitdb")
check("a --db-name option beats everything", params(["--env-file", str(other / ".env"), "--db-name", "cli"], d, {"DB_NAME": "fromenv"})["database"] == "cli")
print("\na wrong --env-file path is NOT silent")
import contextlib, io
buf = io.StringIO()
with contextlib.redirect_stderr(buf):
    p = params(["--env-file", "backend/.env"], folder(), {"DB_NAME": "fromenv"})
check("an --env-file that does not exist prints a warning that names the path and the risk, and the environment is used", "backend/.env was not found" in buf.getvalue() and "DIFFERENT database" in buf.getvalue() and p["database"] == "fromenv", buf.getvalue()[:160])
buf2 = io.StringIO()
with contextlib.redirect_stderr(buf2):
    params(["--env-file", str(folder(ENV) / ".env")], folder(), {})
check("an --env-file that exists prints nothing", buf2.getvalue() == "")

print("\nrobustness")
check("a commented line is ignored, and quotes around a value are removed", ac.parse_env_file(str(folder('DB_NAME="quoted"\n# DB_USER=nobody\n') / ".env")) == {"DB_NAME": "quoted"})
check("an empty or missing path gives no settings instead of an error", ac.parse_env_file("") == {} and ac.parse_env_file("/nonexistent/.env") == {} and ac.parse_env_file(str(folder())) == {})
check("the password is read from .env, so a helper no longer connects without it", params([], folder("DB_PASSWORD=dummy-s3cret\n"), {})["password"] == "dummy-s3cret")

if failures:
    print(f"\nFAILED ({len(failures)})")
    sys.exit(1)
print("\nOK: scripts and test helpers connect to the same database as the app, in the same order of priority")
