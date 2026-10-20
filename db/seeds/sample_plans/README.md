# Recorded plans (the fallback when the AI limit is reached)

Each `<skill>.json` is a real earlier plan from the model for that skill. When a cap or the credit budget stops a live call, the app
replays the recorded plan through the SAME checks and repairs as a fresh one (so it is built for the teacher's own groups, and the
worksheets, number words and passages are checked again) and labels it "sample plan".

More are made by the batch run, which saves what it generates:

    python scripts/batch_generate.py --save-samples --env-file backend/.env

The plans contain no names and no personal data. A skill with no recorded plan simply says the limit was reached.
