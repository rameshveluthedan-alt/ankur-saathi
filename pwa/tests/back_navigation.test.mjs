// The phone's Back button and the "← वापस" buttons (navigation D and F, 29 Oct).
// D: inside the Review, Back follows the teacher's own moves (step 1 → 2 → 3, and into a photo analysis) and goes back one at a time, then leaves the Review
//    as before; the screen's own "←" buttons do the same as Back when they go to the view just before. The "replace today's plan?" dialog closes on Back
//    (keeping the plan), and closed any other way it takes its history entry with it.
// F: Profile's and the register's "← वापस" return to the screen the teacher came from (the Plan screen when the app was opened there).
// The REAL screens in a simulated browser with its real history (pushState, Back, Forward); React Router is a stand-in, so leaving the Review shows as
// the history reaching the entry before it.
//
//     cd pwa
//     npm install --save-dev jsdom@24     (once; see plan_screen.dom.test.mjs)
//     node tests/back_navigation.test.mjs
//
// Without jsdom the test says so and stops without failing.
import fs from 'node:fs'; import path from 'node:path'; import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
let JSDOM;
try { ({ JSDOM } = await import('jsdom')); } catch (e) { console.log('SKIPPED: jsdom is not installed. To run this test: cd pwa; npm install --save-dev jsdom@24'); process.exit(0); }
const here = path.dirname(fileURLToPath(import.meta.url)); const src = path.join(here, '..', 'src'); const out = path.join(here, `.tmp-back-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));      // the temporary build folder is always removed, even if a check fails
const API = ['recordDecisions', 'recordObserved', 'recordORF', 'analysePhotos', 'getSavedAnalyses', 'getReviewCoverage', 'getReviewChannels', 'getCachedPlan',
  'adminSchool', 'adminTeachers', 'adminResetPin', 'adminUnlock', 'adminRecordConsent', 'previewRegister', 'commitRegister', 'downloadRegisterTemplate'];
const stubs = { '../App': 'export const useAuth = () => globalThis.__auth;',
  'react-router-dom': 'export const useNavigate = () => (...a) => globalThis.__navs.push(a); export const useLocation = () => globalThis.__location;',
  './ChangePinScreen': 'export const PinChangeForm = () => null;',
  '../services/api': API.map((n) => `export const ${n} = (...a) => globalThis.__api.${n}(...a);`).join('\n') };
await build({ entryPoints: { review: path.join(src, 'screens/ReviewScreen.jsx'), dialog: path.join(src, 'components/ReplacePlanDialog.jsx'),
    account: path.join(src, 'screens/AccountScreen.jsx'), register: path.join(src, 'screens/RegisterScreen.jsx') },
  bundle: true, format: 'esm', platform: 'node', outdir: out, outExtension: { '.js': '.mjs' }, loader: { '.js': 'jsx', '.jsx': 'jsx' }, external: ['react', 'react-dom', 'react-dom/client'], logLevel: 'error',
  plugins: [{ name: 'stubs', setup(b) { b.onResolve({ filter: /^(\.\.\/App|react-router-dom|\.\/ChangePinScreen|\.\.\/services\/api)$/ }, (a) => ({ path: a.path, namespace: 'stub' })); b.onLoad({ filter: /.*/, namespace: 'stub' }, (a) => ({ contents: stubs[a.path], loader: 'js' })); } }] });
const dom = new JSDOM('<!doctype html><div id="root"></div>', { url: 'http://localhost/', pretendToBeVisual: true });
for (const k of ['window', 'document', 'navigator', 'HTMLElement', 'HTMLInputElement', 'Element', 'Node', 'MouseEvent', 'Event', 'KeyboardEvent', 'localStorage', 'sessionStorage']) Object.defineProperty(globalThis, k, { value: dom.window[k], configurable: true, writable: true });
globalThis.IS_REACT_ACT_ENVIRONMENT = true; globalThis.requestAnimationFrame = (f) => setTimeout(f, 0);
dom.window.Element.prototype.scrollIntoView = () => {};
const React = (await import('react')).default; const { act } = await import('react'); const { createRoot } = await import('react-dom/client');
const Review = (await import(pathToFileURL(path.join(out, 'review.mjs')).href)).default;
const Dialog = (await import(pathToFileURL(path.join(out, 'dialog.mjs')).href)).default;
const Account = (await import(pathToFileURL(path.join(out, 'account.mjs')).href)).default;
const Register = (await import(pathToFileURL(path.join(out, 'register.mjs')).href)).default;

// ── the fake server: two groups, nothing recorded yet today; one saved photo analysis ──
const d0 = new Date(); const TODAY = `${d0.getFullYear()}-${String(d0.getMonth() + 1).padStart(2, '0')}-${String(d0.getDate()).padStart(2, '0')}`;
const PLAN = (finals = {}) => ({ plan_date: TODAY, domain_id: 'numeracy', selected_competency_id: 'N2.3.2', served_from: 'ai',
  groups: [{ label: 'beginner', count: 4, target_competency_id: 'N0.1.1', target_competency_name_hi: 'छाँटना' }, { label: 'progressor', count: 4, target_competency_id: 'N2.3.2', target_competency_name_hi: 'जोड़' }],
  plan: { worksheets: {}, anchor: {}, rotation_schedule: { blocks: [] } }, decisions: { ...finals }, first_judgments: { ...finals }, final_decisions: finals, today_evidence: {} });
let reply = PLAN();
const SAVED = [{ id: 1, worksheet_level: 'progressor', created_at: `${TODAY}T10:00:00`, result: { children_analysed: 2, group_accuracy: 0.5, children: [], copy_errors_excluded: 0 } }];
globalThis.__navs = []; globalThis.__location = { pathname: '/review', state: null };
globalThis.__auth = { teacher: { teacher_id: 'T1', role: 'teacher', employee_code: 'MPT101', enrolled_grades: ['grade_2'] }, selectedDomain: 'numeracy', names: {}, currentPlan: null,
  setCurrentPlan: (p) => { globalThis.__auth.currentPlan = p; }, setTeacher() {}, logout() {} };
globalThis.__api = {
  getCachedPlan: async () => JSON.parse(JSON.stringify(reply)), getReviewChannels: async () => ({ has_plan: false, levels: [], channels: {} }), getSavedAnalyses: async () => JSON.parse(JSON.stringify(SAVED)),
  getReviewCoverage: async () => null, recordDecisions: async () => ({}), recordObserved: async () => ({}), recordORF: async () => ({}), analysePhotos: async () => ({}),
  adminSchool: async () => ({}), adminTeachers: async () => ({ teachers: [] }), adminResetPin: async () => ({}), adminUnlock: async () => ({}), adminRecordConsent: async () => ({}),
  previewRegister: async () => ({}), commitRegister: async () => ({}), downloadRegisterTemplate: async () => { globalThis.__tpl += 1; },
};
let root;
const flush = async () => { for (let i = 0; i < 6; i += 1) await act(async () => { await new Promise((r) => setTimeout(r, 0)); }); };
const show = async (C, props = {}) => { if (root) await act(async () => root.unmount()); root = createRoot(document.getElementById('root')); await act(async () => { root.render(React.createElement(C, props)); }); await flush(); };
const q = (sel) => document.querySelector(sel);
const click = async (el) => { await act(async () => { el.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true })); }); await flush(); };
const H = dom.window.history;
// the Back-press listeners the screens hold, counted (a screen gone must not keep one)
let popListeners = 0;
{ const add = dom.window.addEventListener.bind(dom.window); const rem = dom.window.removeEventListener.bind(dom.window);
  dom.window.addEventListener = (t, f, o) => { if (t === 'popstate') popListeners += 1; return add(t, f, o); };
  dom.window.removeEventListener = (t, f, o) => { if (t === 'popstate') popListeners -= 1; return rem(t, f, o); }; }
const back = async () => { await act(async () => { H.back(); }); await flush(); };
const forward = async () => { await act(async () => { H.forward(); }); await flush(); };
// the Review opened from another screen: that screen's entry, then the Review's own (React Router's fields: usr, key, idx), so leaving the Review shows as reaching 'prev-…'
const enterFrom = (key) => { H.pushState({ usr: null, key: `prev-${key}`, idx: 0 }, ''); H.pushState({ usr: null, key, idx: 1 }, ''); sessionStorage.clear(); };
const stepNow = () => (q('[data-testid="analysis-view"]') ? 'a' : q('[data-testid="review-title"]') && q('[data-testid="review-title"]').dataset.step);
const viewNow = () => (q('[data-testid="back-to-work"]') ? 'a' : stepNow());
let n = 0; const check = (label, ok, extra = '') => { n += 1; console.log(`  ${ok ? 'OK  ' : 'FAIL'} ${label}${ok ? '' : '  ' + extra}`); if (!ok) process.exitCode = 1; };

console.log('D: the phone\'s Back button follows the Review\'s steps');
enterFrom('plan-screen');
await show(Review);
const len0 = H.length;
check('opened at step 1: no history entry of its own (the router\'s entry, marked with the view), so nothing extra to press Back through', viewNow() === '1' && H.length === len0 && H.state.key === 'plan-screen' && H.state.reviewView === '1');
for (const b of document.querySelectorAll('.decision-btn.advance')) await click(b);
await click(q('[data-testid="record-decisions"]'));
check('recorded → step 2: one entry in the history', viewNow() === '2' && H.length === len0 + 1 && H.state.reviewView === '2');
check('...the router\'s fields are kept on it (it sees the same location)', H.state.key === 'plan-screen' && H.state.idx === 1);
await back();
check('Back → step 1', viewNow() === '1');
await forward();
check('Forward → step 2 again', viewNow() === '2');
await click(q('[data-testid="see-analysis"]'));
check('"फ़ोटो विश्लेषण देखें" → the analysis, its own entry', viewNow() === 'a' && H.state.reviewView === 'a');
await back();
check('Back closes the analysis → the children\'s work (step 2)', viewNow() === '2');
await click(q('[data-testid="see-analysis"]'));
const lenA = H.length;
await click(q('[data-testid="back-to-work"]'));
check('"← बच्चों का काम" from the analysis is the same as Back: no new entry, the one before', viewNow() === '2' && H.length === lenA && H.state.reviewView === '2');
await click(q('[data-testid="to-final"]'));
check('"आगे: अंतिम निर्णय" → step 3, its own entry', viewNow() === '3' && H.state.reviewView === '3' && H.state.reviewPrev === '2');
await click(q('[data-testid="final-back"]'));
check('"← 2/3 बच्चों का काम" goes back to the entry before (step 2), as Back would', viewNow() === '2' && H.state.reviewView === '2');
await click(q('[data-testid="to-final"]'));
await back();
check('Back from step 3 → step 2', viewNow() === '2');
await back();
check('Back again → step 1', viewNow() === '1');
await back();
check('Back once more leaves the Review: the history is at the screen before it', H.state && H.state.key === 'prev-plan-screen' && !('reviewView' in H.state), JSON.stringify(H.state));

console.log('\nD: opened at a step, Back leaves from there');
reply = PLAN({ beginner: 'advance', progressor: 'advance' });
enterFrom('tab');
const lenB = H.length;
await show(Review);
check('every final decision recorded: the Review opens at step 3, with no entry of its own (Back leaves at once)', viewNow() === '3' && H.length === lenB && H.state.key === 'tab' && H.state.reviewView === '3');
await click(q('[data-testid="final-back"]'));
check('"← 2/3" there: step 2, as a new entry (there was no step 2 before it), so Back returns to step 3', viewNow() === '2' && H.length === lenB + 1);
await back();
check('...Back → step 3', viewNow() === '3');
reply = PLAN();
globalThis.__location = { pathname: '/review', state: { from: 'plan', channel: 'observed', level: 'beginner' } };
enterFrom('record-now');
const lenC = H.length;
await show(Review);
check('from "अभी दर्ज करें": step 2 with no entry of its own, so Back goes straight back to the plan', viewNow() === '2' && H.length === lenC && H.state.key === 'record-now');
await click(q('[data-testid="back-to-decisions"]'));
check('"← 1/3 पहला अनुमान बदलें" there: step 1, and Back returns to step 2', viewNow() === '1' && H.length === lenC + 1);
await back();
check('...Back → step 2, still the plan\'s group and way', viewNow() === '2' && !!q('[data-testid="from-plan"]'));
globalThis.__location = { pathname: '/review', state: null };
await act(async () => root.unmount()); root = null;
H.pushState({ usr: null, key: 'elsewhere', idx: 2 }, '');
await back();
check('the Review gone, a Back press is not answered by it any more: its listener is removed, nothing shown', popListeners === 0 && !q('[data-testid="review-title"]'), String(popListeners));

console.log('\nD: the "replace today\'s plan?" dialog closes on Back');
let kept = 0; let replaced = 0;
const dialogProps = { kind: 'plan', evidence: { has_evidence: false }, onKeep: () => { kept += 1; }, onReplace: () => { replaced += 1; } };
H.pushState({ usr: null, key: 'plan', idx: 1 }, '');
const lenD = H.length;
await show(Dialog, dialogProps);
check('opening it adds one entry to the history', H.length === lenD + 1 && H.state.dialog === 'replace' && H.state.key === 'plan');
await back();
check('Back keeps the plan: "नहीं, वही रखें" once', kept === 1 && replaced === 0 && H.state.key === 'plan' && !H.state.dialog);
await show(Dialog, dialogProps);
await click(q('[data-testid="replace-keep"]'));
check('"नहीं, वही रखें" tapped: kept once more, and the dialog\'s entry is taken away (the next Back is not spent on it)', kept === 2 && H.state.key === 'plan' && !H.state.dialog);
await show(Dialog, dialogProps);
await click(q('[data-testid="replace-yes"]'));
check('"हाँ, बदलें": replaced, not kept, and its entry taken away', replaced === 1 && kept === 2 && !H.state.dialog);
await show(Dialog, dialogProps);
await act(async () => { dom.window.dispatchEvent(new dom.window.KeyboardEvent('keydown', { key: 'Escape' })); }); await flush();
check('Escape: kept, its entry taken away', kept === 3 && !H.state.dialog);
await show(Dialog, dialogProps);
const lenE = H.length;
await act(async () => root.unmount()); root = createRoot(document.getElementById('root'));
await act(async () => { root.render(React.createElement(Dialog, dialogProps)); }); await flush();
check('opened again on the same entry (React mounting it twice): no second entry', H.length === lenE && H.state.dialog === 'replace');
await click(q('[data-testid="replace-backdrop"]'));
check('tapping outside: kept, its entry taken away', kept === 4 && !H.state.dialog);
await act(async () => root.unmount()); root = null;          // the Plan screen takes the dialog away once it has answered
check('the dialog gone, it holds no Back-press listener', popListeners === 0, String(popListeners));

console.log('\nF: "← वापस" returns to where the teacher came from');
for (const [C, tid, name] of [[Account, 'account-back', 'Profile'], [Register, 'register-back', 'the register']]) {
  H.pushState({ usr: null, key: 'from-review', idx: 3 }, '');
  globalThis.__navs = [];
  await show(C);
  await click(q(`[data-testid="${tid}"]`));
  check(`${name}, reached from another screen of the app: back to it (one step back), not always to the Plan screen`, JSON.stringify(globalThis.__navs) === JSON.stringify([[-1]]), JSON.stringify(globalThis.__navs));
  H.replaceState({ usr: null, key: 'default', idx: 0 }, '');
  globalThis.__navs = [];
  await show(C);
  await click(q(`[data-testid="${tid}"]`));
  check(`${name}, the app opened straight there: to the Plan screen (never out of the app)`, JSON.stringify(globalThis.__navs) === JSON.stringify([['/']]), JSON.stringify(globalThis.__navs));
}

console.log('\nthe class-register template');
globalThis.__tpl = 0;
await show(Register);
const tpl = q('[data-testid="template-link"]');
check('the template button is a button, not a plain link (a link to /api/... is answered by the installed app’s own page, so nothing downloaded)', !!tpl && tpl.tagName === 'BUTTON' && !tpl.getAttribute('href'));
await click(tpl);
check('tapping it fetches and saves the template with the teacher’s sign-in (the same way as the reports)', globalThis.__tpl === 1, String(globalThis.__tpl));

await act(async () => root.unmount());
console.log(process.exitCode ? `\nFAILED (${n} checks)` : `\nAll ${n} checks passed.`);
