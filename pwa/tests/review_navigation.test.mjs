// Navigation around the Review (the click-through of 29 Oct): leaving the Review for Progress no longer loses the teacher's place; the Review loads today's
// plan itself (after the app is reopened it is not in memory) and carries on from the decisions already recorded; step 2 and step 3 have a way back; the
// step marker goes back to a step already reached; a new review asks first; Progress opened from the Review has "← समीक्षा पर लौटें"; the plan screen
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
const notFound = () => Object.assign(new Error('No plan found for this date'), { status: 404 });
globalThis.__navs = []; globalThis.__location = { pathname: '/progress', state: null };
globalThis.__auth = { teacher: { teacher_id: 'T1' }, selectedDomain: 'numeracy', names: {}, currentPlan: null, setCurrentPlan: (p) => { globalThis.__auth.currentPlan = p; } };
globalThis.__api = {
  getCachedPlan: async (...a) => cached(...a), recordDecisions: async (...a) => { decided.push(a); return {}; },
  getSavedAnalyses: async () => saved, getReviewCoverage: async () => null, getReviewChannels: async () => ({ has_plan: false, channels: {} }),
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
const stepNow = () => q('[data-testid="review-steps"]') && q('[data-testid="review-steps"]').dataset.step;
const chosen = (g) => (qa(`.tier-card.tier-${g} .decision-btn.selected`)[0] || { textContent: '' }).textContent;
const fresh = () => { sessionStorage.clear(); globalThis.__auth.currentPlan = null; globalThis.__auth.selectedDomain = 'numeracy'; globalThis.__navs.length = 0; decided.length = 0; saved = []; };
let n = 0; const check = (label, ok, extra = '') => { n += 1; console.log(`  ${ok ? 'OK  ' : 'FAIL'} ${label}${ok ? '' : '  ' + extra}`); if (!ok) process.exitCode = 1; };

console.log('A. the Review loads today\'s plan and carries on');
fresh(); cached = async () => PLAN({ beginner: 'advance', progressor: 'reteach' });
await show(Review);
check('the app reopened (no plan in memory): the Review loads today\'s plan itself and puts it in place', globalThis.__auth.currentPlan && globalThis.__auth.currentPlan.plan_date === TODAY && qa('.tier-card').length + qa('h2').length > 0);
check('...every group already has today\'s decision: it carries on at step 2 ("बच्चों का काम देखें"), not step 1', stepNow() === '2' && qa('h2').some((h) => /बच्चों का काम देखें/.test(h.textContent)));
fresh(); cached = async () => PLAN({ beginner: 'advance' });
await show(Review);
check('one group decided so far: step 1, with that decision already chosen and only the rest to choose', stepNow() === '1' && /आगे बढ़ें/.test(chosen('beginner')) && !chosen('progressor')
  && /बाकी: ▲ प्रगतिशील\)/.test(q('[data-testid="decisions-left"]').textContent));
fresh(); cached = async () => { throw notFound(); };
await show(Review);
check('no plan today: "आज इस विषय की योजना नहीं बनी है…" and no steps', !!q('[data-testid="review-no-plan"]') && /योजना नहीं बनी है/.test(q('[data-testid="review-no-plan"]').textContent) && !q('[data-testid="review-steps"]'));
await click(q('[data-testid="review-make-plan"]'));
check('..."योजना बनाएँ →" goes to the Plan screen', JSON.stringify(globalThis.__navs.at(-1)) === '["/"]');
fresh(); cached = async () => { throw Object.assign(new Error('boom'), { status: 500 }); };
await show(Review);
check('the plan could not be loaded: says so in plain words (not "no plan"), with the same way on', /खुल नहीं सकी/.test(q('[data-testid="review-no-plan"]').textContent));

console.log('\nA. leaving and coming back lands in the same place');
fresh(); cached = async () => PLAN({ beginner: 'advance', progressor: 'reteach' });
await show(Review);
await click(q('[data-testid="channel-observed"]'));
const groupBtn = qa('.tier-option').find((b) => /प्रगतिशील/.test(b.textContent)) || qa('.tier-option')[0];
if (groupBtn) await click(groupBtn);
const before = { channel: q('.domain-tab.active') && q('.domain-tab.active').dataset.testid, group: q('.tier-option.selected') && q('.tier-option.selected').textContent };
await show(Progress);              // the teacher goes to Progress
await show(Review);                // ...and comes back
check('back on the Review: still step 2, the same way of checking and the same group', stepNow() === '2' && q('.domain-tab.active') && q('.domain-tab.active').dataset.testid === before.channel
  && (!before.group || (q('.tier-option.selected') && q('.tier-option.selected').textContent === before.group)), JSON.stringify(before));
