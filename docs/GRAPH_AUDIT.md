# The knowledge graph, as the app uses it: an audit for review

**Why.** The plan puts the **Beginners** on a skill's *predecessor* and the **Proficients** on its *successor*. Teachers trust the three skills only if they read like chapters of one story (the anchor-skill model). The app derives them with a simple rule (`group_skills.derived_beginner_id` / `derived_proficient_id`): the **first hard prerequisite by id**, and the **first hard dependent by its place in its strand**. When a skill has several candidates that is an arbitrary pick.

**Run it** (changes nothing): `python scripts\audit_trios.py --env-file backend\.env` → `docs/graph_audit_trios.csv` (open in Excel; one row per skill).

## Reading the sheet
| Column | Meaning |
|---|---|
| `needs_a_decision`, `priority (1 = look first)` | **1**: the app's pick is in ANOTHER strand, or the skill has NO predecessor although it is above Balvatika (a gap in the graph). **2**: several candidates in the same strand (the app takes the first). Blank: nothing to decide. |
| `hard_prerequisites (candidate predecessors)` / `hard_dependents (candidate successors)` | all the candidates, by name |
| `app_now_*` | what the app does today |
| `proposed_*` | what a rule ("same strand first, then the closest grade") would pick. **It is NOT always better**: for N2.3.2 it would offer a Grade 2 word-problem skill where 3-digit addition (N3.3.1) is the natural extension. Use it as a prompt, not an answer. |
| `flags` | why the row is marked |
| `your_decision_Beginners`, `your_decision_Proficients`, `notes` | **to be filled in** by the reviewer: one skill id for each |

## What the audit found (numeracy, 53 skills)
- **9 skills** have a pick in another strand (not always wrong: place value → 2-digit addition is natural), **9** have no predecessor above Balvatika, **12** have several prerequisites and **14** several dependents.
- Clear misses seen so far: **N3.3.1 → perimeter** (N3.5.2) for the Proficients, where multi-step word problems (N3.3.6) is the natural extension; **N3.3.1's Beginners** get place value (N2.2.2) although 2-digit addition with carrying (N2.3.2) is the closer bridge.

## What happens with the decisions
They become a small table of curated bridges (`skill → preferred predecessor, preferred successor`), loaded with the seeds. The app uses the curated pick when there is one and the rule otherwise, and the ladder lists show the curated skills first. This is deterministic and small, and needs the reviewer's decisions first.
