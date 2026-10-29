// What a tap on a bottom tab does (found on the click-through: tapping the Plan tab on the Plan screen did nothing). No browser and no server.
//
//     cd pwa
//     node tests/tabs.test.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';

const here = path.dirname(fileURLToPath(import.meta.url));
const out = path.join(here, `.tmp-tabs-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));
await build({ entryPoints: { tabs: path.join(here, '..', 'src', 'services', 'tabs.js') }, bundle: true, format: 'esm', platform: 'node', outdir: out, outExtension: { '.js': '.mjs' }, logLevel: 'error' });
const { tabTap, TAB_RESELECT_EVENT, TABS, activeTab } = await import(pathToFileURL(path.join(out, 'tabs.mjs')).href);

let n = 0;
const check = (label, fn) => { fn(); n += 1; console.log(`  OK  ${label}`); };
check('a tap on a tab of ANOTHER screen goes there', () => {
  assert.equal(tabTap('/', '/yojana'), 'navigate');
  assert.equal(tabTap('/yojana', '/'), 'navigate');
  assert.equal(tabTap('/review', '/account'), 'navigate');
});
check('a tap on the tab of the screen we are ON is a "reselect": the screen goes back to its start (before, it did nothing)', () => {
  for (const p of ['/', '/yojana', '/review', '/progress', '/account']) assert.equal(tabTap(p, p), 'reselect');
});
check('the signal the screens listen for has a stable name', () => { assert.equal(TAB_RESELECT_EVENT, 'ankur-tab-reselect'); });
check('the tab names (29 Oct, reviewed by Vaishnavi): what the teacher does there, never two "योजना" alone, and "कक्षा प्रगति" (not "प्रगति", next to the प्रगतिशील group)', () => {
  assert.deepEqual(TABS.map((t) => [t.id, t.icon, t.hi, t.en]), [['/', '🎯', 'योजना बनाएँ', 'Make plan'], ['/yojana', '📋', 'आज की योजना', "Today's plan"],
    ['/review', '☑️', 'समीक्षा', 'Review'], ['/progress', '📊', 'कक्षा प्रगति', 'Class progress'], ['/account', '👤', 'प्रोफ़ाइल', 'Profile']]);
});
check('each screen title and "कैसे काम करता है?" use the same names', () => {
  const read = (f) => fs.readFileSync(path.join(here, '..', 'src', f), 'utf8');
  assert.ok(read('screens/PlanScreen.jsx').includes('<h1>🎯 <Bi hi="योजना बनाएँ" en="Make plan"'));
  assert.ok(read('screens/YojanaScreen.jsx').includes(`<h1>📋 <Bi hi="आज की योजना" en="Today's plan"`));
  assert.ok(read('screens/ProgressScreen.jsx').includes('<h1>📊 <Bi hi="कक्षा की प्रगति" en="Class progress"'));
  const how = read('components/HowItWorks.jsx');
  for (const t of TABS.slice(0, 4)) assert.ok(how.includes(`icon: '${t.icon}', hi: '${t.hi}'`), t.hi);
  for (const old of ['दैनिक योजना', 'Select Lakshya', 'Generate Plan', '"योजना" टैब']) for (const f of ['screens/PlanScreen.jsx', 'screens/YojanaScreen.jsx', 'components/HowItWorks.jsx', 'App.jsx'])
    assert.ok(!read(f).replace(/^\s*(\/\/|\*|\{\/\*).*$/gm, '').includes(old), `${old} in ${f}`);
});
check('the lit tab: the screen’s own; the class register (opened from "योजना बनाएँ") lights "योजना बनाएँ"; the bar uses this rule', () => {
  for (const t of TABS) assert.equal(activeTab(t.id), t.id);
  assert.equal(activeTab('/register'), '/');
  const app = fs.readFileSync(path.join(here, '..', 'src', 'App.jsx'), 'utf8');
  assert.ok(/const lit = activeTab\(path\)/.test(app) && /nav-item \$\{lit === t\.id \? 'active' : ''\}/.test(app) && /const tabs = TABS;/.test(app));
});
fs.rmSync(out, { recursive: true, force: true });
console.log(`\nOK: ${n} checks. Tapping the tab you are on takes that screen back to its start.`);
