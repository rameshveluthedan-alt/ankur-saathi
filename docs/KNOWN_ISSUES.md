# Known issues

## N0.1.1 Beginner worksheet tests only colour, not shape or size

**Found:** 28 October 2026, during Phase 2 testing.

**The skill:** N0.1.1 — "Sorts objects by one attribute (colour, shape, size)".

**The bug:** worksheets generated for the Beginner group on this skill test only the colour attribute. All questions are of the form "which pile does the red ball go in?" with "red" and "blue" as the sort categories. Shape and size — the other two attributes the skill names — don't appear.

**Related issue:** the question stems include the answer. "On the board, picture 1 (red ball): which pile does it go in? (red / blue)" tells the child the answer in the word "red" within the stem. A child who can read "red" can get 5 of 5 right without demonstrating the sorting skill.

**Impact:** a teacher using this worksheet gets a reading like "4 of 14 Beginners achieved sorting", which overstates the result. The honest reading is "4 of 14 Beginners achieved sorting by colour", and because of the stem leak the worksheet doesn't test sorting as a skill.

**Root cause:** likely the prompt and the lack of a reviewed sample plan for N0.1.1. The AI generates it ad hoc on every request, with no few-shot example to anchor the attribute spread.

**Status for this submission:** the N0.1.1 worksheet is being re-curated with Vaishnavi on Wednesday afternoon. The curated version will span all three attributes and move the attribute cue out of the question stem (e.g., "look at picture 1" with the picture label stored separately, not inside the question). A regeneration test on Thursday morning will confirm the fix.

## Photo results count as evidence immediately on AI analysis

When a teacher takes a photo of a worksheet and the AI returns its reading, each child's result is written to `assessment_evidence` as a `written_photo` row at that moment (`prompts/vision_analysis.py`), before the teacher has looked at the result screen. The regenerate warning on the Plan screen and the Progress screen both treat this as recorded evidence.

In practice this is the right behaviour (the teacher doesn't need to "confirm" what she can see on her phone), but it's worth knowing that photo evidence appears before any teacher action beyond taking the photo.
