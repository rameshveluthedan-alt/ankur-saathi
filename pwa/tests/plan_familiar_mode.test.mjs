// "छोटी स्क्रीन" (Shorter screen; stored as familiar_mode): a toggle on Profile that makes the plan screen (YojanaScreen) shorter. Each teach block's one-line script
// folds under "आज की गतिविधि" and the anchor card folds to its title row. The block's title, its re-teach note and its signal panel NEVER fold.
// The REAL Profile and plan screens in a simulated browser: the toggle is flipped on Profile and the plan screen is drawn again. No server.
//
//     cd pwa
//     npm install --save-dev jsdom@24     (once; see plan_screen.dom.test.mjs)
//     node tests/plan_familiar_mode.test.mjs
//
// Without jsdom the test says so and stops without failing.
import fs from 'node:fs'; import path from 'node:path'; import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
let JSDOM;
try { ({ JSDOM } = await import('jsdom')); } catch (e) { console.log('SKIPPED: jsdom is not installed. To run this test: cd pwa; npm install --save-dev jsdom@24'); process.exit(0); }
const here = path.dirname(fileURLToPath(import.meta.url)); const src = path.join(here, '..', 'src'); const out = path.join(here, `.tmp-familiar-${process.pid}`);
// the plan screen shows TODAY's plan only ("आज की योजना"), so its fixture plans are dated today, on the phone's own calendar
const TODAY = (() => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; })();
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));      // the temporary build folder is always removed, even if a check fails
const API = ['adminSchool', 'adminTeachers', 'adminResetPin', 'adminUnlock', 'adminRecordConsent', 'getCachedPlan', 'openAuthedPage', 'worksheetPath', 'prepareOfflineCopy', 'getReviewChannels'];
const stubs = {
  '../App': 'export const useAuth = () => globalThis.__auth;',
  'react-router-dom': 'export const useNavigate = () => () => {};',
  './ChangePinScreen': 'export const PinChangeForm = () => null;',
  '../services/api': API.map((n) => `export const ${n} = (...a) => globalThis.__api.${n}(...a);`).join('\n'),
};
await build({
  entryPoints: { account: path.join(src, 'screens/AccountScreen.jsx'), plan: path.join(src, 'screens/YojanaScreen.jsx') }, bundle: true, format: 'esm', platform: 'node', outdir: out, outExtension: { '.js': '.mjs' },
  loader: { '.js': 'jsx', '.jsx': 'jsx' }, external: ['react', 'react-dom'], logLevel: 'error',
  plugins: [{ name: 'stubs', setup(b) {
    b.onResolve({ filter: /^(\.\.\/App|react-router-dom|\.\/ChangePinScreen|\.\.\/services\/api)$/ }, (a) => ({ path: a.path, namespace: 'stub' }));
    b.onLoad({ filter: /.*/, namespace: 'stub' }, (a) => ({ contents: stubs[a.path], loader: 'js' }));
  } }],
});
const dom = new JSDOM('<!doctype html><div id="root"></div>', { url: 'http://localhost/', pretendToBeVisual: true });
for (const k of ['window', 'document', 'navigator', 'HTMLElement', 'HTMLInputElement', 'Element', 'Node', 'MouseEvent', 'Event', 'localStorage']) Object.defineProperty(globalThis, k, { value: dom.window[k], configurable: true, writable: true });
globalThis.IS_REACT_ACT_ENVIRONMENT = true; globalThis.requestAnimationFrame = (f) => setTimeout(f, 0);
const React = (await import('react')).default; const { act } = await import('react'); const { createRoot } = await import('react-dom/client');
const Account = (await import(pathToFileURL(path.join(out, 'account.mjs')).href)).default;
const Plan = (await import(pathToFileURL(path.join(out, 'plan.mjs')).href)).default;

let n = 0; const check = (label, ok, extra = '') => { n += 1; console.log(`  ${ok ? 'OK  ' : 'FAIL'} ${label}${ok ? '' : '  ' + extra}`); if (!ok) process.exitCode = 1; };
const q = (sel) => document.querySelector(sel); const qa = (sel) => [...document.querySelectorAll(sel)];
const flush = async () => { await act(async () => { await new Promise((r) => setTimeout(r, 0)); }); };
const click = async (el) => { await act(async () => { el.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true })); }); await flush(); };
const folded = (el) => !!(el && el.closest('details') && !el.closest('details').open && !el.closest('summary'));     // inside a CLOSED fold (and not its title line)
const visible = (el) => !!el && !folded(el);

