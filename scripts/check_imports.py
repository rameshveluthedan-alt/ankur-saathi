#!/usr/bin/env python3
"""
Does this Python environment have every package the code uses?   python scripts/check_imports.py [--all]   (from the repository root)

Importing the app is not enough: some packages are imported only when a feature is used (Pillow when a photo arrives, openpyxl when an Excel
register is uploaded), so a missing one would pass an import test and then fail for a teacher. This reads the SOURCE of the backend, the
prompts and the scripts, finds every third-party import wherever it is (inside a function too), and tries each one.

  * MISSING    a package the code needs and the environment lacks: add it to backend/requirements.txt (the pip name is shown). Exit code 1.
  * optional   imported inside try/except ImportError: the code copes without it (a feature is simply unavailable). Reported, exit code 0.

It judges what RUNS IN PRODUCTION: the app (backend/app), the prompts, and the job scripts the container uses. The development scripts (review packs, passage
import, embeddings, the photo scorer) need more packages and are not in the container; --all includes them too.

Use it on the environment a container will have: create a clean one from requirements.txt, then run this in it (deploy/DEPLOY.md, step 6).
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):          # a pipe on Windows uses a legacy code page that cannot print Hindi
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import ast
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DIRS = ["backend/app", "prompts"]
RUNTIME_SCRIPTS = {"auth_admin.py", "create_test_teachers.py", "demo_progress.py", "nightly_reset.py", "ai_usage.py", "anchor_common.py", "batch_generate.py"}
LOCAL_DIRS = ["backend", "backend/app", "prompts", "scripts"]            # where our own modules live (the code adds these to sys.path)
PIP_NAME = {"PIL": "pillow", "dateutil": "python-dateutil", "multipart": "python-multipart", "yaml": "pyyaml", "jose": "python-jose",
            "jwt": "pyjwt", "bs4": "beautifulsoup4", "dotenv": "python-dotenv", "sklearn": "scikit-learn", "cv2": "opencv-python"}


def local_names():
    names = set()
    for d in LOCAL_DIRS:
        p = os.path.join(ROOT, d)
        if os.path.isdir(p):
            for e in os.listdir(p):
                names.add(e[:-3] if e.endswith(".py") else e)
    return names


class Finder(ast.NodeVisitor):
    def __init__(self):
        self.found = []                 # (module, optional)
        self.optional_depth = 0

    def visit_Try(self, node):
        handles_import = any(h.type is None or any(n in ast.dump(h.type) for n in ("ImportError", "ModuleNotFoundError", "Exception")) for h in node.handlers)
        for child in node.body:
            if handles_import:
                self.optional_depth += 1
            self.visit(child)
            if handles_import:
                self.optional_depth -= 1
        for part in (node.handlers, node.orelse, node.finalbody):
            for child in part:
                self.visit(child)

    def visit_Import(self, node):
        for a in node.names:
            self.found.append((a.name.split(".")[0], self.optional_depth > 0))

    def visit_ImportFrom(self, node):
        if node.level == 0 and node.module:
            self.found.append((node.module.split(".")[0], self.optional_depth > 0))


def main():
    std, local = set(sys.stdlib_module_names), local_names()
    include_all = "--all" in sys.argv
    needs = {}                                                           # module -> {"files": set, "optional": bool}
    for d in SOURCE_DIRS + ["scripts"]:
        for dirpath, _, files in os.walk(os.path.join(ROOT, d)):
            if "__pycache__" in dirpath or os.sep + "tests" in dirpath:
                continue
            for f in files:
                if not f.endswith(".py"):
                    continue
                if d == "scripts" and not include_all and f not in RUNTIME_SCRIPTS:
                    continue
                path = os.path.join(dirpath, f)
                try:
                    tree = ast.parse(open(path, encoding="utf-8").read())
                except SyntaxError as e:
                    print(f"  SYNTAX ERROR in {os.path.relpath(path, ROOT)}: {e}")
                    return 1
                fnd = Finder()
                fnd.visit(tree)
                for mod, optional in fnd.found:
                    if mod in std or mod in local or mod.startswith("_"):
                        continue
                    n = needs.setdefault(mod, {"files": set(), "optional": True})
                    n["files"].add(os.path.relpath(path, ROOT).replace("\\", "/"))
                    n["optional"] = n["optional"] and optional              # optional only if EVERY use of it is optional
    missing, optional_missing = [], []
    for mod in sorted(needs):
        if importlib.util.find_spec(mod) is None:
            (optional_missing if needs[mod]["optional"] else missing).append(mod)
    print(f"Python {sys.version.split()[0]}: {len(needs)} third-party packages are imported by the " + ("whole code base (--all)." if include_all else "code that runs in production."))
    for mod in sorted(needs):
        status = "MISSING " if mod in missing else ("optional, not installed" if mod in optional_missing else "ok")
        files = sorted(needs[mod]["files"])
        print(f"  {status:<24} {mod:<16} {files[0]}" + (f" (+{len(files) - 1} more)" if len(files) > 1 else ""))
    if missing:
        print("\nNOT READY. Add these to backend/requirements.txt, then install them: " + ", ".join(PIP_NAME.get(m, m) for m in missing))
        return 1
    if optional_missing:
        print("\nOK, but these optional packages are not installed, so the feature that uses each is unavailable: " + ", ".join(PIP_NAME.get(m, m) for m in optional_missing))
    else:
        print("\nOK: every package the code imports is installed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
