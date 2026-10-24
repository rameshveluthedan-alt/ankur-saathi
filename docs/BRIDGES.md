# Curated skill bridges

For the day's **anchor skill**, the plan puts the **Beginners** on its *predecessor* and the **Proficients** on its *successor*. Until now the app derived them with a rule (the first hard prerequisite by id, the first dependent in its strand), which is arbitrary where a skill has several candidates (see `docs/GRAPH_AUDIT.md`). A **bridge** is a reviewer's decision that replaces the rule for one skill.

**How the app uses it.** The table `skill_bridges` is consulted FIRST (`group_skills.curated_pick`); where a skill has no approved bridge, or a side is empty, the rule decides, exactly as before. The reviewer's pick is also **offered first** in the Beginners' and Proficients' lists, is **always allowed** (even where the graph does not connect it), and is what **"Advance"** proposes. The grade rule still holds: a pick that would put the Beginners ahead of the day's skill, or the Proficients behind it, is refused by the loader and ignored by the app. The table is **optional**: without it the app works as before.

## The files
| File | What it is |
|---|---|
| `docs/skill_bridges_for_review.csv` | **the reviewer's sheet**: 62 skills, with the candidates by name, what the app does now, a proposal, and empty `REVIEWER_decision_*` columns |
| `db/seeds/content/07_skill_bridges.starter.csv` | the 38 proposals as ids, none approved (shipped with the packages) |
| `db/seeds/content/07_skill_bridges.csv` | **your working file** (created by `--init`, never overwritten by a package). `approved` = yes means it is loaded |
| `scripts/load_bridges.py` | validates and loads |
| `db/schema/11_skill_bridges.sql` | the table (the loader creates it when it is missing) |

## The reviewer
In `skill_bridges_for_review.csv`, for each skill she wants to decide, in **`REVIEWER_decision_Beginners`** and **`REVIEWER_decision_Proficients`** she writes either a **skill id** (that is the decision) or **OK** (accept the proposal in the column beside it). A cell left empty is *no decision*: that side follows the rule. Start with `priority` 1.

## You
```powershell
python scripts\load_bridges.py --init                                          # once
python scripts\load_bridges.py --from-review docs\skill_bridges_for_review.csv # her decisions into the working file
python scripts\load_bridges.py --check --env-file backend\.env                 # validate, change nothing
python scripts\load_bridges.py --dry-run --env-file backend\.env               # what loading would change
python scripts\load_bridges.py --env-file backend\.env                         # load
```
Every approved row is checked against the knowledge base: the ids exist, the same subject, the grade rule, at least one side given, no skill approved twice. A wrong row is reported and **not loaded**; the valid rows still are. A pick that the graph does not connect is loaded with a **note** (the graph may be missing a link: worth a look). Loading makes the table hold **exactly** the approved rows (a bridge you un-approve is removed), so it can be run every night.

## The cloud
The nightly job runs the loader (as a step that **cannot stop** the demo reset), so after a change there is nothing new to do: edit the working file, commit, deploy, point the job at the new image, run it once (see `deploy/DEPLOY.md`). The table is created by the loader. **The switch:** `SKILL_BRIDGES=off` makes the app ignore the table (also `0`, `false`, `no`); `gcloud run services update ankur-saathi --region $REGION --update-env-vars SKILL_BRIDGES=off` is the one-command remedy if a wrong row ever got approved. Remove the variable (or set `on`) to switch the bridges back on.

## Tests
`backend/tests/test_skill_bridges.py` (47 checks, inside a transaction that is rolled back). All the other tests run with the bridges **off** (`_scratch.py` sets `SKILL_BRIDGES=off`): they pin what the rule gives, whatever is loaded.
