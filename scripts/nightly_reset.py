#!/usr/bin/env python3
"""
The nightly reset of the public demo (run by a Cloud Run job, scheduled by Cloud Scheduler: see deploy/DEPLOY.md):

  1. the "Change PIN" practice account is put back (its PIN, its lock, its must-change flag), because reviewers are meant to change and lock it;
  2. the demo teacher's progress is cleared and seeded again up to YESTERDAY (India time), because the "consider re-assessing" flags
     are only shown for the last 14 days, so the demo would otherwise slowly go empty.

It does not touch real accounts, reviewers' new schools or the AI usage meter. The database settings come from DB_HOST, DB_USER,
DB_PASSWORD, DB_NAME (and DB_PORT) in the environment, or from --env-file when run on your own machine.

    python scripts/nightly_reset.py [--env-file backend/.env]
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):          # a pipe on Windows uses a legacy code page that cannot print Hindi
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import argparse
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))


def yesterday_india() -> str:
    return (datetime.now(timezone(timedelta(hours=5, minutes=30))).date() - timedelta(days=1)).isoformat()


def run(label, args, env_args):
    print(f"--- {label}", flush=True)
    r = subprocess.run([sys.executable, *args, *env_args], cwd=os.path.dirname(HERE))
    if r.returncode != 0:
        print(f"!!! '{label}' failed with exit code {r.returncode}: the reset is incomplete.", flush=True)
        sys.exit(r.returncode)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--env-file", help="read DB_* settings from this file (on your own machine; in the cloud they are environment variables)")
    ap.add_argument("--end-date", default=None, help="the last seeded day, YYYY-MM-DD (default: yesterday in India)")
    args = ap.parse_args()
    env_args = ["--env-file", args.env_file] if args.env_file else []
    day = args.end_date or yesterday_india()
    run("the practice account is restored", [os.path.join(HERE, "auth_admin.py"), "restore-practice"], env_args)
    run("the demo progress is cleared", [os.path.join(HERE, "demo_progress.py"), "reset", "--yes"], env_args)
    run(f"the demo progress is seeded up to {day}", [os.path.join(HERE, "demo_progress.py"), "seed", "--end-date", day, "--yes"], env_args)
    print("--- the demo is reset", flush=True)


if __name__ == "__main__":
    main()
