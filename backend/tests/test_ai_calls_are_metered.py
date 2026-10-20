"""
Every paid call to the AI must be checked against the budget BEFORE it is made and metered AFTER. This fails if someone adds a call
that is not, or makes the old unmetered call in prompts/orchestrate.py reachable. No database needed.

    python backend/tests/test_ai_calls_are_metered.py
"""
import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
failures = []


def calls_in(func):
    return [n for n in ast.walk(func) if isinstance(n, ast.Call)]


def line_of(func, attr_path):
    """Line numbers of calls like ai_budget.check / client.messages.create inside a function."""
    hits = []
    for c in calls_in(func):
        f, parts = c.func, []
        while isinstance(f, ast.Attribute):
            parts.append(f.attr)
            f = f.value
        if isinstance(f, ast.Name):
            parts.append(f.id)
        if ".".join(reversed(parts)).endswith(attr_path):
            hits.append(c.lineno)
    return hits


def functions(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {n.name: n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


# 1. where the app calls the AI at all
allowed = {"backend/app/services/plan_service.py", "backend/app/services/review_service.py", "prompts/orchestrate.py"}
for base in ("backend/app", "prompts", "scripts"):
    for path in sorted((ROOT / base).rglob("*.py")):
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        if re.search(r"\.messages\.create\(", path.read_text(encoding="utf-8")) and rel not in allowed:
            failures.append(f"{rel} calls the AI but is not a known, metered call site")

# 2. each known call site checks before and meters after
plan = functions(ROOT / "backend/app/services/plan_service.py")
gen = plan["generate_dainik_yojana"]
creates, checks, records = line_of(gen, "messages.create"), line_of(gen, "ai_budget.check"), line_of(gen, "ai_budget.record")
if not (creates and checks and records and min(checks) < min(creates) < min(records)):
    failures.append("generate_dainik_yojana must call ai_budget.check BEFORE messages.create and ai_budget.record right AFTER it")
rep = plan["repair_stick_overflows"]
creates, guards, recs = line_of(rep, "messages.create"), line_of(rep, "ai_budget.guard"), line_of(rep, "ai_budget.record_ctx")
if not (creates and guards and recs and min(guards) < min(creates) < min(recs)):
    failures.append("repair_stick_overflows must call ai_budget.guard before messages.create and ai_budget.record_ctx after it")

review = functions(ROOT / "backend/app/services/review_service.py")
cv = review["call_vision"]
if not (line_of(cv, "on_usage") or any(isinstance(n, ast.Name) and n.id == "on_usage" for n in ast.walk(cv))):
    failures.append("call_vision must report usage through on_usage as soon as the reply arrives")
creates, onu = line_of(cv, "messages.create"), [n.lineno for n in ast.walk(cv) if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "on_usage"]
if not (creates and onu and min(creates) < min(onu)):
    failures.append("call_vision must call on_usage right after messages.create (before it can fail on an unreadable reply)")
an = review["analyse_worksheet_photos"]
checks, cvs = line_of(an, "ai_budget.check"), line_of(an, "call_vision")
if not (checks and cvs and min(checks) < min(cvs)):
    failures.append("analyse_worksheet_photos must call ai_budget.check before call_vision")

# 3. the old unmetered call in orchestrate.py must stay unreachable from the app
for path in sorted((ROOT / "backend/app").rglob("*.py")) + sorted((ROOT / "scripts").glob("*.py")):
    text = path.read_text(encoding="utf-8")
    for m in re.finditer(r"from orchestrate import \(?([^)]*?)\)?\n(?!\s+\w)", text, re.S):
        if "generate_dainik_yojana" in m.group(1):
            failures.append(f"{path.relative_to(ROOT)} imports orchestrate.generate_dainik_yojana, which makes an UNMETERED call")

if failures:
    print("FAILED")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("OK: every paid call is checked before and metered after, and the old unmetered call is unreachable")
