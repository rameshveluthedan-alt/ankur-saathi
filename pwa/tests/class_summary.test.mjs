// The class summary (29 Oct, at /progress/class): the teacher's own page for planning next week. Per subject: the class now, what each group was taught
// and how it went, each group's next step; then the children to look at, the most common mistakes with an activity, and the rules at the foot.
// The server sends roll numbers only; the page adds the NAMES this phone holds, and its foot says the page carries names. Hindi only.
// The REAL screens in a simulated browser with a fake server (the numbers themselves are checked in backend/tests/test_class_summary.py).
//
//     cd pwa
//     npm install --save-dev jsdom@24     (once; see plan_screen.dom.test.mjs)
//     node tests/class_summary.test.mjs
//
// Without jsdom the test says so and stops without failing.
import fs from 'node:fs'; import path from 'node:path'; import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
let JSDOM;
try { ({ JSDOM } = await import('jsdom')); } catch (e) { console.log('SKIPPED: jsdom is not installed. To run this test: cd pwa; npm install --save-dev jsdom@24'); process.exit(0); }
const here = path.dirname(fileURLToPath(import.meta.url)); const src = path.join(here, '..', 'src'); const out = path.join(here, `.tmp-classsum-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));      // the temporary build folder is always removed, even if a check fails
const API = ['getClassSummary', 'getMentorSummary', 'getProgressDashboard', 'downloadClassReport', 'downloadOfficerReport'];
const stubs = { '../App': 'export const useAuth = () => globalThis.__auth;',
  'react-router-dom': 'export const useNavigate = () => (...a) => globalThis.__navs.push(a); export const useLocation = () => ({ pathname: "/progress", state: null });',
  '../services/api': API.map((n) => `export const ${n} = (...a) => globalThis.__api.${n}(...a);`).join('\n') };
await build({ entryPoints: { summary: path.join(src, 'screens/ClassSummary.jsx'), progress: path.join(src, 'screens/ProgressScreen.jsx') }, bundle: true, format: 'esm', platform: 'node', outdir: out,
  outExtension: { '.js': '.mjs' }, loader: { '.js': 'jsx', '.jsx': 'jsx' }, external: ['react', 'react-dom', 'react-dom/client'], logLevel: 'error',
  plugins: [{ name: 'stubs', setup(b) { b.onResolve({ filter: /^(\.\.\/App|react-router-dom|\.\.\/services\/api)$/ }, (a) => ({ path: a.path, namespace: 'stub' })); b.onLoad({ filter: /.*/, namespace: 'stub' }, (a) => ({ contents: stubs[a.path], loader: 'js' })); } }] });
const dom = new JSDOM('<!doctype html><div id="root"></div>', { url: 'http://localhost/', pretendToBeVisual: true });
for (const k of ['window', 'document', 'navigator', 'HTMLElement', 'HTMLInputElement', 'Element', 'Node', 'MouseEvent', 'Event', 'localStorage', 'sessionStorage']) Object.defineProperty(globalThis, k, { value: dom.window[k], configurable: true, writable: true });
globalThis.IS_REACT_ACT_ENVIRONMENT = true; globalThis.requestAnimationFrame = (f) => setTimeout(f, 0);
const React = (await import('react')).default; const { act } = await import('react'); const { createRoot } = await import('react-dom/client');
const Summary = (await import(pathToFileURL(path.join(out, 'summary.mjs')).href)).default;
const Progress = (await import(pathToFileURL(path.join(out, 'progress.mjs')).href)).default;
const appSrc = fs.readFileSync(path.join(src, 'App.jsx'), 'utf8');

// ── what the server answers (backend/app/services/progress_service.py get_class_summary): roll numbers only ──
const RULES = { window_days: 28, stuck_days: 3, not_checked_days: 14, na_days: 2 };
const SUMMARY = () => ({
  period: { start: '2026-10-02', end: '2026-10-29', days: 28 },
  subjects: {
    numeracy: { groups_now: { beginner: 9, progressor: 12, proficient: 9 }, skills_achieved: 22,
      taught: [{ level: 'beginner', skill_id: 'N2.3.1', skill_name_hi: 'बिना हासिल जोड़', days: 3, finals: { advance: 1, reteach: 1, not_sure: 0 } },
               { level: 'progressor', skill_id: 'N2.3.2', skill_name_hi: 'हासिल वाला जोड़', days: 4, finals: { advance: 1, reteach: 2, not_sure: 1 } }],
      stuck: [{ level: 'progressor', skill_id: 'N2.3.2', skill_name_hi: 'हासिल वाला जोड़', days: 4, rolls: [5, 6, 8] }],
      next: { beginner: { skill_id: 'N2.3.2', skill_name_hi: 'हासिल वाला जोड़', reason: 'advance' }, progressor: { skill_id: 'N2.3.2', skill_name_hi: 'हासिल वाला जोड़', reason: 'reteach' },
              proficient: { skill_id: null, skill_name_hi: null, reason: 'no_decision' } } },
    r1_literacy: { groups_now: { beginner: 10, progressor: 10, proficient: 10 }, skills_achieved: 1, taught: [], stuck: [], next: {} },
  },
  not_checked: [3, 12],
  not_achieved_again: [{ roll: 5, days: 2, skills: ['N2.3.2'] }],
  mistakes: [{ misconception_id: 'N2.3.2-M1', skill_id: 'N2.3.2', name_hi: 'हासिल भूलना', children: 2, rolls: [5, 6], activity: { id: 'INT-OP-005', title_hi: 'तीलियों के बंडल से हासिल' } }],
  rules: RULES,
});
let summary = SUMMARY(); let calls = [];
globalThis.__navs = [];
globalThis.__auth = { teacher: { teacher_id: 'T1', employee_code: 'MPT101', school_code: 'S-23', enrolled_grades: ['grade_2'] }, selectedDomain: 'numeracy', setSelectedDomain() {},
  names: { 5: 'सीता', 6: 'रामू', 3: 'गीता' } };          // the phone holds some names (roll 8 and 12: none)
globalThis.__api = { getClassSummary: async (...a) => { calls.push(a); if (summary instanceof Error) throw summary; return JSON.parse(JSON.stringify(summary)); },
  getMentorSummary: async () => ({}), getProgressDashboard: async () => ({ bpp_summary: [], children: [], reassessment_flags: {}, today: { date: '2026-10-29', numeracy: { has_plan: false, by_level: {} }, r1_literacy: { has_plan: false, by_level: {} } } }),
  downloadClassReport: async () => {}, downloadOfficerReport: async () => {} };
let root;
const flush = async () => { for (let i = 0; i < 5; i += 1) await act(async () => { await new Promise((r) => setTimeout(r, 0)); }); };
const show = async (C) => { if (root) await act(async () => root.unmount()); root = createRoot(document.getElementById('root')); await act(async () => { root.render(React.createElement(C)); }); await flush(); };
const q = (sel) => document.querySelector(sel);
const txt = (sel) => (q(sel) ? q(sel).textContent.replace(/\s+/g, ' ').trim() : '');
const click = async (el) => { await act(async () => { el.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true })); }); await flush(); };
let n = 0; const check = (label, ok, extra = '') => { n += 1; console.log(`  ${ok ? 'OK  ' : 'FAIL'} ${label}${ok ? '' : '  ' + extra}`); if (!ok) process.exitCode = 1; };

console.log('the class summary');
await show(Summary);
const page = q('[data-testid="class-summary"]');
const today = (() => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; })();
check('it asks the server for the last 4 weeks up to the phone\'s date', calls.length === 1 && calls[0][0] === 'T1' && calls[0][1] === today, JSON.stringify(calls));
check('the title and the period', txt('[data-testid="class-title"]') === 'कक्षा सारांश · MPT101 · कक्षा 2' && txt('[data-testid="class-period"]') === 'अवधि: 2 अक्टू॰ 2026 – 29 अक्टू॰ 2026 (पिछले 4 हफ़्ते)', txt('[data-testid="class-title"]'));
check('per subject, the class now: the groups and the skills achieved', txt('[data-testid="now-numeracy"]') === 'कक्षा अभी: ● शुरुआती 9 · ▲ प्रगतिशील 12 · ■ दक्ष 9 · कौशल हासिल किए: 22', txt('[data-testid="now-numeracy"]'));
check('what each group was taught: the skill, the days, the final decisions', txt('[data-testid="taught-numeracy-progressor-N2.3.2"]') === '▲ प्रगतिशील: N2.3.2 हासिल वाला जोड़ · 4 दिन · ⬆ 1 · 🔄 2 · ❓ 1', txt('[data-testid="taught-numeracy-progressor-N2.3.2"]'));
check('a subject with no plans: says so', txt('[data-testid="taught-none-r1_literacy"]') === 'इस अवधि में कोई योजना नहीं बनी।' && !q('[data-testid="next-r1_literacy"]'));
check('the next step per group, with why; a group with no decision says to choose when planning', txt('[data-testid="next-numeracy-beginner"]') === '● शुरुआती: N2.3.2 हासिल वाला जोड़ (⬆ आगे बढ़ें);'
  && txt('[data-testid="next-numeracy-progressor"]') === '▲ प्रगतिशील: N2.3.2 हासिल वाला जोड़ (🔄 दोहराएँ);' && /पिछली समीक्षा में निर्णय नहीं; योजना बनाते समय चुनें/.test(txt('[data-testid="next-numeracy-proficient"]')), txt('[data-testid="next-numeracy-beginner"]'));
check('the children to look at, BY NAME where the phone has it (roll 8: the roll number alone)', txt('[data-testid="stuck-progressor-N2.3.2"]') === '▲ प्रगतिशील, N2.3.2 (4 दिन पढ़ाया, अभी हासिल नहीं): 5 सीता, 6 रामू, रोल 8', txt('[data-testid="stuck-progressor-N2.3.2"]'));
check('not checked for 2 weeks, and "not achieved" again and again (with the skill)', txt('[data-testid="look-not-checked"]') === '2 हफ़्ते से नहीं जाँचे: 3 गीता, रोल 12' && txt('[data-testid="look-na"]') === '2+ दिन “अभी नहीं” (NA): 5 सीता (N2.3.2)', txt('[data-testid="look-na"]'));
check('the mistakes with the children who made them and an activity', txt('[data-testid="class-mistake-N2.3.2-M1"]') === 'N2.3.2 “हासिल भूलना”: 5 सीता, 6 रामू → गतिविधि: “तीलियों के बंडल से हासिल”', txt('[data-testid="class-mistake-N2.3.2-M1"]'));
check('the rules at the foot, and that the page carries names (keep it safe)', /3\+ दिन/.test(txt('[data-testid="class-rules"]')) && /14 दिन/.test(txt('[data-testid="class-rules"]')) && /NA 2 या ज़्यादा दिन/.test(txt('[data-testid="class-rules"]'))
  && /बच्चों के नाम हैं/.test(txt('[data-testid="class-footer"]')));
check('printing shows this page alone, a page of its own (no bottom bar)', document.body.classList.contains('print-plan') && page.classList.contains('plan-print') && /path="\/progress\/class"/.test(appSrc) && /path === '\/progress\/class'/.test(appSrc));
dom.window.history.replaceState({ idx: 0 }, '');
await click(q('[data-testid="class-back"]'));
check('"← वापस", opened straight here: to Class progress', JSON.stringify(globalThis.__navs.pop()) === JSON.stringify(['/progress']));

check('the footnote: what the letters, marks and codes mean', txt('[data-testid="class-key"]') === 'A = बिना मदद के करके दिखाया · PA = मदद से या आंशिक रूप से सही · NA = अभी नहीं · N2.3.2 जैसे कोड कौशल-सीढ़ी में दिए गए कौशलों की पहचान करते हैं।', txt('[data-testid="class-key"]'));

console.log('\nwhen there is little to say');
summary = { ...SUMMARY(), not_checked: [], not_achieved_again: [], mistakes: [], subjects: { numeracy: { ...SUMMARY().subjects.numeracy, stuck: [] } } };
await show(Summary);
check('nobody to look at: "कोई नहीं", no stuck line, no mistakes section', txt('[data-testid="look-not-checked"]') === '2 हफ़्ते से नहीं जाँचे: कोई नहीं' && txt('[data-testid="look-na"]') === '2+ दिन “अभी नहीं” (NA): कोई नहीं'
  && !q('[data-testid^="stuck-"]') && !q('[data-testid="class-mistakes"]'));
summary = new Error('offline');
await show(Summary);
check('the server not reached: says so, nothing to print', !!q('[data-testid="class-failed"]') && !q('[data-testid="class-print"]'));
await act(async () => root.unmount()); root = null;
check('leaving the page takes the print rule away again', !document.body.classList.contains('print-plan'));

console.log('\nthe reports card on Class progress');
summary = SUMMARY();
await show(Progress);
const card = q('[data-testid="reports"]');
const after = (a, b) => !!(a && b && (a.compareDocumentPosition(b) & dom.window.Node.DOCUMENT_POSITION_FOLLOWING));
check('the teacher\'s own summary first, then the mentor report, then the CSV files', after(card.querySelector('[data-testid="open-class"]'), card.querySelector('[data-testid="open-mentor"]')) && after(card.querySelector('[data-testid="open-mentor"]'), card.querySelector('[data-testid="class-report"]')));
await click(q('[data-testid="open-class"]'));
check('"📋 कक्षा सारांश" opens /progress/class', JSON.stringify(globalThis.__navs.pop()) === JSON.stringify(['/progress/class']));

await act(async () => root.unmount());
console.log(process.exitCode ? `\nFAILED (${n} checks)` : `\nAll ${n} checks passed.`);
