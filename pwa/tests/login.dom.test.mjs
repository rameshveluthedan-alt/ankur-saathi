// The REAL sign-in screen in a simulated browser, with a fake server: employee code and password, role cards for the reviewers, no registration, no join code.
// A reviewer must be able to sign in without reading a guide: tap a card, press Login.
//
//     cd pwa
//     node tests/login.dom.test.mjs        (needs jsdom, like plan_screen.dom.test.mjs; without it the test says so and stops without failing)
import fs from 'node:fs'; import path from 'node:path'; import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
let JSDOM;
try { ({ JSDOM } = await import('jsdom')); } catch (e) { console.log('SKIPPED: jsdom is not installed. To run this test: cd pwa; npm install --save-dev jsdom@24'); process.exit(0); }
const here = path.dirname(fileURLToPath(import.meta.url)); const src = path.join(here, '..', 'src'); const out = path.join(here, `.tmp-login-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));

const stubs = {
  '../App': 'export const useAuth = () => globalThis.__auth;',
  '../services/api': 'export const login = (...a) => globalThis.__api.login(...a);\nexport const setToken = (...a) => globalThis.__api.setToken(...a);',
};
await build({
  entryPoints: { login: path.join(src, 'screens/LoginScreen.jsx') }, bundle: true, format: 'esm', platform: 'node', outdir: out, outExtension: { '.js': '.mjs' },
  loader: { '.js': 'jsx', '.jsx': 'jsx' }, external: ['react', 'react-dom'], logLevel: 'error', define: { 'import.meta.env.VITE_DEMO_HINT': '"true"' },
  plugins: [{ name: 'stubs', setup(b) {
    b.onResolve({ filter: /^(\.\.\/App|\.\.\/services\/api)$/ }, (a) => ({ path: a.path, namespace: 'stub' }));
    b.onLoad({ filter: /.*/, namespace: 'stub' }, (a) => ({ contents: stubs[a.path], loader: 'js' }));
  } }],
});
const dom = new JSDOM('<!doctype html><div id="root"></div>', { url: 'http://localhost/', pretendToBeVisual: true });
for (const k of ['window', 'document', 'navigator', 'HTMLElement', 'HTMLInputElement', 'Element', 'Node', 'MouseEvent', 'KeyboardEvent', 'Event']) Object.defineProperty(globalThis, k, { value: dom.window[k], configurable: true, writable: true });
globalThis.IS_REACT_ACT_ENVIRONMENT = true; globalThis.requestAnimationFrame = (f) => setTimeout(f, 0);
const React = (await import('react')).default; const { act } = await import('react'); const { createRoot } = await import('react-dom/client');
const Login = (await import(pathToFileURL(path.join(out, 'login.mjs')).href)).default;

let n = 0; const check = (label, ok, extra = '') => { n += 1; console.log(`  ${ok ? 'OK  ' : 'FAIL'} ${label}${ok ? '' : '  ' + extra}`); if (!ok) process.exitCode = 1; };
const q = (sel) => document.querySelector(sel); const qa = (sel) => [...document.querySelectorAll(sel)];
const flush = async () => { await act(async () => { await new Promise((r) => setTimeout(r, 0)); }); };
const click = async (el) => { await act(async () => { el.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true })); }); await flush(); };
const type = async (el, value) => { await act(async () => { Object.getOwnPropertyDescriptor(dom.window.HTMLInputElement.prototype, 'value').set.call(el, value); el.dispatchEvent(new dom.window.Event('input', { bubbles: true })); }); };
const press = async (el, key) => { await act(async () => { el.dispatchEvent(new dom.window.KeyboardEvent('keydown', { key, bubbles: true })); }); await flush(); };
let root;
const mount = async () => { document.body.innerHTML = '<div id="root"></div>'; root = createRoot(document.getElementById('root')); await act(async () => { root.render(React.createElement(Login)); }); await flush(); };

const calls = []; const tokens = []; const profiles = [];
globalThis.__auth = { setTeacher: (p) => profiles.push(p), teacher: null, logout() {} };
globalThis.__api = {
  login: async (c, p) => { calls.push([c, p]); if (p === 'wrong1') throw new Error('The employee code or password is not right.'); return { token: 'tok-' + c, teacher_id: 'x', role: c.startsWith('MPA') ? 'school_admin' : 'teacher', employee_code: c, join_code: null, consent_needed: false }; },
  setToken: (t) => tokens.push(t),
};

console.log('what a person sees');
await mount();
check('an employee code field and a password field, labelled in Hindi and English', !!q('[data-testid="employee-code"]') && !!q('[data-testid="password"]') && /कर्मचारी कोड/.test(q('label[for="employee-code"]').textContent) && q('label[for="employee-code"] .en').textContent === 'Employee code' && /पासवर्ड/.test(q('label[for="password"]').textContent) && q('label[for="password"] .en').textContent === 'Password');
check('no phone number field, no registration, no join code, no school code, no consent tick: the school leader makes the accounts', !['phone', 'toggle-register', 'register-submit', 'join-code', 'school-code', 'consent-block', 'consent-check', 'pin'].some((id) => q(`[data-testid="${id}"]`)) && !/(?<!class )Register|पंजीकरण|जॉइन|join code/i.test(document.body.textContent));  // "class register" (the file the teacher uploads, in How Ankur Saathi works) is not a sign-up
check('it says who makes the account ("आपका खाता आपके स्कूल लीडर द्वारा बनाया जाता है।"), and who to ask when a password is forgotten', /Your account is created by your school leader\./.test(document.body.textContent) && /आपका खाता आपके स्कूल लीडर द्वारा बनाया जाता है।/.test(document.body.textContent) && /Forgot your password\? Ask your school leader/.test(document.body.textContent));
check('the code field helps a phone keyboard: capitals, no auto-correct, 6 characters at most', q('[data-testid="employee-code"]').getAttribute('autocapitalize') === 'characters' && q('[data-testid="employee-code"]').getAttribute('maxlength') === '6' && q('[data-testid="employee-code"]').getAttribute('autocorrect') === 'off');
check('the password is hidden by default, and its field accepts a normal keyboard (not numbers only)', q('[data-testid="password"]').type === 'password' && q('[data-testid="password"]').getAttribute('inputmode') !== 'numeric');

console.log('\nthe reviewers\' cards');
const hint = q('[data-testid="demo-hint"]');
const cards = qa('.demo-card, .demo-group');
check('the cards follow the rule of thumb, in order: 5 minutes (the shared demo teacher), 30 minutes (a test teacher of your own), the school leader', cards.map((c) => c.dataset.testid).join(',') === 'demo-MPT101,demo-testers,demo-MPA101', cards.map((c) => c.dataset.testid).join(','));
check('the 5-minute card is the shared demo teacher with the recorded story: first, the biggest, and it says it is shared and reset every night', q('[data-testid="demo-MPT101"]').classList.contains('demo-card-main') && /5 मिनट/.test(q('[data-testid="demo-MPT101"]').textContent) && /5 minutes: see the recorded story/.test(q('[data-testid="demo-MPT101"]').textContent) && /reset every night/.test(q('[data-testid="demo-MPT101"]').textContent) && /MPT101 · पासवर्ड 4826/.test(q('[data-testid="demo-MPT101"]').textContent));
const testersCard = q('[data-testid="demo-testers"]');
check('the 30-minute card offers the five test teachers as chips, says each reviewer picks a different one, and gives the one password', ['MPT102', 'MPT103', 'MPT104', 'MPT105', 'MPT106'].every((c) => testersCard.querySelector(`[data-testid="demo-${c}"]`)) && /हर समीक्षक अलग कोड चुनें/.test(testersCard.textContent) && /Each reviewer picks a different code/.test(testersCard.textContent) && /पासवर्ड 4826/.test(testersCard.textContent) && /24 बच्चे/.test(testersCard.textContent));
check('the school leader card says what a leader can really do (no "register schools": the department loads schools), with the code and password', /School leader: manage the school's accounts/.test(q('[data-testid="demo-MPA101"]').textContent) && /Teaches too; views teachers' accounts, unlocks them and resets passwords\./.test(q('[data-testid="demo-MPA101"]').textContent) && !/Register schools|स्कूल पंजीकृत/.test(q('[data-testid="demo-MPA101"]').textContent) && /MPA101 · पासवर्ड 7351/.test(q('[data-testid="demo-MPA101"]').textContent));
check('the practice account is offered too ("try changing a password")', !!q('[data-testid="demo-MPT199"]') && /Try changing a password/.test(hint.textContent) && /MPT199 · पासवर्ड 3917/.test(hint.textContent));
check('each card is a large tap target (a button, at least 56 px high) and each chip at least 44 px', qa('.demo-card').every((b) => b.tagName === 'BUTTON' && /min-height:\s*56px/.test(b.getAttribute('style'))) && qa('.demo-chip').length === 5 && qa('.demo-chip').every((b) => b.tagName === 'BUTTON' && /min-height:\s*44px/.test(b.getAttribute('style'))));
check('each card LOOKS tappable: the card style (pointer, lift on hover) and a "भरें ›" (Tap to fill) cue at its end; nothing is chosen yet', ['MPT101', 'MPA101'].every((c) => q(`[data-testid="demo-${c}"]`).classList.contains('demo-card') && /भरें ›/.test(q(`[data-testid="demo-go-${c}"]`).textContent) && /Tap to fill/.test(q(`[data-testid="demo-go-${c}"]`).textContent) && q(`[data-testid="demo-${c}"]`).getAttribute('aria-pressed') === 'false'));
await click(q('[data-testid="demo-MPT101"]'));
check('tapping the teacher card fills in MPT101 and 4826', q('[data-testid="employee-code"]').value === 'MPT101' && q('[data-testid="password"]').value === '4826');
check('the tapped card shows it was chosen ("✓ भर गया", pressed, highlighted); the other card does not', q('[data-testid="demo-MPT101"]').getAttribute('aria-pressed') === 'true' && q('[data-testid="demo-MPT101"]').classList.contains('selected') && /✓ भर गया/.test(q('[data-testid="demo-go-MPT101"]').textContent) && q('[data-testid="demo-MPA101"]').getAttribute('aria-pressed') === 'false' && /भरें ›/.test(q('[data-testid="demo-go-MPA101"]').textContent));
await click(q('[data-testid="demo-MPA101"]'));
check('tapping the school leader card fills in MPA101 and 7351', q('[data-testid="employee-code"]').value === 'MPA101' && q('[data-testid="password"]').value === '7351');
await click(q('[data-testid="demo-MPT104"]'));
check('tapping a test-teacher chip fills in that code and 4826; only that chip shows it is chosen', q('[data-testid="employee-code"]').value === 'MPT104' && q('[data-testid="password"]').value === '4826' && q('[data-testid="demo-MPT104"]').getAttribute('aria-pressed') === 'true' && /✓ MPT104/.test(q('[data-testid="demo-MPT104"]').textContent) && qa('.demo-chip.selected').length === 1 && q('[data-testid="demo-MPT101"]').getAttribute('aria-pressed') === 'false');
await click(q('[data-testid="demo-MPT199"]'));
check('tapping the practice link fills in MPT199 and 3917', q('[data-testid="employee-code"]').value === 'MPT199' && q('[data-testid="password"]').value === '3917');

console.log('\ntyping');
await mount();
await type(q('[data-testid="employee-code"]'), 'mpt101');
check('small letters become capitals as they are typed', q('[data-testid="employee-code"]').value === 'MPT101');
await type(q('[data-testid="employee-code"]'), 'mp-t 1012x');
check('anything that is not a letter or digit is dropped, and the code stops at 6 characters', q('[data-testid="employee-code"]').value === 'MPT101', q('[data-testid="employee-code"]').value);
await type(q('[data-testid="password"]'), 'k7m4qx');
check('the password is kept exactly as typed (small letters stay small)', q('[data-testid="password"]').value === 'k7m4qx');
await type(q('[data-testid="password"]'), 'abcdefghijklmnopq');
check('the password stops at 12 characters', q('[data-testid="password"]').value.length === 12);
await click(q('[data-testid="toggle-password"]'));
check('"Show" reveals the password and the button now says "Hide"; pressing it again hides it', q('[data-testid="password"]').type === 'text' && /Hide/.test(q('[data-testid="toggle-password"]').textContent) && q('[data-testid="toggle-password"]').getAttribute('aria-pressed') === 'true');
await click(q('[data-testid="toggle-password"]'));
check('pressing it again hides the password again', q('[data-testid="password"]').type === 'password' && /Show|दिखाएँ/.test(q('[data-testid="toggle-password"]').textContent));

console.log('\nsigning in');
await mount(); calls.length = 0; profiles.length = 0; tokens.length = 0;
await click(q('[data-testid="login-submit"]'));
check('pressing Login with nothing typed is stopped on the screen, in both languages, and nothing is sent', calls.length === 0 && /Enter your 6-character employee code and your password/.test(q('[data-testid="login-error"]').textContent) && q('[data-testid="login-error"]').getAttribute('role') === 'alert');
await type(q('[data-testid="employee-code"]'), 'MPT10');
await type(q('[data-testid="password"]'), '4826');
await click(q('[data-testid="login-submit"]'));
check('a code shorter than 6 is stopped too', calls.length === 0 && !!q('[data-testid="login-error"]'));
await click(q('[data-testid="demo-MPT101"]'));
check('tapping a card clears an earlier error', !q('[data-testid="login-error"]'));
await click(q('[data-testid="login-submit"]'));
check('Login sends the code in capitals and the password as typed', calls.length === 1 && calls[0][0] === 'MPT101' && calls[0][1] === '4826', JSON.stringify(calls));
check('the session token is kept, and the app is given the profile WITHOUT the token', tokens.length === 1 && tokens[0] === 'tok-MPT101' && profiles.length === 1 && profiles[0].employee_code === 'MPT101' && !('token' in profiles[0]) && !('join_code' in profiles[0]), JSON.stringify(profiles));
await mount(); calls.length = 0; profiles.length = 0;
await type(q('[data-testid="employee-code"]'), 'MPA101'); await type(q('[data-testid="password"]'), '7351');
await press(q('[data-testid="password"]'), 'Enter');
check('Enter in the password field signs in too', calls.length === 1 && calls[0][0] === 'MPA101' && profiles.length === 1 && profiles[0].role === 'school_admin');
await mount(); calls.length = 0; profiles.length = 0;
await type(q('[data-testid="employee-code"]'), 'MPT101'); await type(q('[data-testid="password"]'), 'wrong1');
await click(q('[data-testid="login-submit"]'));
check('a wrong password shows the server\'s own words and does not sign in', /employee code or password is not right/.test(q('[data-testid="login-error"]').textContent) && profiles.length === 0);
console.log(`\n${process.exitCode ? 'SOME CHECKS FAILED' : 'OK: ' + n + ' checks: a reviewer signs in by tapping a card and pressing Login, and there is nothing to register'}`);
