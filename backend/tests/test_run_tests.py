"""
The test runner (scripts/run_tests.py) must report what really happened: a crash after passing checks is a PROBLEM, a skipped part is shown, and the --env-file path is made absolute.

    cd backend && python tests/test_run_tests.py        (no database needed)
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent.parent / "scripts")]
import run_tests as rt

failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


good = "  OK  one\n  OK  two\n\nOK: all fine\n"
j = rt.judge(0, good)
check("a clean suite is good; the closing 'OK:' line is not counted as a check", j["good"] and j["ok"] == 2 and j["fail"] == 0 and not j["crashed"], j)
j = rt.judge(1, "  OK  one\n  OK  two\nTraceback (most recent call last):\n  File x\nValueError: boom\n")
check("checks that PASSED and then a crash is a PROBLEM (a passing count alone would hide it)", not j["good"] and j["crashed"] and j["ok"] == 2, j)
j = rt.judge(1, "  OK  one\n  FAIL two\nFAILED (1)\n")
check("a failing check is a PROBLEM", not j["good"] and j["fail"] == 1, j)
j = rt.judge(1, "  OK  one\n")
check("a non-zero return code with no other sign is still a PROBLEM", not j["good"], j)
j = rt.judge(0, "  OK  one\n  SKIPPED the database checks: no pgvector\nOK so far\n")
check("a skipped part is reported but is not a problem", j["good"] and len(j["skipped"]) == 1 and "pgvector" in j["skipped"][0], j)
j = rt.judge(0, "FAIL at the left margin\n  OK  one\n")
check("a line that starts with FAIL counts as a failing check, indented or not (strict is the safe direction)", j["fail"] == 1 and not j["good"], j)
j = rt.judge(1, "  OK  one\nFAILED (1)\n")
check("...but the closing 'FAILED (n)' summary is not counted a second time (the return code still makes it a PROBLEM)", j["fail"] == 0 and not j["good"], j)
check("the word FAIL inside a line (not at its start) is not a failing check", rt.judge(0, "  OK  the FAIL path is covered\n")["fail"] == 0)
check("a suite with no check lines at all but return code 0 is good", rt.judge(0, "all done\n")["good"])
d = Path(tempfile.mkdtemp())
(d / ".env").write_text("DB_NAME=x\n", encoding="utf-8")
cwd = os.getcwd()
try:
    os.chdir(d)
    p = rt.resolve_env_file(".env")
finally:
    os.chdir(cwd)
check("the --env-file path is made absolute from where the user typed it (the tests run from backend/, where a relative path would be wrong)", Path(p).is_absolute() and Path(p).samefile(d / ".env"), p)
check("no env file given gives None", rt.resolve_env_file(None) is None)
try:
    rt.resolve_env_file("/nonexistent/backend/.env")
    raised = False
except FileNotFoundError as e:
    raised = "nonexistent" in str(e)
check("a missing env file is refused with its path, not ignored", raised)

print("\nthe Python it runs under (found on the first run on a real machine: the system Python was used, 22 suites crashed with one traceback each)")
check("a Python that has what it is asked for reports nothing missing; one that lacks a package names it", rt.missing_modules(sys.executable, ["json", "os"]) == [] and rt.missing_modules(sys.executable, ["json", "no_such_package_xyz", "also_missing_abc"]) == ["no_such_package_xyz", "also_missing_abc"])
check("a Python that cannot even start counts everything as missing (never as fine)", rt.missing_modules("/no/such/python", ["json", "os"]) == ["json", "os"])
tree = Path(tempfile.mkdtemp())
check("with no virtual environment there is nothing to switch to", rt.find_venv_python(tree) is None)
(tree / "backend" / "venv" / "Scripts").mkdir(parents=True); (tree / "backend" / "venv" / "Scripts" / "python.exe").write_text("x")
check("the backend's virtual environment is found where the README creates it (Windows layout)", rt.find_venv_python(tree).endswith("python.exe") and "venv" in rt.find_venv_python(tree))
tree2 = Path(tempfile.mkdtemp()); (tree2 / "backend" / "venv" / "bin").mkdir(parents=True); (tree2 / "backend" / "venv" / "bin" / "python").write_text("x")
check("...and the Linux and macOS layout", rt.find_venv_python(tree2).endswith("python"))
have = lambda lacking: (lambda py: lacking.get(py, []))
py, note, err = rt.choose_interpreter("SYS", "VENV", have({}))
check("the current Python has everything: it is used, with nothing said", py == "SYS" and note == "" and err is None)
py, note, err = rt.choose_interpreter("SYS", "VENV", have({"SYS": ["anthropic", "fastapi"]}))
check("the current Python lacks packages but the backend's environment has them: that one is used, and the note says why", py == "VENV" and "anthropic" in note and "VENV" in note and err is None, note)
py, note, err = rt.choose_interpreter("SYS", None, have({"SYS": ["anthropic"]}))
check("lacking packages and no environment to switch to: an ERROR that names the packages, says to activate the environment (PowerShell and Linux) or to install, and runs nothing", py is None and "anthropic" in err and "Activate.ps1" in err and "source backend/venv/bin/activate" in err and "pip install -r backend/requirements.txt openpyxl tzdata" in err, err)
py, note, err = rt.choose_interpreter("SYS", "VENV", have({"SYS": ["anthropic"], "VENV": ["anthropic"]}))
check("the environment lacks them too: an error, not a silent switch to a broken one", py is None and err is not None)
link = Path(tempfile.mkdtemp()); (link / "real_python").write_text("x")
try:
    os.symlink(link / "real_python", link / "venv_python"); os.symlink(link / "real_python", link / "system_python")
    can_link = True
except (OSError, NotImplementedError, AttributeError):         # Windows allows links only in Developer Mode or as administrator (its venv Python is a real file, so this case is a Linux and macOS one)
    can_link = False
if can_link:
    py, note, err = rt.choose_interpreter(str(link / "system_python"), str(link / "venv_python"), have({str(link / "system_python"): ["anthropic"]}))
    check("a virtual environment's Python is a LINK to the system one: it must still be switched to (found on the real machine: comparing the targets made them look identical, so it never switched)", py == str(link / "venv_python") and err is None, (py, err))
else:
    print("  SKIPPED the symbolic link case: this system does not allow creating links (Windows without Developer Mode)")
py, note, err = rt.choose_interpreter("SAME", "SAME", have({"SAME": ["anthropic"]}))
check("the environment IS the current Python and it lacks them: an error (no pointless 'switch' to itself)", py is None and err is not None)
check("openpyxl and tzdata are advice, NOT requirements: a Python without them is not refused (the suites run without them)", "openpyxl" not in rt.BACKEND_MODULES and "tzdata" not in rt.BACKEND_MODULES and set(rt.OPTIONAL_MODULES) == {"openpyxl", "tzdata"})
check("the package names it checks are the backend's (fastapi, asyncpg, anthropic, pydantic_settings, PIL...), not a guess", all(m in rt.BACKEND_MODULES for m in ("fastapi", "asyncpg", "anthropic", "pydantic_settings", "PIL", "httpx", "jinja2")))

print("\nsaying why, in a line")
crash = "Traceback (most recent call last):\n  File \"x.py\", line 3, in <module>\n    import anthropic\nModuleNotFoundError: No module named 'anthropic'\n"
check("a crash is explained by the last line of its traceback", rt.reason_of(crash) == ["ModuleNotFoundError: No module named 'anthropic'"], rt.reason_of(crash))
check("failing checks are explained by their own lines (up to three)", rt.reason_of("  OK  a\n  FAIL b went wrong\n  FAIL c too\n  FAIL d\n  FAIL e\nFAILED (4)\n") == ["FAIL b went wrong", "FAIL c too", "FAIL d"])
check("a failing check wins over a traceback (it is the more useful line)", rt.reason_of("  FAIL b\n" + crash) == ["FAIL b"])
check("no message at all still says something", rt.reason_of("") == ["exit code was not 0 (no message)"])
groups = rt.summarise([(f"test_{i}", crash) for i in range(22)] + [("test_hindi_style", "  OK a\n  FAIL the style rule\nFAILED (1)\n")])
check("22 suites that crash for ONE reason become ONE line listing them; a different failure stays its own", len(groups) == 2 and len(groups["ModuleNotFoundError: No module named 'anthropic'"]) == 22 and groups["FAIL the style rule"] == ["test_hindi_style"], {k: len(v) for k, v in groups.items()})

if failures:
    print(f"\nFAILED ({len(failures)})")
    sys.exit(1)
print("\nOK: the runner tells a real pass from a hidden crash, shows skips, and passes the env file on as an absolute path")