// a plan: an anchor card, the Progressors re-teaching (with the note) on maths questions, the Beginners on a writing prompt, the Proficients with no panel
const teach = (g, script, extra) => ({ type: 'teach', teach_group: g, duration_minutes: 15, time_start: '0:12', script_hi: script, talking_points: { i_do_hi: 'मैं', we_do_hi: 'हम', you_do_hi: 'तुम' }, ...extra });
const PLAN = {
  plan_date: TODAY, domain_id: 'numeracy', selected_competency_id: 'N2.3.2',
  groups: [{ label: 'beginner', count: 7, target_competency_id: 'N2.3.1' }, { label: 'progressor', count: 14, target_competency_id: 'N2.3.2' }, { label: 'proficient', count: 9, target_competency_id: 'N3.3.1' }],
  plan: {
    explainability: { items: [{ id: 'resources', title_hi: 'सामग्री', title_en: 'Resources', body_hi: '**हर समूह के लिए:**\n• **शुरुआती** («जोड़»): छड़ियाँ। **__x', body_en: '**For each group:**\n• **Beginners** (’addition’): sticks.' }] },
    anchor: { title_hi: 'गाँव का बाज़ार', title_en: 'Village Market Story', narration_hi: 'बाज़ार का खेल', opening_question_hi: 'कितने आम?' }, worksheets: {},
    rotation_schedule: { blocks: [
      { type: 'anchor', duration_minutes: 10 },
      teach('progressor', 'पहले एक जोड़ दिखाओ', { reteach: true, affected_rolls: [4, 5], reteach_mistakes: [{ misconception_id: 'N2.3.2-M1', name_hi: 'हासिल भूलना', children: 2 }],
        signal: { shape: 'maths_questions', signal_curated: true, maths_questions: { core: ['23 + 15 = ?', '36 + 29 = ?', '48 + 37 = ?'], extra_count: 2 } } }),
      teach('beginner', 'तीली से गिनो', { signal: { shape: 'writing_prompt', signal_curated: false, writing_prompt: { prompt: 'अपने परिवार के बारे में तीन वाक्य लिखो' } } }),
      teach('proficient', 'तीन अंकों का जोड़', { signal: { shape: null, signal_curated: false } }),
    ] },
  },
};
globalThis.__auth = { currentPlan: PLAN, setCurrentPlan() {}, teacher: { teacher_id: 'T1', role: 'teacher', school_code: 'S1', enrolled_grades: ['grade_2'] }, selectedDomain: 'numeracy', logout() {} };
globalThis.__api = { getReviewChannels: async () => globalThis.__channels || ({ has_plan: false, levels: [], channels: {} }), adminSchool: async () => ({}), adminTeachers: async () => ({ teachers: [] }), getCachedPlan: async () => PLAN, openAuthedPage: async () => {}, worksheetPath: () => '/w', prepareOfflineCopy: () => {} };
let root;
const show = async (C) => { if (root) await act(async () => root.unmount()); root = createRoot(document.getElementById('root')); await act(async () => { root.render(React.createElement(C)); }); await flush(); };
const blockOf = (g) => q(`.timeline-block.tier-${g}`) || qa('.timeline-block').find((b) => b.textContent.includes(PLAN.groups.find((x) => x.label === g).target_competency_id));
const scriptsOf = () => qa('[data-testid="block-script"]');

console.log('the toggle on Profile');
localStorage.clear();
await show(Account);
const box = () => q('[data-testid="shorter-screen"]');
check('it reads "छोटी स्क्रीन" with "Shorter screen" hideable, and never the old "अनुभवी शिक्षक मोड"', box() && /छोटी स्क्रीन\s*Shorter screen/.test(box().closest('label').textContent) && !!box().closest('label').querySelector('.en')
  && !document.body.textContent.includes('अनुभवी') && !fs.readFileSync(path.join(src, 'screens/AccountScreen.jsx'), 'utf8').includes('अनुभवी'), box() && box().closest('label').textContent);
check('it sits under the "सिर्फ़ हिंदी दिखाएँ" toggle, with its one-line explanation in Hindi and English', (() => {
  const hindi = q('[data-testid="hindi-only"]'); const hint = q('[data-testid="shorter-screen-hint"]');
  return hindi && (hindi.compareDocumentPosition(box()) & dom.window.Node.DOCUMENT_POSITION_FOLLOWING) && hint && /योजना की स्क्रीन छोटी हो जाती है; एक टैप पर सब कुछ खुलता है।/.test(hint.textContent) && /The plan screen gets shorter; one tap opens everything\./.test(hint.textContent);
})());
check('off by default (nothing stored), and a 44 px row like the Hindi-only toggle', !box().checked && parseInt(box().closest('label').style.minHeight, 10) >= 44);

