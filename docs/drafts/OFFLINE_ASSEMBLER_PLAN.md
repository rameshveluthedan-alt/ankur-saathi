# Plans with no connection (build plan, 22 Nov 2026; revised the same day)

**Goal:** a teacher with no signal can still make the next class's plan, and, when online, can choose a quick plan from the block library
(`db/seeds/library`, 880 checked pieces; no AI call) instead of the AI plan. No AI credits are needed for any of this.

## The approach: C (B now, A later), decided 22 Nov with the lead

A library plan is the assembler's output PLUS the server's own repairs, which change what the teacher sees: on a literacy sheet the passage
and its questions come from the passage bank; worksheet numbers are replaced (a sum too big for the Beginners' sticks, a number the lesson
already used) with their Hindi number words; the show-me questions are checked and trimmed to the session's count. That is some 2,000 lines
of Python, still being refined.

- **B, now: the server PREPARES the plans the phone may need,** through its own pipeline (about 0.06 s and 8 KB compressed each, measured),
  and the phone stores them. Offline, the phone opens the prepared plan that matches the teacher's choices. It is the server's plan by
  construction: nothing is ported, nothing can drift.
- **A, later, only if classroom use shows the need:** the assembler and its repairs ported to the phone, for ANY skill offline, with a parity
  test. Not built now.

## Decided

1. **What is prepared:** for each subject, the suggested skill (moving on, and the re-teach where the app suggests one, from the evidence of
   the last online visit) and the next 3 skills on its ladder (moving on), at 45, 60 and 90 minutes, for the next 3 school days: about 90
   plans, some 6 s of server work, about 0.7 MB to download (about 4 MB stored).
2. **Prepared plans are not the teacher's plans:** the server builds them WITHOUT storing them; only the one used offline is uploaded and
   stored.
3. **When they are prepared:** at sign-in, and when the Plan screen opens online, at most once a day, or sooner when their inputs changed
   (the class's groups, the suggestions after a review, the library's version). A version tells the phone whether anything changed.
4. **Stored in IndexedDB** (not localStorage, whose ~5 MB cap is too small), with `navigator.storage.persist()` asked for. They hold the
   class's roll numbers, so they are removed at sign-out; if a plan made offline is not yet uploaded, sign-out asks first.
5. **The Plan screen says what works offline:** a status line, "✓ ऑफ़लाइन योजना तैयार" (with the date it was prepared) or a
   "download now" tap; offline, the prepared skills carry "ऑफ़लाइन उपलब्ध" and the rest are greyed out, and so is the re-teach choice where
   none was prepared.
6. **An outage longer than the buffer:** the phone uses the last prepared day's plan for the chosen skill, dated for the day it is used (only
   the anchor setting and the independent activities rotate by date).
7. **Worksheets of an offline plan: an in-app view** (each group's problems, with the answers for the teacher) to copy onto the board, the
   app's default "no printer" way. The printable pages stay a server feature.
8. **Upload and store on reconnect,** so the review, the ticks and the next plan's evidence work for that day. Each offline plan carries a
   client-made id, so a retry on a flaky network never stores it twice. If the server already has a plan for that day, the server's is kept
   and the teacher is told. The photo sample is worked out on the server at upload, for the date the plan was used.
9. **A choice online too:** beside "आज की योजना बनाएँ" (the AI plan, as now) a second, smaller button "⚡ तैयार हिस्सों से जल्दी योजना"
   asks the server for a library plan (no AI, a few seconds). Offline, the main button opens the prepared plan.

## Steps (each its own commit, asked first)

1. **Server: library plans on request, and prepared plans.** The plan request takes `source: "library"` (decision 9). The pipeline can build
   a plan without storing it. `POST /api/offline/prepare` (signed-in, the teacher's own): the PHONE lists its likely choices (decision 1),
   worked out with the Plan screen's own logic for each group's skill and re-teach ticks, so the server builds exactly what the phone will
   ask for and no screen logic is copied to the server; at most 120 per request, a choice that cannot be built is reported, not fatal; the
   library's version comes back with the plans. Tests: a prepared plan is the plan the server stores for the same choice. (Done 22 Nov.)
2. **Storage on the phone:** IndexedDB, `persist()`, the download at sign-in and when the Plan screen opens, the status line and "download
   now", removal at sign-out (asking first if a plan is waiting to be sent: with the outbox, step 4). (Done 22 Nov: `pwa/src/offline/`,
   `OfflineReady.jsx`; the choices are made with the Plan screen's own `initialRows` / `buildGenerateOptions`; 45 plans per subject.)
3. **The Plan screen:** the "⚡" button; offline, the badges and the greyed-out choices, and "आज की योजना बनाएँ" opening the matching prepared
   plan (decision 6 past the buffer), saved as an offline plan; the Teach screen's label ("📴 बिना इंटरनेट के बनी योजना: इंटरनेट मिलते ही भेजी
   जाएगी") and the in-app worksheet view.
4. **Upload:** `POST /api/plan/offline` (client id, inputs, plan): owner and shape checked, photo sample added, stored as
   `served_from: library_offline`; the same answer for a repeat of the same id; a plan already stored for that day is kept and the phone says
   so. The phone sends waiting plans whenever the network check finds the server, then shows the stored one. Tests (server and phone).
5. **Docs:** an offline section in the teacher-facing help and in `docs/HANDOVER.md`; the new Hindi lines go to the education lead.

## Limits (said plainly)

- Offline, only the prepared skills can be chosen (the suggested one and the next three on each ladder); any other skill needs the internet.
- A teacher who has not been online since signing in on that phone (or whose browser cleared its storage) cannot plan offline until the
  next connection; the status line shows it.
- Offline plans use the class's groups and suggestions as they were at the last online visit.
- Photo marking and the review still need the internet; an offline plan is reviewed after it is uploaded.
- Library plans are AI-drafted pieces not yet reviewed, labelled as such, online and offline.
