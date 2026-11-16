// The Review screen (two steps since 14 Nov, Vaishnavi: "capture evidence -> one final decision"; the first-judgment step is gone): it opens at
// "1/2 · आज का प्रदर्शन दर्ज करें" with one card per group (its way, its count), the other ways only on request, then "2/2 · अंतिम निर्णय: अगली कक्षा में क्या पढ़ाएँ?".
// The REAL Review screen in a simulated browser with a fake server.
//
//     cd pwa
//     npm install --save-dev jsdom@24     (once; see plan_screen.dom.test.mjs)
//     node tests/review_steps.test.mjs
//
// Without jsdom the test says so and stops without failing.
import fs from 'node:fs'; import path from 'node:path'; import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
let JSDOM;
try { ({ JSDOM } = await import('jsdom')); } catch (e) { console.log('SKIPPED: jsdom is not installed. To run this test: cd pwa; npm install --save-dev jsdom@24'); process.exit(0); }
const here = path.dirname(fileURLToPath(import.meta.url)); const src = path.join(here, '..', 'src'); const out = path.join(here, `.tmp-steps-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));      // the temporary build folder is always removed, even if a check fails
const API = ['recordDecisions', 'recordObserved', 'recordORF', 'analysePhotos', 'replaceResults', 'getSavedAnalyses', 'getReviewCoverage', 'getReviewChannels', 'getCachedPlan'];
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
const reviewSrc = fs.readFileSync(path.join(src, 'screens/ReviewScreen.jsx'), 'utf8');

const decided = [];
const d0 = new Date(); const TODAY = `${d0.getFullYear()}-${String(d0.getMonth() + 1).padStart(2, '0')}-${String(d0.getDate()).padStart(2, '0')}`;      // the phone's own date, as the screen uses
sessionStorage.clear();
globalThis.__auth = { teacher: { teacher_id: 'T1' }, selectedDomain: 'numeracy', names: {},
  currentPlan: { plan_date: TODAY, domain_id: 'numeracy', selected_competency_id: 'N2.3.2',
    groups: [{ label: 'beginner', count: 7, target_competency_id: 'N2.3.1', target_competency_name_hi: 'बिना हासिल के जोड़' }, { label: 'progressor', count: 14, target_competency_id: 'N2.3.2', target_competency_name_hi: 'हासिल के साथ जोड़' }, { label: 'proficient', count: 0, target_competency_id: 'N3.3.1' }],
    plan: { worksheets: {} } } };
// today's ways: the Beginners are observed, the Progressors photographed (the Proficients have no children, so no card)
const CH = { has_plan: true, channels: { observed: ['beginner'], photo: ['progressor'] },
  levels: [{ channel: 'observed', level: 'beginner', competency_id: 'N2.3.1', name_hi: 'बिना हासिल के जोड़', rolls: [1, 2, 3] },
           { channel: 'photo', level: 'progressor', competency_id: 'N2.3.2', name_hi: 'हासिल के साथ जोड़', rolls: [4, 5, 6] }] };
globalThis.__api = {
  recordDecisions: async (...a) => { decided.push(a); return {}; },
  getCachedPlan: async () => ({ ...globalThis.__auth.currentPlan, decisions: {} }),      // nothing decided yet today
  getSavedAnalyses: async () => ({ analyses: [] }), getReviewCoverage: async () => null, getReviewChannels: async () => CH,
  recordObserved: async () => ({}), recordORF: async () => ({}), analysePhotos: async () => ({}),
};
const root = createRoot(document.getElementById('root'));
const flush = async () => { for (let i = 0; i < 3; i += 1) await act(async () => { await new Promise((r) => setTimeout(r, 0)); }); };
const q = (sel) => document.querySelector(sel); const qa = (sel) => [...document.querySelectorAll(sel)];
const click = async (el) => { await act(async () => { el.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true })); }); await flush(); };
let n = 0; const check = (label, ok, extra = '') => { n += 1; console.log(`  ${ok ? 'OK  ' : 'FAIL'} ${label}${ok ? '' : '  ' + extra}`); if (!ok) process.exitCode = 1; };

await act(async () => { root.render(React.createElement(Review)); }); await flush();

console.log('the step marker (two steps since 14 Nov: "capture evidence -> one final decision", no first judgment)');
check('the Review opens at "1/2 · आज का प्रदर्शन दर्ज करें" (no separate marker row with other words)', !q('[data-testid="review-steps"]')
  && q('[data-testid="review-title"]').dataset.step === '2' && /^1\/2 आज का प्रदर्शन दर्ज करें/.test(q('[data-testid="review-title"]').textContent.replace(/Record today.*$/, '').trim())
  && q('[data-testid="review-title"] .step-count').textContent === '1/2', q('[data-testid="review-title"]') && q('[data-testid="review-title"]').textContent);
check('no first-judgment step anywhere: no "record-decisions", no "पहला अनुमान" on the screen or in the code\'s step-1 markup', !q('[data-testid="record-decisions"]') && !q('[data-testid="first-intro"]')
  && !q('[data-testid="decisions-left"]') && !q('[data-testid="back-to-decisions"]') && !/पहला अनुमान/.test(document.getElementById('root').textContent) && decided.length === 0);
check('the intro says what to do, in any order, any time today', /किसी भी क्रम में, आज के दिन कभी भी/.test(q('[data-testid="performance-intro"]').textContent));

console.log('\nthe Review\'s icon is ☑️, not a camera (it is not only photos)');
check('☑️ on the bottom tab, the Assess screen\'s heading and "कैसे काम करता है"; 📷 stays only on the photo capture area inside the Photo way', (() => {
  const app = fs.readFileSync(path.join(src, 'services/tabs.js'), 'utf8'); const how = fs.readFileSync(path.join(src, 'components/HowItWorks.jsx'), 'utf8');
  return /\{ id: '\/review', icon: '☑️'/.test(app) && /☑️ <Bi hi="आकलन"/.test(reviewSrc) && /icon: '☑️', hi: 'आकलन'/.test(how)
    && !app.includes('📷') && !how.includes('📷') && (reviewSrc.match(/📷/g) || []).length === 1 && /className="capture-icon">📷</.test(reviewSrc)
    && /^☑️/.test(document.querySelector('h1').textContent);
})());

console.log('\none card per group: its way and its count; a tap opens that group');
const card = (g) => q(`[data-testid="group-card-${g}"]`);
check('a card for each group with children (Beginners, Progressors), none for the empty Proficients', !!q('[data-testid="group-cards"]') && !!card('beginner') && !!card('progressor') && !card('proficient'));
check('each card names its way of checking: "देखकर जाँच" for the observed Beginners, "वर्कशीट जाँच" for the photographed Progressors',
  /देखकर जाँच/.test(card('beginner').textContent) && /वर्कशीट जाँच/.test(card('progressor').textContent));
check('on opening, the first group of today\'s plan is chosen, with its own way: the Beginners\' observation list', card('beginner').classList.contains('on') && !!q('[data-testid="observed-list"]'));
check('no way tabs and no group buttons inside the list: the group card chooses both', !q('[data-testid="channel-observed"]') && !q('[data-testid="channel-photo"]') && !q('[data-testid="observed-list"] .tier-option'));
await click(card('progressor'));
check('a tap on the Progressors\' card: their card is chosen and the photo way opens (no way tab needed)', card('progressor').classList.contains('on') && !card('beginner').classList.contains('on')
  && /AI हर बच्चे का काम पढ़ता है/.test(q('[data-testid="channel-who"]').textContent));
await click(card('beginner'));

console.log('\nthe ⓘ hints (a phone shows no hover tooltip)');
const hintBtn = (id) => q(`[data-testid="${id}"] .hint-btn`);
check('"यही तरीका क्यों?" is an ⓘ, closed: no text until tapped', hintBtn('hint-why-way') && hintBtn('hint-why-way').getAttribute('aria-expanded') === 'false' && !q('[data-testid="hint-why-way"] .hint-text'));
await click(hintBtn('hint-why-way'));
check('...one tap opens why each way fits, and which groups use it today', hintBtn('hint-why-way').getAttribute('aria-expanded') === 'true'
  && !!q('[data-testid="why-observed"]') && !!q('[data-testid="why-photo"]') && /N2\.3\.1/.test(q('[data-testid="why-observed"]').textContent));
check('the ⓘ is a 44 px target (CSS)', /\.hint-btn\s*\{[^}]*min-width:\s*44px[^}]*min-height:\s*44px/.test(fs.readFileSync(path.join(src, 'index.css'), 'utf8')));

console.log('\nthe other ways, only on request');
await click(q('[data-testid="channel-toggle"]'));
check('"दूसरे तरीके भी दिखाएँ": the way tabs appear, and they say what the teacher does',
  /देखकर दर्ज करें/.test(q('[data-testid="channel-observed"]').textContent) && /वर्कशीट की फ़ोटो/.test(q('[data-testid="channel-photo"]').textContent)
  && /पढ़कर सुनाना/.test(q('[data-testid="channel-orf"]').textContent));
const seen = [];          // what the teacher sees with each way chosen
const who = async (id) => { await click(q(`[data-testid="channel-${id}"]`)); seen.push(document.getElementById('root').textContent); return q('[data-testid="channel-who"]').textContent; };
check('the line under the tabs says who does what, for the way chosen; the photo way says the AI reads the work',
  /आप हर बच्चे के लिए A \/ PA \/ NA चुनते हैं/.test(await who('observed')) && /आप वर्कशीट की फ़ोटो लेते हैं; AI हर बच्चे का काम पढ़ता है/.test(await who('photo'))
  && /बच्चा एक मिनट पढ़ता है; आप सही पढ़े गए शब्द और गलतियाँ दर्ज करते हैं/.test(await who('orf')));
check('no card title repeats the tab: with each way chosen, the screen shows no "शिक्षक अवलोकन", "वर्कशीट फ़ोटो", "पठन प्रवाह" or "ORF"', seen.length === 3 && seen.every((t) => !/शिक्षक अवलोकन|वर्कशीट फ़ोटो|पठन प्रवाह|ORF|Teacher Observation|Reading Fluency/.test(t)));
check('the wording stays plain: never "साक्ष्य कैप्चर"', !reviewSrc.includes('साक्ष्य कैप्चर'));

console.log('\non to the decision');
await click(q('[data-testid="to-final"]'));
check('"आगे: अगली कक्षा में क्या पढ़ाएँ, तय करें →" opens "2/2 · अंतिम निर्णय: अगली कक्षा में क्या पढ़ाएँ?"', q('[data-testid="review-title"]').dataset.step === '3'
  && /^2\/2 अंतिम निर्णय: अगली कक्षा में क्या पढ़ाएँ\?/.test(q('[data-testid="review-title"]').textContent) && q('[data-testid="review-title"] .step-count').textContent === '2/2');

console.log('\ntoday\'s ways not known (offline, an older server): the teacher still has a way to record');
await act(async () => root.unmount());
sessionStorage.clear();          // the earlier part left the Review at the decision: start fresh
const root2 = createRoot(document.getElementById('root'));
globalThis.__api.getReviewChannels = async () => ({ has_plan: false, levels: [], channels: {} });
await act(async () => { root2.render(React.createElement(Review)); }); await flush();
check('no group cards, so the way tabs show at once (the bug found on 14 Nov: "ऊपर से एक समूह चुनें" with nothing above it)', !q('[data-testid="group-cards"]') && !!q('[data-testid="channel-observed"]') && !!q('[data-testid="channel-orf"]'));
await act(async () => root2.unmount());

console.log('\nreading aloud: 3-4 children a day, rotating (14 Nov)');
sessionStorage.clear();
const root3 = createRoot(document.getElementById('root'));
globalThis.__api.getReviewChannels = async () => ({ has_plan: true, channels: { orf: ['progressor'] },
  levels: [{ channel: 'orf', level: 'progressor', competency_id: 'L2.5.1', name_hi: 'पढ़ना', rolls: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12] }] });
globalThis.__api.getReviewCoverage = async () => ({ group_rolls: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], analysed_rolls: [], recorded: {}, pending_rolls: [1, 2, 3, 4],
  sample: { mode: 'sample', size: 4, group_size: 12, rolls: [1, 2, 3, 4], rotation: true, later: 8, absent: [] } });
await act(async () => { root3.render(React.createElement(Review)); }); await flush();
check('the reading way says how many today and how many are left for the next days: "आज 4 बच्चे · बाकी 8 अगले दिनों में"', !!q('[data-testid="orf-today"]') && /आज 4 बच्चे · बाकी 8 अगले दिनों में/.test(q('[data-testid="orf-today"]').textContent),
  q('[data-testid="orf-today"]') && q('[data-testid="orf-today"]').textContent);
check('...and the group card counts today\'s 4, not the whole group', /0\/4/.test((q('[data-testid="group-card-count-progressor"]') || {}).textContent || ''), (q('[data-testid="group-card-count-progressor"]') || {}).textContent);
await act(async () => root3.unmount());
console.log(`\n${process.exitCode ? 'SOME CHECKS FAILED' : 'OK: ' + n + ' checks: the Review opens on today\'s performance, one card per group, the other ways on request, then the decision for tomorrow'}`);
