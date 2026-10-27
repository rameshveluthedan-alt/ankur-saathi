// After a save on the Review: the Observed block (what was just recorded, above the children list) and the Reading-aloud block (the child just scored,
// above the empty form). They show the save that just completed and the SERVER's result; a failed save shows its error in place and no block.
// Which children are "still to score" is counted by the server per day, group and skill: tested in backend/tests/test_progress_today.py. No browser and no server.
//
//     cd pwa
//     node tests/review_confirmation.test.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
import React from 'react';
import ReactDOMServer from 'react-dom/server';

const here = path.dirname(fileURLToPath(import.meta.url));
const src = path.join(here, '..', 'src');
const out = path.join(here, `.tmp-confirm-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));      // the temporary build folder is always removed, even if a check fails
await build({
  entryPoints: { view: path.join(src, 'components/ReviewConfirm.jsx') },
  bundle: true, format: 'esm', platform: 'node', outdir: out, outExtension: { '.js': '.mjs' }, loader: { '.js': 'jsx', '.jsx': 'jsx' }, external: ['react', 'react-dom'], logLevel: 'error',
});
const { ObservedSaved, ReadingSaved, SaveError } = await import(pathToFileURL(path.join(out, 'view.mjs')).href);

let n = 0;
const check = (label, fn) => { fn(); n += 1; console.log(`  OK  ${label}`); };
const html = (el) => ReactDOMServer.renderToStaticMarkup(el);
const num = (h, testid) => { const m = h.match(new RegExp(`data-testid="${testid}"[^>]*>[^:]*:\\s*(?:<!-- -->)?(\\d+)`)); return m ? Number(m[1]) : null; };
const review = fs.readFileSync(path.join(src, 'screens', 'ReviewScreen.jsx'), 'utf8');

console.log('Observed: the block after Submit');
const three = { level: 'beginner', items: [{ roll_number: 27, status: 'not_achieved' }, { roll_number: 4, status: 'achieved' }, { roll_number: 25, status: 'not_achieved' }] };
const obs = html(React.createElement(ObservedSaved, { saved: three }));
check('the count in the header is the number of children in the save that just completed: 3 taps -> "3 अवलोकन दर्ज हुए"', () => {
  assert.ok(obs.includes('data-n="3"') && obs.includes('✓ 3 अवलोकन दर्ज हुए') && obs.includes('3 observations recorded'));
});
check('A + PA + NA in the counts row equals that count (a spurious count from a mapping slip fails here)', () => {
  const a = num(obs, 'saved-a'), pa = num(obs, 'saved-pa'), na = num(obs, 'saved-na');
  assert.deepEqual([a, pa, na], [1, 0, 2]);
  assert.equal(a + pa + na, three.items.length);
});
check('the children marked NA are listed by roll, in order: "✗ NA: रोल 25, रोल 27" (NA is a code; "not yet" is a hideable translation)', () => {
  assert.ok(obs.includes('data-testid="saved-na-rolls"') && obs.includes('रोल 25, रोल 27'));
  assert.ok(/✗ NA<span class="en en-inline" lang="en">not yet<\/span>/.test(obs));
});
check('no NA in the save: no NA line', () => {
  const h = html(React.createElement(ObservedSaved, { saved: { level: 'progressor', items: [{ roll_number: 5, status: 'achieved' }] } }));
  assert.ok(!h.includes('saved-na-rolls') && h.includes('✓ 1 अवलोकन दर्ज हुए'));
});
check('in the group\'s colour, with the quiet pointer to the Progress tab; nothing about levels or the group decision', () => {
  assert.ok(obs.includes('saved-block tier-beginner') && obs.includes('data-testid="to-progress"') && obs.includes('प्रगति टैब पर आज के सभी नतीजे और समूह-निर्णय देखें →'));
  assert.ok(!/आपका निर्णय|Your decision|शुरुआती<\/span>|badge-beginner/.test(obs));
});
check('nothing saved (or an empty save): no block at all', () => {
  assert.equal(html(React.createElement(ObservedSaved, { saved: null })), '');
  assert.equal(html(React.createElement(ObservedSaved, { saved: { level: 'beginner', items: [] } })), '');
});

console.log('\nReading aloud: the block after Save');
const read = (result, left = 0) => html(React.createElement(ReadingSaved, { saved: { level: 'progressor', result }, left }));
check('the result shown is the SERVER\'s: 45 CWPM that the server called partly achieved says "~ PA · आंशिक", never "achieved" (no rule on the phone)', () => {
  const h = read({ roll_number: 12, cwpm: 45, classification: 'partially_achieved' });
  assert.ok(h.includes('data-classification="partially_achieved"') && h.includes('~ PA') && h.includes('आंशिक'));
  assert.ok(!h.includes('✓ A<') && !h.includes('प्राप्त<'), 'not achieved, whatever the CWPM');
  const low = read({ roll_number: 12, cwpm: 95, classification: 'not_achieved' });
  assert.ok(low.includes('✗ NA') && low.includes('प्राप्त नहीं'), 'a high CWPM the server did not pass is shown as not achieved');
});
check('the line names the child and the score: "✓ रोल 12: 45 CWPM"', () => {
  assert.ok(/✓ रोल <!-- -->12<!-- -->: <!-- -->45<!-- --> CWPM|✓ रोल 12: 45 CWPM/.test(read({ roll_number: 12, cwpm: 45, classification: 'achieved' })));
});
check('"N more to go" shows the number it is given, and is hidden at 0', () => {
  const h = read({ roll_number: 12, cwpm: 45, classification: 'achieved' }, 9);
  assert.ok(h.includes('data-left="9"') && h.includes('इस समूह में 9 और बच्चे बाकी') && h.includes('9 more children in this group to go'));
  assert.ok(!read({ roll_number: 12, cwpm: 45, classification: 'achieved' }, 0).includes('reading-left'));
});
check('the Review gives it the server\'s count of who is still to score (coverage: today, this group, this skill), not a count kept on the phone', () => {
  assert.ok(/<ReadingSaved saved=\{orfSaved\} left=\{coverage && coverage\.pending_rolls \? coverage\.pending_rolls\.length : 0\}/.test(review));
});
check('in the group\'s colour, with the same pointer to Progress', () => {
  const h = read({ roll_number: 12, cwpm: 45, classification: 'achieved' });
  assert.ok(h.includes('saved-block tier-progressor') && h.includes('data-testid="to-progress"'));
});

console.log('\nwhen a save fails');
check('a failed Observed save shows no block, only its error in place', () => {
  assert.ok(/catch \(e\) \{ setObservedSaved\(null\); setObservedError\(/.test(review), 'the block is cleared on an error');
  assert.ok(/setObservedSaved\(\{ level: sheetLevel, items: observedItems \}\); setObservedError\(''\)/.test(review), 'a success sets exactly this save, and clears an old error');
});
check('a failed Reading-aloud save shows no block, only its error in place', () => {
  assert.ok(/catch \(e\) \{ setOrfSaved\(null\); setOrfError\(/.test(review));
  assert.ok(/setOrfSaved\(\{ level: sheetLevel, result \}\); setOrfError\(''\)/.test(review), 'the block shows the server\'s answer as it came');
});
check('the error is shown in place, read out by a screen reader', () => {
  const h = html(React.createElement(SaveError, { message: 'सहेजा नहीं जा सका: Roll 999 not found', testid: 'orf-error' }));
  assert.ok(h.includes('role="alert"') && h.includes('Roll 999 not found'));
  assert.equal(html(React.createElement(SaveError, { message: '' })), '');
});
check('the two saves no longer raise a message at the top of the screen (the block replaces it)', () => {
  const obsSave = review.slice(review.indexOf('const submitObserved'), review.indexOf('const submitORF'));
  const orfSave = review.slice(review.indexOf('const submitORF'), review.indexOf('return (', review.indexOf('const submitORF')));
  assert.ok(!/notify\(/.test(obsSave) && !/notify\(/.test(orfSave));
});

console.log('\nHindi only');
check('the new lines keep their English in hideable .en spans', () => {
  const all = obs + read({ roll_number: 12, cwpm: 45, classification: 'achieved' }, 3);
  for (const en of ['observations recorded', 'not yet', 'more children in this group to go', 'See all of today&#x27;s results']) {
    const i = all.indexOf(en);
    assert.ok(i > 0 && all.lastIndexOf('class="en', i) > all.lastIndexOf('</span>', i), en);
  }
});

console.log(`\nOK: ${n} checks: after a save the Review shows exactly what was saved and what the server decided, and a failed save shows only its error`);
