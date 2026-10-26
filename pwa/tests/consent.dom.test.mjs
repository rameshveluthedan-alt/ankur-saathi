// The REAL sign-up form and the REAL admin panel, in a simulated browser with a fake server. A new school is created only by someone who confirms the consent statement;
// joining a school with its join code asks for nothing; the admin of a school that has not confirmed sees a warning and can confirm.
//
//     cd pwa
//     node tests/consent.dom.test.mjs        (needs jsdom, like plan_screen.dom.test.mjs; without it the test says so and stops without failing)
import fs from 'node:fs'; import path from 'node:path'; import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
let JSDOM;
try { ({ JSDOM } = await import('jsdom')); } catch (e) { console.log('SKIPPED: jsdom is not installed. To run this test: cd pwa; npm install --save-dev jsdom@24'); process.exit(0); }
const here = path.dirname(fileURLToPath(import.meta.url)); const src = path.join(here, '..', 'src'); const out = path.join(here, `.tmp-consent-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));

const API = ['login', 'registerTeacher', 'setToken', 'adminSchool', 'adminTeachers', 'adminResetPin', 'adminUnlock', 'adminRotateJoinCode', 'adminRecordConsent'];
const stubs = {
  '../App': 'export const useAuth = () => globalThis.__auth;',
  'react-router-dom': 'export const useNavigate = () => () => {};',
  './ChangePinScreen': 'export const PinChangeForm = () => null;',
  '../services/api': API.map((n) => `export const ${n} = (...a) => globalThis.__api.${n}(...a);`).join('\n'),
};
await build({
  entryPoints: { login: path.join(src, 'screens/LoginScreen.jsx'), account: path.join(src, 'screens/AccountScreen.jsx') }, bundle: true, format: 'esm', platform: 'node', outdir: out, outExtension: { '.js': '.mjs' },
  loader: { '.js': 'jsx', '.jsx': 'jsx' }, external: ['react', 'react-dom'], logLevel: 'error', define: { 'import.meta.env.VITE_DEMO_HINT': '"false"' },
  plugins: [{ name: 'stubs', setup(b) {
    b.onResolve({ filter: /^(\.\.\/App|react-router-dom|\.\/ChangePinScreen|\.\.\/services\/api)$/ }, (a) => ({ path: a.path, namespace: 'stub' }));
    b.onLoad({ filter: /.*/, namespace: 'stub' }, (a) => ({ contents: stubs[a.path], loader: 'js' }));
  } }],
});
const dom = new JSDOM('<!doctype html><div id="root"></div>', { url: 'http://localhost/', pretendToBeVisual: true });
for (const k of ['window', 'document', 'navigator', 'HTMLElement', 'HTMLInputElement', 'Element', 'Node', 'MouseEvent', 'Event']) Object.defineProperty(globalThis, k, { value: dom.window[k], configurable: true, writable: true });
globalThis.IS_REACT_ACT_ENVIRONMENT = true; globalThis.requestAnimationFrame = (f) => setTimeout(f, 0);
const React = (await import('react')).default; const { act } = await import('react'); const { createRoot } = await import('react-dom/client');
const Login = (await import(pathToFileURL(path.join(out, 'login.mjs')).href)).default;
const Account = (await import(pathToFileURL(path.join(out, 'account.mjs')).href)).default;
const { CONSENT } = await import(pathToFileURL(path.join(src, 'services/consent.js')).href);

let n = 0; const check = (label, ok, extra = '') => { n += 1; console.log(`  ${ok ? 'OK  ' : 'FAIL'} ${label}${ok ? '' : '  ' + extra}`); if (!ok) process.exitCode = 1; };
const q = (sel) => document.querySelector(sel); const qa = (sel) => [...document.querySelectorAll(sel)];
const flush = async () => { await act(async () => { await new Promise((r) => setTimeout(r, 0)); }); };
const click = async (el) => { await act(async () => { el.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true })); }); await flush(); };
const type = async (el, value) => { await act(async () => { Object.getOwnPropertyDescriptor(dom.window.HTMLInputElement.prototype, 'value').set.call(el, value); el.dispatchEvent(new dom.window.Event('input', { bubbles: true })); }); };
let root;
const mount = async (Screen) => { document.body.innerHTML = '<div id="root"></div>'; root = createRoot(document.getElementById('root')); await act(async () => { root.render(React.createElement(Screen)); }); await flush(); };

console.log('the sign-up form');
const calls = []; globalThis.__auth = { setTeacher() {}, teacher: {}, logout() {} };
// like the real server: a NEW school's admin is given the school's join code, a teacher who JOINED is not
globalThis.__api = { registerTeacher: async (...a) => { calls.push(a); return a[3] ? { token: 't', teacher_id: 'x', role: 'teacher' } : { token: 't', teacher_id: 'x', role: 'school_admin', join_code: 'ABC234' }; }, setToken() {}, login: async () => ({}) };
await mount(Login);
await click(q('[data-testid="toggle-register"]'));
check('the sign-up form shows the consent block when no join code is typed (the school would be NEW)', !!q('[data-testid="consent-block"]'));
check('...with the statement in Hindi AND English, word for word the wording in services/consent.js', q('[data-testid="consent-hi"]').textContent === CONSENT.hi && q('[data-testid="consent-en"]').textContent === CONSENT.en);
check('...and an unticked checkbox that is large enough to tap (a 44 px row)', q('[data-testid="consent-check"]').checked === false && /min-height:\s*44px/.test(q('[data-testid="consent-check"]').closest('label').getAttribute('style')));
const fill = async () => { await type(q('[data-testid="phone"]'), '9876543210'); await type(q('[data-testid="school-code"]'), 'MP-9999'); await click(q('[data-testid="grade-grade_1"]')); await type(q('[data-testid="pin"]'), '7392'); await type(q('[data-testid="pin-confirm"]'), '7392'); };
await fill();
await click(q('[data-testid="register-submit"]'));
check('pressing Register WITHOUT ticking it is stopped on the screen, with a message in Hindi, and nothing is sent', calls.length === 0 && /पुष्टि/.test(q('[data-testid="login-error"]').textContent), q('[data-testid="login-error"]') && q('[data-testid="login-error"]').textContent);
await click(q('[data-testid="consent-check"]'));
check('ticking it ticks it', q('[data-testid="consent-check"]').checked === true);
await click(q('[data-testid="register-submit"]'));
check('now Register is sent, with the VERSION of the statement that was shown (v1)', calls.length === 1 && calls[0][5] === CONSENT.version && calls[0][3] === '' && calls[0][2] === 'MP-9999', JSON.stringify(calls));
check('the new school\'s admin is then shown the join code to share with her teachers', !!q('[data-testid="welcome"]') && q('[data-testid="join-code-shown"]').textContent === 'ABC234', document.body.textContent.slice(0, 120));
check('the version being sent is the one in services/consent.js (and so the one the server compares with its own)', CONSENT.version === 'v1');

console.log('\njoining a school that already exists');
calls.length = 0; await mount(Login);
await click(q('[data-testid="toggle-register"]')); await fill();
await type(q('[data-testid="join-code"]'), 'abc234');
check('typing a join code removes the consent block: the school confirmed it when it was created', !q('[data-testid="consent-block"]'));
await click(q('[data-testid="register-submit"]'));
check('Register is sent at once, with NO consent version', calls.length === 1 && calls[0][3] === 'ABC234' && calls[0][5] === null, JSON.stringify(calls));
await type(q('[data-testid="join-code"]'), '');
check('clearing the join code brings the consent block back', !!q('[data-testid="consent-block"]'));

console.log('\nthe admin panel');
globalThis.__auth = { teacher: { role: 'school_admin', school_code: 'MP-9999', enrolled_grades: ['grade_1'] }, logout() {}, setTeacher() {} };
let school = { school_code: 'MP-9999', join_code: 'ABC234', consent: null, consent_text: { version: 'v1' } };
const recorded = []; let sure = true; dom.window.confirm = (m) => { recorded.push(m); return sure; };
globalThis.__api = { adminSchool: async () => ({ ...school }), adminTeachers: async () => ({ teachers: [] }), adminRecordConsent: async (v) => { recorded.push(['record', v]); school = { ...school, consent: { version: v, attested_at: '2026-10-26T09:00:00+00:00', by: '••••1234', demo: false } }; return {}; }, adminRotateJoinCode: async () => ({}), adminResetPin: async () => ({}), adminUnlock: async () => ({}) };
await mount(Account);
check('a school with no confirmation shows a warning and a button to confirm', !!q('[data-testid="consent-missing"]') && !!q('[data-testid="consent-confirm"]') && !q('[data-testid="consent-recorded"]'));
sure = false; await click(q('[data-testid="consent-confirm"]'));
check('the button first asks, showing the WHOLE statement in both languages; if she says no, nothing is recorded', recorded.length === 1 && recorded[0].includes(CONSENT.hi) && recorded[0].includes(CONSENT.en) && !recorded.some((x) => Array.isArray(x)), JSON.stringify(recorded).slice(0, 200));
sure = true; recorded.length = 0; await click(q('[data-testid="consent-confirm"]')); await flush();
check('if she says yes, the version she read is sent, and the panel then shows it as confirmed, with the date', recorded.some((x) => Array.isArray(x) && x[1] === 'v1') && !!q('[data-testid="consent-recorded"]') && /26\/10\/2026|10\/26\/2026|26 Oct/.test(q('[data-testid="consent-recorded"]').textContent) && !q('[data-testid="consent-missing"]'), q('[data-testid="consent-row"]') && q('[data-testid="consent-row"]').textContent);
school = { ...school, consent: { version: 'demo', attested_at: '2026-10-26T09:00:00+00:00', by: null, demo: true } };
await mount(Account);
check('a demonstration school says that every child in it is fictional, and offers no button', /Demonstration school/.test(q('[data-testid="consent-recorded"]').textContent) && !q('[data-testid="consent-confirm"]'));
globalThis.__auth = { teacher: { role: 'teacher', school_code: 'MP-9999', enrolled_grades: ['grade_1'] }, logout() {}, setTeacher() {} };
await mount(Account);
check('an ordinary teacher sees no admin panel and so no consent row', !q('[data-testid="admin-panel"]') && !q('[data-testid="consent-row"]'));

console.log(`\n${process.exitCode ? 'SOME CHECKS FAILED' : 'OK: ' + n + ' checks: a new school needs the confirmation, a join needs none, and an older school\'s admin can confirm'}`);
