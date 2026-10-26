// Every account the access guide publishes with ONE phone number must be on the login screen's list of demo accounts, with the same PIN.
//
// Found on 26 Oct: the test-school admin (9000000100) was in docs/DEMO_ACCESS.md and the evaluator guide, and the cloud had the account, but the sign-in screen's list of
// demo accounts never got it, so a reviewer looking for "every role" on the screen did not find it. Ranges ("9000000101 to 9000000105") are covered by one example on the screen.
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

const guide = [...read('docs/DEMO_ACCESS.md').matchAll(/\|\s*(9\d{9})\s*\|\s*(\d{4})\s*\|/g)].map((m) => [m[1], m[2]]);
const screen = new Map([...read('pwa/src/screens/LoginScreen.jsx').matchAll(/\[\s*'(9\d{9})'\s*,\s*'(\d{4})'\s*,/g)].map((m) => [m[1], m[2]]));
const evaluator = [...read('docs/EVALUATOR_GUIDE.md').matchAll(/\|\s*(9\d{9})\s*\|\s*(\d{4})\s*\|/g)].map((m) => [m[1], m[2]]);

check(`the access guide publishes single-number accounts (${guide.length} found)`, guide.length >= 4, JSON.stringify(guide));
for (const [phone, pin] of guide) check(`${phone} is on the login screen with PIN ${pin}`, screen.get(phone) === pin, `screen has: ${screen.get(phone)}`);
check('the screen lists no account the guide does not publish (a stale hint would send a reviewer to a wrong PIN)', [...screen.keys()].every((p) => guide.some(([g]) => g === p) || /^90000001(0[1-5])$/.test(p)), [...screen.keys()].join(','));
for (const [phone, pin] of evaluator.filter(([p]) => /^(9876543210|9876500000|9000000100|9000000199)$/.test(p))) check(`the evaluator guide agrees: ${phone} has PIN ${pin} on the screen`, screen.get(phone) === pin, `screen has: ${screen.get(phone)}`);
console.log(`\n${process.exitCode ? 'SOME CHECKS FAILED' : 'OK: ' + n + ' checks: every published single-number account is on the login screen with its PIN'}`);
