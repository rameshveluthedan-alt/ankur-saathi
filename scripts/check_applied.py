"""
Which of the recent bundles are in this working copy? Prints OK or MISSING for each, with the bundle that holds it, and what to do about it.

    python scripts\\check_applied.py

It looks for a marker in each file (a function name or a sentence that every later version of the file still contains), so a bundle that was extracted, and then overwritten by an OLDER bundle, shows up as MISSING.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

# (bundle, what it is, file, marker or None = the file must exist)
CHECKS = [
    ("v27l", "tolerant JSON and one retry", "backend/app/services/model_json.py", None),
    ("v27s", "the CFU top-up call", "backend/app/services/plan_service.py", "async def topup_cfu"),
    ("v27t", "spot-error verdicts", "backend/app/services/cfu.py", "def _verdict"),
    ("v28a", "each group's skill: the proposal", "backend/app/services/group_skills.py", "async def propose"),
    ("v28b", "the re-teach as the group's main block", "prompts/orchestrate.py", "RETEACH_MAIN_RULES"),
    ("v28b", "the re-teach as the group's main block", "backend/app/services/plan_service.py", "def stamp_reteach_main"),
    ("v28c", "the teachers' review: two show-me questions per group", "backend/app/services/cfu.py", "MIN_ITEMS, MAX_ITEMS = 2, 2"),
    ("v28c", "the teachers' review: the routine on the lesson screen", "pwa/src/screens/YojanaScreen.jsx", "20 सेकंड"),
    ("v28d", "try_reteach.py reads backend/.env", "scripts/try_reteach.py", "os.chdir"),
    ("v28e", "a wrong answer that is a right answer in the lesson", "backend/app/services/cfu.py", "def _lesson_results"),
    ("v28e", "no kit-limit sentence in the script", "prompts/orchestrate.py", "NEVER explain the kit size"),
    ("v28f", "vague 'listen for' removed", "backend/app/services/cfu.py", "def _without_vague_listen"),
    ("v28f", "no person who 'did' something", "prompts/cfu_prompt.py", "No PERSON at all"),
    ("v28g", "the Plan screen's per-group panel", "pwa/src/screens/PlanScreen.jsx", "GroupSkillsPanel"),
    ("v28g", "the ladder endpoint", "backend/app/api/routes.py", "/plan/ladder/"),
    ("v28h", "the app's recommendation from the evidence", "backend/app/services/group_skills.py", "def recommend"),
    ("v28h", "the recommendation on the panel", "pwa/src/components/GroupSkillsPanel.jsx", "recommendation"),
    ("v28i", "which skills a group may take", "backend/app/services/group_skills.py", "async def allowed_skills"),
    ("v28i", "a re-teach is the same skill as yesterday", "backend/app/services/plan_service.py", "check_reteach_same_skill"),
    ("v28i", "the panel offers only sensible skills", "pwa/src/components/GroupSkillsPanel.jsx", "skillChoices"),
    ("v28j", "each group's skill at the top right", "pwa/src/services/planSummary.js", None),
    ("v28j", "each group's skill at the top right", "pwa/src/screens/YojanaScreen.jsx", "PlanGroupSkills"),
    ("v28k", "the re-teach block's label", "pwa/src/services/reteachInfo.js", None),
    ("v28k", "the re-teach block's label", "pwa/src/screens/YojanaScreen.jsx", "ReteachNote"),
    ("v28o", "the demo seeds yesterday's plan", "scripts/demo_progress.py", "def seed_yesterday_plan"),
    ("v28o", "the log lists what the model wrote", "backend/app/services/cfu.py", "_STAMPED_BY_CODE"),
    ("v28o", "the runbook updates the nightly job after a redeploy", "deploy/DEPLOY.md", "jobs update ankur-nightly"),
    ("v28q", "a group is never ahead of / behind the day's skill (server)", "backend/app/services/group_skills.py", "def fits_day"),
    ("v28q", "a group is never ahead of / behind the day's skill (screen)", "pwa/src/services/groupSkills.js", "fitsDay"),
    ("v28r", "yesterday's re-teach is remembered (server)", "backend/app/services/group_skills.py", "def reteached_groups"),
    ("v28r", "yesterday's re-teach is shown (screen)", "pwa/src/components/GroupSkillsPanel.jsx", "previous-reteach"),
    ("v28r", "status lists the stored plans", "scripts/demo_progress.py", "Plans stored for the last 14 days"),
    ("v28s", "the group panel is a drawer in the bottom bar", "pwa/src/components/GroupSkillsDrawer.jsx", None),
    ("v28s", "the group panel is a drawer in the bottom bar", "pwa/src/screens/PlanScreen.jsx", "GroupSkillsDrawer"),
    ("v28s", "the real-screen test", "pwa/tests/plan_screen.dom.test.mjs", None),
    ("v28t", "tapping the tab you are on takes that screen back to its start", "pwa/src/services/tabs.js", None),
    ("v28t", "tapping the tab you are on takes that screen back to its start", "pwa/src/App.jsx", "tabTap"),
    ("v28t", "the Plan screen goes back to choosing a skill", "pwa/src/screens/PlanScreen.jsx", "TAB_RESELECT_EVENT"),
    ("v28u", "the re-teach box is the decision and the skill follows it", "pwa/src/services/groupSkills.js", "export function toggleReteach"),
    ("v28u", "the re-teach box is the decision and the skill follows it", "pwa/src/components/GroupSkillsPanel.jsx", "toggleReteach"),
    ("v29e", "a show-me cannot be two wrong right-or-wrong lines (a child guesses)", "backend/app/services/cfu.py", "def _is_wrong_line"),
    ("v29e", "...and the CFU rules ask for a question the child works out", "prompts/cfu_prompt.py", "WORK OUT an answer"),
    ("v29e", "the guessable-question rule is tested", "backend/tests/test_cfu_guessable.py", None),
    ("v29d", "a two-digit addition skill never reaches 100: the show-me rules", "backend/app/services/cfu.py", "max_result"),
    ("v29d", "...and the worksheet repair replaces a total of 100 or more", "backend/app/services/plan_service.py", "three-digit numbers are a later"),
    ("v29d", "the number range note in the plan prompt", "prompts/orchestrate.py", "def range_note"),
    ("v29d", "the I Do uses the SAME sum for the wrong and the right working", "prompts/orchestrate.py", "do the SAME sum again correctly"),
    ("v29d", "the show-me avoids results already on the board", "prompts/cfu_prompt.py", "already written on the board"),
    ("v29d", "the two-digit limit is tested", "backend/tests/test_two_digit_limit.py", None),
    ("v29c", "two questions of one group never share a right answer", "backend/app/services/cfu.py", "def right_answer"),
    ("v29c", "the top-up is told which answers are taken", "prompts/cfu_prompt.py", "The right answers of the questions above"),
    ("v29c", "the You Do points to the worksheet, and no sum is repeated", "prompts/orchestrate.py", "do NOT write problems of your own"),
    ("v29c", "the board problems are separate lines", "pwa/src/components/BoardWork.jsx", "gridTemplateColumns"),
    ("v29c", "the answers check is tested", "backend/tests/test_cfu_answers.py", None),
    ("v29b", "the listen-for wrong answers are computed and checked by code", "backend/app/services/cfu.py", "def verified_listen"),
    ("v29b", "the listen-for check is tested", "backend/tests/test_cfu_listen_for.py", None),
    ("v29a", "the carry strip is a tab above the tens column (no empty box; the other headers grow)", "backend/app/templates/worksheet.html", "pv-header-tall"),
    ("v29a", "the board-work line under the You Do", "pwa/src/screens/YojanaScreen.jsx", "BoardWork"),
    ("v29a", "the board-work line reads the worksheet itself", "pwa/src/services/boardWork.js", "export function boardProblems"),
    ("v28z", "yesterday's skill is offered only as a re-teach, plain only while it is the current choice", "pwa/src/services/groupSkills.js", "export function visibleChoices"),
    ("v28z", "the model is told the truth when a group is on yesterday's skill as a normal lesson", "prompts/orchestrate.py", "NORMAL lesson"),
    ("v28y", "one dropdown holds both decisions (skill and re-teach)", "pwa/src/services/groupSkills.js", "export function chooseOption"),
    ("v28y", "one dropdown holds both decisions (skill and re-teach)", "pwa/src/components/GroupSkillsPanel.jsx", "restore-suggestion"),
    ("v28x", "curated skill bridges: the loader", "scripts/load_bridges.py", None),
    ("v28x", "curated skill bridges: the app consults them first", "backend/app/services/group_skills.py", "async def curated_pick"),
    ("v28x", "curated skill bridges: the table", "db/schema/11_skill_bridges.sql", None),
    ("v28x", "curated skill bridges: the nightly job loads them without stopping the reset", "scripts/nightly_reset.py", "fatal=False"),
    ("v28x", "curated skill bridges: the starter proposals", "db/seeds/content/07_skill_bridges.starter.csv", None),
    ("v28l", "the front-end tests run on Windows", "pwa/tests/group_skills.test.mjs", "pathToFileURL"),
    ("v28l", "the front-end tests run on Windows", "pwa/tests/plan_summary.test.mjs", "pathToFileURL"),
    ("v28l", "the front-end tests run on Windows", "pwa/tests/reteach_note.test.mjs", "pathToFileURL"),
]


def kind_of(bundle, rel):
    """older: a bundle before the v28 series. current: any file of the v28 series (the one package v28p-current holds the current version of all of them)."""
    return "older" if bundle.startswith("v27") else "current"


VERSION = "v29e, 24 Oct: lists the bundles v27l to v29e; the package v29e-current replaces v28m to v29d"


def main():
    status, why, kinds = {}, {}, {}
    for bundle, what, rel, marker in CHECKS:
        p = ROOT / rel
        if not p.exists():
            ok, note = False, f"{rel}: the file is not there"
        elif marker is None:
            ok, note = True, ""
        else:
            ok = marker in p.read_text(encoding="utf-8", errors="replace")
            note = "" if ok else f"{rel}: does not contain '{marker}' ({what})"
        status[bundle] = status.get(bundle, True) and ok
        if not ok:
            why.setdefault(bundle, []).append(note)
            kinds.setdefault(kind_of(bundle, rel), set()).add(bundle)
    print(f"check_applied.py ({VERSION})")
    print(f"Working copy: {ROOT}\n")
    for bundle in sorted(status):
        print(f"  {bundle:<5} {'OK' if status[bundle] else 'MISSING'}")
        for note in why.get(bundle, []):
            print(f"          - {note}")
    # the packages: v28p-current holds the current version of every file of the v28 series, so it is 'in' when every v28 row is OK
    series = [b for b in status if b.startswith("v28")]
    package_ok = all(status[b] for b in series)
    print(f"\n  PACKAGE v29e-current (every file of v28a to v29e, current):  {'OK' if package_ok else 'BEHIND'}")
    print()
    if not kinds:
        print("Everything listed is in this working copy.")
        return 0
    if "current" in kinds:
        print("Something of the v28 series is behind (or was put back by an older bundle). Apply v29e-current.tar.gz ONCE: it holds the current version of every file of the series, so the order does not matter.")
        print("    tar -xzf <downloads>\\v29e-current.tar.gz -C <this folder>")
        print("  and do NOT extract v28a to v29d afterwards: each holds older copies of some of the same files and would put them back.")
    if "older" in kinds:
        print(f"Older bundles missing: {', '.join(sorted(kinds['older']))}. Apply each, oldest first, with  tar -xzf <downloads>\\<bundle>.tar.gz -C <this folder>")
    print("Run this check again afterwards: python scripts\\check_applied.py")
    return 1


if __name__ == "__main__":
    sys.exit(main())
