// The check for understanding in each teach block: its heading always shows, the block's questions come first, and the show-me method (the same in every block) is folded under one line. No browser and no server.
//
//     cd pwa
//     node tests/cfu_fold.test.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const src = fs.readFileSync(path.join(here, '..', 'src', 'screens', 'YojanaScreen.jsx'), 'utf8');
const css = fs.readFileSync(path.join(here, '..', 'src', 'index.css'), 'utf8');

let n = 0;
const check = (label, fn) => { fn(); n += 1; console.log(`  OK  ${label}`); };

const cfu = src.slice(src.indexOf('data-testid="cfu"'), src.indexOf('data-testid="cfu-item"'));
const fold = cfu.slice(cfu.indexOf('<details'), cfu.indexOf('</details>'));

check('sticks are named only in a maths plan: "(छड़ियों से)" and ", with sticks," depend on the plan’s subject (they leaked into every Hindi lesson)', () => {
  assert.ok(fold.includes("{currentPlan.domain_id === 'numeracy' ? ' (छड़ियों से)' : ''}") && fold.includes("{currentPlan.domain_id === 'numeracy' ? ', with sticks,' : ''}"));
  assert.ok(!/समझाएँ \(छड़ियों से\)/.test(fold) && !/at once, with sticks,/.test(fold));
});
check('the heading "समझ की जाँच" (Check for understanding) is OUTSIDE the fold: always visible', () => {
  const heading = cfu.indexOf('hi="समझ की जाँच"');
  assert.ok(heading > -1 && heading < cfu.indexOf('<details'));
  assert.ok(cfu.includes('en="Check for understanding"'));
});
check('the heading and the fold name the PURPOSE, not one technique: no "शो-मी" (show-me is one way to check, the text says how)', () => {
  assert.ok(!/hi="[^"]*शो-मी[^"]*"/.test(cfu) && !/en="[^"]*show-me[^"]*"/i.test(cfu));
});
check('the method is inside a fold that opens on "कैसे करें?" (How to do it), closed by default', () => {
  assert.ok(fold.includes('data-testid="cfu-how"') && fold.includes('hi="कैसे करें?"') && fold.includes('en="How to do it"'));
  assert.ok(!/<details[^>]*\bopen\b/.test(fold));
  assert.ok(fold.includes('तीन, दो, एक') && fold.includes('एक-चौथाई'), 'the wording is unchanged, only folded');
});
check('the questions come after the fold, not inside it', () => {
  assert.ok(src.indexOf('</details>', src.indexOf('data-testid="cfu-how"')) < src.indexOf('data-testid="cfu-item"'));
});
check('tapping the fold does not close the teach block it sits in', () => {
  assert.ok(/data-testid="cfu-how"[^>]*onClick=\{\(e\) => e\.stopPropagation\(\)\}/.test(cfu));
});
check('the fold line shows an arrow that turns when open, and is a comfortable tap target', () => {
  assert.match(css, /\.fold > summary::before\s*\{\s*content:\s*'▸'/);
  assert.match(css, /\.fold\[open\] > summary::before\s*\{\s*content:\s*'▾'/);
  assert.match(css, /\.fold > summary\s*\{[^}]*min-height:\s*40px/);
});

console.log(`\nOK: ${n} checks: the check for understanding shows its heading and questions first, with the show-me method one tap away`);
