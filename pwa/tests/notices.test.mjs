// Messages on the screen instead of pop-ups (services/notify.js, components/Notices.jsx), the folded coverage card and the single Profile button. No browser and no server.
//
//     cd pwa
//     node tests/notices.test.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';

const here = path.dirname(fileURLToPath(import.meta.url));
const src = path.join(here, '..', 'src');
const out = path.join(here, `.tmp-notices-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));      // the temporary build folder is always removed, even if a check fails
await build({
  entryPoints: { notify: path.join(src, 'services/notify.js') },
  bundle: true, format: 'esm', platform: 'node', outdir: out, outExtension: { '.js': '.mjs' }, logLevel: 'error',
});
const { notify, onNotify } = await import(pathToFileURL(path.join(out, 'notify.mjs')).href);

let n = 0;
const check = (label, fn) => { fn(); n += 1; console.log(`  OK  ${label}`); };
const read = (f) => fs.readFileSync(path.join(src, f), 'utf8');

console.log('the message service');
check('a message reaches the screen with its text and kind, each with its own id', () => {
  const seen = [];
  const off = onNotify((m) => seen.push(m));
  const a = notify('✅ 5 अवलोकन दर्ज हुए', 'success');
  const b = notify('समस्या: no network', 'error');
  off();
  notify('after unsubscribing: not seen');
  assert.equal(seen.length, 2);
  assert.deepEqual(seen.map((m) => [m.text, m.kind]), [['✅ 5 अवलोकन दर्ज हुए', 'success'], ['समस्या: no network', 'error']]);
  assert.ok(a !== b);
});
check('with nothing listening (a screen tested on its own) a message is simply dropped, never an error', () => {
  assert.doesNotThrow(() => notify('nobody is listening'));
});

console.log('the screens');
check('no screen opens a blocking pop-up (alert) any more', () => {
  const files = [];
  const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).forEach((e) => (e.isDirectory() ? walk(path.join(d, e.name)) : /\.jsx?$/.test(e.name) && files.push(path.join(d, e.name))));
  walk(src);
  const bad = files.filter((f) => /(^|[^.\w])alert\(/.test(fs.readFileSync(f, 'utf8')));
  assert.deepEqual(bad.map((f) => path.relative(src, f)), []);
});
check('the messages are shown on every signed-in screen; an error stays until tapped away, a success goes by itself', () => {
  assert.ok(/<Notices \/>/.test(read('App.jsx')));
  const v = read('components/Notices.jsx');
  assert.ok(/n\.kind !== 'error'\) setTimeout/.test(v), 'only a non-error message times out');
  assert.ok(/role=\{n\.kind === 'error' \? 'alert' : 'status'\}/.test(v), 'a screen reader announces it');
});
check('the Plan screen has no coverage summary line ("ज्ञान-आधार कवरेज": jargon, bare symbols, and counts that were out of date); each skill still carries its own label', () => {
  const plan = read('screens/PlanScreen.jsx');
  assert.ok(!plan.includes('coverage-card') && !plan.includes('ज्ञान-आधार कवरेज') && !plan.includes('tierCounts'));
  assert.ok(plan.includes("const T = TIERS[c.coverage_tier || 'untested']"));
});
check('there is ONE Profile button: the 👤 tab in the bottom bar (the Plan header has none)', () => {
  assert.ok(!read('screens/PlanScreen.jsx').includes('data-testid="open-account"'));
  assert.ok(/id: '\/account', icon: '👤'/.test(read('services/tabs.js')));
});

console.log(`\nOK: ${n} checks: messages appear on the screen instead of blocking pop-ups, the coverage card is one line, and Profile has one button`);
