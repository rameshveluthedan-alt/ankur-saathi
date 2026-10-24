// The board-work line under a group's You Do: the worksheet's required problems, read from the plan. No browser and no server.
//
//     cd pwa
//     node tests/board_work.test.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
import React from 'react';
import ReactDOMServer from 'react-dom/server';

const here = path.dirname(fileURLToPath(import.meta.url));
const src = path.join(here, '..', 'src');
const out = path.join(here, `.tmp-board-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));      // the temporary build folder is always removed, even if a check fails
await build({
  entryPoints: { logic: path.join(src, 'services/boardWork.js'), view: path.join(src, 'components/BoardWork.jsx') },
  bundle: true, format: 'esm', platform: 'node', outdir: out, outExtension: { '.js': '.mjs' }, loader: { '.js': 'jsx', '.jsx': 'jsx' }, external: ['react', 'react-dom'], logLevel: 'error',
});
const { boardProblems } = await import(pathToFileURL(path.join(out, 'logic.mjs')).href);
const { default: BoardWork } = await import(pathToFileURL(path.join(out, 'view.mjs')).href);

let n = 0;
const check = (label, fn) => { fn(); n += 1; console.log(`  OK  ${label}`); };
const render = (props) => ReactDOMServer.renderToStaticMarkup(React.createElement(BoardWork, props));
// the shape of a recorded plan (N2.3.2): three gridded problems, three plain ones ('= ___'), two word problems; the first six are required
const prob = (number, problem_hi, extra = {}) => ({ number, problem_hi, ...extra });
const progressor = { required_count: 6, problems: [prob(1, '36 + 27', { row_type: 'grid' }), prob(2, '48 + 35', { row_type: 'grid' }), prob(3, '54 + 26', { row_type: 'grid' }), prob(4, '19 + 43 = ___', { row_type: 'plain' }), prob(5, '67 + 28 = ___', { row_type: 'plain' }), prob(6, '29 + 17 = ___', { row_type: 'plain' }),
  prob(7, 'रानी ने 29 रुपये के टमाटर और 34 रुपये की दाल खरीदी। कुल कितने रुपये लगे?'), prob(8, 'कक्षा में 46 लड़कियाँ और 37 लड़के हैं। कुल कितने बच्चे हैं?')] };
const plan = { worksheets: { progressor, beginner: { required_count: 6, problems: [prob(1, '23 + 14'), prob(2, '31 + 25'), prob(3, '42 + 16'), prob(4, '15 + 34'), prob(5, '50 + 23'), prob(6, '24 + 35')] } } };

console.log('the problems');
check('the Progressors\' six required problems are listed in order, the "= ___" is dropped, and the word problems (the extras) are not', () => {
  assert.deepEqual(boardProblems(plan, 'progressor', 'numeracy'), { items: ['36 + 27', '48 + 35', '54 + 26', '19 + 43', '67 + 28', '29 + 17'], required: 6 });
});
check('each group gets its OWN sheet\'s problems', () => {
  assert.deepEqual(boardProblems(plan, 'beginner', 'numeracy').items.slice(0, 2), ['23 + 14', '31 + 25']);
});
check('only the required count is listed: a sheet that asks for the first 4 lists 4', () => {
  const p = { worksheets: { progressor: { ...progressor, required_count: 4 } } };
  assert.deepEqual(boardProblems(p, 'progressor', 'numeracy').items, ['36 + 27', '48 + 35', '54 + 26', '19 + 43']);
});
check('numbers the system replaced after the model wrote are what is shown (the plan\'s own sheet is the source)', () => {
  const p = { worksheets: { progressor: { ...progressor, problems: progressor.problems.map((q, i) => (i === 0 ? { ...q, problem_hi: '37 + 28' } : q)) } } };
  assert.equal(boardProblems(p, 'progressor', 'numeracy').items[0], '37 + 28');
});
console.log('nothing is shown rather than something wrong');
check('literacy: no line (a literacy sheet holds passages and questions, not sums to copy)', () => {
  assert.equal(boardProblems(plan, 'progressor', 'literacy'), null);
});
check('no sheet for the group, no worksheets at all, no plan, no group: nothing', () => {
  assert.equal(boardProblems(plan, 'proficient', 'numeracy'), null);
  assert.equal(boardProblems({}, 'progressor', 'numeracy'), null);
  assert.equal(boardProblems(null, 'progressor', 'numeracy'), null);
  assert.equal(boardProblems(plan, undefined, 'numeracy'), null);
});
check('a required problem that is a long word problem, or has no digits, means no line (it cannot be copied as a sum)', () => {
  const p = { worksheets: { progressor: { required_count: 3, problems: [prob(1, '36 + 27'), prob(2, 'रानी ने 29 रुपये के टमाटर और 34 रुपये की दाल खरीदी। कुल?'), prob(3, '19 + 43')] } } };
  assert.equal(boardProblems(p, 'progressor', 'numeracy'), null);
  assert.equal(boardProblems({ worksheets: { progressor: { required_count: 2, problems: [prob(1, 'a + b'), prob(2, 'c + d')] } } }, 'progressor', 'numeracy'), null);
});
check('a sheet with no required count lists all its problems only if every one is a short sum', () => {
  assert.equal(boardProblems({ worksheets: { progressor: { problems: progressor.problems } } }, 'progressor', 'numeracy'), null);          // the word problems are in it
  assert.equal(boardProblems({ worksheets: { progressor: { problems: progressor.problems.slice(0, 6) } } }, 'progressor', 'numeracy').required, 6);
});
check('a single problem is not a board list', () => {
  assert.equal(boardProblems({ worksheets: { progressor: { required_count: 1, problems: [prob(1, '36 + 27')] } } }, 'progressor', 'numeracy'), null);
});
console.log('on the screen');
check('the line says what it is, numbers the problems like the sheet, and carries the group in its test id', () => {
  const h = render({ plan, group: 'progressor', domain: 'numeracy' });
  assert.ok(h.includes('data-testid="board-work-progressor"') && h.includes('बोर्ड पर लिखें (सवाल 1–6)') && h.includes('Copy to the board: problems 1–6 of the worksheet'));
  assert.equal((h.match(/data-testid="board-problem"/g) || []).length, 6);
  assert.ok(h.includes('1. 36 + 27') && h.includes('4. 19 + 43') && h.includes('6. 29 + 17') && !h.includes('= ___') && !h.includes('रानी'));
});
// found on the second real block: copied as text, spans run together ('28 + 352. 46 + 27': the number 352 appears). Each problem is a BLOCK of its own now, so a copy keeps them on separate lines.
const asCopiedText = (html) => html.replace(/<\/div>/g, '\n').replace(/<[^>]+>/g, '').replace(/&amp;/g, '&').trim();
check('each problem is a block of its own (not a span), so copied text keeps them on separate lines', () => {
  const h = render({ plan: { worksheets: { progressor: { required_count: 6, problems: ['28 + 35', '46 + 27', '39 + 44', '57 + 28', '36 + 36', '49 + 45'].map((t, i) => prob(i + 1, t)) } } }, group: 'progressor', domain: 'numeracy' });
  assert.equal((h.match(/<div[^>]*data-testid="board-problem"/g) || []).length, 6);
  assert.ok(!/<span[^>]*data-testid="board-problem"/.test(h));
});
check('copied as text, the problems are six separate lines and no two run into a number like 352', () => {
  const h = render({ plan: { worksheets: { progressor: { required_count: 6, problems: ['28 + 35', '46 + 27', '39 + 44', '57 + 28', '36 + 36', '49 + 45'].map((t, i) => prob(i + 1, t)) } } }, group: 'progressor', domain: 'numeracy' });
  const lines = asCopiedText(h).split('\n').map((x) => x.trim()).filter(Boolean);
  const mine = lines.filter((x) => /^\d\. \d/.test(x));
  assert.deepEqual(mine, ['1. 28 + 35', '2. 46 + 27', '3. 39 + 44', '4. 57 + 28', '5. 36 + 36', '6. 49 + 45'], lines);
  assert.ok(!/\d{3}\./.test(asCopiedText(h)) && !asCopiedText(h).includes('352'));
});
check('where there is nothing to show, nothing is drawn', () => {
  assert.equal(render({ plan, group: 'progressor', domain: 'literacy' }), '');
  assert.equal(render({ plan: {}, group: 'progressor', domain: 'numeracy' }), '');
});
console.log(`\nOK: ${n} checks. The six board problems are on the screen, copied from the worksheet itself, and nothing is shown that could be wrong`);
