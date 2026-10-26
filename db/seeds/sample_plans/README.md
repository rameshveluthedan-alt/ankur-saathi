# Recorded plans (the fallback when the AI limit is reached)

Each `<skill>.json` is a real earlier plan from the model for that skill. When a cap or the credit budget stops a live call, the app
replays the recorded plan through the SAME checks and repairs as a fresh one (so it is built for the teacher's own groups, and the
worksheets, number words and passages are checked again) and labels it "sample plan".

More are made by the batch run, which saves what it generates:

    python scripts/batch_generate.py --only L2.5.1 --save-samples --redo --yes --max-cost=1      # one skill, about 14 cents; it reads backend/.env itself (there is no --env-file option). Give it ONE skill per run and attach the value with `=`: a long command pasted across a line break loses its last value (`--max-cost` then fails with "expected one argument"). To record several in PowerShell:

    foreach ($s in "L2.3.1","L2.5.1","L2.7.2") { python scripts\batch_generate.py --only $s --save-samples --redo --yes --max-cost=1 }

By default only a plan that came from the AI with NO warnings is saved. On the first real run (25 Oct) all three plans came back with one mild warning each (a worksheet question that echoes the lesson or the story; a seventh problem that reveals a misconception but is beyond the six required) and none was kept. For a reading or writing skill that is normal: a question about the story naturally echoes it. So there is an explicit way to keep such a plan:

    foreach ($s in "L2.3.1","L2.5.1","L2.7.2") { python scripts\batch_generate.py --only $s --save-samples --accept-warnings --redo --yes --max-cost=1 }

Every plan the real model produces is ALSO written, as it is and with its warnings, to `docs/batch/plans/<skill>.json` (git ignores that folder), whether or not it was kept as a sample, so a plan that was paid for is never lost. To keep one by hand: copy it, for example `Copy-Item docs\batch\plans\L2.5.1.json db\seeds\sample_plans\`, then have it read and sign it as below. A file marked `_stub` was made by the fake model and the gate refuses it.

The warnings are then written INSIDE the file (`_recorded_warnings`) with `_reviewed_by` empty. **EVERY recorded plan, with warnings or without, must be read by someone who reads Hindi and then signed, before it is shown to anyone.** The checks cover sums, structure and repeated wording; they do not say whether the Hindi is natural or the story suits the children. She should not read JSON: this writes a page for her, showing the plan as a teacher will see it (after the app's polite-Hindi pass), with the warnings at the top:

    python scripts\review_sample_plans.py list                       which plans there are, and which nobody has read yet
    python scripts\review_sample_plans.py sheet                      a page for every plan nobody has read and signed yet (docs\batch\review\<skill>.html: open it in a browser)
    python scripts\review_sample_plans.py sign L2.5.1 --by "Vaishnavi"   after she has read it: writes her name and the date into the file

Until a plan is signed, `scripts/submission_check.py` reports it as pending (a failure under `--final`). Do not edit the JSON by hand. A teacher never sees these notes: they are removed when the plan is loaded. Which skills to record is a choice, because a recorded plan is what a teacher (or an evaluator) sees when the AI limit is reached or the
credits have run out. Besides the main demo skills it is worth having one for each way of recording a review, so each can still be tried with no AI at all: a skill whose three groups are all
OBSERVED (the quick-tap checklist: N0.1.1, sorting) and one whose groups are all ORAL READING (the reading-fluency recording: L2.5.1). A plan for a skill nobody should be shown does not belong in this folder:
`backend/tests/test_hindi_style.py` checks the Hindi of every file here.

The plans contain no names and no personal data. A skill with no recorded plan simply says the limit was reached.
