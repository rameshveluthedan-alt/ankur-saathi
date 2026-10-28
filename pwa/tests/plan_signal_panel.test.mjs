// The signal panel in each teach block of the plan screen (YojanaScreen): what the children will do, visible without a tap. Two shapes this round: the three core
// maths questions (with a grey line naming the extras) and the writing prompt (larger, read aloud). Any other shape, or none, renders nothing.
// The REAL plan screen is rendered with a fixture plan, the way the server's `signal` will arrive (the server work is separate). No browser and no server.
//
//     cd pwa
//     node tests/plan_signal_panel.test.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
import React from 'react';
import ReactDOMServer from 'react-dom/server';

const here = path.dirname(fileURLToPath(import.meta.url));
const src = path.join(here, '..', 'src');
const out = path.join(here, `.tmp-signal-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));      // the temporary build folder is always removed, even if a check fails
const stubs = {
  '../App': 'export const useAuth = () => globalThis.__auth;',
  '../services/api': 'export const getCachedPlan = async () => { throw new Error("none"); }; export const openAuthedPage = async () => {}; export const worksheetPath = (...a) => "/worksheet/" + a.join("/"); export const prepareOfflineCopy = () => {};',
};
await build({
  entryPoints: { screen: path.join(src, 'screens/YojanaScreen.jsx'), panel: path.join(src, 'components/SignalPanel.jsx') },
  bundle: true, format: 'esm', platform: 'node', outdir: out, outExtension: { '.js': '.mjs' }, loader: { '.js': 'jsx', '.jsx': 'jsx' }, external: ['react', 'react-dom'], logLevel: 'error',
  plugins: [{ name: 'stubs', setup(b) { b.onResolve({ filter: /^(\.\.\/App|\.\.\/services\/api)$/ }, (a) => ({ path: a.path, namespace: 'stub' })); b.onLoad({ filter: /.*/, namespace: 'stub' }, (a) => ({ contents: stubs[a.path], loader: 'js' })); } }],
});
const Screen = (await import(pathToFileURL(path.join(out, 'screen.mjs')).href)).default;
const { QUESTION_SIZE, PROMPT_SIZE } = await import(pathToFileURL(path.join(out, 'panel.mjs')).href);

let n = 0;
const check = (label, fn) => { fn(); n += 1; console.log(`  OK  ${label}`); };

// a plan the way the server sends it, with one teach block per group; `signals` sets each group's block signal (undefined: the field is absent, as in a plan made before)
const maths = (core, extra_count = 2, curated = true) => ({ shape: 'maths_questions', signal_curated: curated, maths_questions: { core, extra_count } });
const writing = (prompt) => ({ shape: 'writing_prompt', signal_curated: false, writing_prompt: { prompt } });
const planWith = (signals) => {
  const teach = (g, script) => ({ type: 'teach', teach_group: g, duration_minutes: 15, time_start: '0:12', script_hi: script, talking_points: { i_do_hi: 'मैं', we_do_hi: 'हम', you_do_hi: 'तुम' },
    ...(signals[g] !== undefined ? { signal: signals[g] } : {}) });
  return {
    plan_date: '2026-10-28', domain_id: 'numeracy', selected_competency_id: 'N2.3.2',
    groups: [{ label: 'beginner', count: 7, target_competency_id: 'N2.3.1' }, { label: 'progressor', count: 14, target_competency_id: 'N2.3.2' }, { label: 'proficient', count: 9, target_competency_id: 'N3.3.1' }],
    plan: { anchor: {}, worksheets: {}, rotation_schedule: { blocks: [{ type: 'anchor', duration_minutes: 10 }, teach('progressor', 'पहले एक जोड़ दिखाओ'), teach('beginner', 'तीली से गिनो'), teach('proficient', 'तीन अंकों का जोड़')] } },
  };
};
const render = (signals) => {
  globalThis.__auth = { currentPlan: planWith(signals), setCurrentPlan() {}, teacher: { teacher_id: 'T1' }, selectedDomain: 'numeracy' };
  return ReactDOMServer.renderToStaticMarkup(React.createElement(Screen));
};
// one group's teach block, from its opening tag to the next block
const blockOf = (h, group) => {
  const i = h.indexOf(`tier-${group}" role="button"`);
  const start = h.lastIndexOf('<div', i);
  const next = h.indexOf('class="timeline-block', i + 1);
  return h.slice(start, next > 0 ? next : undefined);
};
const questions = (h) => [...h.matchAll(/<li data-testid="core-question">([^<]*)<\/li>/g)].map((m) => m[1]);
const rem = (s) => parseFloat(s);

