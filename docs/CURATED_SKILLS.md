# Curated question signals: the current list

**What this is.** The product's worksheet generator and the YojanaScreen's signal panel produce content per skill (see `docs/ROADMAP.md`, section 8). For some skills the content is **chosen for a specific signal** — the three maths questions each provoke a known mistake pattern, the writing prompt elicits a known difficulty, the decoding word list spans the pattern. For the rest the AI picks reasonable content at the right level, but not for a specific mistake.

This document lists which skills have curated question signals today.

## Why this matters

- On a **curated** skill, the Review screen's photo analysis identifies the specific misconception by roll (e.g. "roll 7 missed regrouping into the tens place"), and the Progress screen's re-teach suggestion names the pattern.
- On an **uncurated** skill, the screens show scores and counts, but the mistake pattern will often be "unclear" because the questions were not chosen to discriminate.

The server returns a hidden `signal_curated: true | false` field on each worksheet. **The UI does not surface this to the teacher**: showing a "random" grey note on 90-plus skills would overstate the limitation (the lesson, activity, groups and yesterday-reading are all fine for uncurated skills too). The admission lives here instead.

## Curated skills (today)

Approximate; the live list is in the competencies table (`competencies.signal_curated_at`).

| Skill | Shape | What the curated content catches |
|---|---|---|
| N0.1.1 — sorts by colour, shape or size | observation (no worksheet) | sorting by attribute vs by preference; mixed attributes; missing one object |
| N2.2.1 — adds two 2-digit numbers without regrouping | maths worksheet | mistake in ones place; mistake in tens; reversed digits |
| N2.3.2 — adds two 2-digit numbers with regrouping | maths worksheet | regrouping in ones; regrouping across zero; carrying across both places |
| N3.3.1 — adds 3-digit numbers with regrouping | maths worksheet | regrouping across hundreds; zero in the middle; cascading carries |
| L2.3.1 — reads words with conjunct consonants | decoding (word list) | breaking a conjunct; wrong conjunct chosen; reading as two separate consonants |
| L2.5.1 — reads a grade-level passage at ~40 words a minute | reading-aloud (ORF) | pace; substitution errors; omissions |
| L2.7.2 — writes 3-5 connected sentences | writing | missing conjunctions; sentence boundary; repetition |

**Count today: 7 curated skills out of 101.** The rest fall through to the AI's default content.

## After Wednesday's curation hour (28 Oct)

Vaishnavi and Ramesh will add 5 more skills in a one-hour session:

| Skill | Shape | Status |
|---|---|---|
| N1.3.1 — adds 1-digit numbers | maths worksheet | planned |
| N2.1.4 — place value with 2-digit numbers | maths worksheet | planned |
| N3.3.5 — equal sharing / division | maths worksheet | planned |
| L2.7.1 — writes a sentence from a prompt | writing | planned |
| L2.7.2 — writes 3-5 connected sentences | writing (already curated; expanded for 45/60/90 minute lengths) | planned |

**Count after Wednesday: 12 skills curated** (one skill, L2.7.2, is extended rather than newly curated).

## Expanding this list

Each additional curated skill costs about an hour of the education lead's time (sample content drafted by the AI, mistake patterns reviewed by her, three or more chosen). Writing them in batches of 5 to 10 is efficient; see `docs/ROADMAP.md`, section 8, for the sizing of the full expansion.
