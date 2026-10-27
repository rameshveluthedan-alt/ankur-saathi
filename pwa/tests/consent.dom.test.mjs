// The REAL one-time confirmation screen of the school leader, and the REAL Profile page with the leader's panel, in a simulated browser with a fake server.
// The school leader confirms the consent statement once, at the first sign-in of a school that has none on record; teachers are never asked; the Profile shows the state and lets the leader
// confirm later; accounts are shown by employee code, passwords are "passwords", and there is no join code.
//
//     cd pwa
//     node tests/consent.dom.test.mjs        (needs jsdom, like plan_screen.dom.test.mjs; without it the test says so and stops without failing)
import fs from 'node:fs'; import path from 'node:path'; import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
let JSDOM;
try { ({ JSDOM } = await import('jsdom')); } catch (e) { console.log('SKIPPED: jsdom is not installed. To run this test: cd pwa; npm install --save-dev jsdom@24'); process.exit(0); }
const here = path.dirname(fileURLToPath(import.meta.url)); const src = path.join(here, '..', 'src'); const out = path.join(here, `.tmp-consent-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));

const API = ['adminSchool', 'adminTeachers', 'adminResetPin', 'adminUnlock', 'adminRecordConsent'];
const stubs = {
  '../App': 'export const useAuth = () => globalThis.__auth;',
  'react-router-dom': 'export const useNavigate = () => () => {};',
  './ChangePinScreen': 'export const PinChangeForm = () => null;',
  '../services/api': API.map((n) => `export const ${n} = (...a) => globalThis.__api.${n}(...a);`).join('\n'),
};
await build({
  entryPoints: { gate: path.join(src, 'screens/ConsentGate.jsx'), account: path.join(src, 'screens/AccountScreen.jsx') }, bundle: true, format: 'esm', platform: 'node', outdir: out, outExtension: { '.js': '.mjs' },
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
const Gate = (await import(pathToFileURL(path.join(out, 'gate.mjs')).href)).default;
const Account = (await import(pathToFileURL(path.join(out, 'account.mjs')).href)).default;
const { CONSENT } = await import(pathToFileURL(path.join(src, 'services/consent.js')).href);

let n = 0; const check = (label, ok, extra = '') => { n += 1; console.log(`  ${ok ? 'OK  ' : 'FAIL'} ${label}${ok ? '' : '  ' + extra}`); if (!ok) process.exitCode = 1; };
const q = (sel) => document.querySelector(sel); const qa = (sel) => [...document.querySelectorAll(sel)];
const flush = async () => { await act(async () => { await new Promise((r) => setTimeout(r, 0)); }); };
const click = async (el) => { await act(async () => { el.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true })); }); await flush(); };
let root;
const mount = async (Screen) => { document.body.innerHTML = '<div id="root"></div>'; root = createRoot(document.getElementById('root')); await act(async () => { root.render(React.createElement(Screen)); }); await flush(); await flush(); };

console.log('the school leader\'s one-time confirmation');
const set = []; let loggedOut = 0; const recorded = [];
const leader = { teacher_id: 'L1', role: 'school_admin', employee_code: 'MPA777', school_code: 'MP-1234', enrolled_grades: ['grade_1'], consent_needed: true };
globalThis.__auth = { teacher: leader, setTeacher: (t) => set.push(t), logout: () => { loggedOut += 1; } };
let fail = false;
globalThis.__api = { adminRecordConsent: async (v) => { if (fail) throw new Error('The wording has changed. Reload the page and read it again.'); recorded.push(v); return {}; } };
await mount(Gate);
check('the statement is shown in Hindi AND English, word for word the wording in services/consent.js', q('[data-testid="consent-hi"]').textContent === CONSENT.hi && q('[data-testid="consent-en"]').textContent === CONSENT.en);
check('it tells the leader why she sees it and that it is asked once, in both languages', /आप इस स्कूल के लीडर हैं/.test(q('[data-testid="consent-gate"]').textContent) && /confirmation once/.test(q('[data-testid="consent-gate"]').textContent));
check('the box is unticked and Continue is switched off until it is ticked', q('[data-testid="consent-check"]').checked === false && q('[data-testid="consent-continue"]').disabled === true);
check('the tick has a large tap target (a 44 px row)', /min-height:\s*44px/.test(q('[data-testid="consent-check"]').closest('label').getAttribute('style')));
await click(q('[data-testid="consent-continue"]'));
check('pressing the disabled button does nothing', recorded.length === 0 && set.length === 0);
await click(q('[data-testid="consent-check"]'));
check('ticking the box switches Continue on', q('[data-testid="consent-check"]').checked === true && q('[data-testid="consent-continue"]').disabled === false);
await click(q('[data-testid="consent-continue"]'));
check('Continue records the version she read (v1) exactly once', recorded.length === 1 && recorded[0] === CONSENT.version && CONSENT.version === 'v1', JSON.stringify(recorded));
check('and the app is told consent_needed is now false, with the rest of her profile unchanged (so she goes on to the app)', set.length === 1 && set[0].consent_needed === false && set[0].employee_code === 'MPA777' && set[0].role === 'school_admin' && set[0].school_code === 'MP-1234', JSON.stringify(set));
set.length = 0; recorded.length = 0; fail = true;
await mount(Gate); await click(q('[data-testid="consent-check"]')); await click(q('[data-testid="consent-continue"]'));
check('if the server refuses (an old wording), the reason is shown, she is NOT let through, and she can try again', /wording has changed/.test(q('[data-testid="consent-error"]').textContent) && q('[data-testid="consent-error"]').getAttribute('role') === 'alert' && set.length === 0 && q('[data-testid="consent-continue"]').disabled === false);
await click([...document.querySelectorAll('button')].find((b) => /Log out/.test(b.textContent)));
check('she can log out instead', loggedOut === 1);

console.log('\nthe Profile page of the school leader');
let school = { school_code: 'MP-1234', consent: null, consent_text: { version: 'v1' } };
const asked = []; const calls = []; let sure = true; dom.window.confirm = (m) => { asked.push(m); return sure; };
const rows = [
  { teacher_id: 'L1', code: 'MPA777', role: 'school_admin', children: 0, has_pin: true, must_change_pin: false, locked: false, pin_fixed: false, is_demo: false, is_you: true },
  { teacher_id: 'T1', code: 'MPT201', role: 'teacher', children: 24, has_pin: true, must_change_pin: false, locked: false, pin_fixed: false, is_demo: false, is_you: false },
  { teacher_id: 'T2', code: 'MPT202', role: 'teacher', children: 10, has_pin: true, must_change_pin: true, locked: true, pin_fixed: false, is_demo: false, is_you: false },
  { teacher_id: 'T3', code: 'MPT101', role: 'teacher', children: 30, has_pin: true, must_change_pin: false, locked: false, pin_fixed: true, is_demo: true, is_you: false },
];
globalThis.__auth = { teacher: { ...leader, consent_needed: false }, setTeacher() {}, logout() {} };
globalThis.__api = {
  adminSchool: async () => ({ ...school }), adminTeachers: async () => ({ teachers: rows.map((r) => ({ ...r })) }),
  adminRecordConsent: async (v) => { calls.push(['consent', v]); school = { ...school, consent: { version: v, attested_at: '2026-10-27T09:00:00+00:00', by: 'MPA777', demo: false } }; return {}; },
  adminResetPin: async (id) => { calls.push(['reset', id]); return { temporary_pin: '482901' }; }, adminUnlock: async (id) => { calls.push(['unlock', id]); return {} },
};
await mount(Account);
const panel = q('[data-testid="admin-panel"]');
check('the page shows her own employee code, her school and her role as "school leader"', q('[data-testid="my-code"]').textContent === 'MPA777' && /MP-1234/.test(q('[data-testid="account-info"]').textContent) && /स्कूल लीडर\s*School leader/.test(q('[data-testid="account-info"]').textContent));
check('the panel is titled "school leader" and says she never sees a child\'s data', /स्कूल लीडर\s*School leader/.test(panel.textContent) && /never see any child/.test(panel.textContent));
check('there is NO join code and no way to make one', !q('[data-testid="join-code-value"]') && !q('[data-testid="rotate-join"]') && !/जॉइन|[Jj]oin code/.test(document.body.textContent));
check('every account is shown by its employee code, and her own is marked', qa('[data-testid="teacher-code"]').map((e) => e.textContent).join(',') === 'MPA777,MPT201,MPT202,MPT101' && /आप\s*\/ you/.test(qa('[data-testid="teacher-row"]')[0].textContent));
check('each role is named: the leader as "school leader", the others as teachers; a fixed demo account says so', /स्कूल लीडर/.test(qa('[data-testid="teacher-row"]')[0].textContent) && /शिक्षक/.test(qa('[data-testid="teacher-row"]')[1].textContent) && /पासवर्ड स्थिर\s*fixed demo password/.test(qa('[data-testid="teacher-row"]')[3].textContent));
check('a locked account shows "locked", "new password pending" and an Unlock button; her own row has no Reset', /बंद\s*locked/.test(qa('[data-testid="teacher-row"]')[2].textContent) && /नया पासवर्ड बाकी/.test(qa('[data-testid="teacher-row"]')[2].textContent) && !!q('[data-testid="unlock-T2"]') && !q('[data-testid="reset-L1"]'));
check('the words "PIN" and "पिन" appear nowhere on the page: it is a password everywhere', !/\bPIN\b|पिन/.test(document.body.textContent), (document.body.textContent.match(/.{20}(\bPIN\b|पिन).{20}/) || [''])[0]);
sure = false; await click(q('[data-testid="reset-T1"]'));
check('Reset first asks, naming the account by its code; if she says no, nothing happens', asked.length === 1 && /MPT201/.test(asked[0]) && /पासवर्ड रीसेट/.test(asked[0]) && !calls.length);
sure = true; await click(q('[data-testid="reset-T1"]'));
check('if she says yes, the temporary PASSWORD is shown once, with the account it is for and what it can do', calls.some((c) => c[0] === 'reset' && c[1] === 'T1') && q('[data-testid="temp-pin-value"]').textContent === '482901' && /MPT201/.test(q('[data-testid="temp-pin"]').textContent) && /Temporary password, shown once/.test(q('[data-testid="temp-pin"]').textContent) && /choose a new password/.test(q('[data-testid="temp-pin"]').textContent));
await click(q('[data-testid="unlock-T2"]'));
check('Unlock calls the server for that account', calls.some((c) => c[0] === 'unlock' && c[1] === 'T2'));
check('a school with no confirmation shows a warning and a button to confirm', !!q('[data-testid="consent-missing"]') && !!q('[data-testid="consent-confirm"]') && !q('[data-testid="consent-recorded"]'));
sure = false; asked.length = 0; await click(q('[data-testid="consent-confirm"]'));
check('the button first shows the WHOLE statement in both languages; if she says no, nothing is recorded', asked.length === 1 && asked[0].includes(CONSENT.hi) && asked[0].includes(CONSENT.en) && !calls.some((c) => c[0] === 'consent'));
sure = true; await click(q('[data-testid="consent-confirm"]')); await flush();
check('if she says yes, the version she read is sent, and the panel then shows it as confirmed, with the date', calls.some((c) => c[0] === 'consent' && c[1] === 'v1') && !!q('[data-testid="consent-recorded"]') && /27\/10\/2026|10\/27\/2026|27 Oct/.test(q('[data-testid="consent-recorded"]').textContent) && !q('[data-testid="consent-missing"]'), q('[data-testid="consent-row"]') && q('[data-testid="consent-row"]').textContent);
school = { ...school, consent: { version: 'demo', attested_at: '2026-10-27T09:00:00+00:00', by: null, demo: true } };
await mount(Account);
check('a demonstration school says that every child in it is fictional, and offers no button', /Demonstration school/.test(q('[data-testid="consent-recorded"]').textContent) && !q('[data-testid="consent-confirm"]'));
globalThis.__auth = { teacher: { role: 'teacher', employee_code: 'MPT201', school_code: 'MP-1234', enrolled_grades: ['grade_1'] }, setTeacher() {}, logout() {} };
await mount(Account);
check('an ordinary teacher sees her code and her role, and no leader panel at all', q('[data-testid="my-code"]').textContent === 'MPT201' && /शिक्षक\s*Teacher/.test(q('[data-testid="account-info"]').textContent) && !q('[data-testid="admin-panel"]') && !q('[data-testid="consent-row"]'));
console.log(`\n${process.exitCode ? 'SOME CHECKS FAILED' : 'OK: ' + n + ' checks: the leader confirms once, sees her teachers by code, and there is no join code and no PIN anywhere'}`);
