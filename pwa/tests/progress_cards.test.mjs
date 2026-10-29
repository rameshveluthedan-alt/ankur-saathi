// The Progress screen's "today": the one Today card (a row per group), each child's one-line result today, and the "children to look at" section.
// The screen shows exactly what the server says; WHICH day counts is the server's job and is tested there (backend/tests/test_progress_today.py:
// yesterday's decision and results never show today). No browser and no server.
//
//     cd pwa
//     node tests/progress_cards.test.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
import React from 'react';
import ReactDOMServer from 'react-dom/server';

const here = path.dirname(fileURLToPath(import.meta.url));
const src = path.join(here, '..', 'src');
const out = path.join(here, `.tmp-progress-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));      // the temporary build folder is always removed, even if a check fails
await build({
  entryPoints: { view: path.join(src, 'components/ProgressToday.jsx') },
  bundle: true, format: 'esm', platform: 'node', outdir: out, outExtension: { '.js': '.mjs' }, loader: { '.js': 'jsx', '.jsx': 'jsx' }, external: ['react', 'react-dom'], logLevel: 'error',
});
const { TodayCard, ChildToday, LookAtChildren, DECISION_TEXT } = await import(pathToFileURL(path.join(out, 'view.mjs')).href);

let n = 0;
const check = (label, fn) => { fn(); n += 1; console.log(`  OK  ${label}`); };
const html = (el) => ReactDOMServer.renderToStaticMarkup(el);
const num = (h, testid) => { const m = h.match(new RegExp(`data-testid="${testid}"[^>]*>[^:]*:\\s*(?:<!-- -->)?(\\d+)`)); return m ? Number(m[1]) : null; };

// what the server returns for one subject today (backend/app/services/progress_service.py get_today)
const today = {
  has_plan: true,
  by_level: {
    beginner: { skill_id: 'N2.3.1', a: 2, pa: 1, na: 3, assessed: 6, group_size: 10, decision: 'advance', conflict: true, advance_no_next: false },
    progressor: { skill_id: 'N2.3.2', a: 0, pa: 0, na: 0, assessed: 0, group_size: 14, decision: 'reteach', conflict: true, advance_no_next: true },
    proficient: { skill_id: 'N0.1.1', a: 5, pa: 0, na: 0, assessed: 5, group_size: 6, decision: null, conflict: false, advance_no_next: false },
  },
};
const card = html(React.createElement(TodayCard, { today }));
// one group's row: from the start of its tag (the class comes before the testid) to the start of the next group's tag
const rowStart = (label) => card.lastIndexOf('<', card.indexOf(`data-testid="today-${label}"`));
const row = (label) => { const s = rowStart(label); const next = ['beginner', 'progressor', 'proficient'].map(rowStart).filter((i) => i > s).sort((a, b) => a - b)[0]; return card.slice(s, next); };

console.log('the Today card');
check('ONE card with a row per group, in the order Beginner, Progressor, Proficient, under "आज के नमूने में" (In today\'s sample)', () => {
  assert.equal((card.match(/data-testid="today-card"/g) || []).length, 1);
  const order = ['beginner', 'progressor', 'proficient'].map((l) => card.indexOf(`data-testid="today-${l}"`));
  assert.ok(order.every((i, k) => i > 0 && (k === 0 || i > order[k - 1])), order.join(','));
  assert.ok(card.includes('आज के नमूने में') && card.includes("In today&#x27;s sample"));
});
check('each row carries its group\'s colour edge and shape (tier class and the shaped badge)', () => {
  for (const l of ['beginner', 'progressor', 'proficient']) assert.ok(row(l).includes(`today-row tier-${l}`) && row(l).includes(`badge badge-${l}`), l);
});
check('the counts on a row are the server\'s, and A + PA + NA equals "assessed" (a query or mapping slip that made them disagree fails here)', () => {
  const b = row('beginner');
  const a = num(b, 'count-a'), pa = num(b, 'count-pa'), na = num(b, 'count-na');
  assert.deepEqual([a, pa, na], [2, 1, 3]);
  assert.equal(a + pa + na, today.by_level.beginner.assessed);
  assert.ok(b.includes('10 में से 6 बच्चों का आकलन') || /10<!-- --> में से <!-- -->6<!-- --> बच्चों का आकलन/.test(b), 'assessed 6 of 10, in Hindi ("बच्चों का", as Vaishnavi asked)');
  assert.ok(/assessed <!-- -->6<!-- --> of <!-- -->10|assessed 6 of 10/.test(b), 'and in English');
});
check('the decision shown is the server\'s decision for that group, in the Review screen\'s own words (a swapped advance/re-teach mapping fails here)', () => {
  for (const [decision, words] of Object.entries(DECISION_TEXT)) {
    const h = html(React.createElement(TodayCard, { today: { has_plan: true, by_level: { beginner: { ...today.by_level.beginner, decision, conflict: false } } } }));
    assert.ok(h.includes(`data-decision="${decision}"`) && h.includes(`आपका निर्णय: ${words.hi}`) && h.includes(`Your decision: ${words.en}`), decision);
  }
  assert.equal(DECISION_TEXT.advance.hi, '⬆ आगे बढ़ें');
  assert.equal(DECISION_TEXT.reteach.hi, '🔄 दोहराएँ');
  assert.equal(DECISION_TEXT.not_sure.hi, '❓ पक्का नहीं');
});
check('the decision words are the same as the ones tapped at the Review (services/groupSkills.js)', () => {
  const gsrc = fs.readFileSync(path.join(src, 'services', 'groupSkills.js'), 'utf8');
  for (const w of Object.values(DECISION_TEXT)) assert.ok(gsrc.includes(`hi: '${w.hi}'`), w.hi);
});
check('no decision recorded today: a grey "आज कोई निर्णय दर्ज नहीं" under the counts, and no rare lines', () => {
  const p = row('proficient');
  assert.ok(p.includes('data-decision="none"') && p.includes('आज कोई निर्णय दर्ज नहीं') && p.includes('No decision recorded today'));
  assert.ok(p.indexOf('today-counts-proficient') < p.indexOf('today-decision-proficient'), 'the grey line sits under the counts');
  assert.ok(!p.includes('today-conflict') && !p.includes('today-no-next'));
});
check('conflict: the amber line appears only when the server says so', () => {
  assert.ok(row('beginner').includes('data-testid="today-conflict-beginner"') && row('beginner').includes('आपका निर्णय और आज की जाँच मेल नहीं खाते'));
  assert.ok(!row('proficient').includes('today-conflict'));
});
check('advanced with no next skill: the grey line appears only when the server says so', () => {
  const h = html(React.createElement(TodayCard, { today: { has_plan: true, by_level: { proficient: { ...today.by_level.proficient, decision: 'advance', advance_no_next: true } } } }));
  assert.ok(h.includes('data-testid="today-no-next-proficient"') && h.includes('इसलिए यही कौशल फिर सिखाया जाएगा'));
  assert.ok(!row('beginner').includes('today-no-next'));
});
check('a group nobody was assessed in today shows ONLY the grey "आज किसी का आकलन नहीं हुआ": no counts, no decision, no rare lines (even when the server has a decision)', () => {
  const p = row('progressor');
  assert.ok(p.includes('data-testid="today-none-progressor"') && p.includes('आज किसी का आकलन नहीं हुआ') && p.includes('No assessment today'));
  assert.ok(!/count-a|today-decision|today-conflict|today-no-next/.test(p), p);
});
check('a re-teach decision is shown in the re-teach violet, not the group\'s colour', () => {
  const h = html(React.createElement(TodayCard, { today: { has_plan: true, by_level: { beginner: { ...today.by_level.beginner, decision: 'reteach' } } } }));
  assert.ok(/data-decision="reteach"[^>]*color:var\(--reteach\)/.test(h));
});
check('a subject with no plan today says so', () => {
  const h = html(React.createElement(TodayCard, { today: { has_plan: false, by_level: {} } }));
  assert.ok(h.includes('data-testid="today-no-plan"') && h.includes('आज इस विषय की योजना नहीं बनी'));
});

console.log('\neach child\'s result today');
check('a badge shows the server\'s status for the child\'s skill today: ✓ A, ~ PA, ✗ NA', () => {
  for (const [status, mark] of [['achieved', '✓ A'], ['partially_achieved', '~ PA'], ['not_achieved', '✗ NA']]) {
    const h = html(React.createElement(ChildToday, { today: { skill_id: 'N0.1.1', status } }));
    assert.ok(h.includes(`data-status="${status}"`) && h.includes(mark) && h.includes('आज N0.1.1 पर') && h.includes('Today on N0.1.1'), status);
  }
});
check('a speed reading skill scored by reading aloud (L2.5.1, grade_level) shows the two numbers and "रफ़्तार कक्षा-स्तर पर", not a badge', () => {
  for (const status of ['grade_level', 'achieved']) {
    const h = html(React.createElement(ChildToday, { today: { skill_id: 'L2.5.1', status, cwpm: 42, errors: 3 } }));
    assert.ok(h.includes('data-kind="fluency"') && h.includes('रफ़्तार कक्षा-स्तर पर') && /42(<!-- -->)? सही/.test(h) && /3(<!-- -->)? गलतियाँ/.test(h), status);
    assert.ok(!h.includes('badge-result') && !h.includes('many-errors'), 'no A/PA/NA badge, and no amber on Progress');
  }
});
check('any other skill keeps the A/PA/NA badge (and so does a reading skill recorded without numbers)', () => {
  assert.ok(html(React.createElement(ChildToday, { today: { skill_id: 'N2.3.1', status: 'achieved' } })).includes('data-kind="badge"'));
  assert.ok(html(React.createElement(ChildToday, { today: { skill_id: 'L2.5.2', status: 'achieved', cwpm: 40, errors: 1 } })).includes('data-kind="badge"'), 'pauses at punctuation is not a speed skill');
  assert.ok(html(React.createElement(ChildToday, { today: { skill_id: 'L2.5.1', status: 'achieved' } })).includes('data-kind="badge"'), 'observed, no numbers');
});
check('nothing recorded today (None): no line at all, not even grey text', () => {
  assert.equal(html(React.createElement(ChildToday, { today: null })), '');
  assert.equal(html(React.createElement(ChildToday, { today: undefined })), '');
});
check('the Progress screen shows the badge from TODAY\'s field of the selected subject (numeracy_today / literacy_today)', () => {
  const screen = fs.readFileSync(path.join(src, 'screens', 'ProgressScreen.jsx'), 'utf8');
  assert.ok(/<ChildToday today=\{selectedDomain === 'numeracy' \? c\.numeracy_today : c\.literacy_today\} \/>/.test(screen));
  assert.ok(/<TodayCard today=\{data\.today && data\.today\[selectedDomain\]\} \/>/.test(screen));
  assert.ok(/getProgressDashboard\(teacher\.teacher_id, localToday\(\)\)/.test(screen), 'asks for the phone\'s own today');
});

console.log('\nthe children to look at');
const flags = [
  { child_id: 'a', roll_number: 4, direction: 'higher', evidence_hi: '3 दिन लगातार सही' },
  { child_id: 'b', roll_number: 25, direction: 'lower', evidence_hi: '3 दिन लगातार गलती' },
];
const look = html(React.createElement(LookAtChildren, { flags }));
const screenHtml = look;
check('the Progress "look at these children" heading no longer uses the old "re-assess" wording that promised an assessment screen', () => {
  assert.ok(!/दोबारा आकलन पर विचार करें/.test(screenHtml) && /इन बच्चों पर एक नज़र/.test(screenHtml));
  assert.ok(!/दोबारा आकलन पर विचार करें|Consider re-assessing/.test(fs.readFileSync(path.join(src, 'screens', 'ProgressScreen.jsx'), 'utf8')));
});
check('it says what it is: daily evidence never changes a level by itself (one grey line, Hindi with English)', () => {
  assert.ok(look.includes('रोज़ की जाँच से बच्चे का स्तर अपने आप नहीं बदलता') && look.includes('डाल सकते हैं') && look.includes('on its own'));
});
check('two short lists, each with its own heading: doing well first, then struggling', () => {
  const up = look.indexOf('data-testid="look-at-higher"'), down = look.indexOf('data-testid="look-at-lower"');
  assert.ok(up > 0 && down > up);
  assert.ok(look.includes('⬆ अच्छा प्रदर्शन कर रहे हैं — एक छोटा दोबारा आकलन?') && look.includes('⬇ कठिनाई में हैं — थोड़ी मदद की ज़रूरत?'));
  assert.ok(look.slice(up, down).includes('रोल 4') && look.slice(down).includes('रोल 25'));
});
check('a list with nobody in it is left out, and no flags means no section', () => {
  const onlyUp = html(React.createElement(LookAtChildren, { flags: [flags[0]] }));
  assert.ok(onlyUp.includes('look-at-higher') && !onlyUp.includes('look-at-lower'));
  assert.equal(html(React.createElement(LookAtChildren, { flags: [] })), '');
});

console.log('\nHindi only');
check('every new line has its English in a hideable .en span (the "Hindi only" setting hides it)', () => {
  for (const en of ["In today&#x27;s sample", 'No assessment today', 'No decision recorded today', 'Your decision: Advance', 'assessed', 'Children to look at']) {
    const all = card + look + html(React.createElement(ChildToday, { today: { skill_id: 'N0.1.1', status: 'achieved' } }));
    const i = all.indexOf(en);
    assert.ok(i > 0 && all.lastIndexOf('class="en', i) > all.lastIndexOf('</span>', i), en);
  }
});

console.log(`\nOK: ${n} checks: the Today card, each child's result today and the children to look at show exactly what the server recorded for today`);
