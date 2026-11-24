"""
Reading a class register file (CSV and Excel): no database and no API key needed.

    python backend/tests/test_register_parse.py

The Excel checks run only where openpyxl is installed (the Docker image has it); a damaged Excel file must be refused with a message in both cases.
"""

import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):          # a pipe on Windows uses a legacy code page that cannot print Hindi
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")
import io
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.services import register_service as R

failures = []


def check(name, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f"   {detail}"))
    if not ok:
        failures.append(name)


def refused(data, filename):
    try:
        R.parse_register(data, filename)
    except ValueError as e:
        return str(e)
    return None


TABLE = [("grade", "roll_number", "name", "numeracy_level", "literacy_level"),
         (1, 5, "आशा", "beginner", "progressor"),
         (3, 5, "Ravi", "proficient", "proficient"),
         ("कक्षा 2", "२", "", "शुरुआती", "")]

print("CSV: any of the three separators, with Excel's byte-order mark and Hindi text")
for sep, label in ((",", "comma"), (";", "semicolon"), ("\t", "tab")):
    text = "\ufeff" + "\n".join(sep.join(str(c) for c in r) for r in TABLE) + "\n"
    rows = R.parse_register(text.encode("utf-8"), "r.csv")
    check(f"{label}: 3 children read", len(rows) == 3, len(rows))
    check(f"{label}: Hindi name, Hindi grade and Devanagari roll read", rows[0]["name"] == "आशा" and rows[2]["grade"] == "कक्षा 2" and rows[2]["roll"] == "2", rows)
check("the template has no children in it", R.parse_register(R.TEMPLATE_CSV.encode("utf-8"), "template.csv") == [])

print("Files that cannot be read are refused with a message (the screen shows it), never a server error")
check("an empty file", refused(b"", "x.csv") is not None)
check("a file without the grade and roll_number columns", refused(b"a,b\n1,2\n", "x.csv") is not None)
msg = refused(b"PK\x03\x04 this is not a real workbook", "register.xlsx")
check("a damaged .xlsx", msg is not None and "CSV" in msg, msg)
msg = refused(b"just some text", "register.xlsx")
check("a text file named .xlsx", msg is not None and "CSV" in msg, msg)

try:
    from openpyxl import Workbook
except ImportError:
    print("SKIP  Excel reading (openpyxl is not installed here; the Docker image installs it)")
else:
    print("Excel (.xlsx)")
    wb = Workbook()
    for r in TABLE:
        wb.active.append(list(r))
    buf = io.BytesIO()
    wb.save(buf)
    rows = R.parse_register(buf.getvalue(), "register.xlsx")
    check("3 children read", len(rows) == 3, len(rows))
    check("numeric cells (grade 1, roll 5) read as 1 and 5", rows[0]["grade"] in ("1", "1.0") and rows[0]["roll"] in ("5", "5.0"), rows[0])
    check("Hindi name and Devanagari roll read", rows[0]["name"] == "आशा" and rows[2]["roll"] == "2", rows)
    check("recognised as Excel with no .xlsx in the name", len(R.parse_register(buf.getvalue(), "upload")) == 3)

print()
if failures:
    print(f"{len(failures)} FAILED: {failures}")
    sys.exit(1)
print("ALL PASSED")
