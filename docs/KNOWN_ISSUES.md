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

## Beginner and Proficient worksheets are tagged with the Progressors' mistakes

**Found:** 29 October 2026, reviewing the plan prompt (`docs/drafts/PROMPT_REVIEW_29OCT.md`, point 2).

**What happens:** the prompt lists only the mistakes of the Progressors' skill (the day's skill), yet every worksheet's mistake-revealing problems must carry "an ID from the misconception list". So the Beginner and Proficient sheets either borrow the Progressors' IDs (wrong for their own skill) or carry none.

**Impact:** the photo analysis can name the wrong mistake for a Beginner or Proficient, or none. It probably explains part of why the N0.1.1 Beginner worksheet was weak (the first issue above).

**Status for this submission:** not changed (a prompt change this late would put the plans that are known to work at risk). The fix is in the drafted plan prompt v2: one list of mistakes per group, used for both the show-me questions and the worksheets (`docs/drafts/PROMPT_DRAFT_V2.md`).

## The show-me rules contradict the Hindi style rule

**Found:** 29 October 2026, in the prompt review and in a reviewed plan for L2.5.1.

**What happens:** the Hindi style rules say the teacher never uses abrupt "तुम" commands ("देखें", never "देखो"), but the model line in the show-me rules (`prompts/cfu_prompt.py`) is "बोर्ड पर देखो: 34 + 28 = 52 लिखा है।". A model copies an example before it follows a rule. A reviewed live plan for L2.5.1 still showed "बोर्ड पर देखो" in a Progressor's show-me question.

**Impact:** a command form of the kind the education lead asked us to avoid can reach a teacher. The safety net (`hindi_style.soften_plan`) fixes the command forms it knows, but it is a net, not the rule.

**Status for this submission:** not changed (one string, but even one string needs a new generation to confirm). Fix: "बोर्ड पर देखें" in the example (drafted in v2).

## The plan prompt assumes a 90-minute session, but 45 and 60 minutes can be chosen

**Found:** 29 October 2026, in the prompt review (point 1).

**What happens:** the Plan screen offers 45, 60 and 90 minutes, and the code lays the day out for the length chosen. At 45 minutes the teach blocks are about 15, 7 and 7 minutes. The prompt still tells the model that independent activities run "22-29 minutes", that a re-teach block is "about 27 minutes", that the anchor is always 10 minutes, and that every block gets 3 show-me questions.

**Impact:** a 45-minute plan may give a 7-minute block a full I Do, We Do and You Do. Until the plans are read, the 45 and 60 minute plans are not known to be good: this path has not been checked with the real model.

**Status for this submission:** checked with the real model on 29 October (N2.3.2): **60 minutes read well; 45 did not**, so 45 is hidden from the picker (next entry) and 90 and 60 stay. A real fix (block lengths in the prompt, a shorter anchor, fewer show-me questions in a short block) is in `docs/drafts/PROMPT_DRAFT_V2.md`; whether a 7-minute block is worth teaching at all is a decision for the education lead.

## Writing skills: the worksheets test reading, not writing

**Found:** 30 October 2026, reading two plans for L2.7.2 side by side (`docs/drafts/PLAN_REVIEW_L2.7.2.md`): the recorded fallback plan and a new one.

**What happens:** the Progressors and Proficients are taught to write 3-5 or 5-7 connected sentences, but most of their worksheet problems are reading-comprehension questions about a passage. The new plan adds one writing task to each sheet (1 problem in 6), with an open answer ("any 3 connected sentences") that the photo analysis cannot mark against an answer key. The Beginners' dictation sheet prints the sentences it dictates, so the children can copy them. No mistakes are recorded in the knowledge base for L2.7.1, L2.7.2 or L3.7.1.

**Impact:** the photo after class measures comprehension, and records it as evidence for a writing skill. L2.7.2 is one of the six skills with a recorded fallback plan, so a judge can meet this.

**Status for this submission:** not changed. Fixes (prompt, photo analysis, content) are listed in `docs/drafts/PLAN_REVIEW_L2.7.2.md`; the writing-sheet shape is the open question in `docs/drafts/PROMPT_DRAFT_3N_WORKSHEET.md`.

## 45-minute plans are hidden for the submission

At 45 minutes the teach blocks are 15, 7 and 7 minutes, but the prompt still assumes 22–29-minute blocks. In a test plan (N2.3.2, 29 Oct) a 7-minute Beginner block headed N2.3.2 (addition with regrouping) taught and tested only addition without regrouping, so its worksheet results would have been recorded against the wrong skill. The 45 choice is removed from the time picker (`pwa/src/services/preferences.js`); the server still accepts it. Fix on the roadmap: give the prompt each block's real length, and decide with the education lead whether a 45-minute session teaches two groups instead of three (`docs/drafts/PROMPT_REVIEW_29OCT.md`, point 1).

## The photo analysis reads well but names the mistake roughly

**Found:** 30 October 2026, in the first scored run on photographed worksheets (`docs/vision/`).

**What happens:** on five N2.3.2 sheets (adult handwriting, deliberate mistakes) the AI read the numbers almost perfectly, but when a sheet had carry mistakes it named "drops the carry" (M1) and "writes the whole ones sum" (M2) together every time, and it never named "carries the wrong digit" (M3). It found 5 of 8 copying slips; it missed a plus turned into a minus and a copied number.

**Impact:** the teacher's "which children got it wrong" is dependable; the "why" is a hint. A missed copying slip marks a child down for something that is not a mistake in the skill.

**Status for this submission:** not changed. The review screens show the AI's reading for the teacher to look at, and the teacher decides (her own first judgment is recorded before the photo is read). Improving it needs more test sheets (children's handwriting, other skills, Hindi) and prompt work on separating the carry mistakes (`prompts/vision_analysis.py`).