globalThis.__auth.selectedDomain = 'r1_literacy'; cached = async () => PLAN({}, 'r1_literacy');
await show(Review);
check('another subject starts its own review (step 1), not the maths one\'s place', stepNow() === '1');
globalThis.__auth.selectedDomain = 'numeracy';

console.log('\nA. a choice made on the screen is never overwritten by the server\'s copy');
fresh(); let release; cached = () => new Promise((r) => { release = () => r(PLAN({ beginner: 'advance', progressor: 'advance' })); });
globalThis.__auth.currentPlan = PLAN({});           // the plan is in memory, so step 1 shows at once
await show(Review);
await click(qa('.tier-card.tier-beginner .decision-btn').find((b) => /दोहराएँ/.test(b.textContent)));
await act(async () => { release(); }); await flush();
check('the teacher tapped "दोहराएँ" before the server answered "आगे बढ़ें": her choice stays, and she stays on step 1', /दोहराएँ/.test(chosen('beginner')) && stepNow() === '1');

console.log('\nB. ways back inside the Review');
fresh(); cached = async () => PLAN({ beginner: 'advance', progressor: 'reteach' });
await show(Review);
await click(q('[data-testid="back-to-decisions"]'));
check('step 2 "← निर्णय बदलें": back to step 1 with the decisions kept, ready to record again', stepNow() === '1' && /आगे बढ़ें/.test(chosen('beginner')) && /दोहराएँ/.test(chosen('progressor')) && !q('[data-testid="record-decisions"]').disabled);
check('the marker: "2/3" (reached) can be tapped, "3/3" (no analysis open) cannot', !!q('[data-testid="go-step-2"]') && !q('[data-testid="go-step-3"]'));
await click(q('[data-testid="go-step-2"]'));
check('...tapping "2/3" goes back to the children\'s work', stepNow() === '2');
saved = [ANALYSIS]; await show(Review);
const open = qa('[data-testid="saved-analyses"] button')[0];
await click(open);
check('an analysis opened: step 3', stepNow() === '3');
await click(q('[data-testid="back-to-work"]'));
check('step 3 "← बच्चों का काम: अगला समूह या तरीका": back to step 2, nothing reset (decisions kept)', stepNow() === '2' && decided.length === 0);
check('...and now "3/3" can be tapped to see the analysis again', !!q('[data-testid="go-step-3"]'));
await click(q('[data-testid="go-step-3"]'));
confirmAnswer = false; await click(q('[data-testid="new-review"]'));
check('"नई समीक्षा शुरू करें" asks first: "Cancel" changes nothing', stepNow() === '3');
confirmAnswer = true; await click(q('[data-testid="new-review"]'));
check('..."OK" starts over at step 1 with nothing chosen, and forgets the saved place', stepNow() === '1' && !chosen('beginner') && JSON.parse(sessionStorage.getItem('ankur_review_place') || '{}').step === 1);

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
await show(Yojana);
await click(q('[data-testid="to-review"]'));
check('with a plan: "पढ़ाने के बाद: समीक्षा करें →" goes to the Review', /पढ़ाने के बाद: समीक्षा करें/.test(text()) && JSON.stringify(globalThis.__navs.at(-1)) === '["/review"]');
fresh(); cached = async () => { throw notFound(); };
await show(Yojana);
await click(q('[data-testid="yojana-make-plan"]'));
check('no plan: "योजना बनाएँ →" goes to the Plan screen', JSON.stringify(globalThis.__navs.at(-1)) === '["/"]');

function text() { return document.getElementById('root').textContent; }
await act(async () => root.unmount());
console.log(`\n${process.exitCode ? 'SOME CHECKS FAILED' : 'OK: ' + n + ' checks: the Review keeps its place, has ways back, Progress leads back to it, and the plan screen leads on'}`);
