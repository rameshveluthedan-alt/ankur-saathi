// Observed skills (14 Nov): the task, its materials (the class kit first, else everyday objects) and what A / PA / NA look like, shown inside the
// group's You Do and on the in-class recording page; the back-up sheet's items as text to draw on the board (most schools cannot print).
//
//     cd pwa
//     node tests/observe_panel.test.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
import React from 'react';
import ReactDOMServer from 'react-dom/server';

const here = path.dirname(fileURLToPath(import.meta.url));
const src = path.join(here, '..', 'src');
const out = path.join(here, `.tmp-observe-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));
await build({
  entryPoints: { panel: path.join(src, 'components/ObservePanel.jsx'), board: path.join(src, 'components/BoardWork.jsx'), boardsvc: path.join(src, 'services/boardWork.js') },
  bundle: true, format: 'esm', platform: 'node', outdir: out, outExtension: { '.js': '.mjs' }, loader: { '.js': 'jsx', '.jsx': 'jsx' }, external: ['react', 'react-dom'], logLevel: 'error',
});
const { default: ObservePanel, observeOf } = await import(pathToFileURL(path.join(out, 'panel.mjs')).href);
const { default: BoardWork } = await import(pathToFileURL(path.join(out, 'board.mjs')).href);
const { boardProblems } = await import(pathToFileURL(path.join(out, 'boardsvc.mjs')).href);
const read = (f) => fs.readFileSync(path.join(src, f), 'utf8');

let n = 0;
const check = (label, fn) => { fn(); n += 1; console.log(`  OK  ${label}`); };
const html = (el) => ReactDOMServer.renderToStaticMarkup(el);

const OBS = { task_hi: 'चीज़ों को रंग के हिसाब से छाँटें', task_en: 'Sort the objects by colour', kit_materials_hi: ['रंगीन ब्लॉक'], local_materials_hi: ['पत्तियाँ', 'कंकड़', 'बटन'],
  look_for: { achieved_hi: 'बिना मदद एक ही नियम से सब छाँटता है', partial_hi: 'मदद से छाँटता है या एक-दो गलती', not_yet_hi: 'नियम बीच में बदल देता है', achieved_en: 'Sorts all by one rule without help' } };
const PLAN = { worksheets: {
  beginner: { sheet_kind: 'observed', practice: true, observe: OBS, required_count: 2, problems: [
    { item_type: 'symbol_grid', problem_hi: 'सभी △ पर गोला लगाएँ', board_hi: '△ ○ □ △ ○ △', answer: '3' },
    { item_type: 'compare_boxes', problem_hi: 'जिसमें ज़्यादा हैं उस पर ✓', board_hi: 'क: ★★★★★★ | ख: ★★★★', answer: 'क' }] },
  progressor: { problems: [{ problem_hi: '23 + 15 =' }, { problem_hi: '41 + 36 =' }], required_count: 2 } } };

console.log('the observed task, its materials and what to look for');
check('observeOf finds an observed group\'s task, and nothing for another group', () => {
  assert.equal(observeOf(PLAN, 'beginner'), OBS);
  assert.equal(observeOf(PLAN, 'progressor'), null);
  assert.equal(observeOf(null, 'beginner'), null);
});
check('the panel shows the task, the kit first, then everyday objects, and the worksheet as the back-up', () => {
  const h = html(React.createElement(ObservePanel, { observe: OBS }));
  assert.ok(h.includes('चीज़ों को रंग के हिसाब से छाँटें') && h.includes('रंगीन ब्लॉक') && h.includes('पत्तियाँ, कंकड़, बटन'));
  assert.ok(h.indexOf('रंगीन ब्लॉक') < h.indexOf('पत्तियाँ') && h.includes('बोर्ड पर बनाकर'));
});
check('what A / PA / NA look like for this task, in that order', () => {
  const h = html(React.createElement(ObservePanel, { observe: OBS }));
  const a = h.indexOf('बिना मदद एक ही नियम से'), pa = h.indexOf('मदद से छाँटता है'), na = h.indexOf('नियम बीच में बदल');
  assert.ok(a > -1 && pa > a && na > pa);
});
check('compact (after class): only what to look for, not the task or materials again', () => {
  const h = html(React.createElement(ObservePanel, { observe: OBS, compact: true }));
  assert.ok(h.includes('क्या देखें') && !h.includes('रंगीन ब्लॉक') && !h.includes('चीज़ों को रंग के हिसाब से छाँटें'));
});
check('nothing to show: no panel at all', () => {
  assert.equal(html(React.createElement(ObservePanel, { observe: null })), '');
});

console.log('\nthe back-up sheet on the board');
check('an observed sheet: each item\'s task and the code-written text to draw, in either subject', () => {
  const b = boardProblems(PLAN, 'beginner', 'r1_literacy');
  assert.equal(b.kind, 'observed');
  assert.deepEqual(b.items, [{ task: 'सभी △ पर गोला लगाएँ', draw: '△ ○ □ △ ○ △' }, { task: 'जिसमें ज़्यादा हैं उस पर ✓', draw: 'क: ★★★★★★ | ख: ★★★★' }]);
  const h = html(React.createElement(BoardWork, { plan: PLAN, group: 'beginner', domain: 'numeracy' }));
  assert.ok(h.includes('data-kind="observed"') && h.includes('△ ○ □ △ ○ △') && h.includes('बोर्ड पर बनाएँ'));
});
check('a maths sheet of sums is listed as before', () => {
  assert.deepEqual(boardProblems(PLAN, 'progressor', 'numeracy'), { items: ['23 + 15', '41 + 36'], required: 2 });
});

console.log('\nwhere it shows');
check('inside the group\'s You Do (before the record button) and on the recording page above A / PA / NA', () => {
  const y = read('screens/YojanaScreen.jsx'); const r = read('screens/ReviewScreen.jsx');
  assert.ok(y.indexOf('<ObservePanel observe={observeOf(plan, level)}') > -1 && y.indexOf('<ObservePanel observe={observeOf(plan, level)}') < y.indexOf('{recordButton(level)}', y.indexOf('<ObservePanel')));
  assert.ok(r.includes('<ObservePanel observe={observeOf(plan && plan.plan, observedLevel.level)}'));
});

console.log(`\nOK: ${n} checks: an observed skill shows its task, materials and what to look for where the teacher records, and its back-up sheet as text to draw`);
