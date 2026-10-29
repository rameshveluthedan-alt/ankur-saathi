// The mentor report (29 Oct, at /progress/mentor) and the reports card on the Class progress screen. The report is one printable page for an officer's
// visit: the talking points first (one strength, up to two things to work on, one question), then how the teacher works, then how the children moved,
// then the most common mistakes with an activity, and the rules behind the points at the foot. Hindi only, roll numbers but never a name.
// The reports moved from the screen's header (they pushed the title onto two lines) to a card at its foot; the CSV files stay there, as data.
// The REAL screens in a simulated browser with a fake server (the numbers themselves are checked in backend/tests/test_mentor_summary.py).
//
//     cd pwa
//     npm install --save-dev jsdom@24     (once; see plan_screen.dom.test.mjs)
//     node tests/mentor_report.test.mjs
//
// Without jsdom the test says so and stops without failing.
import fs from 'node:fs'; import path from 'node:path'; import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
let JSDOM;
try { ({ JSDOM } = await import('jsdom')); } catch (e) { console.log('SKIPPED: jsdom is not installed. To run this test: cd pwa; npm install --save-dev jsdom@24'); process.exit(0); }
const here = path.dirname(fileURLToPath(import.meta.url)); const src = path.join(here, '..', 'src'); const out = path.join(here, `.tmp-mentor-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));      // the temporary build folder is always removed, even if a check fails
const API = ['getMentorSummary', 'getProgressDashboard', 'downloadClassReport', 'downloadOfficerReport'];
const stubs = { '../App': 'export const useAuth = () => globalThis.__auth;',
  'react-router-dom': 'export const useNavigate = () => (...a) => globalThis.__navs.push(a); export const useLocation = () => ({ pathname: "/progress", state: null });',
  '../services/api': API.map((n) => `export const ${n} = (...a) => globalThis.__api.${n}(...a);`).join('\n') };
await build({ entryPoints: { mentor: path.join(src, 'screens/MentorReport.jsx'), progress: path.join(src, 'screens/ProgressScreen.jsx') }, bundle: true, format: 'esm', platform: 'node', outdir: out,
  outExtension: { '.js': '.mjs' }, loader: { '.js': 'jsx', '.jsx': 'jsx' }, external: ['react', 'react-dom', 'react-dom/client'], logLevel: 'error',
  plugins: [{ name: 'stubs', setup(b) { b.onResolve({ filter: /^(\.\.\/App|react-router-dom|\.\.\/services\/api)$/ }, (a) => ({ path: a.path, namespace: 'stub' })); b.onLoad({ filter: /.*/, namespace: 'stub' }, (a) => ({ contents: stubs[a.path], loader: 'js' })); } }] });
const dom = new JSDOM('<!doctype html><div id="root"></div>', { url: 'http://localhost/', pretendToBeVisual: true });
for (const k of ['window', 'document', 'navigator', 'HTMLElement', 'HTMLInputElement', 'Element', 'Node', 'MouseEvent', 'Event', 'localStorage', 'sessionStorage']) Object.defineProperty(globalThis, k, { value: dom.window[k], configurable: true, writable: true });
globalThis.IS_REACT_ACT_ENVIRONMENT = true; globalThis.requestAnimationFrame = (f) => setTimeout(f, 0);
const React = (await import('react')).default; const { act } = await import('react'); const { createRoot } = await import('react-dom/client');
const Mentor = (await import(pathToFileURL(path.join(out, 'mentor.mjs')).href)).default;
const Progress = (await import(pathToFileURL(path.join(out, 'progress.mjs')).href)).default;
const appSrc = fs.readFileSync(path.join(src, 'App.jsx'), 'utf8');

// ── what the server answers (backend/app/services/progress_service.py get_mentor_summary) ──
const RULES = { window_days: 28, stuck_days: 3, not_checked_days: 14, not_checked_share: 0.25, evidence_share: 0.5, match_share: 0.5, match_min: 3 };
const SUMMARY = () => ({
  period: { start: '2026-10-02', end: '2026-10-29', days: 28 },
  school: { school_code: 'S-23', block: 'सीहोर', district: 'सीहोर' },
  practice: { plan_days: 18, review_days: 15, groups_taught: 50, groups_checked: 31, judgments_compared: 12, judgments_matched: 5 },
  progress: { class_size: 30, skills_achieved: 22, not_checked: [4, 17, 22],
    groups: { numeracy: { start: { beginner: 12, progressor: 10, proficient: 8 }, start_date: '2026-10-02', end: { beginner: 9, progressor: 12, proficient: 9 }, end_date: '2026-10-29' } },
    stuck: [{ domain_id: 'numeracy', level: 'progressor', skill_id: 'N2.3.2', skill_name_hi: 'हासिल वाला जोड़', days: 4 }] },
  mistakes: [{ misconception_id: 'N2.3.2-M1', skill_id: 'N2.3.2', name_hi: 'हासिल भूलना', children: 7, activity: { id: 'INT-OP-005', title_hi: 'तीलियों के बंडल से हासिल' } },
             { misconception_id: 'N2.3.1-M1', skill_id: 'N2.3.1', name_hi: 'अंक उलटना', children: 3, activity: null }],
  rules: RULES,
  points: { strength: 'पिछले 4 हफ़्तों में 18 दिन योजना बनी और 15 दिन समीक्षा पूरी हुई।',
    work: [{ kind: 'stuck', hi: 'प्रगतिशील समूह में N2.3.2 4 दिन पढ़ाया गया।' }, { kind: 'judgment', hi: '12 में से 5 बार ही पहला अनुमान जाँच से मेल खाया।' }],
    question: 'किन बच्चों को अभी सबसे ज़्यादा मदद चाहिए, और आपको किस बात में मदद चाहिए?' },
});
let summary = SUMMARY(); let calls = [];
globalThis.__navs = [];
globalThis.__auth = { teacher: { teacher_id: 'T1', employee_code: 'MPT101', school_code: 'S-23', enrolled_grades: ['grade_2'] }, selectedDomain: 'numeracy', setSelectedDomain() {}, names: { 4: 'सीता देवी', 17: 'रामू' } };
globalThis.__api = { getMentorSummary: async (...a) => { calls.push(a); if (summary instanceof Error) throw summary; return JSON.parse(JSON.stringify(summary)); },
  getProgressDashboard: async () => ({ bpp_summary: [{ domain_id: 'numeracy', beginner_count: 9, progressor_count: 12, proficient_count: 9 }], children: [], reassessment_flags: {},
    today: { date: '2026-10-29', numeracy: { has_plan: false, by_level: {} }, r1_literacy: { has_plan: false, by_level: {} } } }),
  downloadClassReport: async () => {}, downloadOfficerReport: async () => {} };
let root;
const flush = async () => { for (let i = 0; i < 5; i += 1) await act(async () => { await new Promise((r) => setTimeout(r, 0)); }); };
const show = async (C) => { if (root) await act(async () => root.unmount()); root = createRoot(document.getElementById('root')); await act(async () => { root.render(React.createElement(C)); }); await flush(); };
const q = (sel) => document.querySelector(sel);
const txt = (sel) => (q(sel) ? q(sel).textContent.replace(/\s+/g, ' ').trim() : '');
const click = async (el) => { await act(async () => { el.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true })); }); await flush(); };
let n = 0; const check = (label, ok, extra = '') => { n += 1; console.log(`  ${ok ? 'OK  ' : 'FAIL'} ${label}${ok ? '' : '  ' + extra}`); if (!ok) process.exitCode = 1; };

console.log('the mentor report');
await show(Mentor);
const page = q('[data-testid="mentor-report"]');
const today = (() => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; })();
check('it asks the server for the last 4 weeks up to the phone\'s date', calls.length === 1 && calls[0][0] === 'T1' && calls[0][1] === today, JSON.stringify(calls));
check('the title: "मेंटर रिपोर्ट", the school, block and district, the teacher\'s code and the class', txt('[data-testid="mentor-title"]') === 'मेंटर रिपोर्ट · S-23 · सीहोर, सीहोर · शिक्षक MPT101 · कक्षा 2', txt('[data-testid="mentor-title"]'));
check('the period, in Hindi dates', txt('[data-testid="mentor-period"]') === 'अवधि: 2 अक्टू॰ 2026 – 29 अक्टू॰ 2026 (पिछले 4 हफ़्ते)', txt('[data-testid="mentor-period"]'));
const order = ['mentor-points', 'mentor-practice', 'mentor-progress', 'mentor-mistakes', 'mentor-rules'].map((id) => [...page.querySelectorAll('[data-testid]')].findIndex((e) => e.dataset.testid === id));
check('the order: the talking points first, then how the teacher works, then the children, then the mistakes, then the rules', order.every((i, k) => i >= 0 && (k === 0 || i > order[k - 1])), order.join(','));
check('the points: 👍 the strength, 🎯 each thing to work on, ❓ the question', txt('[data-testid="point-strength"]') === `👍 ${summary.points.strength}` && txt('[data-testid="point-work-stuck"]').startsWith('🎯 प्रगतिशील समूह में N2.3.2')
  && txt('[data-testid="point-work-judgment"]').startsWith('🎯 12 में से 5') && txt('[data-testid="point-question"]') === `❓ ${summary.points.question}`);
check('how the teacher works: plans, full reviews, decisions with evidence, the first judgment', /योजना बनी: 18 दिन · समीक्षा पूरी \(तीनों चरण\): 15 दिन/.test(txt('[data-testid="mentor-practice"]'))
  && /50 में से 31 बार/.test(txt('[data-testid="mentor-practice"]')) && txt('[data-testid="practice-match"]') === 'पहला अनुमान जाँच से मेल खाया: 12 में से 5 बार');
check('the groups at the start and the end of the period, per subject, with the group marks', txt('[data-testid="progress-groups-numeracy"]') === 'गणित, समूह: 2 अक्टू॰ 2026 को ● 12 · ▲ 10 · ■ 8 → 29 अक्टू॰ 2026 को ● 9 · ▲ 12 · ■ 9', txt('[data-testid="progress-groups-numeracy"]'));
check('a subject with no plans in the period has no line', !q('[data-testid="progress-groups-r1_literacy"]'));
check('the stuck groups and the children not checked (roll numbers)', txt('[data-testid="progress-stuck"]') === '3+ दिन एक ही कौशल: ▲ प्रगतिशील N2.3.2 (4 दिन)' && txt('[data-testid="progress-not-checked"]') === '2 हफ़्ते से नहीं जाँचे: 3 बच्चे (रोल 4, 17, 22)', txt('[data-testid="progress-not-checked"]'));
check('the mistakes, with the activity when the bank has one', txt('[data-testid="mistake-N2.3.2-M1"]') === 'N2.3.2 “हासिल भूलना”: 7 बच्चे → गतिविधि: “तीलियों के बंडल से हासिल”' && txt('[data-testid="mistake-N2.3.1-M1"]') === 'N2.3.1 “अंक उलटना”: 3 बच्चे');
check('the rules behind the points, printed with their values', /3\+ दिन/.test(txt('[data-testid="mentor-rules"]')) && /14 दिन/.test(txt('[data-testid="mentor-rules"]')) && /25%/.test(txt('[data-testid="mentor-rules"]'))
  && /50% से कम/.test(txt('[data-testid="mentor-rules"]')) && /कम से कम 3 तुलना/.test(txt('[data-testid="mentor-rules"]')));
check('never a child\'s name, though the phone knows them', !/सीता|रामू/.test(page.textContent));
check('printing shows this page alone (body.print-plan, the .plan-print page), a page of its own (no bottom bar)', document.body.classList.contains('print-plan') && page.classList.contains('plan-print')
  && /path="\/progress\/mentor"/.test(appSrc) && /path === '\/progress\/mentor'/.test(appSrc));
{
  dom.window.history.replaceState({ idx: 2 }, '');
  await click(q('[data-testid="mentor-back"]'));
  check('"← वापस": back to where the teacher came from', JSON.stringify(globalThis.__navs.pop()) === JSON.stringify([-1]));
  dom.window.history.replaceState({ idx: 0 }, '');
  await click(q('[data-testid="mentor-back"]'));
  check('...or, opened straight here, to Class progress', JSON.stringify(globalThis.__navs.pop()) === JSON.stringify(['/progress']));
}

console.log('\nwhen there is little to say');
summary = { ...SUMMARY(), practice: { plan_days: 0, review_days: 0, groups_taught: 0, groups_checked: 0, judgments_compared: 0, judgments_matched: 0 }, mistakes: [],
  progress: { ...SUMMARY().progress, groups: {}, stuck: [], not_checked: [] }, points: { strength: null, work: [], question: SUMMARY().points.question } };
await show(Mentor);
check('no plan in the period: says so instead of a strength; still the question', txt('[data-testid="point-nothing"]') === 'इस अवधि में कोई योजना नहीं बनी।' && !q('[data-testid="point-strength"]') && !!q('[data-testid="point-question"]'));
check('no comparison possible: says so, not "0 में से 0"', txt('[data-testid="practice-match"]') === 'पहला अनुमान जाँच से मेल खाया: अभी तुलना के लिए पर्याप्त जाँच नहीं');
check('no stuck group, no mistakes: those lines are not there; nobody unchecked: "कोई नहीं"', !q('[data-testid="progress-stuck"]') && !q('[data-testid="mentor-mistakes"]') && txt('[data-testid="progress-not-checked"]') === '2 हफ़्ते से नहीं जाँचे: कोई नहीं');
summary = new Error('offline');
await show(Mentor);
check('the server not reached: says so, nothing to print', !!q('[data-testid="mentor-failed"]') && !q('[data-testid="mentor-print"]'));
await act(async () => root.unmount()); root = null;
check('leaving the page takes the print rule away again', !document.body.classList.contains('print-plan'));

console.log('\nthe Class progress screen: the reports at its foot');
summary = SUMMARY();
await show(Progress);
const header = q('.screen-header');
check('the header has only the title now (the report buttons pushed it onto two lines)', !!header && header.children.length === 1 && header.querySelector('h1') && !header.querySelector('button'));
const card = q('[data-testid="reports"]');
const after = (a, b) => !!(a && b && (a.compareDocumentPosition(b) & dom.window.Node.DOCUMENT_POSITION_FOLLOWING));
check('a "📄 रिपोर्ट" card below the children\'s list', !!card && /📄 रिपोर्ट/.test(card.textContent) && after(q('.domain-tabs'), card));
check('the mentor report first, then the two CSV files as data', after(card.querySelector('[data-testid="open-mentor"]'), card.querySelector('[data-testid="class-report"]')) && after(card.querySelector('[data-testid="class-report"]'), card.querySelector('[data-testid="mlo-report"]'))
  && /डेटा, CSV फ़ाइल/.test(card.textContent));
await click(q('[data-testid="open-mentor"]'));
check('"💬 मेंटर रिपोर्ट" opens /progress/mentor', JSON.stringify(globalThis.__navs.pop()) === JSON.stringify(['/progress/mentor']));

await act(async () => root.unmount());
console.log(process.exitCode ? `\nFAILED (${n} checks)` : `\nAll ${n} checks passed.`);