console.log('the maths shape');
const h = render({ progressor: maths(['Q1', 'Q2', 'Q3']), beginner: writing('x y z'), proficient: null });
const prog = blockOf(h, 'progressor');
check('three core questions render exactly 3 numbered lines (an <ol>), in the server\'s order', () => {
  assert.ok(prog.includes('data-testid="signal-panel" data-shape="maths_questions"') && /<ol data-testid="core-questions"/.test(prog));
  assert.deepEqual(questions(prog), ['Q1', 'Q2', 'Q3']);
});
check('the questions on the block equal the server\'s core array, whatever it holds (a dropped or reordered one fails here)', () => {
  const core = ['23 + 15 = ?', '36 + 29 = ?', '48 + 37 = ?'];
  assert.deepEqual(questions(blockOf(render({ progressor: maths(core) }), 'progressor')), core);
  assert.deepEqual(questions(blockOf(render({ progressor: maths(['48 + 37 = ?', '23 + 15 = ?', '36 + 29 = ?']) }), 'progressor')), ['48 + 37 = ?', '23 + 15 = ?', '36 + 29 = ?']);
});
check('the title "तीन मुख्य प्रश्न" with its English hideable', () => {
  assert.ok(/तीन मुख्य प्रश्न<span class="en en-inline" lang="en">The three core questions<\/span>/.test(prog));
});
check('extra_count 2 says "2 और प्रश्न …", extra_count 1 says "1 और प्रश्न …" (the count is the server\'s), in a smaller grey line inside the panel', () => {
  assert.ok(prog.includes('data-extra="2"') && prog.includes('→ 2 और प्रश्न (जो जल्दी ख़त्म करें उनके लिए)') && prog.includes('2 more questions (for early finishers)'));
  const one = blockOf(render({ progressor: maths(['Q1', 'Q2', 'Q3'], 1) }), 'progressor');
  assert.ok(one.includes('data-extra="1"') && one.includes('→ 1 और प्रश्न (') && !one.includes('2 और प्रश्न') && one.includes('1 more question (for'));
  const panel = prog.slice(prog.indexOf('data-testid="signal-panel"'));
  assert.ok(panel.indexOf('data-testid="extra-line"') > panel.indexOf('</ol>'), 'below the questions');
  assert.ok(/data-testid="extra-line"[^>]*style="font-size:0.75rem;color:var\(--text-secondary\)/.test(panel), 'small and grey');
});
check('no extras: no extras line', () => {
  assert.ok(!blockOf(render({ progressor: maths(['Q1', 'Q2', 'Q3'], 0) }), 'progressor').includes('extra-line'));
});
check('signal_curated false renders exactly as true: no "random" note, no badge for curated skills either', () => {
  const t = blockOf(render({ progressor: maths(['Q1', 'Q2', 'Q3'], 2, true) }), 'progressor');
  const f = blockOf(render({ progressor: maths(['Q1', 'Q2', 'Q3'], 2, false) }), 'progressor');
  assert.equal(f, t);
  assert.ok(!/curated|यादृच्छिक|random|AI ने चुने/i.test(f));
});

console.log('\nthe writing shape');
const beg = blockOf(h, 'beginner');
check('the prompt renders in the writing panel, under the title "लेखन कार्य"', () => {
  assert.ok(beg.includes('data-shape="writing_prompt"') && /data-testid="writing-prompt"[^>]*>x y z<\/div>/.test(beg));
  assert.ok(/लेखन कार्य<span class="en en-inline" lang="en">Writing prompt<\/span>/.test(beg));
  assert.ok(!beg.includes('core-question'));
});
check(`the prompt is LARGER than a maths question (${PROMPT_SIZE} > ${QUESTION_SIZE}): the teacher reads it aloud`, () => {
  const p = beg.match(/data-testid="writing-prompt"[^>]*style="font-size:([\d.]+rem)/);
  const q = prog.match(/data-testid="core-questions" style="[^"]*font-size:([\d.]+rem)/);
  assert.ok(p && q, 'both sizes found');
  assert.ok(rem(p[1]) > rem(q[1]), `${p[1]} > ${q[1]}`);
});
check('a long prompt is cut at two lines with "…" (CSS line clamp), the whole text kept for the worksheet', () => {
  const css = fs.readFileSync(path.join(src, 'index.css'), 'utf8');
  assert.match(css, /\.signal-prompt\s*\{[^}]*-webkit-line-clamp:\s*2[^}]*overflow:\s*hidden/);
  const long = 'अपने परिवार के बारे में तीन वाक्य लिखो। '.repeat(8).trim();
  assert.ok(blockOf(render({ beginner: writing(long) }), 'beginner').includes(`title="${long}"`));
});

