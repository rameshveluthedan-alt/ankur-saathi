// "आज की योजना" shows TODAY's plan only (29 Oct). A phone brings back yesterday's page in the morning (the app is not closed, it waits in the background),
// so the plan in memory may be an older day's, or another subject's. Then today's stored plan is loaded for the chosen subject; with none stored, an
// older day's plan is put away (never shown as today's) while a plan of today for the other subject is still shown; a failure says so. The day is
// looked at again when the app comes back to the screen, so a phone left open across midnight moves on.
// The REAL plan screen in a simulated browser with a fake server.
//
//     cd pwa
//     npm install --save-dev jsdom@24     (once; see plan_screen.dom.test.mjs)
//     node tests/yojana_today.test.mjs
//
// Without jsdom the test says so and stops without failing.
import fs from 'node:fs'; import path from 'node:path'; import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
let JSDOM;
try { ({ JSDOM } = await import('jsdom')); } catch (e) { console.log('SKIPPED: jsdom is not installed. To run this test: cd pwa; npm install --save-dev jsdom@24'); process.exit(0); }
const here = path.dirname(fileURLToPath(import.meta.url)); const src = path.join(here, '..', 'src'); const out = path.join(here, `.tmp-yojtoday-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));      // the temporary build folder is always removed, even if a check fails
const API = ['getCachedPlan', 'getReviewChannels', 'openAuthedPage', 'worksheetPath', 'prepareOfflineCopy'];
const stubs = { '../App': 'export const useAuth = () => globalThis.__auth;',
  'react-router-dom': 'export const useNavigate = () => (...a) => globalThis.__navs.push(a); export const useLocation = () => ({ pathname: "/yojana", state: null });',
  '../services/api': API.map((n) => `export const ${n} = (...a) => globalThis.__api.${n}(...a);`).join('\n') };
await build({ entryPoints: { yojana: path.join(src, 'screens/YojanaScreen.jsx') }, bundle: true, format: 'esm', platform: 'node', outdir: out,
  outExtension: { '.js': '.mjs' }, loader: { '.js': 'jsx', '.jsx': 'jsx' }, external: ['react', 'react-dom', 'react-dom/client'], logLevel: 'error',
  plugins: [{ name: 'stubs', setup(b) { b.onResolve({ filter: /^(\.\.\/App|react-router-dom|\.\.\/services\/api)$/ }, (a) => ({ path: a.path, namespace: 'stub' })); b.onLoad({ filter: /.*/, namespace: 'stub' }, (a) => ({ contents: stubs[a.path], loader: 'js' })); } }] });
const dom = new JSDOM('<!doctype html><div id="root"></div>', { url: 'http://localhost/', pretendToBeVisual: true });
for (const k of ['window', 'document', 'navigator', 'HTMLElement', 'HTMLInputElement', 'Element', 'Node', 'MouseEvent', 'Event', 'localStorage', 'sessionStorage']) Object.defineProperty(globalThis, k, { value: dom.window[k], configurable: true, writable: true });
globalThis.IS_REACT_ACT_ENVIRONMENT = true; globalThis.requestAnimationFrame = (f) => setTimeout(f, 0);
dom.window.Element.prototype.scrollIntoView = () => {};
const React = (await import('react')).default; const { act } = await import('react'); const { createRoot } = await import('react-dom/client');
const ReactDOMServer = (await import('react-dom/server')).default;
const Yojana = (await import(pathToFileURL(path.join(out, 'yojana.mjs')).href)).default;

// ── the days, on the phone's own calendar (a clock moved forward stands for "after midnight") ──
const RealDate = Date;
const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
const TODAY = iso(new RealDate()); const YESTERDAY = iso(new RealDate(RealDate.now() - 864e5)); const TOMORROW = iso(new RealDate(RealDate.now() + 864e5));
const moveClock = (days) => { const shift = days * 864e5; globalThis.Date = class extends RealDate { constructor(...a) { if (a.length) super(...a); else super(RealDate.now() + shift); } static now() { return RealDate.now() + shift; } }; };
// a plan whose one teach block says which day and subject it is
const PLAN = (day, domain = 'numeracy', tag = `${day} ${domain}`) => ({ plan_date: day, domain_id: domain, selected_competency_id: domain === 'numeracy' ? 'N2.3.2' : 'L2.5.1', served_from: 'ai',
  groups: [{ label: 'progressor', count: 4, target_competency_id: 'N2.3.2' }],
  plan: { worksheets: {}, anchor: {}, rotation_schedule: { blocks: [{ type: 'teach', teach_group: 'progressor', duration_minutes: 20, script_hi: `PLAN-OF ${tag}`, talking_points: { you_do_hi: 'तुम करोगे' } }] } } });
let server = {};                                    // `${day} ${domain}` -> plan stored on the server
let fail = false; let calls = []; let hold = null;
const notFound = () => Object.assign(new Error('not found'), { status: 404 });
globalThis.__navs = [];
globalThis.__auth = { teacher: { teacher_id: 'T1' }, selectedDomain: 'numeracy', names: {}, currentPlan: null, setCurrentPlan: (p) => { globalThis.__auth.currentPlan = p; rerender(); } };
globalThis.__api = {
  getCachedPlan: async (t, day, domain) => { calls.push([day, domain]); if (hold) await hold; if (fail) throw new TypeError('Failed to fetch'); const p = server[`${day} ${domain}`]; if (!p) throw notFound(); return JSON.parse(JSON.stringify(p)); },
  getReviewChannels: async () => ({ has_plan: false, levels: [], channels: {} }), openAuthedPage: async () => {}, worksheetPath: () => '/w', prepareOfflineCopy: () => {},
};
let listeners = 0;
for (const target of [dom.window, dom.window.document]) {
  const add = target.addEventListener.bind(target); const rem = target.removeEventListener.bind(target);
  target.addEventListener = (t, f, o) => { if (t === 'focus' || t === 'visibilitychange') listeners += 1; return add(t, f, o); };
  target.removeEventListener = (t, f, o) => { if (t === 'focus' || t === 'visibilitychange') listeners -= 1; return rem(t, f, o); };
}
// everything the page ever put on the screen, even for a moment: each added element is kept (a record holds it even after it is replaced)
let seen = []; let added = [];
new dom.window.MutationObserver((records) => { for (const r of records) for (const nd of r.addedNodes) if (nd.nodeType === 1) {
  added.push(nd); const m = nd.textContent.match(/PLAN-OF (\d{4}-\d{2}-\d{2} [a-z0-9_-]+)/); if (m) seen.push(m[1]); } })
  .observe(document.body, { childList: true, subtree: true });
const everEmpty = () => added.some((nd) => (nd.matches && nd.matches('[data-testid="yojana-empty"]')) || (nd.querySelector && nd.querySelector('[data-testid="yojana-empty"]')));
let root; let rerender = () => {};
const flush = async () => { for (let i = 0; i < 6; i += 1) await act(async () => { await new Promise((r) => setTimeout(r, 0)); }); };
const show = async (plan, domain = 'numeracy') => {
  if (root) await act(async () => root.unmount());
  Object.assign(globalThis.__auth, { currentPlan: plan, selectedDomain: domain }); calls = [];
  root = createRoot(document.getElementById('root'));
  rerender = () => root.render(React.createElement(Yojana, { key: 'y' }));        // the app re-renders its screens when the plan in memory changes
  await act(async () => { rerender(); }); await flush();
};
const shown = () => { const m = document.body.textContent.match(/PLAN-OF (\d{4}-\d{2}-\d{2} [a-z0-9_-]+)/); return m ? m[1] : null; };
const empty = () => !!document.querySelector('[data-testid="yojana-empty"]');
let n = 0; const check = (label, ok, extra = '') => { n += 1; console.log(`  ${ok ? 'OK  ' : 'FAIL'} ${label}${ok ? '' : '  ' + extra}`); if (!ok) process.exitCode = 1; };

console.log('the plan in memory is today\'s');
server = { [`${TODAY} numeracy`]: PLAN(TODAY) };
await show(PLAN(TODAY));
check('today\'s plan for the chosen subject: shown, nothing asked of the server', shown() === `${TODAY} numeracy` && calls.length === 0, JSON.stringify(calls));

await act(async () => { dom.window.document.dispatchEvent(new dom.window.Event('visibilitychange')); dom.window.dispatchEvent(new dom.window.Event('focus')); }); await flush();
check('...and coming back to the app the same day asks nothing either', shown() === `${TODAY} numeracy` && calls.length === 0, JSON.stringify(calls));

console.log('\nthe phone brought back yesterday\'s page');
server = { [`${TODAY} numeracy`]: PLAN(TODAY, 'numeracy', `${TODAY} numeracy-stored`) };
let release; hold = new Promise((r) => { release = r; });
Object.assign(globalThis.__auth, { currentPlan: PLAN(YESTERDAY), selectedDomain: 'numeracy' }); calls = []; seen = [];
if (root) await act(async () => root.unmount());
root = createRoot(document.getElementById('root')); rerender = () => root.render(React.createElement(Yojana, { key: 'y' }));
await act(async () => { rerender(); });
check('while today\'s plan is being fetched: a spinner (not "no plan"), and yesterday\'s plan is never on the screen, not even for a moment', shown() === null && !!document.querySelector('.loading') && !empty()
  && !seen.some((x) => x.startsWith(YESTERDAY)) && calls.length === 1 && calls[0][0] === TODAY, JSON.stringify(seen));
hold = null; release(); await flush();
check('today\'s stored plan is loaded and shown', shown() === `${TODAY} numeracy-stored` && globalThis.__auth.currentPlan.plan_date === TODAY);
server = {};
await show(PLAN(YESTERDAY));
check('no plan stored for today: "कोई योजना नहीं", not yesterday\'s plan', empty() && shown() === null && !document.querySelector('[data-testid="yojana-load-failed"]'));
check('...and yesterday\'s plan is put away (the printed plan and the tick sheet cannot use it as today\'s)', globalThis.__auth.currentPlan === null);
fail = true;
await show(PLAN(YESTERDAY));
check('no internet: still not yesterday\'s plan; the screen says today\'s could not be opened', empty() && shown() === null && /आज की योजना खुल नहीं सकी/.test(document.querySelector('[data-testid="yojana-load-failed"]')?.textContent || ''));
fail = false;
check('the empty state still leads to making a plan', !!document.querySelector('[data-testid="yojana-make-plan"]'));
server = {};
Object.assign(globalThis.__auth, { currentPlan: PLAN(YESTERDAY), selectedDomain: 'numeracy' });
if (root) await act(async () => root.unmount());
root = createRoot(document.getElementById('root')); rerender = () => root.render(React.createElement(Yojana, { key: 'y' }));
let release2; hold = new Promise((r) => { release2 = r; }); added = []; seen = [];          // the server's answer held: the screen as it is before anything is loaded
await act(async () => { root.render(React.createElement(Yojana, { key: 'y' })); });
check('the very first frame with an older day’s plan in memory: the spinner, neither that plan nor a moment of "no plan"', !!document.querySelector('.loading') && !everEmpty() && !seen.length && shown() === null, `empty shown: ${everEmpty()}, plans shown: ${seen}`);
hold = null; release2(); await flush();
globalThis.__auth.currentPlan = PLAN(YESTERDAY);
const firstFrame = ReactDOMServer.renderToStaticMarkup(React.createElement(Yojana));          // drawn once, with nothing loaded yet: the first frame itself
check('...the first frame itself (drawn alone): the spinner, not "no plan" and not the older plan', /class="loading"/.test(firstFrame) && !/yojana-empty/.test(firstFrame) && !/PLAN-OF/.test(firstFrame));

console.log('\nthe other subject');
server = { [`${TODAY} r1_literacy`]: PLAN(TODAY, 'r1_literacy') };
await show(PLAN(TODAY, 'numeracy'), 'r1_literacy');
check('today\'s maths plan in memory, Hindi chosen, a Hindi plan stored today: the Hindi plan', shown() === `${TODAY} r1_literacy` && calls.length === 1 && calls[0][1] === 'r1_literacy', shown());
server = {};
await show(PLAN(TODAY, 'numeracy'), 'r1_literacy');
check('no Hindi plan today: today\'s maths plan is still shown (it is a real plan of today), and kept', shown() === `${TODAY} numeracy` && globalThis.__auth.currentPlan.domain_id === 'numeracy');

const pending = [];
globalThis.__api.getCachedPlan = (t, day, domain) => new Promise((res, rej) => { calls.push([day, domain]); pending.push({ domain, go: () => (server[`${day} ${domain}`] ? res(JSON.parse(JSON.stringify(server[`${day} ${domain}`]))) : rej(notFound())) }); });
server = { [`${TODAY} numeracy`]: PLAN(TODAY, 'numeracy'), [`${TODAY} r1_literacy`]: PLAN(TODAY, 'r1_literacy') };
await show(PLAN(YESTERDAY), 'numeracy');
globalThis.__auth.selectedDomain = 'r1_literacy'; await act(async () => { rerender(); }); await flush();
await act(async () => { pending.find((x) => x.domain === 'r1_literacy').go(); }); await flush();
await act(async () => { pending.find((x) => x.domain === 'numeracy').go(); }); await flush();
check('the subject changed while loading: the late answer for the subject left behind never replaces the new one', shown() === `${TODAY} r1_literacy` && globalThis.__auth.currentPlan.domain_id === 'r1_literacy', shown());
globalThis.__api.getCachedPlan = async (t, day, domain) => { calls.push([day, domain]); if (fail) throw new TypeError('Failed to fetch'); const p = server[`${day} ${domain}`]; if (!p) throw notFound(); return JSON.parse(JSON.stringify(p)); };

console.log('\nafter a reload (nothing in memory)');
server = { [`${TODAY} numeracy`]: PLAN(TODAY) };
await show(null);
check('today\'s stored plan is loaded, as before', shown() === `${TODAY} numeracy` && calls.length === 1);

console.log('\nleft open across midnight');
server = { [`${TODAY} numeracy`]: PLAN(TODAY) };
await show(PLAN(TODAY));
moveClock(1);
await act(async () => { dom.window.document.dispatchEvent(new dom.window.Event('visibilitychange')); }); await flush();
check('the app comes back the next morning: the new day has no plan yet, so "कोई योजना नहीं" (yesterday\'s is put away)', empty() && shown() === null && calls.some((c) => c[0] === TOMORROW), JSON.stringify(calls));
server[`${TOMORROW} numeracy`] = PLAN(TOMORROW);
await act(async () => { dom.window.dispatchEvent(new dom.window.Event('focus')); }); await flush();
check('...and once the new day\'s plan exists, coming back (focus) shows it', shown() === `${TOMORROW} numeracy`, shown());
globalThis.Date = RealDate;
await act(async () => root.unmount()); root = null;

console.log('\nonly when the screen is open');
const before = calls.length;
await act(async () => { dom.window.document.dispatchEvent(new dom.window.Event('visibilitychange')); dom.window.dispatchEvent(new dom.window.Event('focus')); }); await flush();
check('the screen gone, coming back to the app asks nothing: its listeners are removed', calls.length === before && listeners === 0, String(listeners));

console.log(process.exitCode ? `\nFAILED (${n} checks)` : `\nAll ${n} checks passed.`);
