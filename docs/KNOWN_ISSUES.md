# Known issues

## N0.1.1 Beginner worksheet tests only colour, not shape or size

**Found:** 28 October 2026, during Phase 2 testing.

**The skill:** N0.1.1 — "Sorts objects by one attribute (colour, shape, size)".

**The bug:** worksheets generated for the Beginner group on this skill test only the colour attribute. All questions are of the form "which pile does the red ball go in?" with "red" and "blue" as the sort categories. Shape and size — the other two attributes the skill names — don't appear.

**Related issue:** the question stems include the answer. "On the board, picture 1 (red ball): which pile does it go in? (red / blue)" tells the child the answer in the word "red" within the stem. A child who can read "red" can get 5 of 5 right without demonstrating the sorting skill.

**Impact:** a teacher using this worksheet gets a reading like "4 of 14 Beginners achieved sorting", which overstates the result. The honest reading is "4 of 14 Beginners achieved sorting by colour", and because of the stem leak the worksheet doesn't test sorting as a skill.

**Root cause:** likely the prompt and the lack of a reviewed sample plan for N0.1.1. The AI generates it ad hoc on every request, with no few-shot example to anchor the attribute spread.

**Status for this submission:** the N0.1.1 worksheet is being re-curated with Vaishnavi on Wednesday afternoon. The curated version will span all three attributes and move the attribute cue out of the question stem (e.g., "look at picture 1" with the picture label stored separately, not inside the question). A regeneration test on Thursday morning will confirm the fix.

## The observation prompts can describe a task the plan does not contain

**Found:** 29 October 2026, reviewing a lab plan for N0.1.1 (all three groups on N0.1.1).

**What the plan said to observe** (its review prompts, written by the AI): "स्वतंत्र अभ्यास और टीच ब्लॉक के दौरान देखें कि कौन सा बच्चा बिना याद दिलाए 10 से ज़्यादा चीज़ें एक नियम से अलग कर पा रहा है और नियम बोल पा रहा है" — sorting more than 10 objects by a rule the child chooses, and saying it.

**What the same plan had the children do on their own** (You Do): worksheet questions where the rule is given and the child only counts, with fewer than 10 items ("बोर्ड पर: 3 लाल गोले, 2 नीले गोले। नियम रंग है। लाल चीज़ें कितनी हैं?"). Only the Progressors' We Do had 10 objects and a rule to choose, and that is done together, not by each child.

**Impact:** the teacher is told to watch for something no child does on their own that day; her A / PA / NA would in fact be about counting. The same weakness as the worksheet issue above, on the observation side.

**Root cause:** the AI writes the review prompts and the activities in the same plan, and nothing checks that one matches the other.

**What the app does now (lab, 29 Oct):** the screens no longer show the AI's prompt text. The Review, the plan screen and the printed plan give one general instruction instead: "स्वतंत्र अभ्यास (तुम करोगे) के दौरान बच्चों को काम करते हुए देखें, फिर हर बच्चे के लिए A / PA / NA चुनें।", with the meanings of A / PA / NA (for Vaishnavi's review). A group checked by observation that also has a worksheet is told the worksheet is practice, not to be photographed. The prompts stay in the plan's data.

**Suggested prompt rule** (for `prompts/orchestrate.py`, PART E; the prompt is Ramesh's work, not changed in the lab):

> - Observation reminders must describe what to watch for in an activity that this plan's own You Do (or independent practice) contains, done by each child individually. Name that activity.
> - If a skill today is checked by observation, the You Do for its group must include such an activity: the child does the skill itself (for sorting: mixed objects, the child chooses a rule, sorts and says the rule), not a worksheet that gives the rule and asks for a count.
> - Write the A / PA / NA criteria in terms of that same activity.

With the rule in place (and a check in `plan_service.py` that each observation reminder names an activity found in the You Do), the screens could show the plan's own prompts again.

## Photo results count as evidence immediately on AI analysis

When a teacher takes a photo of a worksheet and the AI returns its reading, each child's result is written to `assessment_evidence` as a `written_photo` row at that moment (`prompts/vision_analysis.py`), before the teacher has looked at the result screen. The regenerate warning on the Plan screen and the Progress screen both treat this as recorded evidence.

In practice this is the right behaviour (the teacher doesn't need to "confirm" what she can see on her phone), but it's worth knowing that photo evidence appears before any teacher action beyond taking the photo.
