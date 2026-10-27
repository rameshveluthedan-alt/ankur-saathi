// Hindi first, its English translation after it (components/Bi.jsx), and the "Hindi only" setting that hides the English (services/language.js). No browser and no server.
//
//     cd pwa
//     node tests/bilingual.test.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
import React from 'react';
import ReactDOMServer from 'react-dom/server';

const here = path.dirname(fileURLToPath(import.meta.url));
const src = path.join(here, '..', 'src');
const out = path.join(here, `.tmp-bi-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));      // the temporary build folder is always removed, even if a check fails
await build({
  entryPoints: { bi: path.join(src, 'components/Bi.jsx'), language: path.join(src, 'services/language.js') },
  bundle: true, format: 'esm', platform: 'node', outdir: out, outExtension: { '.js': '.mjs' }, loader: { '.js': 'jsx', '.jsx': 'jsx' }, external: ['react', 'react-dom'], logLevel: 'error',
});

// a stand-in for the browser: localStorage and the body's classes
const store = new Map();
globalThis.localStorage = { getItem: (k) => (store.has(k) ? store.get(k) : null), setItem: (k, v) => store.set(k, String(v)), removeItem: (k) => store.delete(k) };
const classes = new Set();
globalThis.document = { body: { classList: { toggle: (c, on) => { if (on) classes.add(c); else classes.delete(c); return on; }, contains: (c) => classes.has(c) } } };

const { default: Bi } = await import(pathToFileURL(path.join(out, 'bi.mjs')).href);
const { getHindiOnly, setHindiOnly, applyLanguage } = await import(pathToFileURL(path.join(out, 'language.mjs')).href);

let n = 0;
const check = (label, fn) => { fn(); n += 1; console.log(`  OK  ${label}`); };
const html = (props) => ReactDOMServer.renderToStaticMarkup(React.createElement(Bi, props));

console.log('the Hindi and its English');
check('Hindi first, then the English in a .en span marked lang="en" (a screen reader switches voice)', () => {
  assert.equal(html({ hi: 'समीक्षा', en: 'Review' }), 'समीक्षा<span class="en" lang="en">Review</span>');
});
check('inline puts the English on the same line', () => {
  assert.equal(html({ hi: 'गणित', en: 'Numeracy', inline: true }), 'गणित<span class="en en-inline" lang="en">Numeracy</span>');
});
check('no English: just the Hindi, and no empty span', () => {
  assert.equal(html({ hi: 'गणित' }), 'गणित');
});

console.log('the "Hindi only" setting');
check('off by default: the English shows', () => {
  applyLanguage();
  assert.equal(getHindiOnly(), false);
  assert.ok(!classes.has('hide-en'));
});
check('on: the body gets hide-en at once, and the setting is kept', () => {
  setHindiOnly(true);
  assert.ok(classes.has('hide-en') && getHindiOnly());
});
check('kept across a reload: applying the stored setting hides the English again', () => {
  classes.clear();
  applyLanguage();
  assert.ok(classes.has('hide-en'));
});
check('off again: the English comes back and nothing is left stored', () => {
  setHindiOnly(false);
  assert.ok(!classes.has('hide-en') && !getHindiOnly() && store.size === 0);
});
check('a browser that refuses storage (private mode) still switches the screen, and nothing breaks', () => {
  const saved = globalThis.localStorage;
  globalThis.localStorage = { getItem: () => { throw new Error('denied'); }, setItem: () => { throw new Error('denied'); }, removeItem: () => { throw new Error('denied'); } };
  setHindiOnly(true);
  assert.ok(classes.has('hide-en'));
  assert.equal(getHindiOnly(), false);
  globalThis.localStorage = saved;
  setHindiOnly(false);
});

console.log('the screens');
const read = (f) => fs.readFileSync(path.join(src, f), 'utf8');
check('the stylesheet hides exactly the .en spans when the setting is on', () => {
  assert.match(read('index.css'), /body\.hide-en \.en\s*\{\s*display:\s*none;\s*\}/);
});
check('the setting is applied before the first paint, and the Profile screen has the switch', () => {
  assert.ok(/applyLanguage\(\)/.test(read('main.jsx')));
  assert.ok(read('screens/AccountScreen.jsx').includes('data-testid="hindi-only"'));
});
check('the screen headings use Bi, so "Hindi only" hides their English', () => {
  for (const [f, hi] of [['screens/PlanScreen.jsx', 'योजना बनाएँ'], ['screens/YojanaScreen.jsx', 'दैनिक योजना'], ['screens/ReviewScreen.jsx', 'समीक्षा'], ['screens/ProgressScreen.jsx', 'प्रगति'], ['screens/AccountScreen.jsx', 'प्रोफ़ाइल']]) {
    assert.ok(read(f).includes(`<Bi hi="${hi}"`), f);
  }
});

console.log(`\nOK: ${n} checks: Hindi comes first with its English after it, and "Hindi only" hides the English and nothing else`);
