#!/usr/bin/env python3
"""
Adds ONE line to backend/app/core/config.py: the CFU_ENABLED switch (check-for-understanding questions, docs/CFU.md).

Your config.py is yours (it reads your .env), so it is never shipped whole: this script only inserts the line, keeps everything else and your line endings,
and does nothing if the line is already there.   python scripts/add_cfu_setting.py   (from the repository root)
Without the line the feature still works (it defaults to ON); the line is what lets CFU_ENABLED=false switch it off.
"""
import re
import sys
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "backend" / "app" / "core" / "config.py"
LINE = "cfu_enabled: bool = True                    # check-for-understanding show-me questions in every lesson (docs/CFU.md). false = plans exactly as before"


def main() -> int:
    raw = PATH.read_bytes()
    text = raw.decode("utf-8-sig")
    bom = raw.startswith(b"\xef\xbb\xbf")
    nl = "\r\n" if "\r\n" in text else "\n"
    if re.search(r"^\s+cfu_enabled\s*:", text, re.M):
        print("config.py already has cfu_enabled: nothing to do.")
        return 0
    lines = text.split(nl)
    for pattern in (r"^(\s+)reteach_duration_minutes\s*:", r"^(\s+)default_teaching_minutes\s*:", r"^(\s+)transition_duration_minutes\s*:"):
        for i, l in enumerate(lines):
            m = re.match(pattern, l)
            if m:
                lines.insert(i + 1, m.group(1) + LINE)
                PATH.write_bytes((("\ufeff" if bom else "") + nl.join(lines)).encode("utf-8"))
                print(f"Added cfu_enabled to config.py after line {i + 1}. Everything else is unchanged.")
                return 0
    for i, l in enumerate(lines):                       # no neighbour found: put it just before model_config, inside the class
        if re.match(r"^\s+model_config\s*=", l):
            lines.insert(i, re.match(r"^(\s+)", l).group(1) + LINE + nl.join(["", ""]).rstrip(nl[0]))
            PATH.write_bytes((("\ufeff" if bom else "") + nl.join(lines)).encode("utf-8"))
            print("Added cfu_enabled to config.py before model_config.")
            return 0
    print("Could not find where to put it. Add this line inside class Settings by hand:\n    " + LINE)
    return 1


if __name__ == "__main__":
    sys.exit(main())
