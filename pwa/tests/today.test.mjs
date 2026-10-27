// "Today" is the phone's LOCAL date, not the UTC date (services/today.js). No browser and no server.
//
//     cd pwa
//     node tests/today.test.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

process.env.TZ = 'Asia/Kolkata';         // the teachers' time zone: UTC + 5:30
const here = path.dirname(fileURLToPath(import.meta.url));
const src = path.join(here, '..', 'src');
const { localToday } = await import(pathToFileURL(path.join(src, 'services', 'today.js')).href);

let n = 0;
const check = (label, fn) => { fn(); n += 1; console.log(`  OK  ${label}`); };

check('at 01:30 in India (still the previous day in UTC) today is the Indian date, not yesterday', () => {
  const night = new Date('2026-10-27T20:00:00Z');          // 28 Oct, 01:30 IST
  assert.equal(night.toISOString().slice(0, 10), '2026-10-27', 'the old way gave yesterday');
  assert.equal(localToday(night), '2026-10-28');
});
check('in the afternoon both agree', () => {
  assert.equal(localToday(new Date('2026-10-28T09:00:00Z')), '2026-10-28');
});
check('just before midnight in India it is still the same day', () => {
  assert.equal(localToday(new Date('2026-10-28T18:29:00Z')), '2026-10-28');      // 23:59 IST
});
check('months and days are always two digits (the server reads YYYY-MM-DD)', () => {
  assert.equal(localToday(new Date('2026-02-03T06:00:00Z')), '2026-02-03');
});
check('no screen computes today from the UTC date any more', () => {
  const files = [];
  const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).forEach((e) => (e.isDirectory() ? walk(path.join(d, e.name)) : /\.jsx?$/.test(e.name) && files.push(path.join(d, e.name))));
  walk(src);
  const bad = files.filter((f) => /toISOString\(\)\.(split|slice)/.test(fs.readFileSync(f, 'utf8')));
  assert.deepEqual(bad.map((f) => path.relative(src, f)), []);
});

console.log(`\nOK: ${n} checks: "today" is the phone's own date, so nothing made before 05:30 goes to yesterday`);
