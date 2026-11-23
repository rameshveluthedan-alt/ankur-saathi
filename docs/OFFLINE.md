# Offline and low-data behaviour

Measured in a real browser (a mobile-sized window, the service worker active) against the real production server, then with the device set offline **and the server stopped**.

## What works with no network
| | |
|---|---|
| **The app opens** | The page and its code come from the service worker, so it opens on a phone with no signal. |
| **The list of skills** | Kept for 7 days and refreshed in the background (it is public reference data: no child, no teacher). |
| **Today's plan** | As soon as a plan is on screen, the app quietly keeps a copy of it (the stored plan and each group's worksheet), one request at a time. After that it reopens with all its blocks, even after the app is closed and reopened. Kept for 24 hours. |
| **The worksheets** | Open and print from that copy. (A worksheet that was never prepared, for example a plan made on another phone, needs the internet.) |

## What needs the internet, and what the app says
| | |
|---|---|
| **A banner** | "इंटरनेट नहीं है ... / Offline. Plans and worksheets you already opened are available, and plans for the skills prepared on this phone can be made; sending photos and the review need the internet." It appears by itself and disappears by itself. |
| **Generate** | Opens the plan PREPARED on the phone for the chosen skill and time (next section). For a skill or time that was not prepared it stays switched off for that choice, with the reason written under it. |
| **Sending photos** | Switched off, with the reason; the photos already chosen stay on the screen. |
| **Recording a decision, observations, reading scores** | Need the internet. If tapped, one clear sentence in Hindi and English (never the browser's "Failed to fetch"). **Nothing is queued for later yet** (roadmap, `docs/STATUS.md`). |
| **A worksheet that cannot be opened** | The same sentence; the blank tab that used to be left behind is closed. |

## Plans with no connection (23 Nov 2026; build plan `docs/drafts/OFFLINE_ASSEMBLER_PLAN.md`)
| | |
|---|---|
| **What is prepared** | While online (at sign-in, and when the Plan screen opens; at most once a day unless the suggestions or the groups change), the phone asks the server to PREPARE the plans it may need: for each subject, the suggested skill (the one the last review points to for the Progressors), moving on and its re-teach where the app suggests one, and the next 3 skills on its ladder, at 45 / 60 / 90 minutes, for the next 3 school days: 45 plans a subject, about 0.7 MB compressed. The server builds each from the block library through its own pipeline, with no AI call, and does NOT store them: they are not the teacher's plans until one is used. |
| **Where they are kept** | IndexedDB on the phone (persistent storage is asked for). They hold the class's roll numbers, never a name. |
| **The Plan screen says** | "✓ ऑफ़लाइन योजना तैयार (… तक, N कौशल)", or "⏳ … तैयार हो रही हैं", or "पहले इस विषय की एक योजना इंटरनेट के साथ बनाएँ" (no plan yet in the subject, so nothing to suggest), or "अभी तैयार नहीं" with **⬇ अभी डाउनलोड करें**. Offline, the prepared skills carry **📴 ऑफ़लाइन उपलब्ध** and the rest are greyed (a tap says why). |
| **Generate offline** | Opens the prepared plan for the chosen skill and time. The group panel usually cannot load offline, so each skill's DEFAULT choice (the app's suggestion, recorded when preparing) is used. Past the 3 prepared days, the last prepared day's plan for the same choice. A choice that was not prepared (another time, a changed group skill) says so and makes nothing: never a different plan. |
| **The Teach screen** | "📴 बिना इंटरनेट के बनी योजना", with the library note; **📝 shows each worksheet in the app** (instructions, passage, problems, the answers on a tap) to copy onto the board: the printable page is on the server only. A reload with no connection finds the plan again. |
| **Sending** | At opening, at sign-in and whenever the connection comes back, waiting plans are sent (oldest first) and the teacher is told. The server stores each ONCE (a client-made id: a retry is answered 'duplicate'); if a plan for that day is already stored (another phone, or one made online meanwhile) the server's is kept and the phone's removed, with a message. The groups stored are those the phone planned with, limited to the teacher's own children; the photo sample is worked out for the day of use. After that the review, photos and progress work for that day as for any plan. |
| **Privacy and sign-out** | The prepared plans go whenever the signed-in person changes. Plans made offline belong to their teacher: another teacher signing in on the phone removes them, and sign-out says first when one is not yet sent ("… लॉग आउट करने पर वह हमेशा के लिए हट जाएगी"). |
| **The ⚡ quick plan (online)** | A second button under "आज की योजना बनाएँ": the plan built from the library by the server in seconds, with no AI call (labelled as library plans are). |

**Limits:** offline, only the prepared skills can be planned; a teacher who has not been online since signing in on that phone (or whose browser cleared its storage) cannot plan offline until the next connection (the status line shows it); offline plans use the groups and suggestions of the last online visit; photo marking and the review need the internet.

## How the app knows it is offline
A phone can show signal bars and still get nothing through, and the service worker answers many requests from its saved copies, so most requests succeed even when the server cannot be reached. So the app uses three signals (`pwa/src/services/network.js`):
1. the browser's own online/offline flag (airplane mode);
2. a failed request;
3. a **probe**: a 54-byte request to `/health` that is never answered from a cache. It runs when the app opens, after a failure, when the browser says "online", when the teacher comes back to the app, and **every 15 seconds while offline** to notice the return.

An ordinary answer does **not** clear a remembered failure (it may have come from a saved copy); only a probe that gets an answer does.

## Slow networks and small phones
- **The server compresses** what it sends. The app's JavaScript goes from 395 KB to 112 KB; the whole first load (page, script, style, icons) travels about **120 KB** (measured on the live app on 31 October; it was 88 KB when first measured, before later features).
- **A slow or hanging connection:** after 6 seconds the plan and worksheet reads fall back to the saved copy instead of waiting for ever.
- **Photos shrink on the phone** before they are sent: 1600 px at quality 0.8, and 1200 px at 0.7 on a phone that reports 2 GB of memory or less (Chrome and Edge on Android report it; other browsers use the normal size). The server shrinks them again before the AI sees them.

## Privacy of the copies on the phone
The plan and worksheet copies hold roll numbers, never a child's name (the names are fetched separately and never kept). They are **removed whenever the signed-in person changes**: signing out, being signed out, signing in. The app itself and the public skill list stay. A different teacher on the same phone sees none of them.

## How to try it yourself
1. Sign in, choose a skill, press **Generate** (or use skill N2.3.2 on the demo teacher: a recorded sample plan appears if the AI limit is reached) and wait for the plan.
2. Switch on **airplane mode** (or, on a desktop: DevTools → Network → Offline).
3. Reload. The app opens, the offline notice shows, the plan is there, a worksheet opens; on the Plan tab Generate is off with its reason.
4. Switch the network back on: the notice goes away by itself within seconds.

## Known limits
- Decisions, observations, reading scores and photos are **not** queued for later; they need the internet.
- Not tested on a budget Android phone with 2 to 3 GB of RAM yet.
- The "photos need the internet" message on the Review screen is covered by the code and the shared network logic, but was **not** exercised in the real-browser run.
