// The Review's step 3, the FINAL decision (29 Oct): for each group with children, the teacher's first judgment, today's evidence (A / PA / NA, how many of the
// group were assessed) and the app's suggestion (re-teach when a third or more made a mistake; nothing when too few were checked), with the choice starting on
// her first judgment. Recording it sends stage 'final' (the decision tomorrow's plan suggests from); a change from the first judgment is said.
// The REAL Review screen in a simulated browser with a fake server. The server side is in backend/tests/test_plan_routes.py.
//
//     cd pwa
//     npm install --save-dev jsdom@24     (once; see plan_screen.dom.test.mjs)
//     node tests/review_final.test.mjs
//
// Without jsdom the test says so and stops without failing.
import fs from 'node:fs'; import path from 'node:path'; import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
let JSDOM;
try { ({ JSDOM } = await import('jsdom')); } catch (e) { console.log('SKIPPED: jsdom is not installed. To run this test: cd pwa; npm install --save-dev jsdom@24'); process.exit(0); }
const here = path.dirname(fileURLToPath(import.meta.url)); const src = path.join(here, '..', 'src'); const out = path.join(here, `.tmp-final-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));      // the temporary build folder is always removed, even if a check fails
const API = ['recordDecisions', 'recordObserved', 'recordORF', 'analysePhotos', 'getSavedAnalyses', 'getReviewCoverage', 'getReviewChannels', 'getCachedPlan'];
const stubs = { '../App': 'export const useAuth = () => globalThis.__auth;', 'react-router-dom': 'export const useNavigate = () => (...a) => globalThis.__navs.push(a); export const useLocation = () => globalThis.__location || ({ pathname: "/review", state: null });',
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

// ── the fake server ──
const d0 = new Date(); const TODAY = `${d0.getFullYear()}-${String(d0.getMonth() + 1).padStart(2, '0')}-${String(d0.getDate()).padStart(2, '0')}`;
const EV = { beginner: { a: 2, pa: 1, na: 3, assessed: 6, group_size: 7, recommend: true, very_small: false },
             progressor: { a: 0, pa: 0, na: 0, assessed: 0, group_size: 14, recommend: false, very_small: false } };
const PLAN = ({ first = { beginner: 'advance', progressor: 'reteach' }, final = {}, evidence = EV } = {}) => ({
  plan_date: TODAY, domain_id: 'numeracy', selected_competency_id: 'N2.3.2', served_from: 'ai',
  groups: [{ label: 'beginner', count: 7, target_competency_id: 'N2.3.1', target_competency_name_hi: 'बिना हासिल के जोड़' }, { label: 'progressor', count: 14, target_competency_id: 'N2.3.2', target_competency_name_hi: 'हासिल के साथ जोड़' }, { label: 'proficient', count: 0, target_competency_id: 'N3.3.1' }],
  plan: { worksheets: {}, rotation_schedule: { blocks: [] } },
  decisions: { ...first, ...final }, first_judgments: first, final_decisions: final, today_evidence: evidence });
let reply = PLAN(); let planCalls = 0; const saves = [];
globalThis.__navs = [];
globalThis.__auth = { teacher: { teacher_id: 'T1' }, selectedDomain: 'numeracy', names: {}, currentPlan: null, setCurrentPlan: (p) => { globalThis.__auth.currentPlan = p; } };
globalThis.__api = {
  getCachedPlan: async () => { planCalls += 1; return JSON.parse(JSON.stringify(reply)); },
  recordDecisions: async (...a) => { saves.push(a); return {}; },
  getSavedAnalyses: async () => [], getReviewCoverage: async () => null, getReviewChannels: async () => ({ has_plan: false, channels: {} }),
  recordObserved: async () => ({}), recordORF: async () => ({}), analysePhotos: async () => ({}),
};
let root;
const flush = async () => { for (let i = 0; i < 5; i += 1) await act(async () => { await new Promise((r) => setTimeout(r, 0)); }); };
const show = async () => { if (root) await act(async () => root.unmount()); root = createRoot(document.getElementById('root')); await act(async () => { root.render(React.createElement(Review)); }); await flush(); };
const q = (sel) => document.querySelector(sel);
const click = async (el) => { await act(async () => { el.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true })); }); await flush(); };
const stepNow = () => q('[data-testid="review-title"]').dataset.step;
const pressed = (g, d) => q(`[data-testid="final-${g}-${d}"]`).getAttribute('aria-pressed') === 'true';
const fresh = () => { sessionStorage.clear(); globalThis.__auth.currentPlan = null; saves.length = 0; globalThis.__navs.length = 0; };
let n = 0; const check = (label, ok, extra = '') => { n += 1; console.log(`  ${ok ? 'OK  ' : 'FAIL'} ${label}${ok ? '' : '  ' + extra}`); if (!ok) process.exitCode = 1; };

console.log('getting to step 3');
fresh(); reply = PLAN();
await show();
check('first judgments recorded for every group: the Review opens at step 2', stepNow() === '2');
const before = planCalls;
await click(q('[data-testid="to-final"]'));
check('"आगे: अंतिम निर्णय →": step 3 ("3/3 अंतिम निर्णय"), with today\'s evidence fetched again (the children\'s work may have changed it)', stepNow() === '3' && /3\/3 अंतिम निर्णय/.test(q('[data-testid="review-title"]').textContent) && planCalls === before + 1);
check('one card for each group with children (no card for the empty Proficients)', !!q('[data-testid="final-beginner"]') && !!q('[data-testid="final-progressor"]') && !q('[data-testid="final-proficient"]'));

console.log('\nwhat each card shows');
check('each card names the skill the decision is about: "N2.3.1 · बिना हासिल के जोड़"', /^N2\.3\.1 · बिना हासिल के जोड़$/.test(q('[data-testid="skill-3-beginner"]').textContent) && /^N2\.3\.2 · हासिल के साथ जोड़$/.test(q('[data-testid="skill-3-progressor"]').textContent));
check('the Beginners: first judgment "⬆ आगे बढ़ें"', /पहला अनुमान.*⬆ आगे बढ़ें/.test(q('[data-testid="final-first-beginner"]').textContent));
check('...today\'s evidence "✓ A 2 · ~ PA 1 · ✗ NA 3 (7 में से 6 बच्चों का आकलन)"', /✓ A 2 · ~ PA 1 · ✗ NA 3/.test(q('[data-testid="final-evidence-beginner"]').textContent) && /7 में से 6 बच्चों का आकलन/.test(q('[data-testid="final-evidence-beginner"]').textContent), q('[data-testid="final-evidence-beginner"]').textContent);
check('...the app\'s suggestion, with its rule: "सुझाव: 🔄 दोहराएँ (जाँचे गए बच्चों में से एक-तिहाई या ज़्यादा से गलती हुई; कम से कम 4 बच्चों की जाँच)"',
  /सुझाव: 🔄 दोहराएँ \(जाँचे गए बच्चों में से एक-तिहाई या ज़्यादा से गलती हुई; कम से कम 4 बच्चों की जाँच\)/.test(q('[data-testid="final-suggest-beginner"]').textContent));
check('...and the choice starts on her first judgment (⬆ आगे बढ़ें chosen), not on the suggestion', pressed('beginner', 'advance') && !pressed('beginner', 'reteach'));
check('the Progressors, nobody assessed yet: "अभी किसी का आकलन नहीं", no suggestion, the choice on their first judgment (🔄)',
  /अभी किसी का आकलन नहीं/.test(q('[data-testid="final-evidence-progressor"]').textContent) && !q('[data-testid="final-suggest-progressor"]') && pressed('progressor', 'reteach'));

console.log('\nchanging and recording');
await click(q('[data-testid="final-beginner-reteach"]'));
check('the Beginners changed to 🔄: "पहला अनुमान ⬆ आगे बढ़ें → अंतिम 🔄 दोहराएँ"', pressed('beginner', 'reteach') && /पहला अनुमान ⬆ आगे बढ़ें → अंतिम 🔄 दोहराएँ/.test(q('[data-testid="final-changed-beginner"]').textContent));
check('the Progressors unchanged: no change line', !q('[data-testid="final-changed-progressor"]'));
await click(q('[data-testid="final-progressor-reteach"]'));
check('a group with no choice: "अंतिम निर्णय दर्ज करें" is off and the line names it', q('[data-testid="record-final"]').disabled && /बाकी: ▲ प्रगतिशील\)/.test(q('[data-testid="finals-left"]').textContent));
await click(q('[data-testid="final-progressor-not_sure"]'));
await click(q('[data-testid="record-final"]'));
check('recording sends the FINAL decisions, stage "final" (what tomorrow\'s plan suggests from)', saves.length === 1 && JSON.stringify(saves[0][3]) === JSON.stringify({ beginner: 'reteach', progressor: 'not_sure' }) && saves[0][4] === 'final', JSON.stringify(saves[0]));
check('...and says so: "✓ अंतिम निर्णय दर्ज हुए। अगली योजना इन्हीं से सुझाई जाएगी।" (and nothing more: no Progress pointer, the tab does that)', /✓ अंतिम निर्णय दर्ज हुए। अगली योजना इन्हीं से सुझाई जाएगी।/.test(q('[data-testid="final-saved"]').textContent) && !q('[data-testid="record-final"]'));
check('...no Progress pointer at the end of the review', !q('[data-testid="final-to-progress"]') && !q('[data-testid="final-saved"] button') && !/प्रगति टैब पर/.test(q('[data-testid="final-saved"]').textContent));
await click(q('[data-testid="final-beginner-advance"]'));
check('changing a decision after recording: the record button is back (nothing is changed until recorded again)', !!q('[data-testid="record-final"]') && !q('[data-testid="final-saved"]') && saves.length === 1);

console.log('\ncoming back, and the other cases');
fresh(); reply = PLAN({ final: { beginner: 'reteach', progressor: 'not_sure' } });
await show();
check('final decisions recorded for every group: the Review opens at step 3, showing them as recorded', stepNow() === '3' && pressed('beginner', 'reteach') && pressed('progressor', 'not_sure') && !!q('[data-testid="final-saved"]'));
fresh(); reply = PLAN({ final: { beginner: 'reteach' } });
await show(); await click(q('[data-testid="to-final"]'));
check('a final decision already recorded for one group: it starts on that (🔄), the other on its first judgment (🔄 for the Progressors)', pressed('beginner', 'reteach') && pressed('progressor', 'reteach'));
fresh(); reply = PLAN({ evidence: { ...EV, beginner: { a: 1, pa: 0, na: 2, assessed: 3, group_size: 7, recommend: false, very_small: true } } });
await show(); await click(q('[data-testid="to-final"]'));
check('only three checked: "बहुत कम बच्चे जाँचे गए; ऐप कोई सुझाव नहीं देता।" and no suggestion', /बहुत कम बच्चे जाँचे गए/.test(q('[data-testid="final-too-few-beginner"]').textContent) && !q('[data-testid="final-suggest-beginner"]'));
check('step 3\'s way back carries step 2\'s badge: "← 2/3 · बच्चों का काम"', q('[data-testid="final-back"] .step-count') && q('[data-testid="final-back"] .step-count').textContent === '2/3' && /बच्चों का काम/.test(q('[data-testid="final-back"]').textContent));
await click(q('[data-testid="final-back"]'));
check('"← बच्चों का काम" goes back to step 2', stepNow() === '2');
fresh(); reply = PLAN(); delete reply.today_evidence;          // the 29 Oct case: a server not yet restarted sends no evidence (so could a failed load)
await show(); await click(q('[data-testid="to-final"]'));
check('no evidence in the reply: "अभी नहीं दिख रही; पेज दोबारा खोलें", NEVER "अभी किसी का आकलन नहीं" (the teacher had assessed everyone)',
  !!q('[data-testid="final-evidence-unknown-beginner"]') && /अभी नहीं दिख रही; पेज दोबारा खोलें/.test(q('[data-testid="final-evidence-beginner"]').textContent)
  && !/अभी किसी का आकलन नहीं/.test(document.getElementById('root').textContent) && !q('[data-testid="final-suggest-beginner"]'));

await act(async () => root.unmount());
console.log(`\n${process.exitCode ? 'SOME CHECKS FAILED' : 'OK: ' + n + ' checks: step 3 shows each group\'s first judgment, today\'s evidence and the suggestion, and records the final decision'}`);
