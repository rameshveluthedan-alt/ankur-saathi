// Recording during the lesson (29 Oct): observation and reading aloud happen in You Do, so the plan screen's teach block of a group checked that way has
// "✓/⏱️ अभी दर्ज करें", which opens the Review straight at step 2 with that way and group chosen, WITHOUT asking the first judgment first (the teacher's own
// observations need nothing to protect them from); a banner says so and leads back to the plan. Photo groups get no such button (photos are after class).
// The REAL plan and Review screens in a simulated browser with a fake server.
//
//     cd pwa
//     npm install --save-dev jsdom@24     (once; see plan_screen.dom.test.mjs)
//     node tests/record_now.test.mjs
//
// Without jsdom the test says so and stops without failing.
import fs from 'node:fs'; import path from 'node:path'; import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
let JSDOM;
try { ({ JSDOM } = await import('jsdom')); } catch (e) { console.log('SKIPPED: jsdom is not installed. To run this test: cd pwa; npm install --save-dev jsdom@24'); process.exit(0); }
const here = path.dirname(fileURLToPath(import.meta.url)); const src = path.join(here, '..', 'src'); const out = path.join(here, `.tmp-recnow-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));      // the temporary build folder is always removed, even if a check fails
const API = ['recordDecisions', 'recordObserved', 'recordORF', 'analysePhotos', 'getSavedAnalyses', 'getReviewCoverage', 'getReviewChannels', 'getCachedPlan', 'openAuthedPage', 'worksheetPath', 'prepareOfflineCopy'];
const stubs = { '../App': 'export const useAuth = () => globalThis.__auth;',
  'react-router-dom': 'export const useNavigate = () => (...a) => globalThis.__navs.push(a); export const useLocation = () => globalThis.__location;',
  '../services/api': API.map((n) => `export const ${n} = (...a) => globalThis.__api.${n}(...a);`).join('\n') };
await build({ entryPoints: { review: path.join(src, 'screens/ReviewScreen.jsx'), yojana: path.join(src, 'screens/YojanaScreen.jsx') }, bundle: true, format: 'esm', platform: 'node', outdir: out,
  outExtension: { '.js': '.mjs' }, loader: { '.js': 'jsx', '.jsx': 'jsx' }, external: ['react', 'react-dom', 'react-dom/client'], logLevel: 'error',
  plugins: [{ name: 'stubs', setup(b) { b.onResolve({ filter: /^(\.\.\/App|react-router-dom|\.\.\/services\/api)$/ }, (a) => ({ path: a.path, namespace: 'stub' })); b.onLoad({ filter: /.*/, namespace: 'stub' }, (a) => ({ contents: stubs[a.path], loader: 'js' })); } }] });
const dom = new JSDOM('<!doctype html><div id="root"></div>', { url: 'http://localhost/', pretendToBeVisual: true });
for (const k of ['window', 'document', 'navigator', 'HTMLElement', 'HTMLInputElement', 'Element', 'Node', 'MouseEvent', 'Event', 'localStorage', 'sessionStorage']) Object.defineProperty(globalThis, k, { value: dom.window[k], configurable: true, writable: true });
globalThis.IS_REACT_ACT_ENVIRONMENT = true; globalThis.requestAnimationFrame = (f) => setTimeout(f, 0);
dom.window.Element.prototype.scrollIntoView = () => {};
const React = (await import('react')).default; const { act } = await import('react'); const { createRoot } = await import('react-dom/client');
const Review = (await import(pathToFileURL(path.join(out, 'review.mjs')).href)).default;
const Yojana = (await import(pathToFileURL(path.join(out, 'yojana.mjs')).href)).default;

// ── the fake server: the Beginners observed, the Progressors photographed, the Proficients read aloud ──
const d0 = new Date(); const TODAY = `${d0.getFullYear()}-${String(d0.getMonth() + 1).padStart(2, '0')}-${String(d0.getDate()).padStart(2, '0')}`;
const teach = (g) => ({ type: 'teach', teach_group: g, duration_minutes: 20, script_hi: `${g} का काम`, talking_points: { you_do_hi: 'तुम करोगे' } });
const PLAN = (decisions = {}, finals = {}) => ({ plan_date: TODAY, domain_id: 'numeracy', selected_competency_id: 'N2.3.2', served_from: 'ai',
  groups: [{ label: 'beginner', count: 4, target_competency_id: 'N0.1.1', target_competency_name_hi: 'छाँटना' }, { label: 'progressor', count: 4, target_competency_id: 'N2.3.2', target_competency_name_hi: 'जोड़' },
           { label: 'proficient', count: 4, target_competency_id: 'L2.5.1', target_competency_name_hi: 'पढ़ने की रफ़्तार' }],
  plan: { worksheets: {}, anchor: {}, rotation_schedule: { blocks: [teach('beginner'), teach('progressor'), teach('proficient')] } },
  decisions: { ...decisions, ...finals }, first_judgments: decisions, final_decisions: finals, today_evidence: {} });
const CH = { has_plan: true, channels: { observed: ['beginner'], photo: ['progressor'], orf: ['proficient'] },
  levels: [{ channel: 'observed', level: 'beginner', competency_id: 'N0.1.1', name_hi: 'छाँटना', rolls: [1, 2, 3, 4] },
           { channel: 'photo', level: 'progressor', competency_id: 'N2.3.2', name_hi: 'जोड़', rolls: [5, 6, 7, 8] },
           { channel: 'orf', level: 'proficient', competency_id: 'L2.5.1', name_hi: 'पढ़ने की रफ़्तार', rolls: [9, 10, 11, 12] }] };
let reply = PLAN(); let ch = CH;
const SAMPLE = (rolls) => ({ mode: 'all', size: rolls.length, group_size: rolls.length, rolls, done: [], left: rolls, margin_points: 0, absent: [] });
globalThis.__navs = []; globalThis.__location = { pathname: '/review', state: null };
globalThis.__auth = { teacher: { teacher_id: 'T1' }, selectedDomain: 'numeracy', names: {}, currentPlan: null, setCurrentPlan: (p) => { globalThis.__auth.currentPlan = p; } };
globalThis.__api = {
  getCachedPlan: async () => JSON.parse(JSON.stringify(reply)), getReviewChannels: async () => JSON.parse(JSON.stringify(ch)), getSavedAnalyses: async () => [],
  getReviewCoverage: async (t, d, dm, level) => { const rolls = { beginner: [1, 2, 3, 4], progressor: [5, 6, 7, 8], proficient: [9, 10, 11, 12] }[level];
    return { group_rolls: rolls, analysed_rolls: [], pending_rolls: rolls, labels: {}, sample: SAMPLE(rolls), recorded: {} }; },
  recordDecisions: async () => ({}), recordObserved: async () => ({}), recordORF: async () => ({}), analysePhotos: async () => ({}),
  openAuthedPage: async () => {}, worksheetPath: () => '/w', prepareOfflineCopy: () => {},
};
let root;
const flush = async () => { for (let i = 0; i < 5; i += 1) await act(async () => { await new Promise((r) => setTimeout(r, 0)); }); };
const show = async (C) => { if (root) await act(async () => root.unmount()); root = createRoot(document.getElementById('root')); await act(async () => { root.render(React.createElement(C)); }); await flush(); };
const q = (sel) => document.querySelector(sel);
const click = async (el) => { await act(async () => { el.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true })); }); await flush(); };
const stepNow = () => q('[data-testid="review-title"]') && q('[data-testid="review-title"]').dataset.step;
let n = 0; const check = (label, ok, extra = '') => { n += 1; console.log(`  ${ok ? 'OK  ' : 'FAIL'} ${label}${ok ? '' : '  ' + extra}`); if (!ok) process.exitCode = 1; };

console.log('the plan screen: "अभी दर्ज करें" where the check happens in class');
globalThis.__auth.currentPlan = PLAN();
await show(Yojana);
const openBlock = async (g) => { const b = [...document.querySelectorAll('.timeline-block')].find((x) => x.textContent.includes(`${g} का काम`)); if (b.getAttribute('aria-expanded') !== 'true') await click(b); };
check('the button is in "You Do" (तुम करोगे): with the blocks closed there is none', !q('[data-testid^="record-now-"]'));
await openBlock('beginner');          // one block is open at a time
check('opened, it sits inside the Beginners\' "तुम करोगे" talking point, after its instruction', (() => { const b = q('[data-testid="record-now-beginner"]'); const tp = b && b.closest('.talking-point');
  return !!tp && /तुम करोगे/.test(tp.querySelector('.talking-point-label').textContent) && /तुम करोगे/.test(tp.textContent); })());
check('the observed Beginners\' block: "✓ अभी दर्ज करें · देखकर दर्ज करें"', /✓ अभी दर्ज करें.*देखकर दर्ज करें/.test(q('[data-testid="record-now-beginner"]').textContent) && q('[data-testid="record-now-beginner"]').dataset.channel === 'observed');
await openBlock('proficient');
check('the Proficients, read aloud: "⏱️ अभी दर्ज करें · पढ़कर सुनाना"', /⏱️ अभी दर्ज करें.*पढ़कर सुनाना/.test(q('[data-testid="record-now-proficient"]').textContent));
await openBlock('progressor');
check('the photographed Progressors: no button (photos are taken after class)', !q('[data-testid="record-now-progressor"]'));
await openBlock('beginner');
const block = q('[data-testid="record-now-beginner"]').closest('.timeline-block');
const expanded = block.getAttribute('aria-expanded');
await click(q('[data-testid="record-now-beginner"]'));
check('tapping it opens the Review with the way and the group (and does not open or close the teach block)', JSON.stringify(globalThis.__navs.at(-1)) === JSON.stringify(['/review', { state: { from: 'plan', channel: 'observed', level: 'beginner' } }])
  && block.getAttribute('aria-expanded') === expanded, JSON.stringify(globalThis.__navs.at(-1)));
ch = { has_plan: false, levels: [], channels: {} };
await show(Yojana); await openBlock('beginner');
check('the ways not known: no "अभी दर्ज करें" anywhere (never a guess)', !q('[data-testid^="record-now-"]'));
ch = CH;

console.log('\nthe Review, opened from the plan during the lesson');
sessionStorage.clear(); globalThis.__auth.currentPlan = null; reply = PLAN();          // nothing judged yet today
globalThis.__location = { pathname: '/review', state: { from: 'plan', channel: 'observed', level: 'beginner' } };
await show(Review);
check('straight to step 2, no first judgment asked (none recorded today)', stepNow() === '2' && !q('[data-testid="record-decisions"]'));
check('...with that way and group chosen: "देखकर दर्ज करें", the Beginners\' skill and their list', q('[data-testid="channel-observed"]').classList.contains('active') && /● शुरुआती(Beginner)? · N0\.1\.1/.test(q('[data-testid="skill-2"]').textContent) && !!q('[data-testid="obs-1-achieved"]'));
check('...and a banner: "पाठ के दौरान दर्ज कर रहे हैं; पहला अनुमान और अंतिम निर्णय पढ़ाने के बाद।"', /पाठ के दौरान दर्ज कर रहे हैं; पहला अनुमान और अंतिम निर्णय पढ़ाने के बाद/.test(q('[data-testid="from-plan"]').textContent));
await click(q('[data-testid="back-to-plan"]'));
check('..."← योजना" goes back to the plan', JSON.stringify(globalThis.__navs.at(-1)) === '["/yojana"]');
globalThis.__location = { pathname: '/review', state: { from: 'plan', channel: 'orf', level: 'proficient' } };
sessionStorage.clear(); globalThis.__auth.currentPlan = null;
await show(Review);
check('from the Proficients\' block: step 2 with "पढ़कर सुनाना" and their skill', stepNow() === '2' && q('[data-testid="channel-orf"]').classList.contains('active') && /■ दक्ष(Proficient)? · L2\.5\.1/.test(q('[data-testid="skill-2"]').textContent));
reply = PLAN({ beginner: 'advance', progressor: 'advance', proficient: 'advance' }, { beginner: 'advance', progressor: 'advance', proficient: 'advance' });
sessionStorage.clear(); globalThis.__auth.currentPlan = null;
globalThis.__location = { pathname: '/review', state: { from: 'plan', channel: 'observed', level: 'beginner' } };
await show(Review);
check('even with today\'s final decisions recorded (which would open step 3), it stays where the teacher asked: step 2', stepNow() === '2' && q('[data-testid="channel-observed"]').classList.contains('active'));

ch = { ...CH, channels: { observed: ['beginner', 'proficient'], photo: ['progressor'] },
  levels: [CH.levels[0], CH.levels[1], { channel: 'observed', level: 'proficient', competency_id: 'N3.3.1', name_hi: 'तीन अंकों का जोड़', rolls: [9, 10, 11, 12] }] };
reply = PLAN(); reply.groups[2] = { label: 'proficient', count: 4, target_competency_id: 'N3.3.1', target_competency_name_hi: 'तीन अंकों का जोड़' };
sessionStorage.clear(); globalThis.__auth.currentPlan = null;
globalThis.__location = { pathname: '/review', state: { from: 'plan', channel: 'observed', level: 'proficient' } };
await show(Review);
check('two groups observed today: from the Proficients\' block it is the Proficients that are chosen, not the first observed group', /■ दक्ष(Proficient)? · N3\.3\.1/.test(q('[data-testid="skill-2"]').textContent) && !!q('[data-testid="obs-9-achieved"]') && !q('[data-testid="obs-1-achieved"]'),
  q('[data-testid="skill-2"]') && q('[data-testid="skill-2"]').textContent);
ch = CH;

console.log('\nopened normally (from the tab), nothing changes');
reply = PLAN(); sessionStorage.clear(); globalThis.__auth.currentPlan = null;
globalThis.__location = { pathname: '/review', state: null };
await show(Review);
check('step 1 asks the first judgment as before, and no banner', stepNow() === '1' && !!q('[data-testid="record-decisions"]') && !q('[data-testid="from-plan"]'));

await act(async () => root.unmount());
console.log(`\n${process.exitCode ? 'SOME CHECKS FAILED' : 'OK: ' + n + ' checks: observation and reading aloud can be recorded during the lesson, straight from the plan, without the first judgment first'}`);
