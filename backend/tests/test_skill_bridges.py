"""
Curated skill bridges: the reviewer's pick for the Beginners and the Proficients comes FIRST, the graph rule is the fallback, and the loader only ever stores valid, approved rows.

    cd backend && python tests/test_skill_bridges.py --env-file .env

Everything runs inside a transaction that is ROLLED BACK at the end (the table is created and dropped inside it): your data is not changed.
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import asyncio
import contextlib
import csv
import io
import json
import os
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("AUTH_MODE", "off")
os.environ["SKILL_BRIDGES"] = "on"            # this test is about the bridges (the other tests run with them off: they pin what the RULE gives)
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "prompts"), str(ROOT / "backend"), str(HERE)]
import load_bridges as lb

failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def R(skill, b=None, p=None, approved=True, line=2, note=""):
    return {"line": line, "skill_id": skill, "raw_skill": skill, "predecessor_id": b, "successor_id": p, "note": note, "approved": approved}


async def main():
    import _scratch
    import anthropic
    from app.services import group_skills as gs, plan_service
    db = await _scratch.connect()
    DEMO = "10000001-aaaa-bbbb-cccc-000000000001"
    today = date.today()
    tr = db.transaction()
    await tr.start()
    try:
        ddl = lb.DDL.read_text(encoding="utf-8")
        ins = lambda s, b, p, ok=True: db.execute("INSERT INTO skill_bridges (skill_id, predecessor_id, successor_id, note, approved) VALUES ($1, $2, $3, 'test', $4) ON CONFLICT (skill_id) DO UPDATE SET predecessor_id = $2, successor_id = $3, approved = $4", s, b, p, ok)

        print("the table is OPTIONAL: the app works exactly as before without it (the cloud has none until the loader has run)")
        await db.execute("DROP TABLE IF EXISTS skill_bridges")
        check("without the table the rule decides: N3.3.1 gives the Beginners N2.2.2 and the Proficients N3.5.2 (perimeter)", (await gs.derived_beginner_id(db, "N3.3.1"), await gs.derived_proficient_id(db, "N3.3.1")) == ("N2.2.2", "N3.5.2"))
        lad0 = await gs.ladder(db, "N3.3.1")
        check("...and the ladder and the advance options work too", lad0["beginner"]["id"] == "N2.2.2" and (await gs.next_options(db, "N3.3.1"))[0]["id"] == "N3.5.2")
        await db.execute(ddl)
        await db.execute(ddl)
        check("the table definition can be run again and again (CREATE TABLE IF NOT EXISTS)", await lb.table_exists(db))
        check("an EMPTY table changes nothing", (await gs.derived_beginner_id(db, "N3.3.1"), await gs.derived_proficient_id(db, "N3.3.1")) == ("N2.2.2", "N3.5.2"))

        print("\nan approved bridge comes FIRST")
        await ins("N3.3.1", "N2.3.2", "N3.3.6")
        check("N3.3.1: the Beginners get 2-digit addition with carrying (N2.3.2) and the Proficients multi-step word problems (N3.3.6), not perimeter", (await gs.derived_beginner_id(db, "N3.3.1"), await gs.derived_proficient_id(db, "N3.3.1")) == ("N2.3.2", "N3.3.6"))
        lad = await gs.ladder(db, "N3.3.1")
        check("the ladder shows them, and they come first in the lists the teacher chooses from", lad["beginner"]["id"] == "N2.3.2" and lad["proficient"]["id"] == "N3.3.6" and lad["options"]["beginner"][0]["id"] == "N2.3.2" and lad["options"]["proficient"][0]["id"] == "N3.3.6")
        check("the graph's other candidates are still offered after them (nothing is taken away)", "N2.2.2" in [x["id"] for x in lad["options"]["beginner"]] and "N3.5.2" in [x["id"] for x in lad["options"]["proficient"]])
        check("'Advance' for a group that was on N3.3.1 now proposes the reviewer's successor first, not perimeter", (await gs.next_options(db, "N3.3.1"))[0]["id"] == "N3.3.6")
        await ins("N2.3.3", "N1.3.2", "N2.3.4", ok=False)
        check("a row that is NOT approved is ignored: the rule decides", await gs.derived_beginner_id(db, "N2.3.3") == "N1.2.4")
        await ins("N2.3.3", None, "N2.3.4", ok=True)
        check("a side left empty follows the rule, the other side is the reviewer's", (await gs.derived_beginner_id(db, "N2.3.3"), await gs.derived_proficient_id(db, "N2.3.3")) == ("N1.2.4", "N2.3.4"))
        await ins("N0.2.1", "N0.2.1", "N0.2.2")
        check("'stay on the skill itself' for the Beginners is honoured, and the day's skill is not listed among its own foundations", await gs.derived_beginner_id(db, "N0.2.1") == "N0.2.1" and "N0.2.1" not in [x["id"] for x in (await gs.ladder(db, "N0.2.1"))["options"]["beginner"]])

        print("\nthe grade rule is kept even if a wrong row got into the table (belt and braces)")
        await ins("N2.3.2", "N3.3.1", "N0.2.1")
        check("the Beginners are never AHEAD of the day's skill, the Proficients never BEHIND it: such a pick is ignored and the rule decides", (await gs.derived_beginner_id(db, "N2.3.2"), await gs.derived_proficient_id(db, "N2.3.2")) == ("N2.3.1", "N3.3.1"))
        await db.execute("DELETE FROM skill_bridges WHERE skill_id = 'N2.3.2'")

        print("\na pick the graph does not connect is still OFFERED and ALLOWED (the reviewer decided)")
        before = (await gs.allowed_skills(db, DEMO, "numeracy", today, "N1.2.1"))["proficient"]
        await ins("N1.2.1", "N0.2.1", "N1.2.3")
        after = (await gs.allowed_skills(db, DEMO, "numeracy", today, "N1.2.1"))["proficient"]
        check("N1.2.3 is not among N1.2.1's dependents in the graph, so it was not allowed; with the bridge it is", "N1.2.3" not in before and "N1.2.3" in after)
        check("...and it heads the Proficients' list", (await gs.ladder(db, "N1.2.1"))["options"]["proficient"][0]["id"] == "N1.2.3")
        refused = None
        await db.execute("DELETE FROM skill_bridges WHERE skill_id = 'N1.2.1'")
        try:
            await gs.clean_group_skills(db, "numeracy", "N1.2.1", {"proficient": "N1.2.3"}, allowed=await gs.allowed_skills(db, DEMO, "numeracy", today, "N1.2.1"))
        except gs.GroupSkillError as e:
            refused = str(e)
        check("(without the bridge the same choice is refused by the server)", refused is not None)
        await ins("N1.2.1", "N0.2.1", "N1.2.3")
        check("(with it the server accepts the choice)", (await gs.clean_group_skills(db, "numeracy", "N1.2.1", {"proficient": "N1.2.3"}, allowed=await gs.allowed_skills(db, DEMO, "numeracy", today, "N1.2.1"))) == {"proficient": "N1.2.3"})

        print("\n'Advance' proposes the reviewer's successor")
        snap = {"beginner": {"count": 1, "rolls": [1], "target": "N2.3.1"}, "progressor": {"count": 1, "rolls": [2], "target": "N2.3.2"}, "proficient": {"count": 1, "rolls": [3], "target": "N3.3.1"}}
        await db.execute("""INSERT INTO daily_plans (teacher_id, plan_date, domain_id, selected_competency_id, plan_content, explainability, groups_snapshot) VALUES ($1, $2, 'numeracy', 'N2.3.2', '{}'::jsonb, $3::jsonb, $4::jsonb)
                            ON CONFLICT (teacher_id, plan_date, domain_id) DO UPDATE SET explainability = EXCLUDED.explainability, groups_snapshot = EXCLUDED.groups_snapshot, plan_content = EXCLUDED.plan_content""",
                         DEMO, today - timedelta(days=1), json.dumps({"teacher_decision_proficient": "advance", "teacher_decision_beginner": "advance"}), json.dumps(snap))
        g = (await gs.propose(db, DEMO, "numeracy", today))["groups"]
        check("the Proficients, who were on N3.3.1 and chose Advance, are proposed N3.3.6 (the reviewer's pick), not perimeter", g["proficient"]["proposed"]["id"] == "N3.3.6", g["proficient"]["proposed"])
        check("the Beginners' Advance from N2.3.1 is still N2.3.2", g["beginner"]["proposed"]["id"] == "N2.3.2")
        await db.execute("UPDATE skill_bridges SET approved = FALSE WHERE skill_id = 'N3.3.1'")
        check("with the bridge un-approved it is perimeter again (the rule)", (await gs.propose(db, DEMO, "numeracy", today))["groups"]["proficient"]["proposed"]["id"] == "N3.5.2")
        await db.execute("UPDATE skill_bridges SET approved = TRUE WHERE skill_id = 'N3.3.1'")

        print("\nthe plan itself uses the bridge (a stand-in model)")
        SAMPLE = json.loads((ROOT / "db" / "seeds" / "sample_plans" / "N2.3.2.json").read_text(encoding="utf-8"))

        class Fake:
            def __init__(self):
                self.calls, self.prompt = 0, ""

            async def create(self, **kw):
                self.calls += 1
                self.prompt = kw["messages"][0]["content"]
                return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(SAMPLE, ensure_ascii=False))], stop_reason="end_turn", usage=SimpleNamespace(input_tokens=6000, output_tokens=9000))
        fake = Fake()
        anthropic.AsyncAnthropic = lambda **kw: SimpleNamespace(messages=fake)
        levels = {1: "beginner", 2: "beginner", 3: "beginner", 4: "progressor", 5: "progressor", 6: "progressor", 7: "proficient", 8: "proficient"}
        tid, _school = await _scratch.make_class(db, {r: (lv, lv) for r, lv in levels.items()}, grade="grade_2")
        with contextlib.redirect_stdout(io.StringIO()):
            await plan_service.generate_dainik_yojana(db, tid, "N3.3.1", "numeracy", today + timedelta(days=40))
        row = await db.fetchrow("SELECT groups_snapshot FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2", tid, today + timedelta(days=40))
        snapshot = json.loads(row["groups_snapshot"]) if isinstance(row["groups_snapshot"], str) else row["groups_snapshot"]
        check("a plan for N3.3.1 puts the Beginners on N2.3.2, the Progressors on N3.3.1 and the Proficients on N3.3.6", {k: v["target"] for k, v in snapshot.items()} == {"beginner": "N2.3.2", "progressor": "N3.3.1", "proficient": "N3.3.6"}, {k: v["target"] for k, v in snapshot.items()})
        check("...and the model's request names those skills", fake.calls == 1 and "N3.3.6" in fake.prompt and "N2.3.2" in fake.prompt)

        print("\nthe switch: SKILL_BRIDGES=off ignores the table (a wrong row can be neutralised in one command, without a deploy)")
        os.environ["SKILL_BRIDGES"] = "off"
        check("with the switch off, N3.3.1 follows the RULE although a bridge is approved (Beginners N2.2.2, Proficients N3.5.2)", (await gs.derived_beginner_id(db, "N3.3.1"), await gs.derived_proficient_id(db, "N3.3.1")) == ("N2.2.2", "N3.5.2"))
        os.environ["SKILL_BRIDGES"] = "OFF"
        check("(any capitals)", await gs.derived_beginner_id(db, "N3.3.1") == "N2.2.2")
        os.environ["SKILL_BRIDGES"] = "on"
        check("switched on again, the bridge is used", await gs.derived_beginner_id(db, "N3.3.1") == "N2.3.2")

        print("\nthe loader reads a table tolerantly")
        tmp = Path(tempfile.mkdtemp())
        write_csv(tmp / "w.csv", lb.FIELDS, [["N3.3.1 Adds 3-digit numbers", "N2.3.2 Adds two 2-digit numbers (carry)", "N3.3.6", "demo fix", "yes"], ["N2.3.3", "N1.3.2", "N2.3.4", "", ""], ["N2.3.1", "N1.3.1", "N2.3.2", "n", "OK"], ["", "", "", "", ""]])
        rows = lb.read_working(tmp / "w.csv")
        check("an id is taken from a cell that also holds a name; yes / OK mean approved; an empty cell does not; an empty line is skipped", [(r["skill_id"], r["predecessor_id"], r["approved"]) for r in rows] == [("N3.3.1", "N2.3.2", True), ("N2.3.3", "N1.3.2", False), ("N2.3.1", "N1.3.1", True)])
        try:
            lb.read_working(tmp / "your_table.csv")
            msg = ""
        except SystemExit as e:
            msg = str(e)
        check("a file that is not there says so plainly, and says what to do (the 'your_table.csv' mistake)", "File not found" in msg and "your_table.csv" in msg and "Google Sheet" in msg and "--init" in msg, msg[:120])

        print("\nthe loader refuses a wrong row, and only a wrong row")
        await db.execute("DELETE FROM skill_bridges")
        bad = [R("N3.3.1", "N2.3.2", "N3.3.6", line=2), R("N9.9.9", "N2.3.2", None, line=3), R("N2.3.2", "L1.3.1", None, line=4), R("N2.3.2", "N3.3.1", None, line=5), R("N2.3.3", None, None, line=6), R("N2.3.1", "N1.3.1", None, line=7),
               R("N2.3.1", "N1.3.1", None, line=8), R("N1.2.1", None, "N1.2.3", line=9), R("N2.3.4", "N2.3.3", None, approved=False, line=10), R("N2.3.2", "N2.3.1", "N0.2.1", line=11)]
        good, errors, warnings, unapproved = await lb.validate(db, bad)
        by = {line: msg for line, _s, msg in errors}
        check("a skill that does not exist, another subject, the Beginners AHEAD of the skill, nobody named, a row approved twice, and the Proficients BELOW the skill are each an ERROR", set(by) == {3, 4, 5, 6, 8, 11}, sorted(by))
        check("the valid rows are kept: N3.3.1, the first N2.3.1 and N1.2.1", sorted(r["skill_id"] for r in good) == ["N1.2.1", "N2.3.1", "N3.3.1"], [r["skill_id"] for r in good])
        check("a row nobody approved is neither loaded nor an error, and is counted", unapproved == 1 and 10 not in by)
        check("a pick the graph does not connect is LOADED with a note (N1.2.1 -> N1.2.3): the reviewer decided", any("N1.2.1" in w and "N1.2.3" in w for w in warnings), warnings)

        print("\nloading makes the table hold exactly the approved rows")
        rows_ok = [R("N3.3.1", "N2.3.2", "N3.3.6", note="a"), R("N2.3.1", "N1.3.1", "N2.3.2", note="b")]
        check("first load: both added", await lb.sync(db, rows_ok) == {"inserted": 2, "updated": 0, "unchanged": 0, "removed": 0})
        check("again: nothing changes (it can be run every night)", await lb.sync(db, rows_ok) == {"inserted": 0, "updated": 0, "unchanged": 2, "removed": 0})
        rows_ok[0] = R("N3.3.1", "N2.3.2", "N3.5.2", note="a")
        check("a changed decision is updated", await lb.sync(db, rows_ok) == {"inserted": 0, "updated": 1, "unchanged": 1, "removed": 0} and await gs.derived_proficient_id(db, "N3.3.1") == "N3.5.2")
        before_rows = await db.fetchval("SELECT count(*) FROM skill_bridges")
        c = await lb.sync(db, rows_ok[:1], dry_run=True)
        check("a DRY RUN says what would change and changes nothing", c["removed"] == 1 and await db.fetchval("SELECT count(*) FROM skill_bridges") == before_rows)
        check("a bridge no longer approved is REMOVED (the file is the source of truth)", (await lb.sync(db, rows_ok[:1]))["removed"] == 1 and await db.fetchval("SELECT count(*) FROM skill_bridges") == 1)
        await db.execute("DROP TABLE skill_bridges")
        check("the table is created by the loader when it is missing (the cloud's first run)", (await lb.sync(db, rows_ok))["inserted"] == 2 and await lb.table_exists(db))
        await db.execute("DROP TABLE skill_bridges")
        check("a dry run on a database without the table creates nothing", (await lb.sync(db, rows_ok, dry_run=True))["inserted"] == 2 and not await lb.table_exists(db))
        await db.execute(ddl)

        print("\nthe reviewer's sheet")
        review = ["skill", "Beginners (predecessor)", "Proficients (successor)", "REVIEWER_decision_Beginners", "REVIEWER_decision_Proficients", "REVIEWER_notes", "source"]
        write_csv(tmp / "review.csv", review, [
            ["N3.3.1 Adds 3-digit numbers with regrouping", "N2.3.2 Adds two 2-digit numbers", "N3.3.6 Solves multi-step word problems", "OK", "ok", "agreed", "TABLE"],
            ["N2.3.3 Subtracts 2-digit numbers", "N1.3.2 Subtracts single-digit numbers", "N2.3.4 Subtracts with borrowing", "", "N2.3.4", "", "TABLE"],
            ["N1.2.1 Recites number names 1 to 100", "N0.2.1 Recites 1 to 20", "N1.2.3 Reads numerals", "", "", "", "TABLE"],
            ["N2.2.2 Understands place value", "", "", "ok", "", "", "NEEDS DECISION"],
            ["N2.3.2 Adds 2-digit with regrouping", "N2.3.1 Adds without regrouping", "N3.3.1 Adds 3-digit", "maybe", "N3.3.1", "", "TABLE"]])
        decided, problems = lb.read_review(tmp / "review.csv")
        d = {r["skill_id"]: r for r in decided}
        check("OK accepts the proposal beside it; a skill id is the decision; an empty cell is no decision", d["N3.3.1"]["predecessor_id"] == "N2.3.2" and d["N3.3.1"]["successor_id"] == "N3.3.6" and d["N2.3.3"]["predecessor_id"] is None and d["N2.3.3"]["successor_id"] == "N2.3.4")
        check("a row with no decision at all is skipped (it keeps following the rule)", "N1.2.1" not in d)
        check("'OK' where there is no proposal, and a word that is neither OK nor an id, are reported as PROBLEMS, not guessed", len(problems) == 2 and any("N2.2.2" in p for p in problems) and any("maybe" in p for p in problems), problems)
        base = [R("N2.3.3", "N1.3.2", None, approved=False, note="starter"), R("N1.2.1", "N0.2.1", "N1.2.3", approved=False, note="starter")]
        merged = {r["skill_id"]: r for r in lb.merge(base, decided)}
        check("merging replaces the skills the reviewer decided and keeps every other row as it was", merged["N2.3.3"]["approved"] and merged["N2.3.3"]["successor_id"] == "N2.3.4" and not merged["N1.2.1"]["approved"] and merged["N1.2.1"]["note"] == "starter")

        print("\nthe working file and the starter")
        old_argv, old_cwd = sys.argv, os.getcwd()
        wf = tmp / "work.csv"
        sys.argv = ["load_bridges.py", "--init", "--csv", str(wf)]
        with contextlib.redirect_stdout(io.StringIO()):
            await lb.main()
        starter = lb.read_working(lb.STARTER)
        check("--init creates the working file from the starter, with NOTHING approved", wf.exists() and len(lb.read_working(wf)) == len(starter) > 30 and not any(r["approved"] for r in lb.read_working(wf)))
        write_csv(wf, lb.FIELDS, [["N2.3.3", "N1.3.2", "N2.3.4", "mine", "yes"]])
        sys.argv = ["load_bridges.py", "--init", "--csv", str(wf)]
        with contextlib.redirect_stdout(io.StringIO()):
            await lb.main()
        check("--init never overwrites a working file you have edited", len(lb.read_working(wf)) == 1)
        sys.argv = ["load_bridges.py", "--from-review", str(tmp / "review.csv"), "--csv", str(wf)]
        with contextlib.redirect_stdout(io.StringIO()):
            code = await lb.main()
        after = {r["skill_id"]: r for r in lb.read_working(wf)}
        check("--from-review writes the decisions into the working file (the problems make the exit code 1)", code == 1 and after["N3.3.1"]["approved"] and after["N2.3.3"]["successor_id"] == "N2.3.4", code)
        sys.argv, _ = old_argv, os.chdir(old_cwd)
        all_rows = [dict(r, approved=True) for r in starter]
        g2, e2, _w2, _u2 = await lb.validate(db, all_rows)
        check(f"EVERY proposal in the starter ({len(starter)}) is valid against the knowledge base (ids exist, same subject, the grade rule): approving them all would load without a single error", not e2 and len(g2) == len(starter), e2[:3])

        print("\nthe nightly job: a failed bridge load never stops the demo reset")
        import nightly_reset as nr
        bad_script = tmp / "fails.py"
        bad_script.write_text("import sys; sys.exit(3)\n", encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            rc = nr.run("a step that fails", [str(bad_script)], [], fatal=False)
        check("a step marked not fatal returns its exit code and the reset goes on", rc == 3)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                nr.run("a step that fails", [str(bad_script)], [])
            fatal_stopped = False
        except SystemExit as e:
            fatal_stopped = e.code == 3
        check("a step that is fatal (the demo reset itself) still stops everything, as before", fatal_stopped)
    finally:
        await tr.rollback()
        await db.close()
    if failures:
        print(f"\nFAILED ({len(failures)})")
        sys.exit(1)
    print("\nOK: an approved bridge comes first and the rule is the fallback, the grade rule holds, the loader stores only valid approved rows, and the table is optional")


if __name__ == "__main__":
    asyncio.run(main())
