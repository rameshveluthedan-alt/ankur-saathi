// The demo accounts must say the SAME thing everywhere a reviewer can meet them: the login screen, the access guide, the evaluator guide and the scripts that create them.
//
// Found on 26 Oct: the test-school admin was in the guides and in the cloud but never on the sign-in screen, so a reviewer looking for "every role" did not find it.
// Since 27 Oct accounts are named by EMPLOYEE CODE (six letters or digits) and the list is one teacher, one school leader and one practice account: this test checks each of them.
//
//     cd pwa
//     node tests/demo_accounts.test.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(here, '..', '..');
const read = (p) => fs.readFileSync(path.join(root, p), 'utf8');
let n = 0;
const check = (label, ok, extra = '') => { n += 1; console.log(`  ${ok ? 'OK  ' : 'FAIL'} ${label}${ok ? '' : '  ' + extra}`); if (!ok) process.exitCode = 1; };

const loginSrc = read('pwa/src/screens/LoginScreen.jsx');
const rows = (text) => [...text.matchAll(/\|\s*`?([A-Z]{3}\d{3})`?\s*\|\s*`?(\d{4})`?\s*\|/g)].map((m) => [m[1], m[2]]);
const guide = rows(read('docs/DEMO_ACCESS.md'));
const evaluator = rows(read('docs/EVALUATOR_GUIDE.md'));
const screen = new Map([...loginSrc.matchAll(/code:\s*'([A-Z0-9]{6})'\s*,\s*password:\s*'(\d{4})'/g)].map((m) => [m[1], m[2]]));
const py = read('scripts/auth_admin.py');
const defaults = { teacher: (py.match(/DEMO_PIN",\s*"(\d+)"/) || [])[1], leader: (py.match(/DEMO_ADMIN_PIN",\s*"(\d+)"/) || [])[1], practice: (py.match(/DEMO_PRACTICE_PIN",\s*"(\d+)"/) || [])[1] };
const names = read('scripts/demo_accounts.py');
const named = { teacher: (names.match(/DEMO_TEACHER\s*=\s*"(\w+)"/) || [])[1], leader: (names.match(/LEADER\s*=\s*"(\w+)"/) || [])[1], practice: (names.match(/PRACTICE\s*=\s*"(\w+)"/) || [])[1] };

check(`the access guide publishes single-code accounts (${guide.length} found)`, guide.length >= 3, JSON.stringify(guide));
check(`the login screen lists at least a teacher, a school leader and the practice account (${screen.size} found)`, screen.size >= 3, JSON.stringify([...screen]));
for (const [code, pw] of guide) check(`${code} is on the login screen with password ${pw}`, screen.get(code) === pw, `screen has: ${screen.get(code)}`);
check('the screen lists no account the guide does not publish (a stale hint would send a reviewer to a wrong password)', [...screen.keys()].every((c) => guide.some(([g]) => g === c)), [...screen.keys()].join(','));
for (const [code, pw] of evaluator) check(`the evaluator guide agrees: ${code} has password ${pw} on the screen`, screen.get(code) === pw, `screen has: ${screen.get(code)}`);
check('the evaluator guide names at least the teacher, the school leader and the practice account', ['teacher', 'leader', 'practice'].every((k) => evaluator.some(([c]) => c === named[k])), JSON.stringify(evaluator));
for (const k of ['teacher', 'leader', 'practice']) {
  check(`the ${k} is ${named[k]} in scripts/demo_accounts.py and has the same password (${defaults[k]}) as the script sets and the screen shows`, !!named[k] && screen.get(named[k]) === defaults[k], `script ${named[k]}/${defaults[k]}, screen ${screen.get(named[k])}`);
}
check('every code on the screen is three letters and three digits, as the guides say', [...screen.keys()].every((c) => /^[A-Z]{3}\d{3}$/.test(c)));
check('no phone number is left on the login screen (accounts are named by employee code)', !/\b[6-9]\d{9}\b/.test(loginSrc));
check('the login screen has no registration, no join code and no consent tick: the school leader makes the accounts', !/registerTeacher|join-code|toggle-register|consent-block|GRADE_CHOICES/.test(loginSrc));
console.log(`\n${process.exitCode ? 'SOME CHECKS FAILED' : 'OK: ' + n + ' checks: the screen, the guides and the scripts agree on every demo account'}`);
