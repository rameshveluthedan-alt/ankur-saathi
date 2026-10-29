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
  assert.ok(!h.includes('saved-na-rolls') && h.includes('✓ 1 अवलोकन दर्ज हुआ') && h.includes('1 observation recorded'), 'one: the singular, in Hindi and English');
});
check('in the group\'s colour, with a small button to Progress ("📊 कक्षा प्रगति देखें →", a button, not a text link); nothing about levels or the group decision', () => {
  assert.ok(obs.includes('saved-block tier-beginner') && /<button type="button" class="btn btn-secondary btn-small" data-testid="to-progress"[^>]*>📊 /.test(obs) && obs.includes('कक्षा प्रगति देखें →'));
  assert.ok(!obs.includes('demo-link') && !obs.includes('प्रगति टैब पर आज के सभी नतीजे'));
  assert.ok(!/आपका निर्णय|Your decision|शुरुआती<\/span>|badge-beginner/.test(obs));
});
check('nothing saved (or an empty save): no block at all', () => {
  assert.equal(html(React.createElement(ObservedSaved, { saved: null })), '');
  assert.equal(html(React.createElement(ObservedSaved, { saved: { level: 'beginner', items: [] } })), '');
});

console.log('\nReading aloud: the block after Save');
// a reading skill that is not about speed (pauses at punctuation): it keeps the A/PA/NA line
const read = (result, left = 0) => html(React.createElement(ReadingSaved, { saved: { level: 'progressor', skill: 'L2.5.2', result }, left }));
// a speed reading skill: the two numbers the teacher entered and the pace label
const pace = (classification, cwpm, errors, left = 0) => html(React.createElement(ReadingSaved,
  { saved: { level: 'progressor', skill: 'L2.5.1', result: { roll_number: 12, cwpm, classification }, entry: { cwpm, errors } }, left }));
check('the result shown is the SERVER\'s: 45 CWPM that the server called partly achieved says "~ PA · आंशिक", never "achieved" (no rule on the phone)', () => {
  const h = read({ roll_number: 12, cwpm: 45, classification: 'partially_achieved' });
  assert.ok(h.includes('data-classification="partially_achieved"') && h.includes('~ PA') && h.includes('आंशिक'));
  assert.ok(!h.includes('✓ A<') && !h.includes('प्राप्त<'), 'not achieved, whatever the CWPM');
  const low = read({ roll_number: 12, cwpm: 95, classification: 'not_achieved' });
  assert.ok(low.includes('✗ NA') && low.includes('प्राप्त नहीं'), 'a high CWPM the server did not pass is shown as not achieved');
});
check('a speed skill: the pace label comes from the mapping, never "reader" words: grade_level at 42 CWPM says "रफ़्तार कक्षा-स्तर पर", not "ग्रेड-स्तरीय पाठक"', () => {
  const h = pace('grade_level', 42, 3);
  assert.ok(h.includes('रफ़्तार कक्षा-स्तर पर') && h.includes('Pace at grade level'));
  assert.ok(!/पाठक|reader/i.test(h.replace(/data-classification="[^"]*"/g, '')), 'no reader wording anywhere');
});
check('the three bands map to the three pace labels, from the band names and from the A/PA/NA codes the server sends today alike', () => {
  for (const [codes, label] of [[['grade_level', 'achieved'], 'रफ़्तार कक्षा-स्तर पर'], [['developing', 'partially_achieved'], 'रफ़्तार विकसित हो रही'], [['early_reader', 'not_achieved'], 'रफ़्तार धीमी']]) {
    for (const c of codes) assert.ok(pace(c, 30, 2).includes(label), `${c} -> ${label}`);
  }
});
check('the two numbers are the ones the teacher entered, each in its place: 42 सही · 3 गलतियाँ (correct and errors never swap)', () => {
  const h = pace('grade_level', 42, 3);
  assert.ok(/data-testid="fluency-correct">42(<!-- -->)? सही/.test(h), 'correct = 42');
  assert.ok(/data-testid="fluency-errors">3(<!-- -->)? गलतियाँ/.test(h), 'errors = 3');
  assert.ok(/✓ रोल (<!-- -->)?12(<!-- -->)?: /.test(h), 'the roll just scored');
});
check('no errors still reads "0 गलतियाँ" (every line has the same shape, never an empty field)', () => {
  assert.ok(/data-testid="fluency-errors">0(<!-- -->)? गलतियाँ/.test(pace('developing', 30, 0)));
});
check('many errors (a quarter or more of the correct words) turn only the errors part amber with ⚠; none does not', () => {
  const many = pace('grade_level', 40, 40);
  assert.ok(/class="many-errors">40(<!-- -->)? गलतियाँ(<!-- -->)? ⚠/.test(many), 'errors = correct: amber');
  assert.ok(many.includes('रफ़्तार कक्षा-स्तर पर'), 'the pace label is unchanged');
  assert.ok(!pace('grade_level', 40, 0).includes('many-errors') && !pace('grade_level', 40, 9).includes('many-errors'), 'no errors, or under a quarter: not amber');
});
check('a reading skill not about speed (pauses, expression) keeps the A/PA/NA line: "✓ रोल 12: 45 सही शब्द/मिनट" (no "CWPM")', () => {
  assert.ok(/✓ रोल <!-- -->12<!-- -->: <!-- -->45<!-- --> सही शब्द\/मिनट|✓ रोल 12: 45 सही शब्द\/मिनट/.test(read({ roll_number: 12, cwpm: 45, classification: 'achieved' })));
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
  assert.ok(/setObservedSaved\(\{ level: sheetLevel, items: observedItems, result: res \}\); setObservedError\(''\)/.test(review), 'a success sets exactly this save (with the server\'s answer), and clears an old error');
});
check('a failed Reading-aloud save shows no block, only its error in place', () => {
  assert.ok(/catch \(e\) \{ setOrfSaved\(null\); setOrfError\(/.test(review));
  assert.ok(/setOrfSaved\(\{ level: sheetLevel, skill: orfLevel\?\.competency_id, result,/.test(review), 'the block shows the server\'s answer as it came');
  assert.ok(/entry: \{ cwpm: parseInt\(orfEntry\.cwpm\), errors: parseInt\(orfEntry\.error_count \|\| 0\) \}/.test(review), 'with the two numbers the teacher entered');
  assert.ok(/setOrfError\(''\)/.test(review), 'a success clears an old error');
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
  for (const en of ['observations recorded', 'not yet', 'more children in this group to go', 'See class progress']) {
    const i = all.indexOf(en);
    assert.ok(i > 0 && all.lastIndexOf('class="en', i) > all.lastIndexOf('</span>', i), en);
  }
});

console.log(`\nOK: ${n} checks: after a save the Review shows exactly what was saved and what the server decided, and a failed save shows only its error`);
