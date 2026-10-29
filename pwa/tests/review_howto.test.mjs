// How to do each way of checking (29 Oct): on the Review, "▸ कैसे करें?" under the way chosen, with the plan's own review prompts (what to look for in today's
// skill) for observation, the meanings of A / PA / NA, the photo steps and the reading-aloud steps; reading aloud shows the text to read (one not read in class
// today) and records THAT passage, never a made-up one; and the plan screen's "☑️ आज की समीक्षा" fold says, before class, how each group will be checked.
// The REAL Review and plan screens in a simulated browser with a fake server. The server's passage choice is tested in backend/tests/test_review_recorded.py.
//
//     cd pwa
//     npm install --save-dev jsdom@24     (once; see plan_screen.dom.test.mjs)
//     node tests/review_howto.test.mjs
//
// Without jsdom the test says so and stops without failing.
import fs from 'node:fs'; import path from 'node:path'; import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
let JSDOM;
try { ({ JSDOM } = await import('jsdom')); } catch (e) { console.log('SKIPPED: jsdom is not installed. To run this test: cd pwa; npm install --save-dev jsdom@24'); process.exit(0); }
const here = path.dirname(fileURLToPath(import.meta.url)); const src = path.join(here, '..', 'src'); const out = path.join(here, `.tmp-howto-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));      // the temporary build folder is always removed, even if a check fails
const API = ['recordDecisions', 'recordObserved', 'recordORF', 'analysePhotos', 'getSavedAnalyses', 'getReviewCoverage', 'getReviewChannels', 'getCachedPlan', 'openAuthedPage', 'worksheetPath', 'prepareOfflineCopy'];
const stubs = { '../App': 'export const useAuth = () => globalThis.__auth;', 'react-router-dom': 'export const useNavigate = () => () => {}; export const useLocation = () => globalThis.__location || ({ pathname: "/review", state: null });',
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

// ── the fake server: a plan whose three groups are checked three ways ──
const d0 = new Date(); const TODAY = `${d0.getFullYear()}-${String(d0.getMonth() + 1).padStart(2, '0')}-${String(d0.getDate()).padStart(2, '0')}`;
const LOOK = 'छँटाई के समय देखें कि बच्चा एक ही नियम पर टिका रहता है या बीच में बदल देता है।';
const PLAN = { plan_date: TODAY, domain_id: 'r1_literacy', selected_competency_id: 'L2.3.1', served_from: 'ai',
  groups: [{ label: 'beginner', count: 4, target_competency_id: 'N0.1.1', target_competency_name_hi: 'छाँटना' }, { label: 'progressor', count: 4, target_competency_id: 'L2.3.1', target_competency_name_hi: 'संयुक्त अक्षर' }, { label: 'proficient', count: 4, target_competency_id: 'L2.5.1', target_competency_name_hi: 'पढ़ने की रफ़्तार' }],
  plan: { worksheets: { beginner: { problems: [{ number: 1, problem_hi: 'लाल चीज़ें कितनी हैं?' }] } }, anchor: {}, rotation_schedule: { blocks: [{ type: 'teach', teach_group: 'progressor', duration_minutes: 30, script_hi: 'पढ़ना' }] },
    review_prompts: { observation_reminders_hi: [LOOK, 'आज कोई अवलोकन वाली दक्षता नहीं है।'] } },
  decisions: { beginner: 'advance', progressor: 'advance', proficient: 'advance' } };
const PASSAGE = { id: 'RP-006', title: 'पानी बचाओ', text: 'पानी बहुत कीमती है। हमें पानी बचाना चाहिए।', word_count: 72 };
const channels = (passage = PASSAGE) => ({ has_plan: true, channels: { observed: ['beginner'], photo: ['progressor'], orf: ['proficient'] },
  levels: [{ channel: 'observed', level: 'beginner', competency_id: 'N0.1.1', name_hi: 'छाँटना', rolls: [1, 2, 3, 4] },
           { channel: 'photo', level: 'progressor', competency_id: 'L2.3.1', name_hi: 'संयुक्त अक्षर', rolls: [5, 6, 7, 8] },
           { channel: 'orf', level: 'proficient', competency_id: 'L2.5.1', name_hi: 'पढ़ने की रफ़्तार', rolls: [9, 10, 11, 12], ...(passage ? { passage } : {}) }] });
let ch = channels(); const orfSaves = [];
const SAMPLE = (rolls) => ({ mode: 'all', size: rolls.length, group_size: rolls.length, rolls, done: [], left: rolls, margin_points: 0, absent: [] });
globalThis.__auth = { teacher: { teacher_id: 'T1' }, selectedDomain: 'r1_literacy', names: {}, currentPlan: null, setCurrentPlan: (p) => { globalThis.__auth.currentPlan = p; } };
globalThis.__api = {
  getCachedPlan: async () => JSON.parse(JSON.stringify(PLAN)), getReviewChannels: async () => JSON.parse(JSON.stringify(ch)), getSavedAnalyses: async () => [],
  getReviewCoverage: async (t, d, dom2, level) => { const rolls = { beginner: [1, 2, 3, 4], progressor: [5, 6, 7, 8], proficient: [9, 10, 11, 12] }[level];
    return { group_rolls: rolls, analysed_rolls: [], pending_rolls: rolls, labels: {}, sample: SAMPLE(rolls), recorded: {} }; },
  recordORF: async (t, entry) => { orfSaves.push(entry); return { status: 'recorded', roll_number: entry.roll_number, cwpm: entry.cwpm, classification: 'achieved' }; },
  recordDecisions: async () => ({}), recordObserved: async () => ({}), analysePhotos: async () => ({}),
  openAuthedPage: async () => {}, worksheetPath: () => '/w', prepareOfflineCopy: () => {},
};
let root;
const flush = async () => { for (let i = 0; i < 5; i += 1) await act(async () => { await new Promise((r) => setTimeout(r, 0)); }); };
const show = async (C) => { if (root) await act(async () => root.unmount()); root = createRoot(document.getElementById('root')); await act(async () => { root.render(React.createElement(C)); }); await flush(); };
const q = (sel) => document.querySelector(sel);
const click = async (el) => { await act(async () => { el.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true })); }); await flush(); };
const type = async (el, v) => { await act(async () => { Object.getOwnPropertyDescriptor(dom.window.HTMLInputElement.prototype, 'value').set.call(el, v); el.dispatchEvent(new dom.window.Event('input', { bubbles: true })); }); await flush(); };
const how = () => q('[data-testid^="how-"]');
let n = 0; const check = (label, ok, extra = '') => { n += 1; console.log(`  ${ok ? 'OK  ' : 'FAIL'} ${label}${ok ? '' : '  ' + extra}`); if (!ok) process.exitCode = 1; };

console.log('"▸ कैसे करें?" on the Review, for each way');
sessionStorage.clear();
await show(Review);
await click(q('[data-testid="channel-observed"]'));
check('observing: a closed "कैसे करें?" fold under the "who does what" line', how() && how().dataset.testid === 'how-observed' && how().tagName === 'DETAILS' && !how().open && /कैसे करें\?/.test(how().querySelector('summary').textContent));
check('...it starts with the general instruction (watch during independent practice, then A / PA / NA), NOT the plan\'s AI-written prompt (which on 29 Oct asked for a task the plan did not have)',
  /स्वतंत्र अभ्यास \(तुम करोगे\) के दौरान बच्चों को काम करते हुए देखें, फिर हर बच्चे के लिए A \/ PA \/ NA चुनें/.test(how().textContent) && !how().textContent.includes(LOOK) && !/आज की योजना से/.test(how().textContent));
check('step 2 names the group and skill being observed: "● शुरुआती · N0.1.1 · छाँटना"', /● शुरुआती(Beginner)? · N0\.1\.1 · छाँटना/.test(q('[data-testid="skill-2"]').textContent), q('[data-testid="skill-2"]') && q('[data-testid="skill-2"]').textContent);
check('...the Beginners also have a worksheet: "इस कौशल की वर्कशीट अभ्यास के लिए है; जाँच … देखकर होती है, वर्कशीट की फ़ोटो से नहीं"', /इस कौशल की वर्कशीट अभ्यास के लिए है; जाँच बच्चों को करते हुए देखकर होती है, वर्कशीट की फ़ोटो से नहीं/.test(q('[data-testid="worksheet-practice"]').textContent));
check('...and says what A, PA and NA mean', /A = करके दिखाया, बिना मदद · PA = मदद से, या आधा सही · NA = अभी नहीं/.test(how().textContent));
await click(q('[data-testid="channel-photo"]'));
check('photo: the skill line follows the photographed group ("▲ प्रगतिशील · L2.3.1 · संयुक्त अक्षर"), and no worksheet-is-practice line (photos ARE the check here)', /▲ प्रगतिशील(Progressor)? · L2\.3\.1 · संयुक्त अक्षर/.test(q('[data-testid="skill-2"]').textContent) && !q('[data-testid="worksheet-practice"]'));
check('photo: the steps (roll number at the top, flat in good light, the suggested sample, up to 6, no names), and no observation prompt',
  how().dataset.testid === 'how-photo' && /रोल नंबर लिखे/.test(how().textContent) && /समतल रखें, अच्छी रोशनी में/.test(how().textContent) && /नमूना/.test(how().textContent) && /बच्चे का नाम न हो/.test(how().textContent) && !how().textContent.includes(LOOK));
await click(q('[data-testid="channel-orf"]'));
check('reading aloud: the steps (one minute, count the words read correctly, what counts as an error)',
  how().dataset.testid === 'how-orf' && /एक मिनट का समय/.test(how().textContent) && /सही पढ़े गए शब्द गिनें/.test(how().textContent) && /गलत शब्द, छूटा शब्द, या जो शब्द आपको बताना पड़ा/.test(how().textContent));

console.log('\nthe text to read aloud');
check('the card names the text to read: "पढ़ने का पाठ: «पानी बचाओ» (72 शब्द)"', /पढ़ने का पाठ.*«पानी बचाओ» \(72 शब्द/.test(q('[data-testid="orf-passage"]').textContent));
check('..."पाठ दिखाएँ" opens the text itself, large, for the child to read', !q('[data-testid="orf-passage-text"]').open && q('[data-testid="orf-passage-text"]').textContent.includes(PASSAGE.text));
await click(q('[data-testid="orf-chip-9"]'));
await type(document.querySelector('input[aria-label^="सही शब्द प्रति मिनट"]'), '42');
await type(document.querySelector('input[aria-label^="गलतियाँ"]'), '3');
await click([...document.querySelectorAll('button.btn-primary')].find((b) => b.onclick !== undefined && /सहेज|दर्ज|Save/.test(b.textContent)) || [...document.querySelectorAll('.card button.btn-primary')].at(-1));
check('saving records THAT passage (RP-006), not a made-up RP-004', orfSaves.length === 1 && orfSaves[0].passage_id === 'RP-006' && orfSaves[0].roll_number === 9, JSON.stringify(orfSaves[0]));
ch = channels(null); sessionStorage.clear(); globalThis.__auth.currentPlan = null;
await show(Review);
await click(q('[data-testid="channel-orf"]'));
check('no text in the bank for the skill: says so, and how to choose one', /पाठ बैंक में नहीं मिला/.test(q('[data-testid="orf-no-passage"]').textContent));
await click(q('[data-testid="orf-chip-10"]'));
await type(document.querySelector('input[aria-label^="सही शब्द प्रति मिनट"]'), '30');
await click([...document.querySelectorAll('.card button.btn-primary')].at(-1));
check('...and the score is saved with no passage (null), never an invented one', orfSaves.length === 2 && orfSaves[1].passage_id === null, JSON.stringify(orfSaves[1]));
check('the code no longer has RP-004 anywhere on the Review', !fs.readFileSync(path.join(src, 'screens/ReviewScreen.jsx'), 'utf8').includes('RP-004'));

const savedSheets = PLAN.plan.worksheets; PLAN.plan.worksheets = {};
ch = channels(); sessionStorage.clear(); globalThis.__auth.currentPlan = null;
await show(Review); await click(q('[data-testid="channel-observed"]'));
check('an observed group with NO worksheet: no worksheet-is-practice line', !!how() && !q('[data-testid="worksheet-practice"]'));
PLAN.plan.worksheets = savedSheets;

console.log('\nthe plan screen: "☑️ आज की समीक्षा"');
ch = channels(); globalThis.__auth.currentPlan = JSON.parse(JSON.stringify(PLAN));
await show(Yojana);
const fold = () => q('[data-testid="review-today"]');
check('a closed fold "☑️ आज की समीक्षा: कैसे जाँचें"', fold() && !fold().open && /आज की समीक्षा: कैसे जाँचें/.test(fold().querySelector('summary').textContent));
check('...each group, its skill and its way: ● शुरुआती N0.1.1 ✓ देखकर दर्ज करें, ▲ प्रगतिशील L2.3.1 📸 वर्कशीट की फ़ोटो (the AI reads), ■ दक्ष L2.5.1 ⏱️ पढ़कर सुनाना',
  /● शुरुआती N0\.1\.1: ✓ देखकर दर्ज करें/.test(q('[data-testid="review-way-beginner"]').textContent) && /▲ प्रगतिशील L2\.3\.1: 📸 वर्कशीट की फ़ोटो/.test(q('[data-testid="review-way-progressor"]').textContent)
  && /AI हर बच्चे का काम पढ़ता है/.test(q('[data-testid="review-way-progressor"]').textContent) && /■ दक्ष L2\.5\.1: ⏱️ पढ़कर सुनाना/.test(q('[data-testid="review-way-proficient"]').textContent));
check('...the observed Beginners\' worksheet is marked as practice; the photographed Progressors\' is not', !!q('[data-testid="review-way-practice-beginner"]') && !q('[data-testid="review-way-practice-progressor"]'));
check('...the text the Proficients will read aloud, and for the group observed the general instruction (not the plan\'s AI prompt)', /«पानी बचाओ»/.test(q('[data-testid="review-way-passage-proficient"]').textContent)
  && /देखकर दर्ज करना(Observing)?: स्वतंत्र अभ्यास \(तुम करोगे\) के दौरान/.test(q('[data-testid="review-observe"]').textContent) && !fold().textContent.includes(LOOK));
ch = { has_plan: false, levels: [], channels: {} };
await show(Yojana);
check('the ways not known (no channels): says the Review will show them, and (the plan says something is observed) gives the general instruction', /समीक्षा स्क्रीन पर हर समूह का तरीका दिखेगा/.test(fold().textContent) && !q('[data-testid="review-way-beginner"]')
  && !!q('[data-testid="review-observe"]') && !fold().textContent.includes(LOOK));

await act(async () => root.unmount());
console.log(`\n${process.exitCode ? 'SOME CHECKS FAILED' : 'OK: ' + n + ' checks: each way of checking says how to do it, reading aloud shows and records its text, and the plan screen says how each group is checked'}`);
