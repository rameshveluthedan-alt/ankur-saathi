// "Today's time" on the Plan screen (45 / 60 / 90 minutes): the REAL Plan screen in a simulated browser with a fake server, plus the request the app builds.
// The last choice is kept on the device and preselected; 90 on first use; the chosen time goes with every plan request (session_minutes), and nowhere else.
// That the server lays the plan out for it is tested in backend/tests/test_session_minutes.py.
//
//     cd pwa
//     npm install --save-dev jsdom@24     (once; see plan_screen.dom.test.mjs)
//     node tests/plan_session_length.test.mjs
//
// Without jsdom the test says so and stops without failing.
import fs from 'node:fs'; import path from 'node:path'; import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
let JSDOM;
try { ({ JSDOM } = await import('jsdom')); } catch (e) { console.log('SKIPPED: jsdom is not installed. To run this test: cd pwa; npm install --save-dev jsdom@24'); process.exit(0); }
const here = path.dirname(fileURLToPath(import.meta.url)); const src = path.join(here, '..', 'src'); const out = path.join(here, `.tmp-session-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));      // the temporary build folder is always removed, even if a check fails
const stubs = { '../App': 'export const useAuth = () => globalThis.__auth;', 'react-router-dom': 'export const useNavigate = () => globalThis.__navigate;',
  '../services/api': 'export const getCompetencies = (...a) => globalThis.__api.getCompetencies(...a); export const getGroups = (...a) => globalThis.__api.getGroups(...a); export const generatePlan = (...a) => globalThis.__api.generatePlan(...a); export const getGroupProposal = (...a) => globalThis.__api.getGroupProposal(...a); export const getLadder = (...a) => globalThis.__api.getLadder(...a);' };
const loader = { '.js': 'jsx', '.jsx': 'jsx' };
await build({ entryPoints: { screen: path.join(src, 'screens/PlanScreen.jsx') }, bundle: true, format: 'esm', platform: 'node', outdir: out, outExtension: { '.js': '.mjs' }, loader, external: ['react', 'react-dom', 'react-dom/client'], logLevel: 'error',
  plugins: [{ name: 'stubs', setup(b) { b.onResolve({ filter: /^(\.\.\/App|react-router-dom|\.\.\/services\/api)$/ }, (a) => ({ path: a.path, namespace: 'stub' })); b.onLoad({ filter: /.*/, namespace: 'stub' }, (a) => ({ contents: stubs[a.path], loader: 'js' })); } }] });
await build({ entryPoints: { api: path.join(src, 'services/api.js') }, bundle: true, format: 'esm', platform: 'node', outdir: out, outExtension: { '.js': '.mjs' }, loader, logLevel: 'error' });

const dom = new JSDOM('<!doctype html><div id="root"></div>', { url: 'http://localhost/', pretendToBeVisual: true });
for (const k of ['window', 'document', 'navigator', 'HTMLElement', 'Element', 'Node', 'MouseEvent', 'Event', 'localStorage']) Object.defineProperty(globalThis, k, { value: dom.window[k], configurable: true, writable: true });
globalThis.IS_REACT_ACT_ENVIRONMENT = true; globalThis.requestAnimationFrame = (f) => setTimeout(f, 0);
dom.window.Element.prototype.scrollIntoView = () => {};
const React = (await import('react')).default; const { act } = await import('react'); const { createRoot } = await import('react-dom/client');
const Screen = (await import(pathToFileURL(path.join(out, 'screen.mjs')).href)).default;
const api = await import(pathToFileURL(path.join(out, 'api.mjs')).href);

const sk = (id) => ({ id, name_hi: id, name_en: id, grade_level: 'grade_2' });
const LADDER = { beginner: sk('N2.3.1'), progressor: sk('N2.3.2'), proficient: sk('N3.3.1'), options: { beginner: [sk('N2.3.1')], proficient: [sk('N3.3.1')] } };
const generateCalls = [];
globalThis.__auth = { teacher: { teacher_id: 'T1', total_children: 30 }, selectedDomain: 'numeracy', setSelectedDomain() {}, setCurrentPlan() {} };
globalThis.__navigate = () => {};
globalThis.__api = {
  getCompetencies: async () => ({ competencies: [{ ...sk('N2.3.2'), coverage_tier: 'tested' }] }),
  getGroups: async () => ({ groups: [{ label: 'beginner', count: 7 }, { label: 'progressor', count: 14 }, { label: 'proficient', count: 9 }] }),
  getGroupProposal: async () => ({ has_history: false, groups: {}, previous_date: null }),
  getLadder: async () => LADDER,
  generatePlan: async (...a) => { generateCalls.push(a); return { plan: {} }; },
};
const flush = async () => { await act(async () => { await new Promise((r) => setTimeout(r, 0)); }); };
const q = (sel) => document.querySelector(sel); const qa = (sel) => [...document.querySelectorAll(sel)];
const click = async (el) => { await act(async () => { el.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true })); }); };
const chosen = () => qa('[data-testid="session-length"] input[type="radio"]').filter((i) => i.checked).map((i) => Number(i.value));
const generateBtn = () => qa('button.btn-primary').find((b) => /Generate/.test(b.textContent));
let root;
const mount = async () => { if (root) await act(async () => root.unmount()); root = createRoot(document.getElementById('root')); await act(async () => { root.render(React.createElement(Screen)); }); await flush(); };
const generate = async () => { await click(qa('.competency-item').find((e) => e.textContent.includes('N2.3.2'))); await flush(); await click(generateBtn()); await flush(); return generateCalls[generateCalls.length - 1]; };
let n = 0; const check = (label, ok, extra = '') => { n += 1; console.log(`  ${ok ? 'OK  ' : 'FAIL'} ${label}${ok ? '' : '  ' + extra}`); if (!ok) process.exitCode = 1; };

console.log('the chooser');
localStorage.clear();
await mount();
check('first use (nothing stored): three choices, 45 / 60 / 90 minutes, and 90 is selected', qa('[data-testid="session-length"] input[type="radio"]').map((i) => i.value).join() === '45,60,90' && chosen().join() === '90', chosen().join());
check('it sits above the skill list, with its heading and the one-line hint, in Hindi with the English hideable', (() => {
  const box = q('[data-testid="session-length"]'); const list = q('.competency-item');
  return box && list && (box.compareDocumentPosition(list) & dom.window.Node.DOCUMENT_POSITION_FOLLOWING) && /आज का समय/.test(box.textContent)
    && /कम समय हो तो कम गतिविधियाँ और छोटी वर्कशीट/.test(box.textContent) && box.querySelectorAll('.en').length >= 4;
})());
check('each choice is a 44 px tap target (the whole label, not the small radio)', qa('[data-testid^="session-"][data-checked]').every((l) => parseInt(l.style.minHeight, 10) >= 44 && l.contains(l.querySelector('input[type="radio"]'))),
  qa('[data-testid^="session-"][data-checked]').map((l) => l.style.minHeight).join());
check('the chosen one fills with the brand green (a setting for the whole session, not a group colour)', /green-dark/.test(q('[data-testid="session-90"]').style.background) && !/green-dark/.test(q('[data-testid="session-45"]').style.background) && !/tier|beginner|progressor|proficient/.test(q('[data-testid="session-90"]').getAttribute('style')));
let call = await generate();
check('Generate sends 90 when nothing was chosen', call[4].sessionMinutes === 90, JSON.stringify(call[4]));

console.log('\nchoosing, and remembering');
await click(q('[data-testid="session-45"]'));
check('tapping 45 selects it (and only it), and keeps it on the device under "session_minutes"', chosen().join() === '45' && localStorage.getItem('session_minutes') === '45', `${chosen().join()} / ${localStorage.getItem('session_minutes')}`);
call = await generate();
check('Generate then sends 45 (if the choice were not sent, the server would lay the plan out for 90)', call[4].sessionMinutes === 45, JSON.stringify(call[4]));
localStorage.setItem('session_minutes', '60');
await mount();
check('"60" stored on the device: the screen opens with 60 preselected', chosen().join() === '60', chosen().join());
call = await generate();
check('...and sends 60', call[4].sessionMinutes === 60, JSON.stringify(call[4]));
localStorage.setItem('session_minutes', '30');
await mount();
check('a value this app does not offer ("30") falls back to 90', chosen().join() === '90', chosen().join());

console.log('\nthe request');
const bodies = [];
globalThis.fetch = async (url, opts) => { bodies.push({ url, body: JSON.parse(opts.body) }); return { ok: true, status: 200, json: async () => ({}) }; };
await api.generatePlan('T1', 'N2.3.2', 'numeracy', '2026-10-28', { sessionMinutes: 45 });
check('the POST to /plan/generate carries session_minutes: 45', /\/plan\/generate/.test(bodies[0].url) && bodies[0].body.session_minutes === 45, JSON.stringify(bodies[0]));
await api.generatePlan('T1', 'N2.3.2', 'numeracy', '2026-10-28');
check('without a time the field is left out (the server then uses the teacher\'s stored time, 90 unless changed): an older caller is unchanged', !('session_minutes' in bodies[1].body), JSON.stringify(bodies[1].body));
check('it is not sent as a preference anywhere else: only the plan request carries it', bodies.length === 2 && !fs.readFileSync(path.join(src, 'services', 'api.js'), 'utf8').replace(/generatePlan[\s\S]*?\}\);/, '').includes('session_minutes'));

await act(async () => root.unmount());
console.log(`\n${process.exitCode ? 'SOME CHECKS FAILED' : 'OK: ' + n + ' checks: today\'s time is chosen on the Plan screen, remembered on the device, and sent with every plan request'}`);
