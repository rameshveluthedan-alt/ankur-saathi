// What the app does when the network is missing or slow, with no browser and no server: a fake `fetch` and fake storage stand in.
//
// Found on the first cloud test (25 Oct): with no network, Generate showed the browser's raw "Failed to fetch", a worksheet showed it too and left a blank tab behind, and nothing said
// WHY a button did nothing. This checks the fix at its source: every request passes through authFetch, so a failed network becomes one clear sentence everywhere; the offline notice and
// the "needs the internet" reasons follow the app's own idea of being online; the offline copies of a teacher's plan and worksheets are removed when the signed-in person changes.
//
//     cd pwa
//     node tests/offline.test.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
import React from 'react';
import ReactDOMServer from 'react-dom/server';

const here = path.dirname(fileURLToPath(import.meta.url));
const src = path.join(here, '..', 'src');
const out = path.join(here, `.tmp-offline-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));
fs.mkdirSync(out, { recursive: true });

// browser stand-ins, in place BEFORE the modules are loaded (network.js listens to `window` when it is imported)
const listeners = {};
const fakeWindow = {
  addEventListener: (type, fn) => { (listeners[type] = listeners[type] || []).push(fn); },
  dispatchEvent: (ev) => { (listeners[ev.type] || []).forEach(fn => fn(ev)); return true; },
  open: () => null,
};
globalThis.window = fakeWindow;
globalThis.Event = globalThis.Event || class { constructor(type) { this.type = type; } };
const store = new Map();
globalThis.localStorage = { getItem: (k) => (store.has(k) ? store.get(k) : null), setItem: (k, v) => store.set(k, String(v)), removeItem: (k) => store.delete(k) };
const setNavigator = (onLine) => Object.defineProperty(globalThis, 'navigator', { value: onLine === undefined ? {} : { onLine, deviceMemory: undefined }, configurable: true, writable: true });
setNavigator(true);
const timers = new Map(); let timerId = 0;                                                  // the recovery timer is captured, not waited for
globalThis.setInterval = (fn, ms) => { timers.set(++timerId, { fn, ms }); return timerId; };
globalThis.clearInterval = (id) => { timers.delete(id); };

// ONE bundle, so the API and the network state are the same copy, as in the real app
const entry = path.join(out, 'entry.js');
fs.writeFileSync(entry, ['services/api.js', 'services/network.js', 'services/offlineCache.js', 'utils/imageCompress.js', 'components/OfflineBanner.jsx']
  .map((f, i) => `export * as m${i} from ${JSON.stringify(path.join(src, f))};`).join('\n') + `\nexport { default as OfflineBanner } from ${JSON.stringify(path.join(src, 'components/OfflineBanner.jsx'))};\n`);
await build({ entryPoints: { bundle: entry }, bundle: true, format: 'esm', platform: 'node', outdir: out, outExtension: { '.js': '.mjs' }, loader: { '.js': 'jsx', '.jsx': 'jsx' }, external: ['react', 'react-dom'], logLevel: 'error' });
const M = await import(pathToFileURL(path.join(out, 'bundle.mjs')).href);
const { m0: api, m1: net, m2: cacheMod, m3: img, m4: bannerMod, OfflineBanner } = M;

let n = 0;
const check = (label, ok, extra = '') => { n += 1; console.log(`  ${ok ? 'OK  ' : 'FAIL'} ${label}${ok ? '' : '  ' + extra}`); if (!ok) process.exitCode = 1; };
const reply = (status = 200, body = {}) => ({ ok: status < 400, status, statusText: String(status), json: async () => body, clone() { return this; }, text: async () => '<html>sheet</html>', blob: async () => new Blob(['x']) });
const failing = async () => { throw new TypeError('Failed to fetch'); };
let calls = [];
let fetchImpl = async () => reply();
globalThis.fetch = (...a) => { calls.push(a[0]); return fetchImpl(...a); };
const fakeTab = () => ({ closed: false, close() { this.closed = true; }, location: { href: '' } });

console.log('the network state');
check('online to begin with', net.isOnline() === true);
let heard = 0; const stop = net.subscribe(() => { heard += 1; });
net.markNetworkFailed(); net.markNetworkFailed();
check('a failed request makes the app offline; listeners hear it ONCE; probing every 15 seconds starts (to notice when it is back)', net.isOnline() === false && heard === 1 && timers.size === 1 && [...timers.values()][0].ms === 15000, `heard=${heard} timers=${timers.size}`);
const asked = [];
const answers = async (u, o) => { asked.push([u, o]); return reply(); };
check('a PROBE that gets an answer puts the app back online, stops the probing and tells the listeners', (await net.probe(answers)) === true && net.isOnline() && timers.size === 0 && heard === 2, `heard=${heard} timers=${timers.size}`);
check('the probe asks for /health and says cache: no-store, so the service worker can never answer it from a saved copy', asked[0][0] === '/health' && asked[0][1].cache === 'no-store', JSON.stringify(asked[0]));
check('a probe that gets no answer marks the app offline and starts the probing', (await net.probe(failing)) === false && !net.isOnline() && timers.size === 1);
check('...and an answer that is an ERROR page (HTTP 500) still counts as reachable: the server answered', (await net.probe(async () => reply(500))) === true && net.isOnline());

console.log('\nthe case that matters most: the phone says online, the service worker answers from saved copies, but the server cannot be reached');
net.markNetworkFailed();
fetchImpl = async () => reply(200, { ok: 1 });
await api.getMe();
check('an ordinary page request that SUCCEEDS does NOT clear a failure (it may have come from a saved copy): the app stays offline', net.isOnline() === false);
fetchImpl = failing; calls = [];
const tick = () => new Promise(r => setTimeout(r, 0));
[...timers.values()][0].fn(); await tick();
check('the 15-second probing really asks the server (/health) and a failed answer keeps the app offline', calls.includes('/health') && net.isOnline() === false, JSON.stringify(calls));
fetchImpl = async () => reply(200); calls = [];
[...timers.values()][0].fn(); await tick();
check('...and the first answer brings it back online and stops the probing', net.isOnline() === true && timers.size === 0, `online=${net.isOnline()} timers=${timers.size}`);
net.markNetworkFailed(); setNavigator(false); calls = [];
[...timers.values()][0].fn(); await tick();
check('while the BROWSER says offline the probing waits (no pointless request) for its own "online" event', calls.length === 0 && net.isOnline() === false);
setNavigator(true); fetchImpl = failing; calls = [];
fakeWindow.dispatchEvent({ type: 'online' }); await tick();
check('"online" from the browser starts a probe: it is believed only when the server answers, so a failed probe leaves the app offline', calls.includes('/health') && net.isOnline() === false);
fetchImpl = async () => reply(); fakeWindow.dispatchEvent({ type: 'online' }); await tick();
check('...and a probe that gets an answer clears it', net.isOnline() === true && timers.size === 0);
setNavigator(false);
check("the browser's own 'offline' flag also means offline, with no request needed", net.isOnline() === false);
setNavigator(true);
check('...and back online when the flag says so', net.isOnline() === true);
stop();
let seen = 0; const stop2 = net.subscribe(() => { seen += 1; });
setNavigator(false); fakeWindow.dispatchEvent({ type: 'offline' });
check("the browser's 'offline' tells the screens at once (the offline notice appears without any request)", seen === 1 && net.isOnline() === false, String(seen));
setNavigator(true); fetchImpl = async () => reply(); fakeWindow.dispatchEvent({ type: 'online' });
check("the browser's 'online' tells the screens AT ONCE too, before the probe has answered (found in the DOM test: the notice used to stay up after airplane mode was switched off)", seen === 2 && net.isOnline() === true, String(seen));
await tick(); stop2();
const e = new net.NetworkError();
check('the message a teacher sees says, in Hindi AND English, that it needs the internet and that what she opened is still shown; it never says "Failed to fetch"', /इंटरनेट/.test(e.message) && /No internet/.test(e.message) && /still shown/.test(e.message) && !/Failed to fetch/.test(e.message) && e.offline === true && e.code === 'offline', e.message);

console.log('\nevery request goes through one door');
fetchImpl = failing;
let err = null; try { await api.getMe(); } catch (x) { err = x; }
check('a request with no network fails with the clear message (a NetworkError), not the browser\'s', err instanceof net.NetworkError && err.offline === true && !/Failed to fetch/.test(err.message), String(err && err.message));
check('...and the app now knows it is offline', net.isOnline() === false);
await net.probe(async () => reply());
fetchImpl = async () => reply(500, { detail: 'boom' });
err = null; try { await api.getMe(); } catch (x) { err = x; }
check('a server error (HTTP 500) is NOT a network failure: the error is shown as it is and the app is not marked offline', !(err instanceof net.NetworkError) && err.status === 500 && net.isOnline() === true, String(err));
api.setToken('tok'); let sentAuth; fetchImpl = async (u, o) => { sentAuth = o.headers.Authorization; return reply(); }; await api.getMe(); api.setToken(null);
check('the sign-in token is sent when there is one', sentAuth === 'Bearer tok', String(sentAuth));

console.log('\nopening a worksheet with no network (it used to leave a blank tab)');
let tab = fakeTab(); fakeWindow.open = () => tab;
fetchImpl = failing; err = null;
try { await api.openAuthedPage('/worksheet/T/2026-10-24/numeracy/progressor'); } catch (x) { err = x; }
check('no network: the blank tab is CLOSED and the clear message is raised', tab.closed === true && err instanceof net.NetworkError, `closed=${tab.closed} ${err}`);
tab = fakeTab(); fetchImpl = async () => reply(404, { detail: 'No plan' });
err = null; try { await api.openAuthedPage('/worksheet/x'); } catch (x) { err = x; }
check('an answer of "not found" also closes the tab and shows the server\'s reason', tab.closed === true && /No plan/.test(String(err && err.message)));
tab = fakeTab(); fetchImpl = async () => reply(200);
await api.openAuthedPage('/worksheet/T/2026-10-24/numeracy/progressor');
check('a worksheet that opens: the tab is kept and pointed at the page', tab.closed === false && /^blob:/.test(tab.location.href), tab.location.href);

console.log('\npreparing the offline copy of a plan');
calls = []; fetchImpl = async () => reply();
await api.prepareOfflineCopy('T1', '2026-10-24', 'numeracy', ['beginner', 'progressor', 'proficient']);
check('the STORED plan is fetched first (the address the app reopens it from; a freshly generated plan never asked for it), then each level\'s worksheet, once, in order', JSON.stringify(calls) === JSON.stringify(['/api/plan/T1/2026-10-24/numeracy', ...['beginner', 'progressor', 'proficient'].map(l => `/api/worksheet/T1/2026-10-24/numeracy/${l}`)]), JSON.stringify(calls));
calls = []; let k = 0; fetchImpl = async () => { k += 1; if (k === 2) throw new TypeError('Failed to fetch'); return reply(); };
let threw = false; try { await api.prepareOfflineCopy('T1', 'd', 'numeracy', ['beginner', 'progressor', 'proficient']); } catch { threw = true; }
check('if the network drops partway it stops quietly (no error, no further requests): it only prepares a copy', !threw && calls.length === 2, `threw=${threw} calls=${calls.length}`);
calls = []; fetchImpl = async () => reply(); await api.prepareOfflineCopy('T1', 'd', 'numeracy', undefined);
check('a plan with no worksheets still gets its stored plan kept, and nothing else', calls.length === 1 && calls[0] === '/api/plan/T1/d/numeracy', JSON.stringify(calls));

console.log('\nthe private offline copies');
const deleted = [];
const fakeCaches = { delete: async (name) => { deleted.push(name); return name !== 'workbox-precache-v2'; }, keys: async () => [] };
check('only the plan and worksheet copies are removed: never the app itself, never the public list of skills', JSON.stringify(cacheMod.PRIVATE_CACHES) === '["plan-cache","worksheet-cache"]' && (await cacheMod.clearPrivateCaches(fakeCaches)) === 2 && JSON.stringify(deleted) === '["plan-cache","worksheet-cache"]', JSON.stringify(deleted));
check('no cache storage (an old browser, a private window): nothing happens and nothing breaks', (await cacheMod.clearPrivateCaches(null)) === 0 && (await cacheMod.clearPrivateCaches({ delete: async () => { throw new Error('denied'); } })) === 0);
globalThis.caches = fakeCaches; store.clear();
deleted.length = 0; api.setToken('first'); await new Promise(r => setTimeout(r, 0));
check('SIGNING IN clears the previous person\'s offline copies', deleted.length === 2, JSON.stringify(deleted));
deleted.length = 0; api.setToken('first'); await new Promise(r => setTimeout(r, 0));
check('...but setting the same token again does not', deleted.length === 0);
deleted.length = 0; api.setToken(null); await new Promise(r => setTimeout(r, 0));
check('SIGNING OUT (or being signed out) clears them, so they cannot be read on a shared phone', deleted.length === 2 && api.getToken() === null, JSON.stringify(deleted));
deleted.length = 0; api.setToken(null); await new Promise(r => setTimeout(r, 0));
check('signing out when already signed out does nothing', deleted.length === 0);
delete globalThis.caches;

console.log('\nthe photos');
check('a phone with 2 GB of RAM or less sends a smaller photo (1200 px, quality 0.7)', JSON.stringify([2, 1, 0.5].map(g => img.compressionSettings(g))) === JSON.stringify([{ maxSide: 1200, quality: 0.7 }, { maxSide: 1200, quality: 0.7 }, { maxSide: 1200, quality: 0.7 }]));
check('4 GB and more, or a browser that does not say, keep the normal size (1600 px, quality 0.8)', [4, 8, undefined, 0].every(g => JSON.stringify(img.compressionSettings(g)) === JSON.stringify({ maxSide: 1600, quality: 0.8 })));
setNavigator(true); Object.defineProperty(globalThis.navigator, 'deviceMemory', { value: 2, configurable: true });
check("the browser's own deviceMemory is what is used when nothing is passed", img.compressionSettings().maxSide === 1200);

console.log('\nthe offline notice');
setNavigator(false);
const off = ReactDOMServer.renderToStaticMarkup(React.createElement(OfflineBanner));
check('offline: the notice appears, in Hindi and English, and says what still works and what needs the internet', /data-testid="offline-banner"/.test(off) && /इंटरनेट नहीं है/.test(off) && /Offline\. Plans and worksheets you already opened are available/.test(off) && /need the internet/.test(off), off.slice(0, 120));
setNavigator(true); net.markNetworkOk();
check('online: nothing is shown', ReactDOMServer.renderToStaticMarkup(React.createElement(OfflineBanner)) === '');
check('the hook the screens use is exported', typeof bannerMod.useOnline === 'function' && typeof bannerMod.NEEDS_INTERNET === 'string');

console.log(`\n${process.exitCode ? 'SOME CHECKS FAILED' : 'OK: ' + n + ' checks: a missing network becomes one clear sentence, a blank tab is never left behind, worksheets are prepared for offline use, and the offline copies never outlive the signed-in person'}`);
