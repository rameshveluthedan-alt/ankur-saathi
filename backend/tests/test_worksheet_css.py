"""
The printed worksheet must fit the page. A box with width: 100% AND a margin on the left or right is wider than its container, and its edge is cut
off when printed (the word-problem answer boxes lost their right border this way: width 100% plus a 28 px left margin). This reads the template's
styles and refuses that combination. No browser needed; it also shows that it WOULD have caught the original rule.

    python backend/tests/test_worksheet_css.py
"""
import re
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[1] / "app" / "templates" / "worksheet.html"
failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


def nonzero(v: str) -> bool:
    return v.strip() not in ("0", "0px", "0pt", "0mm", "auto", "") and not re.fullmatch(r"0(\.0+)?[a-z%]*", v.strip())


def too_wide_rules(css: str) -> list:
    """Selectors whose rule has a full width AND a horizontal margin."""
    bad = []
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)                       # a comment inside a rule must not be read as a declaration
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        decl = dict((k.strip().lower(), v.strip().lower()) for k, _, v in (d.partition(":") for d in body.split(";")) if k.strip())
        if decl.get("width") != "100%":
            continue
        left = right = "0"
        if "margin" in decl:
            parts = decl["margin"].replace("!important", "").split()
            if len(parts) == 1: left = right = parts[0]
            elif len(parts) == 2: left = right = parts[1]
            elif len(parts) == 3: left = right = parts[1]
            elif len(parts) >= 4: right, left = parts[1], parts[3]
        left = decl.get("margin-left", left)
        right = decl.get("margin-right", right)
        if nonzero(left) or nonzero(right):
            bad.append(" ".join(sel.split()))
    return bad


css = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", TEMPLATE.read_text(encoding="utf-8"), re.S))
check("the template has styles to check", len(css) > 2000)
check("no rule combines width: 100% with a horizontal margin (it would be wider than its page)", too_wide_rules(css) == [], too_wide_rules(css))
check("the check would have caught the original bug (width 100% with a 28px left margin)", too_wide_rules(".answer-box-wide { width: 100%; min-height: 36px; margin: 4px 0 4px 28px; }") == [".answer-box-wide"])
check("...even when a comment sits inside the rule (as the fixed template's does)", too_wide_rules(".y { /* note: width: 100% would overflow */ width: 100%; margin: 0 0 0 28px; }") == [".y"])
check("...and a margin-left on its own", too_wide_rules(".x { width: 100%; margin-left: 12px; }") == [".x"])
check("...but not a box that fills the space after its margin (width: auto), or one with no side margin",
      too_wide_rules(".a { display: block; width: auto; margin: 4px 0 4px 28px; } .b { width: 100%; margin: 4px 0; } .c { width: 100%; margin: 0 auto 0 0; }") == [])
check("the template asks for A4 paper, not Letter", re.search(r"@page\s*\{[^}]*size:\s*A4", css) is not None)

if failures:
    print(f"\nFAILED ({len(failures)})")
    sys.exit(1)
print("\nOK: nothing in the worksheet template is wider than its page")
