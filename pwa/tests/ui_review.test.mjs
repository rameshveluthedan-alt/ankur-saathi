// UI review, points 2-4: "अंकुर साथी कैसे काम करता है?" (how the parts come together) on the login screen only (not on Profile); logout at the top of Profile, asking first
// (it removes this phone's offline copies); and failures in plain Hindi a teacher can act on, never the server's raw English.
// The REAL Login and Profile screens in a simulated browser, and services/errors.js. No server.
//
//     cd pwa
//     npm install --save-dev jsdom@24     (once; see plan_screen.dom.test.mjs)
//     node tests/ui_review.test.mjs
//
// Without jsdom the test says so and stops without failing.
import fs from 'node:fs'; import path from 'node:path'; import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
let JSDOM;
try { ({ JSDOM } = await import('jsdom')); } catch (e) { console.log('SKIPPED: jsdom is not installed. To run this test: cd pwa; npm install --save-dev jsdom@24'); process.exit(0); }
const here = path.dirname(fileURLToPath(import.meta.url)); const src = path.join(here, '..', 'src'); const out = path.join(here, `.tmp-uireview-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));      // the temporary build folder is always removed, even if a check fails
const API = ['login', 'setToken', 'adminSchool', 'adminTeachers', 'adminResetPin', 'adminUnlock', 'adminRecordConsent'];
const stubs = { '../App': 'export const useAuth = () => globalThis.__auth;', 'react-router-dom': 'export const useNavigate = () => () => {};', './ChangePinScreen': 'export const PinChangeForm = () => null;',
  '../services/api': API.map((n) => `export const ${n} = (...a) => globalThis.__api.${n}(...a);`).join('\n') };
await build({ entryPoints: { login: path.join(src, 'screens/LoginScreen.jsx'), account: path.join(src, 'screens/AccountScreen.jsx'), errors: path.join(src, 'services/errors.js'), network: path.join(src, 'services/network.js') },
  bundle: true, format: 'esm', platform: 'node', outdir: out, outExtension: { '.js': '.mjs' }, loader: { '.js': 'jsx', '.jsx': 'jsx' }, external: ['react', 'react-dom', 'react-dom/client'], logLevel: 'error',
  define: { 'import.meta.env.VITE_DEMO_HINT': '"true"' },
  plugins: [{ name: 'stubs', setup(b) { b.onResolve({ filter: /^(\.\.\/App|react-router-dom|\.\/ChangePinScreen|\.\.\/services\/api)$/ }, (a) => ({ path: a.path, namespace: 'stub' })); b.onLoad({ filter: /.*/, namespace: 'stub' }, (a) => ({ contents: stubs[a.path], loader: 'js' })); } }] });
const dom = new JSDOM('<!doctype html><div id="root"></div>', { url: 'http://localhost/', pretendToBeVisual: true });
for (const k of ['window', 'document', 'navigator', 'HTMLElement', 'HTMLInputElement', 'Element', 'Node', 'MouseEvent', 'Event', 'localStorage']) Object.defineProperty(globalThis, k, { value: dom.window[k], configurable: true, writable: true });
globalThis.IS_REACT_ACT_ENVIRONMENT = true; globalThis.requestAnimationFrame = (f) => setTimeout(f, 0);
const React = (await import('react')).default; const { act } = await import('react'); const { createRoot } = await import('react-dom/client');
const Login = (await import(pathToFileURL(path.join(out, 'login.mjs')).href)).default;
const Account = (await import(pathToFileURL(path.join(out, 'account.mjs')).href)).default;
const { friendlyError } = await import(pathToFileURL(path.join(out, 'errors.mjs')).href);
const { NetworkError } = await import(pathToFileURL(path.join(out, 'network.mjs')).href);
const read = (f) => fs.readFileSync(path.join(src, f), 'utf8');

let loggedOut = 0; let confirmAnswer = false; let confirmText = '';
dom.window.confirm = (t) => { confirmText = t; return confirmAnswer; };
globalThis.__auth = { teacher: { teacher_id: 'T1', role: 'school_admin', employee_code: 'MPA101', school_code: 'S1', enrolled_grades: ['grade_2'] }, setTeacher() {}, logout: () => { loggedOut += 1; } };
globalThis.__api = { login: async () => ({}), setToken() {}, adminSchool: async () => ({}), adminTeachers: async () => ({ teachers: Array.from({ length: 6 }, (_, i) => ({ teacher_id: `t${i}`, code: `MPT10${i}`, role: 'teacher', children: 24 })) }),
  adminResetPin: async () => ({}), adminUnlock: async () => ({}), adminRecordConsent: async () => ({}) };
let root;
const flush = async () => { for (let i = 0; i < 3; i += 1) await act(async () => { await new Promise((r) => setTimeout(r, 0)); }); };
const show = async (C) => { if (root) await act(async () => root.unmount()); root = createRoot(document.getElementById('root')); await act(async () => { root.render(React.createElement(C)); }); await flush(); };
const q = (sel) => document.querySelector(sel); const qa = (sel) => [...document.querySelectorAll(sel)];
const click = async (el) => { await act(async () => { el.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true })); }); await flush(); };
let n = 0; const check = (label, ok, extra = '') => { n += 1; console.log(`  ${ok ? 'OK  ' : 'FAIL'} ${label}${ok ? '' : '  ' + extra}`); if (!ok) process.exitCode = 1; };

console.log('2. "कैसे काम करता है"');
await show(Login);
const how = () => q('[data-testid="how-it-works"]');
check('on the login screen, before signing in: a fold "ℹ️ अंकुर साथी कैसे काम करता है?" (How Ankur Saathi works), closed', how() && how().tagName === 'DETAILS' && !how().open && /अंकुर साथी कैसे काम करता है\?/.test(how().querySelector('summary').textContent) && /How Ankur Saathi works/.test(how().querySelector('summary').textContent));
check('four steps in the app\'s order, each named as its tab and naming what powers it: योजना बनाएँ (कौशल-सीढ़ी), आज की योजना (AI + जाँच), समीक्षा (फ़ोटो, अवलोकन, पढ़कर सुनाना), कक्षा प्रगति',
  (() => { const st = qa('[data-testid="how-step"]').map((li) => li.textContent);
    return st.length === 4 && /1\. योजना बनाएँ.*कौशल-सीढ़ी/.test(st[0]) && /2\. आज की योजना.*AI \+ जाँच/.test(st[1]) && /3\. समीक्षा.*फ़ोटो, अवलोकन, पढ़कर सुनाना/.test(st[2]) && /पहला अनुमान/.test(st[2]) && /अंतिम निर्णय/.test(st[2]) && /अवलोकन/.test(st[2]) && /पढ़कर सुनाना/.test(st[2]) && /observation, or reading aloud/.test(st[2]) && /4\. कक्षा प्रगति/.test(st[3]); })());
check('...the loop back to tomorrow\'s plan, and that names never reach the AI', /↻ आपके निर्णय और आज के नतीजे कल की योजना का सुझाव बनाते हैं/.test(q('[data-testid="how-loop"]').textContent) && /बच्चों के नाम AI को कभी नहीं भेजे जाते/.test(how().textContent));
check('every line keeps its English in a hideable translation ("Hindi only" hides it)', qa('[data-testid="how-step"]').every((li) => li.querySelector('.en')) && !!q('[data-testid="how-loop"] .en'));
await show(Account);
check('...and NOT on Profile (a duplicate there: Profile is for account tasks); it is on the login screen only', !how() && !/HowItWorks/.test(read('screens/AccountScreen.jsx')) && /import HowItWorks from '\.\.\/components\/HowItWorks'/.test(read('screens/LoginScreen.jsx')));

console.log('\n3. logout');
const lo = () => qa('[data-testid="logout"]');
check('one logout button, at the TOP of Profile (in the account card, before the leader\'s teacher list)', lo().length === 1 && !!lo()[0].closest('[data-testid="account-info"]')
  && (lo()[0].compareDocumentPosition(q('[data-testid="teacher-row"]')) & dom.window.Node.DOCUMENT_POSITION_FOLLOWING), `${lo().length} buttons`);
confirmAnswer = false; await click(lo()[0]);
check('tapping it asks first, saying the offline copies go; "Cancel" keeps her signed in', loggedOut === 0 && /लॉग आउट करें\? इस फ़ोन पर रखी योजनाएँ और वर्कशीट हट जाएँगी।/.test(confirmText), confirmText);
confirmAnswer = true; await click(lo()[0]);
check('"OK" logs out', loggedOut === 1);

console.log('\n4. failures in plain Hindi');
const act1 = { hi: 'योजना नहीं बन सकी', en: 'The plan could not be made' };
const err = (status, message, extra = {}) => Object.assign(new Error(message), { status, ...extra });
const quiet = console.warn; console.warn = () => {};
check('no internet: the plain offline sentence, as it is', friendlyError(new NetworkError(), act1) === new NetworkError().message && /इंटरनेट/.test(new NetworkError().message));
check('a server error in English (500): what failed, why and what to do, in Hindi, without the raw text', (() => { const t = friendlyError(err(500, 'Plan generation failed: KeyError foo'), act1);
  return /^योजना नहीं बन सकी \(The plan could not be made\)। सर्वर अभी जवाब नहीं दे रहा। थोड़ी देर बाद फिर कोशिश करें।/.test(t) && !/KeyError/.test(t); })());
check('a message the server wrote in Hindi is kept (it was written for the teacher)', friendlyError(err(400, 'एक दोहराव वही कौशल है जो कल था।'), act1).endsWith(': एक दोहराव वही कौशल है जो कल था।'));
check('a plainer reason for this action wins: a reading-aloud 404 says the roll number is not in the class', /यह रोल नंबर इस कक्षा में नहीं है।/.test(friendlyError(err(404, 'Roll 999 not found'), { hi: 'सहेजा नहीं जा सका', en: 'Could not save' }, { 404: { hi: 'यह रोल नंबर इस कक्षा में नहीं है।', en: "This roll number isn't in this class." } })));
check('other cases: 404 "not found, reopen", 400 "check what was sent", 401 "sign in again"', /पेज दोबारा खोलकर/.test(friendlyError(err(404, 'x'), act1)) && /जाँचकर फिर कोशिश करें/.test(friendlyError(err(422, 'x'), act1)) && /फिर से लॉगिन करें/.test(friendlyError(err(401, 'x'), act1)));
localStorage.setItem('ankur_hindi_only', '1');
check('"Hindi only" on: no English in the message', !/[A-Za-z]/.test(friendlyError(err(500, 'boom'), act1)), friendlyError(err(500, 'boom'), act1));
localStorage.removeItem('ankur_hindi_only'); console.warn = quiet;
check('the teacher\'s screens no longer show e.message raw (only the AI-limit message, which the server writes in both languages)', ['screens/PlanScreen.jsx', 'screens/ReviewScreen.jsx', 'screens/ProgressScreen.jsx', 'screens/YojanaScreen.jsx'].every((f) => {
  const code = read(f); return !/notify\(e\.message(?! \+ \(samples)|\+ ':' \+ e\.message|'\): ' \+ e\.message|\+ ': ' \+ e\.message/.test(code) && (code.match(/e\.message/g) || []).length <= (f === 'screens/PlanScreen.jsx' ? 1 : 0); }));

await act(async () => root.unmount());
console.log(`\n${process.exitCode ? 'SOME CHECKS FAILED' : 'OK: ' + n + ' checks: how it works is one tap away, logout is at the top and asks first, and failures read in plain Hindi'}`);