console.log('\nthe empty shapes');
const none = blockOf(render({}), 'proficient');
check('shape null renders no panel, and the block is exactly what it was before (same markup as a plan with no signal at all)', () => {
  const nul = blockOf(h, 'proficient');
  assert.ok(!nul.includes('signal-panel'));
  assert.equal(nul, none);
});
check('shapes not shipped this round (passage_questions, word_list) render no panel either, nor does an unknown one', () => {
  // every payload is filled in, so a shape wrongly sent down the maths or the writing path would show something
  const full = { maths_questions: { core: ['Q1', 'Q2', 'Q3'], extra_count: 2 }, writing_prompt: { prompt: 'x y z' },
    passage_questions: { passage: 'एक कहानी', questions: ['Q1'] }, word_list: { words: ['कमल', 'नल'] } };
  for (const shape of ['passage_questions', 'word_list', 'something_new']) {
    assert.equal(blockOf(render({ proficient: { shape, signal_curated: true, ...full } }), 'proficient'), none, shape);
  }
});
check('a maths or writing shape with nothing in it renders no empty box', () => {
  assert.equal(blockOf(render({ proficient: maths([]) }), 'proficient'), none);
  assert.equal(blockOf(render({ proficient: writing('  ') }), 'proficient'), none);
});

console.log('\nwhere it sits');
check('under the one-line script, above the closed talking points and understanding check', () => {
  const script = prog.indexOf('पहले एक जोड़ दिखाओ'), panel = prog.indexOf('data-testid="signal-panel"'), more = prog.indexOf('▸ बात के मुद्दे');
  assert.ok(script > -1 && panel > script && more > panel, `${script} < ${panel} < ${more}`);
  assert.ok(!prog.includes('मैं करूँगा'), 'the talking points stay closed');
});
check('the block title names the group\'s skill today ("— N2.3.2"), from the plan\'s groups', () => {
  assert.ok(/data-testid="block-skill"[^>]*> — (<!-- -->)?N2\.3\.2<\/span>/.test(prog) && /block-skill[^>]*> — (<!-- -->)?N2\.3\.1</.test(beg));
});
check('the worksheet buttons are unchanged: the panel is not a second link', () => {
  const panel = prog.slice(prog.indexOf('data-testid="signal-panel"'));
  assert.ok(!/<a |<button|onClick/.test(panel.slice(0, panel.indexOf('</ol>'))));
});

console.log(`\nOK: ${n} checks: each teach block shows what the children will do (three core questions or a writing prompt), and nothing for other shapes`);
