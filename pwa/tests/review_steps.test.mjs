// The Review screen's first step (UI review, point 1): "record" stays off until every group with children has a decision, and a line says which groups are left;
// a marker shows the three steps (decide, the children's work, analysis) and where the teacher is; the wording is plain ("बच्चों का काम देखें", not "साक्ष्य कैप्चर").
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
const reviewSrc = fs.readFileSync(path.join(src, 'screens/ReviewScreen.jsx'), 'utf8');

const decided = [];
const d0 = new Date(); const TODAY = `${d0.getFullYear()}-${String(d0.getMonth() + 1).padStart(2, '0')}-${String(d0.getDate()).padStart(2, '0')}`;      // the phone's own date, as the screen uses
sessionStorage.clear();
globalThis.__auth = { teacher: { teacher_id: 'T1' }, selectedDomain: 'numeracy', names: {},
  currentPlan: { plan_date: TODAY, domain_id: 'numeracy', selected_competency_id: 'N2.3.2',
    groups: [{ label: 'beginner', count: 7, target_competency_id: 'N2.3.1', target_competency_name_hi: 'बिना हासिल के जोड़' }, { label: 'progressor', count: 14, target_competency_id: 'N2.3.2', target_competency_name_hi: 'हासिल के साथ जोड़' }, { label: 'proficient', count: 0, target_competency_id: 'N3.3.1' }],
    plan: { worksheets: {} } } };
globalThis.__api = {
  recordDecisions: async (...a) => { decided.push(a); return {}; },
  getCachedPlan: async () => ({ ...globalThis.__auth.currentPlan, decisions: {} }),      // nothing decided yet today
  getSavedAnalyses: async () => ({ analyses: [] }), getReviewCoverage: async () => null, getReviewChannels: async () => ({ channels: [] }),
  recordObserved: async () => ({}), recordORF: async () => ({}), analysePhotos: async () => ({}),
};
const root = createRoot(document.getElementById('root'));
const flush = async () => { for (let i = 0; i < 3; i += 1) await act(async () => { await new Promise((r) => setTimeout(r, 0)); }); };
const q = (sel) => document.querySelector(sel); const qa = (sel) => [...document.querySelectorAll(sel)];
const click = async (el) => { await act(async () => { el.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true })); }); await flush(); };
const pick = (group, which) => qa(`.tier-card.tier-${group} .decision-btn`).find((b) => b.textContent.includes(which));
const record = () => q('[data-testid="record-decisions"]');
let n = 0; const check = (label, ok, extra = '') => { n += 1; console.log(`  ${ok ? 'OK  ' : 'FAIL'} ${label}${ok ? '' : '  ' + extra}`); if (!ok) process.exitCode = 1; };

await act(async () => { root.render(React.createElement(Review)); }); await flush();

console.log('the step marker');
check('step 1\'s heading carries the step: "1/3 · आज हर समूह कैसा रहा?" (no separate marker row with other words)', !q('[data-testid="review-steps"]')
  && q('[data-testid="review-title"]').dataset.step === '1' && /^1\/3 आज हर समूह कैसा रहा\?/.test(q('[data-testid="review-title"]').textContent.replace(/How did.*$/, '').trim())
  && q('[data-testid="review-title"] .step-count').textContent === '1/3');

console.log('\nthe Review\'s icon is ☑️, not a camera (it is not only photos)');
check('☑️ on the bottom tab, the Review\'s heading and "कैसे काम करता है"; 📷 stays only on the photo capture area inside the Photo way', (() => {
  const app = fs.readFileSync(path.join(src, 'services/tabs.js'), 'utf8'); const how = fs.readFileSync(path.join(src, 'components/HowItWorks.jsx'), 'utf8');
  return /\{ id: '\/review', icon: '☑️'/.test(app) && /<h1>☑️ <Bi hi="समीक्षा"/.test(reviewSrc) && /icon: '☑️', hi: 'समीक्षा'/.test(how)
    && !app.includes('📷') && !how.includes('📷') && (reviewSrc.match(/📷/g) || []).length === 1 && /className="capture-icon">📷</.test(reviewSrc)
    && /^☑️/.test(document.querySelector('h1').textContent);
})());

console.log('\nthe ⓘ hints (a phone shows no hover tooltip)');
const hintBtn = (id) => q(`[data-testid="${id}"] .hint-btn`);
check('step 1 has an ⓘ, closed: no text until tapped', hintBtn('hint-decisions') && hintBtn('hint-decisions').getAttribute('aria-expanded') === 'false' && !q('[data-testid="hint-decisions"] .hint-text'));
await click(hintBtn('hint-decisions'));
check('...one tap opens what each choice does to the next plan, in Hindi with its English', hintBtn('hint-decisions').getAttribute('aria-expanded') === 'true'
  && /⬆ आगे बढ़ें: अगली योजना में अगला कौशल। 🔄 दोहराएँ या ❓ पक्का नहीं: अगली योजना में वही कौशल, दोबारा समझाकर।/.test(q('[data-testid="hint-decisions"] .hint-text').textContent)
  && !!q('[data-testid="hint-decisions"] .hint-text .en'));
await click(hintBtn('hint-decisions'));
check('...and a second tap closes it', !q('[data-testid="hint-decisions"] .hint-text'));
check('the ⓘ is a 44 px target (CSS)', /\.hint-btn\s*\{[^}]*min-width:\s*44px[^}]*min-height:\s*44px/.test(fs.readFileSync(path.join(src, 'index.css'), 'utf8')));

