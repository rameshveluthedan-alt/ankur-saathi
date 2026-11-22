# Plans with no connection: the library assembler on the phone (build plan, 22 Nov 2026)

**Goal:** a teacher with no signal can still make the next class's plan. The block library (`db/seeds/library`, 880 checked pieces) is built
into a plan by CODE with no AI (`backend/app/services/library_assembler.py`), so the same can run on the phone. No AI credits are needed for
any of this.

## Decided (22 Nov, with the lead)

1. **A server bundle, downloaded at sign-in** (not built into the app): the library and every skill's ladder and sheet kind come from the
   server, so a library fix or a change to the reviewed skill bridges reaches phones without an app deploy. About 0.5 MB compressed
   (4.25 MB as stored), refreshed only when its version changes.
2. **Stored in IndexedDB** (not localStorage, whose ~5 MB cap the library nearly fills), with `navigator.storage.persist()` asked for, so
   the browser does not clear it under storage pressure.
3. **A visible status on the Plan screen:** "✓ ऑफ़लाइन योजना तैयार" when the bundle and the class are on the phone, and a "download now"
   tap when a weak signal interrupted the download at sign-in.
4. **A parity test:** the same inputs give the SAME plan JSON on the server (Python) and on the phone (JavaScript), so the two assemblers
   can never drift apart silently.
5. **Worksheets of an offline plan: an in-app view** (each group's problems, with the answers for the teacher) to copy onto the board, the
   app's default "no printer" way. The printable pages stay a server feature.
6. **Upload and store on reconnect,** so the review, the ticks and the next plan's re-teach evidence work for that day. Each offline plan
   carries a client-made id, so a retry on a flaky network never stores it twice. If the server already has a plan for that day, the
   server's is kept and the teacher is told.

7. **A choice when online too (added 22 Nov):** beside "आज की योजना बनाएँ" (the AI plan, as now), a second, smaller button
   "⚡ तैयार हिस्सों से जल्दी योजना" builds the plan from the library in seconds with no AI call: online the SERVER builds it (the request
   asks for the library), offline the PHONE does. Both are the same plan (the parity test). A teacher in a hurry, or the team stretching the
   credits, can use it; after the credits end it is what every plan is anyway.

## What the phone needs

| | From | Private? | Kept |
|---|---|---|---|
| The library (ok pieces only), every skill's ladder (Beginner / Proficient defaults and the options), sheet kind, names | `GET /api/offline/bundle` (signed-in; a version, 304 when unchanged) | no children's data | across sign-out |
| The class's groups (counts, roll numbers) and the re-teach suggestions per subject | the Plan screen's own requests (`/plan/groups`, `/plan/proposal`), saved when it loads them online | yes | removed at sign-out |
| Plans made offline, until uploaded | made on the phone | yes | until uploaded; sign-out asks first if any is unsent |

## Steps (each its own commit, asked first)

1. **Server: one finishing step and the bundle.** The steps the server applies to a library plan after assembly (the pace stamp, the
   observation reminders, the last block's "अगली कक्षा में", the reading-sheet story line, the session length) move into one function, so
   the phone port has one list to copy and the parity test one thing to compare. `GET /api/offline/bundle` with its version. The plan
   request takes `source: "library"` (decision 7): the server builds from the library with no AI call, whatever the AI's state. Tests.
2. **The phone's assembler** (`pwa/src/offline/`): the session layout (`session_shape`, `group_slots`, the 3 + N extras; `pacePlan` is
   already on the phone), the priority group, `assemble` and the finishing step, ported. **The parity test**
   (`backend/tests/test_offline_parity.py`): for a spread of inputs (skills of both subjects and every sheet kind × 45 / 60 / 90 × move
   on / re-teach, several dates) the Python plan and the plan from node running the phone's code are compared field by field.
3. **Storage on the phone:** IndexedDB (bundle, class, offline plans), `persist()`, the download at sign-in and the refresh, the status
   line with "download now", the class saved when the Plan screen loads it, everything private removed at sign-out.
4. **The Plan screen offline:** when the network check says offline (or the request fails for want of a network) and the bundle and class
   are ready, "आज की योजना बनाएँ" builds the plan on the phone with the teacher's choices (skills, re-teach, time), saves it, and opens it.
   The "⚡ जल्दी योजना" button (decision 7): online it asks the server for a library plan; offline it does the same as above.
   The Teach screen labels it ("📴 बिना इंटरनेट के बनी योजना: इंटरनेट मिलते ही भेजी जाएगी") and shows its worksheets in the app.
5. **Upload:** `POST /api/plan/offline` (the client id, the inputs, the groups as the phone had them, the plan): the server checks the
   plan's shape, adds the photo sample from the groups, stores it as `served_from: library_offline`, and answers the same for a repeat of
   the same id; a different plan already stored for that day is kept, and the phone says so. The phone sends waiting plans whenever the
   network check finds the server, then replaces its copy with the stored one. Tests (server and phone).
6. **Docs:** an offline section in the teacher-facing help and in `docs/HANDOVER.md`; the new Hindi lines go to the education lead.

## Limits (said plainly)

- A teacher who has never been online since signing in on that phone (or whose browser cleared its storage) cannot plan offline until the
  next connection; the status line shows it.
- An offline plan is built from the class's groups as they were at the last online visit; the next upload brings the server up to date.
- Photo marking and the review still need the internet; an offline plan is reviewed after it is uploaded.
- Library plans are AI-drafted pieces not yet reviewed, labelled as such, the same as on the server.
