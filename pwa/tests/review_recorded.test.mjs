// The Review shows the teacher's own recorded choices (29 Oct feedback): each child's recorded A / PA / NA stays visible after a save and when she comes back
// (from the server), a change is marked "PA → NA" until submitted, Submit counts what it will do, and the block after a save says what happened (recorded,
// updated, both, or no change; a roll not in the class is never counted). Reading aloud lists the children read today with their numbers.
// The REAL Review screen in a simulated browser with a fake server. That the server reports these is tested in backend/tests/test_review_recorded.py.
//
//     cd pwa
//     npm install --save-dev jsdom@24     (once; see plan_screen.dom.test.mjs)
//     node tests/review_recorded.test.mjs
//
// Without jsdom the test says so and stops without failing.
import fs from 'node:fs'; import path from 'node:path'; import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
let JSDOM;
try { ({ JSDOM } = await import('jsdom')); } catch (e) { console.log('SKIPPED: jsdom is not installed. To run this test: cd pwa; npm install --save-dev jsdom@24'); process.exit(0); }
const here = path.dirname(fileURLToPath(import.meta.url)); const src = path.join(here, '..', 'src'); const out = path.join(here, `.tmp-recorded-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));      // the temporary build folder is always removed, even if a check fails
const API = ['recordDecisions', 'recordObserved', 'recordORF', 'analysePhotos', 'getSavedAnalyses', 'getReviewCoverage', 'getReviewChannels', 'getCachedPlan'];
const stubs = { '../App': 'export const useAuth = () => globalThis.__auth;', 'react-router-dom': 'export const useNavigate = () => () => {}; export const useLocation = () => globalThis.__location || ({ pathname: "/review", state: null });',
  '../services/api': API.map((n) => `export const ${n} = (...a) => globalThis.__api.${n}(...a);`).join('\n') };
await build({ entryPoints: { review: path.join(src, 'screens/ReviewScreen.jsx') }, bundle: true, format: 'esm', platform: 'node', outdir: out, outExtension: { '.js': '.mjs' },
  loader: { '.js': 'jsx', '.jsx': 'jsx' }, external: ['react', 'react-dom', 'react-dom/client'], logLevel: 'error',
  plugins: [{ name: 'stubs', setup(b) { b.onResolve({ filter: /^(\.\.\/App|react-router-dom|\.\.\/services\/api)$/ }, (a) => ({ path: a.path, namespace: 'stub' })); b.onLoad({ filter: /.*/, namespace: 'stub' }, (a) => ({ contents: stubs[a.path], loader: 'js' })); } }] });
const dom = new JSDOM('<!doctype html><div id="root"></div>', { url: 'http://localhost/', pretendToBeVisual: true });
for (const k of ['window', 'document', 'navigator', 'HTMLElement', 'HTMLInputElement', 'Element', 'Node', 'MouseEvent', 'Event', 'localStorage', 'sessionStorage']) Object.defineProperty(globalThis, k, { value: dom.window[k], configurable: true, writable: true });
globalThis.IS_REACT_ACT_ENVIRONMENT = true; globalThis.requestAnimationFrame = (f) => setTimeout(f, 0);
dom.window.Element.prototype.scrollIntoView = () => {};
const React = (await import('react')).default; const { act } = await import('react'); const { createRoot } = await import('react-dom/client');
const Review = (await import(pathToFileURL(path.join(out, 'review.mjs')).href)).default;

// ── the fake server: today's maths plan with the decisions made, observation for the Progressors (rolls 3, 4, 5) ──
const d0 = new Date(); const TODAY = `${d0.getFullYear()}-${String(d0.getMonth() + 1).padStart(2, '0')}-${String(d0.getDate()).padStart(2, '0')}`;
const PLAN = (domain) => ({ plan_date: TODAY, domain_id: domain, selected_competency_id: domain === 'numeracy' ? 'N2.3.2' : 'L2.5.1', served_from: 'ai',
  groups: [{ label: 'beginner', count: 0, target_competency_id: 'N2.3.1' }, { label: 'progressor', count: 3, target_competency_id: 'N2.3.2' }, { label: 'proficient', count: 0, target_competency_id: 'N3.3.1' }],
  plan: { worksheets: {}, rotation_schedule: { blocks: [] } }, decisions: { progressor: 'advance' } });
// a small group: no sample, everyone (the shape the server always sends)
const SAMPLE = (rolls) => ({ mode: 'all', size: rolls.length, group_size: rolls.length, rolls, done: [], left: rolls, margin_points: 0, absent: [] });
let recorded = { 3: { status: 'achieved' }, 4: { status: 'partially_achieved' } };           // what the server holds for today
let saveReply = null; const saves = [];
globalThis.__auth = { teacher: { teacher_id: 'T1' }, selectedDomain: 'numeracy', names: {}, currentPlan: null, setCurrentPlan: (p) => { globalThis.__auth.currentPlan = p; } };
globalThis.__api = {
  getCachedPlan: async (t, d, domain) => PLAN(domain), recordDecisions: async () => ({}), getSavedAnalyses: async () => [],
  getReviewChannels: async (t, d, domain) => (domain === 'numeracy'
    ? { has_plan: true, channels: { observed: ['progressor'] }, levels: [{ channel: 'observed', level: 'progressor', competency_id: 'N2.3.2', name_hi: 'जोड़', rolls: [3, 4, 5] }] }
    : { has_plan: true, channels: { orf: ['progressor'] }, levels: [{ channel: 'orf', level: 'progressor', competency_id: 'L2.5.1', name_hi: 'पढ़ना', rolls: [12, 13] }] }),
  getReviewCoverage: async (t, d, domain) => (domain === 'numeracy'
    ? { group_rolls: [3, 4, 5], analysed_rolls: Object.keys(recorded).map(Number), pending_rolls: [3, 4, 5].filter((r) => !recorded[r]), labels: {}, sample: SAMPLE([3, 4, 5]), recorded: JSON.parse(JSON.stringify(recorded)) }
    : { group_rolls: [12, 13], analysed_rolls: [12], pending_rolls: [13], labels: {}, sample: SAMPLE([12, 13]), recorded: { 12: { status: 'achieved', cwpm: 42, errors: 3 } } }),
  recordObserved: async (t, d, items) => { saves.push(items); return saveReply(items); },
  recordORF: async () => ({}), analysePhotos: async () => ({}),
};
let root;
const flush = async () => { for (let i = 0; i < 5; i += 1) await act(async () => { await new Promise((r) => setTimeout(r, 0)); }); };
const show = async () => { if (root) await act(async () => root.unmount()); root = createRoot(document.getElementById('root')); await act(async () => { root.render(React.createElement(Review)); }); await flush(); };
const q = (sel) => document.querySelector(sel);
const click = async (el) => { await act(async () => { el.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true })); }); await flush(); };
const btn = (r, st) => q(`[data-testid="obs-${r}-${st}"]`);
const submit = () => q('[data-testid="obs-submit"]');
let n = 0; const check = (label, ok, extra = '') => { n += 1; console.log(`  ${ok ? 'OK  ' : 'FAIL'} ${label}${ok ? '' : '  ' + extra}`); if (!ok) process.exitCode = 1; };

console.log('the recorded choices stay visible');
sessionStorage.clear();
await show();
check('opening the Review: roll 3\'s recorded A and roll 4\'s recorded PA are shown chosen, marked "✓ दर्ज"; roll 5 (not yet) has none',
  btn(3, 'achieved').getAttribute('aria-pressed') === 'true' && btn(3, 'achieved').dataset.state === 'recorded' && btn(4, 'partially_achieved').dataset.state === 'recorded'
  && !!q('[data-testid="obs-recorded-3"]') && /✓ दर्ज/.test(q('[data-testid="obs-recorded-3"]').textContent) && !q('[data-testid="obs-recorded-5"]')
  && ['achieved', 'partially_achieved', 'not_achieved'].every((st) => btn(5, st).getAttribute('aria-pressed') === 'false'));
console.log('\nwhy this way (today\'s skills need only observation)');
check('no plain note "आज के कौशल के लिए यही तरीका चाहिए"; instead a closed "ⓘ यही तरीका क्यों?", and only the needed way is shown', !/यही तरीका चाहिए/.test(document.getElementById('root').textContent)
  && /यही तरीका क्यों\?/.test(q('[data-testid="hint-why-way"] .hint-btn').textContent) && !q('[data-testid="hint-why-way"] .hint-text') && !!q('[data-testid="channel-observed"]') && !q('[data-testid="channel-photo"]'));
await click(q('[data-testid="hint-why-way"] .hint-btn'));
check('...open: why ("यह कौशल बच्चे करके या बोलकर दिखाते हैं … देखकर आँका जाता है, लिखकर नहीं") and which group and skill today ("▲ प्रगतिशील N2.3.2")',
  /देखकर आँका जाता है, लिखकर नहीं/.test(q('[data-testid="why-observed"]').textContent) && /आज.*▲ प्रगतिशील N2\.3\.2/.test(q('[data-testid="why-observed"]').textContent) && !q('[data-testid="why-photo"]'));
await click(q('[data-testid="channel-toggle"]'));
check('..."दूसरे तरीके भी दिखाएँ" shows all three ways; "सिर्फ़ ज़रूरी तरीके दिखाएँ" goes back', !!q('[data-testid="channel-photo"]') && !!q('[data-testid="channel-orf"]') && /सिर्फ़ ज़रूरी तरीके दिखाएँ/.test(q('[data-testid="channel-toggle"]').textContent));
await click(q('[data-testid="channel-toggle"]'));
check('...back to the needed way only', !q('[data-testid="channel-photo"]') && !!q('[data-testid="channel-observed"]'));

console.log('\nthe recorded choices, before any change');
check('nothing changed yet: Submit says just "✓ जमा करें" and is off', /^✓ जमा करें/.test(submit().textContent) && !/बदलाव|नया/.test(submit().textContent) && submit().disabled);

console.log('\nchanging, before Submit');
await click(btn(4, 'not_achieved'));
check('roll 4 PA → NA: NA is chosen, marked as a change (dashed), with "PA → NA" next to it', btn(4, 'not_achieved').dataset.state === 'changing' && /PA → NA/.test(q('[data-testid="obs-change-4"]').textContent)
  && btn(4, 'partially_achieved').getAttribute('aria-pressed') === 'false' && /dashed/.test(btn(4, 'not_achieved').style.outline));
await click(btn(5, 'achieved'));
check('roll 5 A (first time): chosen, no change mark; Submit counts "1 नया, 1 बदलाव"', btn(5, 'achieved').dataset.state === 'new' && !q('[data-testid="obs-change-5"]') && /जमा करें · 1 नया, 1 बदलाव/.test(submit().textContent), submit().textContent);
await click(btn(3, 'achieved'));
check('tapping roll 3\'s recorded A again is no change: nothing added to Submit', /जमा करें · 1 नया, 1 बदलाव/.test(submit().textContent) && btn(3, 'achieved').dataset.state === 'recorded');
await click(btn(4, 'partially_achieved'));
check('roll 4 back to its recorded PA: the change is gone ("✓ दर्ज" again), Submit "1 नया"', !q('[data-testid="obs-change-4"]') && !!q('[data-testid="obs-recorded-4"]') && /जमा करें · 1 नया/.test(submit().textContent) && !/बदलाव/.test(submit().textContent));
await click(btn(4, 'not_achieved'));

console.log('\nafter Submit: what happened, and the choices stay');
saveReply = () => ({ status: 'recorded', items_recorded: 2, new: 1, changed: 1, unchanged: 0, not_found: [],
  results: [{ roll_number: 4, status: 'not_achieved', previous: 'partially_achieved', outcome: 'changed' }, { roll_number: 5, status: 'achieved', previous: null, outcome: 'new' }] });
recorded = { 3: { status: 'achieved' }, 4: { status: 'not_achieved' }, 5: { status: 'achieved' } };
await click(submit());
const block = () => q('[data-testid="observed-saved"]').textContent;
check('only the two changes were sent', saves.length === 1 && JSON.stringify(saves[0].map((i) => [i.roll_number, i.status]).sort()) === JSON.stringify([[4, 'not_achieved'], [5, 'achieved']]));
check('the block says what happened: "✓ 2 अवलोकन: 1 नया, 1 बदला गया" and "बदले: रोल 4 PA → NA"', /✓ 2 अवलोकन: 1 नया, 1 बदला गया/.test(block()) && /रोल 4 PA → NA/.test(q('[data-testid="saved-changes"]').textContent), block());
check('...and the list keeps the teacher\'s choices, now recorded: roll 4 NA, roll 5 A, roll 3 A (not ticks only)',
  btn(4, 'not_achieved').dataset.state === 'recorded' && btn(5, 'achieved').dataset.state === 'recorded' && btn(3, 'achieved').dataset.state === 'recorded' && /^✓ जमा करें/.test(submit().textContent) && submit().disabled);

console.log('\nthe other cases');
await click(btn(3, 'not_achieved'));
saveReply = () => ({ status: 'recorded', items_recorded: 1, new: 0, changed: 1, unchanged: 0, not_found: [], results: [{ roll_number: 3, status: 'not_achieved', previous: 'achieved', outcome: 'changed' }] });
recorded = { ...recorded, 3: { status: 'not_achieved' } };
await click(submit());
check('only a change: "✓ 1 अवलोकन बदला गया" (the 29 Oct example, said in the singular)', /✓ 1 अवलोकन बदला गया/.test(block()) && q('[data-testid="observed-saved-count"]').dataset.kind === 'changed', block());
await click(btn(5, 'not_achieved'));
saveReply = () => ({ status: 'recorded', items_recorded: 0, new: 0, changed: 0, unchanged: 1, not_found: [99], results: [{ roll_number: 5, status: 'not_achieved', previous: 'not_achieved', outcome: 'unchanged' }] });
await click(submit());
check('nothing different on the server: "कोई बदलाव नहीं"; a roll not in the class: "रोल 99 कक्षा में नहीं है, दर्ज नहीं हुआ" (never counted)', /कोई बदलाव नहीं/.test(block()) && /रोल 99 कक्षा में नहीं है, दर्ज नहीं हुआ/.test(q('[data-testid="saved-not-found"]').textContent), block());

console.log('\ncoming back');
await show();
check('the Review opened again: the recorded choices are shown from the server (roll 3 NA, 4 NA, 5 A)', btn(3, 'not_achieved').dataset.state === 'recorded' && btn(4, 'not_achieved').dataset.state === 'recorded' && btn(5, 'achieved').dataset.state === 'recorded');

console.log('\nreading aloud');
sessionStorage.clear(); globalThis.__auth.selectedDomain = 'r1_literacy'; globalThis.__auth.currentPlan = null;
await show();
const read = q('[data-testid="orf-recorded"]');
check('"आज पढ़ चुके: 1 बच्चा" (a fold), with roll 12\'s numbers: "42 सही · 3 गलतियाँ" and its pace', read && /आज पढ़ चुके: 1 बच्चा/.test(read.querySelector('summary').textContent)
  && /रोल 12/.test(q('[data-testid="orf-recorded-12"]').textContent) && /42 सही · 3 गलतियाँ · रफ़्तार कक्षा-स्तर पर/.test(q('[data-testid="orf-recorded-12"]').textContent), read && read.textContent);
check('...and how to correct a wrong entry: the same roll again, the newest counts', /वही रोल नंबर फिर दर्ज करें; नया नतीजा गिना जाएगा/.test(read.textContent));

await act(async () => root.unmount());
console.log(`\n${process.exitCode ? 'SOME CHECKS FAILED' : 'OK: ' + n + ' checks: the Review shows what was recorded, marks changes before Submit, and says after a save what was new, changed or the same'}`);
