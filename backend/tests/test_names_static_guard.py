"""
Names must never reach the AI. This test fails if any module that builds a request to the AI (or a printed worksheet) so
much as mentions children's names. It is structural: it does not need a database or an API key.

    python backend/tests/test_names_static_guard.py

See docs/PRIVACY.md. The companion test, test_names_never_reach_ai.py, checks the real outgoing request for a canary name.
"""

import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):          # a pipe on Windows uses a legacy code page that cannot print Hindi
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")
import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SERVICES = ROOT / "backend" / "app" / "services"

# modules that build a request to the AI, a prompt, or a printed sheet: they must know nothing about names
NEVER = [SERVICES / "plan_service.py", SERVICES / "worksheet_service.py", ROOT / "backend" / "app" / "templates" / "worksheet.html"] + sorted((ROOT / "prompts").glob("*.py"))
# the only modules that may touch the child_names table
TABLE_USERS = {"names_service.py", "register_service.py"}
# the only modules that may import names_service
SERVICE_USERS = {"names_service.py", "register_service.py", "progress_service.py", "review_service.py", "routes.py"}

failures = []

for path in NEVER:
    text = path.read_text(encoding="utf-8")
    for word in ("child_names", "names_service"):
        if re.search(rf"\b{word}\b", text):
            failures.append(f"{path.relative_to(ROOT)} mentions {word}: nothing that builds an AI request may know about names")
    if path.suffix == ".html" and re.search(r"नाम|Name\s*:|student", text, re.I):
        failures.append(f"{path.relative_to(ROOT)} has a name field: a photo of the sheet goes to the AI, so the sheet must carry only a roll or class number")

for path in sorted((ROOT / "backend" / "app").rglob("*.py")) + sorted((ROOT / "prompts").glob("*.py")) + sorted((ROOT / "scripts").glob("*.py")):
    text = path.read_text(encoding="utf-8")
    if re.search(r"\bchild_names\b", text) and path.name not in TABLE_USERS:
        failures.append(f"{path.relative_to(ROOT)} reads child_names but is not one of {sorted(TABLE_USERS)}")
    if re.search(r"import names_service|from app\.services\.names_service|names_service\.", text) and path.name not in SERVICE_USERS:
        failures.append(f"{path.relative_to(ROOT)} uses names_service but is not one of {sorted(SERVICE_USERS)}")

# the photo-analysis service builds the AI request, so inside it names may appear ONLY after the AI has answered (to scrub the reply)
tree = ast.parse((SERVICES / "review_service.py").read_text(encoding="utf-8"))
funcs = {n.name: n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
call_vision = ast.get_source_segment((SERVICES / "review_service.py").read_text(encoding="utf-8"), funcs["call_vision"])
if "names" in call_vision.lower().replace("filenames", ""):
    failures.append("review_service.call_vision (the function that sends the request) refers to names")
analyse = funcs["analyse_worksheet_photos"]
sent_line = next(n.lineno for n in ast.walk(analyse) if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "call_vision")
early = [n.lineno for n in ast.walk(analyse) if (isinstance(n, ast.Name) and n.id == "names_service") or (isinstance(n, ast.ImportFrom) and n.module and "names_service" in str(n.names[0].name) + n.module)]
if any(line <= sent_line for line in early):
    failures.append("analyse_worksheet_photos uses names before the request is sent")

# the officer (MLO) report must never carry names
progress = (SERVICES / "progress_service.py").read_text(encoding="utf-8")
mlo = ast.get_source_segment(progress, {n.name: n for n in ast.walk(ast.parse(progress)) if isinstance(n, ast.AsyncFunctionDef)}["export_mlo_report_csv"])
if re.search(r"names?_service|\bchild_names\b|\bname\b", mlo, re.I):
    failures.append("export_mlo_report_csv refers to names: the officer report is roll numbers only")

if failures:
    print("FAILED")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print(f"OK: {len(NEVER)} request-building modules know nothing about names; the officer report is roll numbers only; "
      f"child_names is read only by {sorted(TABLE_USERS)}")
