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
| **A banner** | "इंटरनेट नहीं है ... / Offline. Plans and worksheets you already opened are available; making a new plan and sending photos need the internet." It appears by itself and disappears by itself. |
| **Generate** | Switched off, with the reason written under it. |
| **Sending photos** | Switched off, with the reason; the photos already chosen stay on the screen. |
| **Recording a decision, observations, reading scores** | Need the internet. If tapped, one clear sentence in Hindi and English (never the browser's "Failed to fetch"). **Nothing is queued for later yet** (roadmap, `docs/STATUS.md`). |
| **A worksheet that cannot be opened** | The same sentence; the blank tab that used to be left behind is closed. |

## How the app knows it is offline
A phone can show signal bars and still get nothing through, and the service worker answers many requests from its saved copies, so most requests succeed even when the server cannot be reached. So the app uses three signals (`pwa/src/services/network.js`):
1. the browser's own online/offline flag (airplane mode);
2. a failed request;
3. a **probe**: a 54-byte request to `/health` that is never answered from a cache. It runs when the app opens, after a failure, when the browser says "online", when the teacher comes back to the app, and **every 15 seconds while offline** to notice the return.

An ordinary answer does **not** clear a remembered failure (it may have come from a saved copy); only a probe that gets an answer does.

## Slow networks and small phones
- **The server compresses** what it sends. The app's JavaScript goes from 279 KB to 83 KB; the whole first load (page, script, style, icons) travels **88 KB**, against 336 KB before.
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
