// Navigation around the Review (the click-through of 29 Oct): leaving the Review for Progress no longer loses the teacher's place; the Review loads today's
// plan itself (after the app is reopened it is not in memory) and carries on from the decisions already recorded; step 2 and step 3 have a way back; the
// step marker only shows where the teacher is; "फ़ोटो विश्लेषण देखें →" appears only when there is a photo analysis; a new review asks first; Progress opened from the Review has "← समीक्षा पर लौटें"; the plan screen
// leads on to the Review, and with no plan, to making one. The REAL Review, Progress and plan screens in a simulated browser with a fake server.
//
//     cd pwa
//     npm install --save-dev jsdom@24     (once; see plan_screen.dom.test.mjs)
//     node tests/review_navigation.test.mjs
//
// Without jsdom the test says so and stops without failing.
import fs from 'node:fs'; import path from 'node:path'; import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
let JSDOM;
try { ({ JSDOM } = await import('jsdom')); } catch (e) { console.log('SKIPPED: jsdom is not installed. To run this test: cd pwa; npm install --save-dev jsdom@24'); process.exit(0); }
const here = path.dirname(fileURLToPath(import.meta.url)); const src = path.join(here, '..', 'src'); const out = path.join(here, `.tmp-nav-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));      // the temporary build folder is always removed, even if a check fails
const API = ['recordDecisions', 'recordObserved', 'recordORF', 'analysePhotos', 'getSavedAnalyses', 'getReviewCoverage', 'getReviewChannels', 'getCachedPlan',
  'getProgressDashboard', 'downloadClassReport', 'downloadOfficerReport', 'openAuthedPage', 'worksheetPath', 'prepareOfflineCopy'];
const stubs = { '../App': 'export const useAuth = () => globalThis.__auth;',
  'react-router-dom': 'export const useNavigate = () => (...a) => globalThis.__navs.push(a); export const useLocation = () => globalThis.__location;',
  '../services/api': API.map((n) => `export const ${n} = (...a) => globalThis.__api.${n}(...a);`).join('\n') };
await build({ entryPoints: { review: path.join(src, 'screens/ReviewScreen.jsx'), progress: path.join(src, 'screens/ProgressScreen.jsx'), yojana: path.join(src, 'screens/YojanaScreen.jsx') },
  bundle: true, format: 'esm', platform: 'node', outdir: out, outExtension: { '.js': '.mjs' }, loader: { '.js': 'jsx', '.jsx': 'jsx' }, external: ['react', 'react-dom', 'react-dom/client'], logLevel: 'error',
  plugins: [{ name: 'stubs', setup(b) { b.onResolve({ filter: /^(\.\.\/App|react-router-dom|\.\.\/services\/api)$/ }, (a) => ({ path: a.path, namespace: 'stub' })); b.onLoad({ filter: /.*/, namespace: 'stub' }, (a) => ({ contents: stubs[a.path], loader: 'js' })); } }] });
const dom = new JSDOM('<!doctype html><div id="root"></div>', { url: 'http://localhost/', pretendToBeVisual: true });
for (const k of ['window', 'document', 'navigator', 'HTMLElement', 'HTMLInputElement', 'Element', 'Node', 'MouseEvent', 'Event', 'localStorage', 'sessionStorage']) Object.defineProperty(globalThis, k, { value: dom.window[k], configurable: true, writable: true });
globalThis.IS_REACT_ACT_ENVIRONMENT = true; globalThis.requestAnimationFrame = (f) => setTimeout(f, 0);
dom.window.Element.prototype.scrollIntoView = () => {};
const React = (await import('react')).default; const { act } = await import('react'); const { createRoot } = await import('react-dom/client');
const Review = (await import(pathToFileURL(path.join(out, 'review.mjs')).href)).default;
const Progress = (await import(pathToFileURL(path.join(out, 'progress.mjs')).href)).default;
const Yojana = (await import(pathToFileURL(path.join(out, 'yojana.mjs')).href)).default;
const reviewSrc = fs.readFileSync(path.join(src, 'screens/ReviewScreen.jsx'), 'utf8');

// ── the fake server ──
const d0 = new Date(); const TODAY = `${d0.getFullYear()}-${String(d0.getMonth() + 1).padStart(2, '0')}-${String(d0.getDate()).padStart(2, '0')}`;
const PLAN = (decisions = {}, domain = 'numeracy') => ({ plan_date: TODAY, domain_id: domain, selected_competency_id: 'N2.3.2', served_from: 'ai',
  groups: [{ label: 'beginner', count: 7, target_competency_id: 'N2.3.1' }, { label: 'progressor', count: 14, target_competency_id: 'N2.3.2' }, { label: 'proficient', count: 0, target_competency_id: 'N3.3.1' }],
  plan: { session_minutes: 90, worksheets: {}, anchor: {}, rotation_schedule: { blocks: [{ type: 'teach', teach_group: 'progressor', duration_minutes: 30, script_hi: 'पहले जोड़' }] } },
  has_evidence: false, evidence_by_group: {}, decisions });
const ANALYSIS = { id: 1, worksheet_level: 'progressor', created_at: new Date().toISOString(),
  result: { children_analysed: 3, group_accuracy: 0.6, per_child: [], misconceptions_detected: [], not_assessed: [], unknown_rolls: [], outside_group_rolls: [], skipped_duplicates: [], duplicates_in_batch: [], unreadable_sheets: 0, copy_errors_excluded: 0 } };
let cached; let saved = []; const decided = [];
// today's ways: unknown (as an older server or a failed load), or known for the group cards: the Beginners observed, the Progressors photographed
const NO_CH = { has_plan: false, channels: {} };
const CH = { has_plan: true, channels: { observed: ['beginner'], photo: ['progressor'] },
  levels: [{ channel: 'observed', level: 'beginner', competency_id: 'N2.3.1', rolls: [1, 2] }, { channel: 'photo', level: 'progressor', competency_id: 'N2.3.2', rolls: [3, 4] }] };
let channels = NO_CH;
const notFound = () => Object.assign(new Error('No plan found for this date'), { status: 404 });
globalThis.__navs = []; globalThis.__location = { pathname: '/progress', state: null };
globalThis.__auth = { teacher: { teacher_id: 'T1' }, selectedDomain: 'numeracy', names: {}, currentPlan: null, setCurrentPlan: (p) => { globalThis.__auth.currentPlan = p; } };
globalThis.__api = {
  getCachedPlan: async (...a) => cached(...a), recordDecisions: async (...a) => { decided.push(a); return {}; },
  getSavedAnalyses: async () => saved, getReviewCoverage: async () => null, getReviewChannels: async () => channels,
  recordObserved: async () => ({}), recordORF: async () => ({}), analysePhotos: async () => ({}),
  getProgressDashboard: async () => null, downloadClassReport: async () => {}, downloadOfficerReport: async () => {},
  openAuthedPage: async () => {}, worksheetPath: () => '/w', prepareOfflineCopy: () => {},
};
let confirmAnswer = false; dom.window.confirm = () => confirmAnswer;

let root;
const flush = async () => { for (let i = 0; i < 4; i += 1) await act(async () => { await new Promise((r) => setTimeout(r, 0)); }); };
const show = async (C) => { if (root) await act(async () => root.unmount()); root = createRoot(document.getElementById('root')); await act(async () => { root.render(React.createElement(C)); }); await flush(); };
const q = (sel) => document.querySelector(sel); const qa = (sel) => [...document.querySelectorAll(sel)];
const click = async (el) => { await act(async () => { el.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true })); }); await flush(); };
const stepNow = () => q('[data-testid="review-title"]') && q('[data-testid="review-title"]').dataset.step;
const chosen = (g) => (qa(`.tier-card.tier-${g} .decision-btn.selected`)[0] || { textContent: '' }).textContent;
const fresh = () => { sessionStorage.clear(); globalThis.__auth.currentPlan = null; globalThis.__auth.selectedDomain = 'numeracy'; globalThis.__navs.length = 0; decided.length = 0; saved = []; };
let n = 0; const check = (label, ok, extra = '') => { n += 1; console.log(`  ${ok ? 'OK  ' : 'FAIL'} ${label}${ok ? '' : '  ' + extra}`); if (!ok) process.exitCode = 1; };

console.log('A. the Review loads today\'s plan and carries on');
fresh(); cached = async () => PLAN({ beginner: 'advance', progressor: 'reteach' });
await show(Review);
check('the app reopened (no plan in memory): the Review loads today\'s plan itself and puts it in place', globalThis.__auth.currentPlan && globalThis.__auth.currentPlan.plan_date === TODAY && qa('.group-card').length + qa('h2').length > 0);
check('...it opens at "1/2 आज का प्रदर्शन दर्ज करें" (two steps since 14 Nov: no first judgment, whatever an old record holds)', stepNow() === '2' && qa('h2').some((h) => /आज का प्रदर्शन दर्ज करें/.test(h.textContent))
  && !q('[data-testid="record-decisions"]'));
fresh(); cached = async () => ({ ...PLAN({}), final_decisions: { beginner: 'advance', progressor: 'reteach' } });
await show(Review);
check('every group already has today\'s FINAL decision: it opens at "2/2 अंतिम निर्णय", showing them', stepNow() === '3' && /आगे बढ़ें/.test(chosen('beginner')) && /दोहराएँ/.test(chosen('progressor')));
fresh(); cached = async () => ({ ...PLAN({}), final_decisions: { beginner: 'advance' } });
await show(Review);
check('only one group decided finally: it stays at 1/2 (the children\'s work first)', stepNow() === '2');
fresh(); cached = async () => { throw notFound(); };
await show(Review);
check('no plan today: "आज इस विषय की योजना नहीं बनी है…" and no steps', !!q('[data-testid="review-no-plan"]') && /योजना नहीं बनी है/.test(q('[data-testid="review-no-plan"]').textContent) && !q('[data-testid="review-steps"]'));
await click(q('[data-testid="review-make-plan"]'));
check('..."योजना बनाएँ →" goes to the Plan screen', JSON.stringify(globalThis.__navs.at(-1)) === '["/"]');
fresh(); cached = async () => { throw Object.assign(new Error('boom'), { status: 500 }); };
await show(Review);
check('the plan could not be loaded: says so in plain words (not "no plan"), with the same way on', /खुल नहीं सकी/.test(q('[data-testid="review-no-plan"]').textContent));

console.log('\nA. leaving and coming back lands in the same place');
channels = CH;
fresh(); cached = async () => PLAN({});
await show(Review);
check('(today\'s ways known: a card per group, the first group chosen at once)', !!q('[data-testid="group-card-beginner"]') && q('[data-testid="group-card-beginner"]').classList.contains('on'));
await click(q('[data-testid="group-card-progressor"]'));
check('the teacher picks the Progressors\' card: the photo way opens for them', q('[data-testid="group-card-progressor"]').classList.contains('on') && !!q('[data-testid="pilot-photo"]'));
await show(Progress);              // the teacher goes to Progress
await show(Review);                // ...and comes back
check('back on the Review: still 1/2, the same group and its way (the Progressors, by photo)', stepNow() === '2' && q('[data-testid="group-card-progressor"]').classList.contains('on')
  && !q('[data-testid="group-card-beginner"]').classList.contains('on') && !!q('[data-testid="pilot-photo"]'));
globalThis.__auth.selectedDomain = 'r1_literacy'; cached = async () => PLAN({}, 'r1_literacy');
await show(Review);
check('another subject starts its own review (1/2, its first group), not the maths one\'s place', stepNow() === '2' && q('[data-testid="group-card-beginner"]').classList.contains('on'));
globalThis.__auth.selectedDomain = 'numeracy';
channels = NO_CH;

console.log('\nA. a choice made on the screen is never overwritten by the server\'s copy');
fresh(); let release; cached = () => new Promise((r) => { release = () => r({ ...PLAN({}), final_decisions: { beginner: 'advance', progressor: 'advance' } }); });
globalThis.__auth.currentPlan = PLAN({});           // the plan is in memory, so the Review shows at once
await show(Review);
await click(q('[data-testid="to-final"]'));          // the decision step fetches today's record again: still on its way
await click(q('[data-testid="final-beginner-reteach"]'));
await act(async () => { release(); }); await flush();
check('the teacher tapped "दोहराएँ" before the server answered "आगे बढ़ें": her choice stays, and she stays on the decision', /दोहराएँ/.test(chosen('beginner')) && stepNow() === '3');

console.log('\nB. ways back inside the Review');
fresh(); cached = async () => PLAN({ beginner: 'advance', progressor: 'reteach' });
await show(Review);
check('1/2 has no way back to a first judgment (the step is gone): no "← 1/3 पहला अनुमान बदलें"', !q('[data-testid="back-to-decisions"]') && !/पहला अनुमान/.test(text()));
check('there is no separate step marker: the heading says the step (1/2 · आज का प्रदर्शन दर्ज करें), and nothing in it can be tapped', !q('[data-testid="review-steps"]') && !q('[data-testid="review-title"] button')
  && q('[data-testid="review-title"] .step-count').textContent === '1/2');
check('no photo analysis today: no "फ़ोटो विश्लेषण देखें →" (it would open an empty page)', !q('[data-testid="see-analysis"]'));
saved = [ANALYSIS, { ...ANALYSIS, id: 0, worksheet_level: 'beginner' }]; await show(Review);
check('with one today: the button is there', !!q('[data-testid="see-analysis"]') && /फ़ोटो विश्लेषण देखें/.test(q('[data-testid="see-analysis"]').textContent));
await click(q('[data-testid="see-analysis"]'));
check('...and opens today\'s newest analysis INSIDE 1/2 (it is a result, not a step), never the empty "results will appear" page', stepNow() === '2'
  && !!q('[data-testid="back-to-work"]') && !q('[data-testid="see-analysis"]') && !/फ़ोटो विश्लेषण के बाद परिणाम यहाँ दिखेंगे/.test(document.getElementById('root').textContent));
check('...its way back says where it goes: "← आज का प्रदर्शन: अगला समूह"', /आज का प्रदर्शन: अगला समूह/.test(q('[data-testid="back-to-work"]').textContent));
await click(q('[data-testid="back-to-work"]'));
check('"← आज का प्रदर्शन": back to the groups, nothing reset, nothing recorded', stepNow() === '2' && !!q('[data-testid="see-analysis"]') && decided.length === 0);
await click(q('[data-testid="see-analysis"]'));
check('..."फ़ोटो विश्लेषण देखें →" goes back to the analysis just left', stepNow() === '2' && !!q('[data-testid="back-to-work"]'));
await click(q('[data-testid="to-final"]'));
check('"आगे: अंतिम निर्णय: कल क्या पढ़ाएँ? →" (also under the analysis) leads to 2/2', stepNow() === '3');
check('the decision step has no "नई समीक्षा शुरू करें" (removed 29 Oct: every change has its own way, and it suggested the review was thrown away)',
  !q('[data-testid="new-review"]') && !/नई समीक्षा/.test(document.getElementById('root').textContent) && !/startNewReview|नई समीक्षा/.test(reviewSrc));

console.log('\nC. Progress, opened from the Review, leads back');
check('every "see it on Progress" pointer on the Review says it came from the Review', (reviewSrc.match(/onOpenProgress=\{toProgress\}/g) || []).length === 3 && !/navigate\('\/progress'\)/.test(reviewSrc)
  && /const toProgress = \(\) => navigate\('\/progress', \{ state: \{ from: 'review' \} \}\)/.test(reviewSrc));
globalThis.__location = { pathname: '/progress', state: { from: 'review' } };
await show(Progress);
check('Progress opened from the Review: "← समीक्षा पर लौटें" at the top', !!q('[data-testid="back-to-review"]') && /समीक्षा पर लौटें/.test(q('[data-testid="back-to-review"]').textContent));
await click(q('[data-testid="back-to-review"]'));
check('...which goes to the Review', JSON.stringify(globalThis.__navs.at(-1)) === '["/review"]');
globalThis.__location = { pathname: '/progress', state: null };
await show(Progress);
check('Progress opened from its tab: no such button', !q('[data-testid="back-to-review"]'));

console.log('\nE. the plan screen leads on');
fresh(); globalThis.__auth.currentPlan = PLAN({});
localStorage.clear();
await show(Yojana);
check('the review button waits until every group is marked taught, and says which are left (13 Nov)', q('[data-testid="to-review"]').disabled && /बाकी/.test(q('[data-testid="to-review-left"]').textContent));
for (const box of [...document.querySelectorAll('[data-testid^="taught-"] input')]) await click(box);
check('...every group ticked "इस समूह को पढ़ा दिया": it opens, and the tabs show ✓', !q('[data-testid="to-review"]').disabled && !q('[data-testid="to-review-left"]'));
await click(q('[data-testid="to-review"]'));
check('with a plan: "पढ़ाने के बाद: काम देखें और कल तय करें →" goes to the Review', /पढ़ाने के बाद: काम देखें और कल तय करें/.test(text()) && JSON.stringify(globalThis.__navs.at(-1)) === '["/review"]');
fresh(); cached = async () => { throw notFound(); };
await show(Yojana);
await click(q('[data-testid="yojana-make-plan"]'));
check('no plan: "योजना बनाएँ →" goes to the Plan screen', JSON.stringify(globalThis.__navs.at(-1)) === '["/"]');

function text() { return document.getElementById('root').textContent; }
await act(async () => root.unmount());
console.log(`\n${process.exitCode ? 'SOME CHECKS FAILED' : 'OK: ' + n + ' checks: the Review keeps its place, has ways back, Progress leads back to it, and the plan screen leads on'}`);