check('step 1: each group\'s card names the skill its first judgment is about: "N2.3.1 · बिना हासिल के जोड़" (the group is in the card\'s badge)', /^N2\.3\.1 · बिना हासिल के जोड़$/.test(q('[data-testid="skill-1-beginner"]').textContent) && /^N2\.3\.2 · हासिल के साथ जोड़$/.test(q('[data-testid="skill-1-progressor"]').textContent));

console.log('\n"record" waits for a decision for every group');
check('nothing chosen: "record" is off, and the line names both groups with children (the Proficients have none, so they are not asked)',
  record().disabled && /हर समूह के लिए एक विकल्प चुनें \(बाकी: ● शुरुआती, ▲ प्रगतिशील\)/.test(q('[data-testid="decisions-left"]').textContent), q('[data-testid="decisions-left"]') && q('[data-testid="decisions-left"]').textContent);
await click(record());
check('...tapping it does nothing', decided.length === 0);
await click(pick('beginner', 'आगे बढ़ें'));
check('one group chosen: still off, and the line names only the group left', record().disabled && /बाकी: ▲ प्रगतिशील\)/.test(q('[data-testid="decisions-left"]').textContent) && !/शुरुआती/.test(q('[data-testid="decisions-left"]').textContent));
await click(pick('progressor', 'दोहराएँ'));
check('every group with children chosen: "record" is on, and the line is gone', !record().disabled && !q('[data-testid="decisions-left"]'));
check('the button says what comes next, plainly: "दर्ज करें → बच्चों का काम देखें" (not "साक्ष्य कैप्चर")', /दर्ज करें → बच्चों का काम देखें/.test(record().textContent) && !reviewSrc.includes('साक्ष्य कैप्चर'));
await click(record());
check('recording sends the two decisions and moves on: the marker shows "2/3", and the heading is "बच्चों का काम देखें"',
  decided.length === 1 && JSON.stringify(decided[0][3]) === JSON.stringify({ beginner: 'advance', progressor: 'reteach' }) && decided[0][4] === 'first'
  && q('[data-testid="review-title"]').dataset.step === '2' && /^2\/3 बच्चों का काम देखें/.test(q('[data-testid="review-title"]').textContent) && [...document.querySelectorAll('h2')].some((h) => /बच्चों का काम देखें/.test(h.textContent)), JSON.stringify(decided[0]));

check('step 2: no ⓘ for the ways (the line under the tabs says it, always visible); the tabs say what the teacher does',
  !q('[data-testid="hint-channels"]') && /देखकर दर्ज करें/.test(q('[data-testid="channel-observed"]').textContent) && /वर्कशीट की फ़ोटो/.test(q('[data-testid="channel-photo"]').textContent)
  && /पढ़कर सुनाना/.test(q('[data-testid="channel-orf"]').textContent));
const seen = [];          // what the teacher sees with each way chosen
const who = async (id) => { await click(q(`[data-testid="channel-${id}"]`)); seen.push(document.getElementById('root').textContent); return q('[data-testid="channel-who"]').textContent; };
check('the line under the tabs says who does what, for the way chosen; the photo way says the AI reads the work',
  /आप हर बच्चे के लिए A \/ PA \/ NA चुनते हैं/.test(await who('observed')) && /आप वर्कशीट की फ़ोटो लेते हैं; AI हर बच्चे का काम पढ़ता है/.test(await who('photo'))
  && /बच्चा एक मिनट पढ़ता है; आप सही पढ़े गए शब्द और गलतियाँ दर्ज करते हैं/.test(await who('orf')));
check('no card title repeats the tab: with each way chosen, the screen shows no "शिक्षक अवलोकन", "वर्कशीट फ़ोटो", "पठन प्रवाह" or "ORF"', seen.length === 3 && seen.every((t) => !/शिक्षक अवलोकन|वर्कशीट फ़ोटो|पठन प्रवाह|ORF|Teacher Observation|Reading Fluency/.test(t)));

await act(async () => root.unmount());
console.log(`\n${process.exitCode ? 'SOME CHECKS FAILED' : 'OK: ' + n + ' checks: the Review asks for a decision for every group before moving on, and shows its three steps'}`);
