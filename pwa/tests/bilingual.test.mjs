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
globalThis.document = { body: { classList: { toggle: (c, on) => { if (on) classes.add(c); else classes.delete(c); return on; }, contains: (c) => classes.has(c) } }, documentElement: { lang: 'hi' } };

const { default: Bi } = await import(pathToFileURL(path.join(out, 'bi.mjs')).href);
const { getLang, setLang, LANGS, getHindiOnly, setHindiOnly, applyLanguage, bi } = await import(pathToFileURL(path.join(out, 'language.mjs')).href);

let n = 0;
const check = (label, fn) => { fn(); n += 1; console.log(`  OK  ${label}`); };
const html = (props) => ReactDOMServer.renderToStaticMarkup(React.createElement(Bi, props));

console.log('the Hindi and its English');
check('Hindi first in a .hi span, then the English in a .en span marked lang="en" (a screen reader switches voice)', () => {
  assert.equal(html({ hi: 'समीक्षा', en: 'Review' }), '<span class="hi">समीक्षा</span><span class="en" lang="en">Review</span>');
});
check('inline puts the English on the same line', () => {
  assert.equal(html({ hi: 'गणित', en: 'Numeracy', inline: true }), '<span class="hi">गणित</span><span class="en en-inline" lang="en">Numeracy</span>');
});
check('no English: just the Hindi, and no empty span', () => {
  assert.equal(html({ hi: 'गणित' }), 'गणित');
});

console.log('the language setting: Hindi (default), English, both');
check('the three modes, Hindi by default: the body hides the English', () => {
  assert.deepEqual(LANGS, ['hi', 'en', 'both']);
  applyLanguage();
  assert.equal(getLang(), 'hi');
  assert.ok(classes.has('hide-en') && !classes.has('lang-en'));
});
check('English: the body gets lang-en (the Hindi with a translation is hidden), and the setting is kept', () => {
  setLang('en');
  assert.ok(classes.has('lang-en') && !classes.has('hide-en') && getLang() === 'en');
  assert.equal(document.documentElement.lang, 'en');
});
check('kept across a reload: applying the stored setting gives English again', () => {
  classes.clear();
  applyLanguage();
  assert.ok(classes.has('lang-en'));
});
check('both: neither class, so Hindi and its English both show', () => {
  setLang('both');
  assert.ok(!classes.has('lang-en') && !classes.has('hide-en') && getLang() === 'both');
});
check('an unknown value is ignored', () => {
  setLang('fr');
  assert.equal(getLang(), 'both');
});
check('the earlier "Hindi only" checkbox (ankur_hindi_only) is read as Hindi, and the compatibility helpers still work', () => {
  store.clear(); store.set('ankur_hindi_only', '1');
  assert.equal(getLang(), 'hi');
  assert.equal(getHindiOnly(), true);
  setHindiOnly(false);
  assert.equal(getLang(), 'both');
  assert.ok(!store.has('ankur_hindi_only'));
  setHindiOnly(true);
  assert.equal(getLang(), 'hi');
});
check('pop-ups and messages (plain text): Hindi, English, or "हिंदी (English)" by the setting', () => {
  setLang('hi');
  assert.equal(bi('समस्या', 'Error'), 'समस्या');
  setLang('en');
  assert.equal(bi('समस्या', 'Error'), 'Error');
  setLang('both');
  assert.equal(bi('समस्या', 'Error'), 'समस्या (Error)');
  assert.equal(bi('समस्या'), 'समस्या');
});
check('a browser that refuses storage (private mode) still switches the screen, and nothing breaks', () => {
  const saved = globalThis.localStorage;
  globalThis.localStorage = { getItem: () => { throw new Error('denied'); }, setItem: () => { throw new Error('denied'); }, removeItem: () => { throw new Error('denied'); } };
  setLang('en');
  assert.ok(classes.has('lang-en'));
  assert.equal(bi('समस्या', 'Error'), 'Error');
  assert.equal(getLang(), 'hi');
  globalThis.localStorage = saved;
  setLang('hi');
});

console.log('the screens');
const read = (f) => fs.readFileSync(path.join(src, f), 'utf8');
check('the stylesheet hides the .en spans in Hindi, and the .hi spans in English', () => {
  assert.match(read('index.css'), /body\.hide-en \.en\s*\{\s*display:\s*none;\s*\}/);
  assert.match(read('index.css'), /body\.lang-en \.hi\s*\{\s*display:\s*none;\s*\}/);
});
check('the setting is applied before the first paint; the pill is on every screen and the Profile screen has the three options', () => {
  assert.ok(/applyLanguage\(\)/.test(read('main.jsx')));
  assert.ok(read('App.jsx').includes('<LangSwitch />'));
  const acc = read('screens/AccountScreen.jsx');
  for (const id of ['hindi-only', 'lang-opt-en']) assert.ok(acc.includes(id), id);
  assert.ok(!acc.includes('lang-opt-both'), '"both" is no longer offered on Profile (14 Nov: it doubled the text)');
});
check('the screen headings use Bi, so "Hindi only" hides their English', () => {
  for (const [f, hi] of [['screens/PlanScreen.jsx', 'योजना बनाएँ'], ['screens/YojanaScreen.jsx', 'पढ़ाएँ: आज की योजना'], ['screens/ReviewScreen.jsx', 'आकलन'], ['screens/ProgressScreen.jsx', 'कक्षा की प्रगति'], ['screens/AccountScreen.jsx', 'प्रोफ़ाइल']]) {
    assert.ok(read(f).includes(`<Bi hi="${hi}"`), f);
  }
});

check('no screen writes an English translation in brackets after Hindi any more (it would stay visible with "Hindi only")', () => {
  const files = [];
  const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).forEach((e) => (e.isDirectory() ? walk(path.join(d, e.name)) : /\.jsx$/.test(e.name) && files.push(path.join(d, e.name))));
  walk(src);
  // Hindi, a space, then "(English words)" in the JSX itself. Kept on purpose: aria-labels (read aloud, never shown) and the consent confirm box (the leader sees the whole statement in both languages).
  const bad = files.flatMap((f) => fs.readFileSync(f, 'utf8').split('\n').map((l, i) => [f, i + 1, l]))
    .filter(([, , l]) => /[ऀ-ॿ][^`'"<>{}]{0,80} \([A-Z][A-Za-z' ,./:;!?-]{2,}\)/.test(l) && !/aria-label=|^\s*(\/\/|\*)|CONSENT\.en/.test(l));
  assert.deepEqual(bad.map(([f, i]) => `${path.relative(src, f)}:${i}`), []);
});

console.log(`\nOK: ${n} checks: Hindi and its English, shown by the language setting (Hindi, English or both)`);