console.log('\nthe plan screen with it OFF (as today)');
await show(Plan);
check('every one-line script is visible without a tap, and there is no "आज की गतिविधि" fold', scriptsOf().length === 3 && scriptsOf().every(visible) && !q('[data-testid="script-fold"]'));
check('the anchor card is open as today (no fold)', !!q('[data-testid="anchor-card"]') && !q('[data-testid="anchor-fold"]') && visible(q('[data-testid="anchor-card"] p')));
check('"यह योजना क्यों?": the labels wrapped in ** are bold (<strong>), the markers never show, and the rest is plain', await (async () => {
  await click(q('[data-testid="why-toggle"]'));
  const b = qa('[data-testid="why-body"]')[0];
  return !!b && [...b.querySelectorAll('strong')].map((x) => x.textContent).join('|') === 'हर समूह के लिए:|शुरुआती' && !b.textContent.includes('**') && /• शुरुआती \(«जोड़»\): छड़ियाँ। x$/.test(b.textContent)
    && [...b.nextElementSibling.querySelectorAll('strong')].map((x) => x.textContent).join('|') === 'For each group:|Beginners';
})());
check('the anchor card names its story: "एंकर गतिविधि: «गाँव का बाज़ार»" with the English title hideable (the heading was the same generic words for every skill)', (() => {
  const t = q('[data-testid="anchor-title"]');
  return !!t && /«गाँव का बाज़ार»/.test(t.textContent) && /Village Market Story/.test(t.querySelector('.en').textContent) && !!t.closest('h3') && /एंकर गतिविधि/.test(t.closest('h3').textContent);
})());

console.log('\nflipping it on Profile, then the plan screen again');
await show(Account);
await click(box());
check('the tick is stored on the phone as familiar_mode = "true"', box().checked && localStorage.getItem('familiar_mode') === 'true', localStorage.getItem('familiar_mode'));
await show(Plan);
check('the plan screen drawn next has changed: each one-line script is in a "आज की गतिविधि" fold, CLOSED', qa('[data-testid="script-fold"]').length === 3 && qa('[data-testid="script-fold"]').every((d) => !d.open && /आज की गतिविधि/.test(d.querySelector('summary').textContent))
  && scriptsOf().length === 3 && scriptsOf().every(folded));
const prog = blockOf('progressor');
check('the block title stays visible: group, skill and minutes', visible(prog.querySelector('strong')) && /प्रगतिशील/.test(prog.querySelector('strong').textContent) && visible(prog.querySelector('[data-testid="block-skill"]')) && /15 मि\./.test(prog.textContent));
check('the re-teach note stays visible', visible(prog.querySelector('[data-testid="reteach-note"]')));
check('the three core questions stay visible (never folded)', qa('[data-testid="core-question"]').length === 3 && qa('[data-testid="core-question"]').every(visible));
check('the writing prompt stays visible (never folded)', visible(q('[data-testid="writing-prompt"]')));
check('the anchor card is folded to its title row, closed: its title shows, its text does not', (() => {
  const f = q('[data-testid="anchor-fold"]');
  return f && !f.open && /एंकर गतिविधि/.test(f.querySelector('summary').textContent) && /10 मि\./.test(f.querySelector('summary').textContent) && folded([...f.querySelectorAll('p')].find((p) => p.textContent.includes('बाज़ार'))) && !q('[data-testid="anchor-card"]');
})());
const expandedBefore = prog.getAttribute('aria-expanded');
await click(prog.querySelector('[data-testid="script-fold"] summary'));
check('one tap opens the script, and does not open or close the teach block itself', prog.querySelector('[data-testid="script-fold"]').open && visible(prog.querySelector('[data-testid="block-script"]')) && prog.getAttribute('aria-expanded') === expandedBefore);
check('the talking points and the understanding check stay closed, as today', !document.body.textContent.includes('मैं करूँगा'));

console.log('\nand off again');
await show(Account);
await click(box());
check('unticked: stored as "false"', !box().checked && localStorage.getItem('familiar_mode') === 'false');
await show(Plan);
check('the plan screen is back as today: scripts visible, anchor card open', !q('[data-testid="script-fold"]') && scriptsOf().every(visible) && !!q('[data-testid="anchor-card"]'));

await act(async () => root.unmount());
console.log(`\n${process.exitCode ? 'SOME CHECKS FAILED' : 'OK: ' + n + ' checks: "छोटी स्क्रीन" folds the one-line scripts and the anchor card; the title, the re-teach note and the signal panel never fold'}`);
