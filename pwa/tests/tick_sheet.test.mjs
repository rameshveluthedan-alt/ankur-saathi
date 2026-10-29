// The paper tick sheet (29 Oct, at /plan/ticks): for recording during You Do without the phone. One table per group checked by observing (रोल | A | PA | NA)
// or by reading aloud (रोल | सही शब्द | गलतियाँ, with the text to read), roll numbers but never a name; photo groups get none; with the ways unknown, no sheet
// (never a guess). The plan screen's "आज की समीक्षा" fold opens it only when a group is observed or read aloud.
// The REAL sheet and plan screens in a simulated browser with a fake server. Whether it prints well is checked by hand with a real print.
//
//     cd pwa
//     npm install --save-dev jsdom@24     (once; see plan_screen.dom.test.mjs)
//     node tests/tick_sheet.test.mjs
//
// Without jsdom the test says so and stops without failing.
import fs from 'node:fs'; import path from 'node:path'; import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
let JSDOM;
try { ({ JSDOM } = await import('jsdom')); } catch (e) { console.log('SKIPPED: jsdom is not installed. To run this test: cd pwa; npm install --save-dev jsdom@24'); process.exit(0); }
const here = path.dirname(fileURLToPath(import.meta.url)); const src = path.join(here, '..', 'src'); const out = path.join(here, `.tmp-ticks-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));      // the temporary build folder is always removed, even if a check fails
const API = ['getReviewChannels', 'getCachedPlan', 'openAuthedPage', 'worksheetPath', 'prepareOfflineCopy'];
const stubs = { '../App': 'export const useAuth = () => globalThis.__auth;',
  'react-router-dom': 'export const useNavigate = () => (...a) => globalThis.__navs.push(a); export const useLocation = () => ({ pathname: "/", state: null });',
  '../services/api': API.map((n) => `export const ${n} = (...a) => globalThis.__api.${n}(...a);`).join('\n') };
await build({ entryPoints: { ticks: path.join(src, 'screens/TickSheet.jsx'), yojana: path.join(src, 'screens/YojanaScreen.jsx') }, bundle: true, format: 'esm', platform: 'node', outdir: out,
  outExtension: { '.js': '.mjs' }, loader: { '.js': 'jsx', '.jsx': 'jsx' }, external: ['react', 'react-dom', 'react-dom/client'], logLevel: 'error',
  plugins: [{ name: 'stubs', setup(b) { b.onResolve({ filter: /^(\.\.\/App|react-router-dom|\.\.\/services\/api)$/ }, (a) => ({ path: a.path, namespace: 'stub' })); b.onLoad({ filter: /.*/, namespace: 'stub' }, (a) => ({ contents: stubs[a.path], loader: 'js' })); } }] });
const dom = new JSDOM('<!doctype html><div id="root"></div>', { url: 'http://localhost/', pretendToBeVisual: true });
for (const k of ['window', 'document', 'navigator', 'HTMLElement', 'HTMLInputElement', 'Element', 'Node', 'MouseEvent', 'Event', 'localStorage', 'sessionStorage']) Object.defineProperty(globalThis, k, { value: dom.window[k], configurable: true, writable: true });
globalThis.IS_REACT_ACT_ENVIRONMENT = true; globalThis.requestAnimationFrame = (f) => setTimeout(f, 0);
dom.window.Element.prototype.scrollIntoView = () => {};
const React = (await import('react')).default; const { act } = await import('react'); const { createRoot } = await import('react-dom/client');
const Ticks = (await import(pathToFileURL(path.join(out, 'ticks.mjs')).href)).default;
const Yojana = (await import(pathToFileURL(path.join(out, 'yojana.mjs')).href)).default;
const appSrc = fs.readFileSync(path.join(src, 'App.jsx'), 'utf8');

// ── the fake server: the Beginners observed, the Progressors photographed, the Proficients read aloud ──
const teach = (g) => ({ type: 'teach', teach_group: g, duration_minutes: 20, script_hi: `${g} का काम`, talking_points: { you_do_hi: 'तुम करोगे' } });
const PLAN = () => ({ plan_date: '2026-10-29', domain_id: 'numeracy', selected_competency_id: 'N2.3.2', served_from: 'ai',
  groups: [{ label: 'beginner', count: 4, target_competency_id: 'N0.1.1' }, { label: 'progressor', count: 4, target_competency_id: 'N2.3.2' }, { label: 'proficient', count: 3, target_competency_id: 'L2.5.1' }],
  plan: { worksheets: {}, anchor: {}, rotation_schedule: { blocks: [teach('beginner'), teach('progressor'), teach('proficient')] } } });
const CH = { has_plan: true, channels: { observed: ['beginner'], photo: ['progressor'], orf: ['proficient'] },
  levels: [{ channel: 'orf', level: 'proficient', competency_id: 'L2.5.1', name_hi: 'पढ़ने की रफ़्तार', rolls: [11, 9, 10], passage: { id: 'RP-7', title: 'मेला', text: '…', word_count: 62 } },
           { channel: 'observed', level: 'beginner', competency_id: 'N0.1.1', name_hi: 'छाँटना', rolls: [3, 1, 4, 2] },
           { channel: 'photo', level: 'progressor', competency_id: 'N2.3.2', name_hi: 'जोड़', rolls: [5, 6, 7, 8] }] };
let ch = CH; let calls = [];
globalThis.__navs = [];
globalThis.__auth = { teacher: { teacher_id: 'T1', employee_code: 'MPT101', enrolled_grades: ['grade_2'] }, selectedDomain: 'numeracy', names: { 1: 'सीता देवी', 9: 'रामू' }, currentPlan: PLAN(), setCurrentPlan() {} };
globalThis.__api = { getReviewChannels: async (...a) => { calls.push(a); if (ch instanceof Error) throw ch; return JSON.parse(JSON.stringify(ch)); },
  getCachedPlan: async () => PLAN(), openAuthedPage: async () => {}, worksheetPath: () => '/w', prepareOfflineCopy: () => {} };
let root;
const flush = async () => { for (let i = 0; i < 5; i += 1) await act(async () => { await new Promise((r) => setTimeout(r, 0)); }); };
const show = async (C) => { if (root) await act(async () => root.unmount()); root = createRoot(document.getElementById('root')); await act(async () => { root.render(React.createElement(C)); }); await flush(); };
const q = (sel) => document.querySelector(sel); const qa = (sel) => [...document.querySelectorAll(sel)];
const click = async (el) => { await act(async () => { el.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true })); }); await flush(); };
const cells = (tr) => [...tr.children].map((c) => c.textContent.trim());
let n = 0; const check = (label, ok, extra = '') => { n += 1; console.log(`  ${ok ? 'OK  ' : 'FAIL'} ${label}${ok ? '' : '  ' + extra}`); if (!ok) process.exitCode = 1; };

console.log('the sheet');
await show(Ticks);
const sheet = q('[data-testid="tick-sheet"]');
check('it asks the server for the review ways of the plan\'s own day and subject', calls.length === 1 && calls[0][0] === 'T1' && calls[0][1] === '2026-10-29' && calls[0][2] === 'numeracy', JSON.stringify(calls));
check('the title: "टिक शीट", the teacher\'s code, the class and the date', /टिक शीट · MPT101 · कक्षा 2 · 29 अक्टू॰ 2026/.test(q('[data-testid="ticks-title"]').textContent), q('[data-testid="ticks-title"]').textContent);
check('when to fill it and where it goes after class (step 2)', /तुम करोगे/.test(q('[data-testid="ticks-when"]').textContent) && /चरण 2/.test(q('[data-testid="ticks-when"]').textContent));
check('one table per observed or read-aloud group, in group order; none for the photographed Progressors', JSON.stringify(qa('[data-testid^="tick-group-"]').map((e) => e.dataset.testid)) === JSON.stringify(['tick-group-beginner', 'tick-group-proficient']));
const beg = q('[data-testid="tick-group-beginner"]');
check('the Beginners: the skill and the way in the heading', /शुरुआती · N0\.1\.1 छाँटना · ✓ देखकर दर्ज करें/.test(beg.querySelector('[data-testid="tick-head"]').textContent), beg.querySelector('[data-testid="tick-head"]').textContent);
check('observing: columns रोल | A | PA | NA', JSON.stringify(cells(beg.querySelector('thead tr'))) === JSON.stringify(['रोल', 'A', 'PA', 'NA']));
check('a row per child, roll numbers in order, the boxes empty', JSON.stringify([...beg.querySelectorAll('tbody tr')].map(cells)) === JSON.stringify([1, 2, 3, 4].map((r) => [String(r), '', '', ''])));
check('the meanings of A / PA / NA are the Review\'s own ("A = करके दिखाया, बिना मदद")', /A = करके दिखाया, बिना मदद · PA = मदद से, या आधा सही · NA = अभी नहीं/.test(beg.querySelector('[data-testid="tick-key"]').textContent));
const pro = q('[data-testid="tick-group-proficient"]');
check('reading aloud: columns रोल | सही शब्द | गलतियाँ, a row per child in order', JSON.stringify(cells(pro.querySelector('thead tr'))) === JSON.stringify(['रोल', 'सही शब्द', 'गलतियाँ'])
  && JSON.stringify([...pro.querySelectorAll('tbody tr')].map((tr) => cells(tr)[0])) === JSON.stringify(['9', '10', '11']));
check('reading aloud: the text to read and its length, and the error rule', /«मेला» \(62 शब्द\) · एक मिनट/.test(pro.querySelector('[data-testid="tick-passage"]').textContent) && /छूटा शब्द/.test(pro.querySelector('[data-testid="tick-key"]').textContent));
check('never a child\'s name, though the phone knows them', !/सीता|रामू/.test(sheet.textContent));
check('printing shows this page alone (body.print-plan, with the page\'s .plan-print class)', document.body.classList.contains('print-plan') && sheet.classList.contains('plan-print'));
check('a page of its own: the route, and no bottom bar there', /path="\/plan\/ticks"/.test(appSrc) && /path === '\/plan\/ticks'/.test(appSrc));
await click(q('[data-testid="ticks-back"]'));
check('"← वापस" leads to the plan', JSON.stringify(globalThis.__navs.pop()) === JSON.stringify(['/yojana']));

console.log('no sheet where there is nothing to record on paper, or the ways are not known');
ch = { ...CH, levels: CH.levels.map((l) => (l.level === 'proficient' ? { ...l, passage: undefined } : l)) };
await show(Ticks);
check('no text in the bank: the sheet says to take a text not read today', /आज नहीं पढ़ा/.test(q('[data-testid="tick-passage"]').textContent));
ch = { has_plan: true, channels: { photo: ['progressor'] }, levels: [CH.levels[2]] };
await show(Ticks);
check('only photo groups today: "टिक शीट की ज़रूरत नहीं", no table and no print button', !!q('[data-testid="ticks-none"]') && !q('table') && !q('[data-testid="ticks-print"]'));
ch = { has_plan: false, levels: [], channels: {} };
await show(Ticks);
check('no stored plan: no sheet (never a guess)', !!q('[data-testid="ticks-unknown"]') && !q('table'));
ch = new Error('offline');
await show(Ticks);
check('the server not reached: no sheet either', !!q('[data-testid="ticks-unknown"]') && !q('table'));
await act(async () => root.unmount()); root = null;
check('leaving the page takes the print rule away again', !document.body.classList.contains('print-plan'));

console.log('the plan screen opens it');
ch = CH;
await show(Yojana);
check('"🖨️ टिक शीट" in "आज की समीक्षा" when a group is observed or read aloud', !!q('[data-testid="review-today"] [data-testid="open-ticks"]'));
await click(q('[data-testid="open-ticks"]'));
check('it opens /plan/ticks', JSON.stringify(globalThis.__navs.pop()) === JSON.stringify(['/plan/ticks']));
ch = { has_plan: true, channels: { photo: ['progressor'] }, levels: [CH.levels[2]] };
await show(Yojana);
check('only photo groups: no tick sheet button', !q('[data-testid="open-ticks"]'));
ch = { has_plan: false, levels: [], channels: {} };
await show(Yojana);
check('the ways not known: no tick sheet button', !q('[data-testid="open-ticks"]'));

await act(async () => root.unmount());
console.log(process.exitCode ? `\nFAILED (${n} checks)` : `\nAll ${n} checks passed.`);
