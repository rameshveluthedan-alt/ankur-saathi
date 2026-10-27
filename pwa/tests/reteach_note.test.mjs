// The note on a re-teach block of the lesson plan: the label, the children, the mistakes, the pace. No browser and no server.
//
//     cd pwa
//     node tests/reteach_note.test.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
import React from 'react';
import ReactDOMServer from 'react-dom/server';

const here = path.dirname(fileURLToPath(import.meta.url));
const src = path.join(here, '..', 'src');
const out = path.join(here, `.tmp-note-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));      // the temporary build folder is always removed, even if a check fails
await build({
  entryPoints: { logic: path.join(src, 'services/reteachInfo.js'), view: path.join(src, 'components/ReteachNote.jsx') },
  bundle: true, format: 'esm', platform: 'node', outdir: out, outExtension: { '.js': '.mjs' }, loader: { '.js': 'jsx', '.jsx': 'jsx' }, external: ['react', 'react-dom'], logLevel: 'error',
});
const { pacePlan, isReteachMain, reteachTitle, reteachSummary, PACE } = await import(pathToFileURL(path.join(out, 'logic.mjs')).href);
const { default: Note } = await import(pathToFileURL(path.join(out, 'view.mjs')).href);

let n = 0;
const check = (label, fn) => { fn(); n += 1; console.log(`  OK  ${label}`); };
const render = (block, expanded = false) => ReactDOMServer.renderToStaticMarkup(React.createElement(Note, { block, expanded }));
// the block from the first real re-teach run: the Progressors, 29 minutes, rolls 4 and 5, the dropped carry
const rt = { type: 'teach', teach_group: 'progressor', reteach: true, duration_minutes: 29, affected_rolls: [4, 5], reteach_mistakes: [{ misconception_id: 'N2.3.2-M1', name_hi: 'हासिल भूलना: हासिल छोड़ देता है', children: 2 }] };
const LABELS = { progressor: { hi: 'प्रगतिशील', en: 'Progressor' } };

console.log('the pace');
check('the pace the teachers called realistic is 2 + 6 + 7 + 4 + 8 = 27 minutes, and a 27-minute block gets exactly that', () => {
  assert.deepEqual(PACE.map((p) => p.min), [2, 6, 7, 4, 8]);
  assert.deepEqual(pacePlan(27).parts.map((p) => p.min), [2, 6, 7, 4, 8]);
  assert.equal(pacePlan(27).scaled, false);
});
check('a 29-minute block (the real one) gets 2, 6, 8, 4, 9: whole minutes that add up to 29', () => {
  const p = pacePlan(29);
  assert.deepEqual(p.parts.map((x) => x.min), [2, 6, 8, 4, 9]);
  assert.equal(p.total, 29);
  assert.equal(p.scaled, true);
});
check('for every block length from 10 to 90 minutes the parts add up to the length exactly, none is under 1, and the order never changes', () => {
  for (let d = 10; d <= 90; d += 1) {
    const p = pacePlan(d);
    assert.equal(p.parts.reduce((a, x) => a + x.min, 0), d, `length ${d}`);
    assert.ok(p.parts.every((x) => x.min >= 1), `length ${d}`);
    assert.deepEqual(p.parts.map((x) => x.key), ['recall', 'i_do', 'we_do', 'show_me', 'you_do']);
  }
});
check('no usable length (missing, not a number, or under 10 minutes): no pace line instead of a nonsense one; a length given as text works', () => {
  assert.equal(pacePlan(undefined), null);
  assert.equal(pacePlan(NaN), null);
  assert.equal(pacePlan(9), null);
  assert.equal(pacePlan('29').total, 29);
});

console.log('what counts as a re-teach block');
check('only a teach block marked as a re-teach counts: not a plain teach block, and not the old separate block (which has its own display)', () => {
  assert.equal(isReteachMain(rt), true);
  assert.equal(isReteachMain({ type: 'teach', teach_group: 'beginner' }), false);
  assert.equal(isReteachMain({ type: 'teach', reteach: false }), false);
  assert.equal(isReteachMain({ type: 'reteach', teach_group: 'beginner' }), false);
  assert.equal(isReteachMain(undefined), false);
});
check('the title says re-teach and names the group, in the style of the other titles', () => {
  assert.equal(reteachTitle(rt, LABELS), '🔄 पुनः शिक्षण: प्रगतिशील पढ़ाएँ (Re-teach Progressor)');
  assert.ok(reteachTitle({ teach_group: 'x' }, LABELS).includes('पुनः शिक्षण: x'));
});
check('a re-teach block with nothing recorded gets empty lists, not an error', () => {
  const s = reteachSummary({ type: 'teach', reteach: true, teach_group: 'progressor' });
  assert.deepEqual([s.isReteach, s.rolls, s.mistakes], [true, [], []]);
  assert.equal(s.pace, null);
});

console.log('what the note shows');
const closed = render(rt, false);
check('collapsed: that it is a re-teach, which children (their roll numbers) and which mistake, with how many children', () => {
  assert.ok(closed.includes('data-testid="reteach-note"') && closed.includes('पुनः शिक्षण (Re-teach)'));
  assert.ok(closed.includes('data-testid="reteach-children"') && closed.includes('रोल 4, 5'));
  assert.ok(closed.includes('data-testid="reteach-mistakes"') && closed.includes('हासिल भूलना: हासिल छोड़ देता है (2 बच्चे)'));
});
check('the mistakes and the children are from the LAST REVIEW, never "yesterday" (कल): the last plan can be days ago', () => {
  assert.ok(closed.includes('पिछली जाँच की गलतियों पर') && closed.includes('पिछली जाँच में गलती करने वाले बच्चे'));
  assert.ok(!/(^|[\s>(])कल[\s:]/.test(closed));
});
check('collapsed: the pace and the tips are NOT shown yet (they come when the block is opened)', () => {
  assert.ok(!closed.includes('reteach-pace') && !closed.includes('reteach-tips'));
});
const open = render(rt, true);
check('opened: the pace for THIS block (29 minutes), in Hindi and English', () => {
  assert.ok(open.includes('सुझाया समय (29 मि.)'));
  assert.ok(open.includes('कल की बात 2 · मैं करूँगा 6 · हम करेंगे 8 · जाँच 4 · तुम करोगे 9'));
  assert.ok(open.includes('Recall 2 · I Do 6 · We Do 8 · Show-me 4 · You Do 9'));
});
check('opened: what the teachers asked for: the wrong way first and erased, a quiet visit with no names or roll numbers, the quarter rule', () => {
  assert.ok(open.includes('data-testid="reteach-tips"'));
  assert.ok(open.includes('गलत वाला मिटा दें') && open.includes('चुपचाप') && open.includes('नाम या रोल नंबर न बोलें') && open.includes('एक-चौथाई से ज़्यादा'));
});
check('nothing recorded: it says the usual mistakes are re-taught, and shows no children line and no empty list', () => {
  const h = render({ type: 'teach', teach_group: 'progressor', reteach: true, duration_minutes: 27 }, false);
  assert.ok(h.includes('data-testid="reteach-no-mistake"') && h.includes('आम गलतियाँ दोबारा समझाई जाएँगी'));
  assert.ok(!h.includes('reteach-children') && !h.includes('reteach-mistakes'));
});
check('no block length: the pace line is left out and the tips are still there', () => {
  const h = render({ ...rt, duration_minutes: undefined }, true);
  assert.ok(!h.includes('reteach-pace') && h.includes('reteach-tips'));
});
check('a plain teach block, and the old separate re-teach block, get NO note from this component (nothing is added to them)', () => {
  assert.equal(render({ type: 'teach', teach_group: 'beginner', duration_minutes: 22 }, true), '');
  assert.equal(render({ type: 'reteach', teach_group: 'beginner', affected_rolls: [1] }, true), '');
  assert.equal(render({ type: 'anchor' }, true), '');
});

fs.rmSync(out, { recursive: true, force: true });
console.log(`\nOK: ${n} checks. A re-teach block says so, names the children and the mistakes, and gives a pace that adds up to its length.`);
