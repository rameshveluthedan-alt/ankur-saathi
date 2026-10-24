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
const { tabTap, TAB_RESELECT_EVENT } = await import(pathToFileURL(path.join(out, 'tabs.mjs')).href);

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
fs.rmSync(out, { recursive: true, force: true });
console.log(`\nOK: ${n} checks. Tapping the tab you are on takes that screen back to its start.`);
