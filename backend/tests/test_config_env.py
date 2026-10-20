"""
The settings must start the server whatever the .env file holds: lines the app does not use (the scripts' DB_* parts, or anything else)
are ignored, and when there is no DATABASE_URL the connection is built from DB_* with the password percent-encoded.

    python backend/tests/test_config_env.py
"""
import os
import sys
import tempfile
from urllib.parse import unquote, urlsplit

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")]
from app.core.config import Settings

failures = []


def check(label, ok):
    print(f"  {'OK ' if ok else 'FAIL'} {label}")
    if not ok:
        failures.append(label)


def settings_from(env_text, env=None):
    """Settings as if backend/.env held env_text (the app reads .env from the folder it starts in)."""
    # a real environment variable beats a line in .env (correctly), so the test must not inherit one from the shell it runs in
    own = ("DB_", "DATABASE_URL", "PIN_HASH_ITERATIONS", "CLAUDE_MAX_TOKENS", "AI_ALLOCATION_USD")
    saved_cwd, saved = os.getcwd(), {k: os.environ.pop(k, None) for k in list(os.environ) if k.startswith(own)}
    try:
        with tempfile.TemporaryDirectory() as d:
            try:
                open(os.path.join(d, ".env"), "w", encoding="utf-8").write(env_text)
                os.chdir(d)
                os.environ.update(env or {})
                return Settings()
            finally:
                os.chdir(saved_cwd)            # BEFORE the folder is deleted: on Windows the current directory cannot be removed
    finally:
        os.chdir(saved_cwd)
        for k in (env or {}):
            os.environ.pop(k, None)
        os.environ.update({k: v for k, v in saved.items() if v is not None})


tricky = "p@ss:w/rd#1"
print("a .env that holds the scripts' DB_* lines (the case that stopped the server)")
s = settings_from(f"DB_HOST=127.0.0.1\nDB_PORT=5432\nDB_USER=postgres\nDB_PASSWORD={tricky}\nDB_NAME=ankur_saathi\nANTHROPIC_API_KEY=x\n")
u = urlsplit(s.database_url)
check("the server starts (no 'extra inputs are not permitted')", True)
check("the URL is built from the parts", u.hostname == "127.0.0.1" and u.port == 5432 and u.username == "postgres" and u.path == "/ankur_saathi")
check("a password with @ : / # survives (it is percent-encoded)", unquote(u.password) == tricky and "@" not in s.database_url.split("@", 1)[1].split("/")[0].replace("127.0.0.1", ""))
print("the other ways of writing it")
check("DATABASE_URL, when given, wins over the parts", settings_from("DATABASE_URL=postgresql://a:b@h:1/d\nDB_HOST=other\n").database_url == "postgresql://a:b@h:1/d")
check("a password-less local setup works", settings_from("DB_HOST=localhost\nDB_USER=me\nDB_NAME=x\n").database_url == "postgresql://me@localhost:5432/x")
check("no .env at all falls back to the local default", settings_from("").database_url == "postgresql://postgres@localhost/ankur_saathi")
check("an environment variable is read as well as the file", settings_from("", {"DB_HOST": "dbhost", "DB_PASSWORD": "pw"}).database_url == "postgresql://postgres:pw@dbhost:5432/ankur_saathi")
print("lines the app does not know")
s = settings_from("SOMETHING_ELSE=1\nCLAUDE_MAX_TOKENS=9000\nAI_ALLOCATION_USD=750\nPIN_HASH_ITERATIONS=1000\nNOT_A_SETTING=yes\n")
check("unknown lines are ignored, known ones still read", s.claude_max_tokens == 9000 and s.ai_allocation_usd == 750 and s.pin_hash_iterations == 1000)

if failures:
    print(f"\nFAILED ({len(failures)})")
    sys.exit(1)
print("\nOK: the server starts whatever the .env holds, and the database URL is built safely")
