// The time chip in the plan screen's title ("⏱ 60 मिनट") and the printed plan's "योजना समय": how long the plan is. It reads the length the SERVER recorded on the plan
// (session_minutes: the time the teacher chose), never the AI's own total_minutes; a plan made before that falls back to its blocks added up, rounded to 45 / 60 / 90
// when within 5 minutes. That the server records it is tested in backend/tests/test_plan_service.py. No browser and no server.
//
//     cd pwa
//     node tests/plan_time_chip.test.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
import React from 'react';
import ReactDOMServer from 'react-dom/server';

const here = path.dirname(fileURLToPath(import.meta.url));
const src = path.join(here, '..', 'src');
const out = path.join(here, `.tmp-chip-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));      // the temporary build folder is always removed, even if a check fails
const stubs = {
  '../App': 'export const useAuth = () => globalThis.__auth;',
  'react-router-dom': 'export const useNavigate = () => () => {};',
  '../services/api': 'export const getReviewChannels = async () => globalThis.__channels || ({ has_plan: false, levels: [], channels: {} }); export const getCachedPlan = async () => { throw new Error("none"); }; export const openAuthedPage = async () => {}; export const worksheetPath = (...a) => "/w/" + a.join("/"); export const prepareOfflineCopy = () => {};',
};
await build({
  entryPoints: { screen: path.join(src, 'screens/YojanaScreen.jsx'), print: path.join(src, 'screens/PlanPrint.jsx'), minutes: path.join(src, 'services/planMinutes.js') },
  bundle: true, format: 'esm', platform: 'node', outdir: out, outExtension: { '.js': '.mjs' }, loader: { '.js': 'jsx', '.jsx': 'jsx' }, external: ['react', 'react-dom'], logLevel: 'error',
  plugins: [{ name: 'stubs', setup(b) { b.onResolve({ filter: /^(\.\.\/App|react-router-dom|\.\.\/services\/api)$/ }, (a) => ({ path: a.path, namespace: 'stub' })); b.onLoad({ filter: /.*/, namespace: 'stub' }, (a) => ({ contents: stubs[a.path], loader: 'js' })); } }],
});
globalThis.localStorage = { getItem: () => null, setItem() {}, removeItem() {} };
const Screen = (await import(pathToFileURL(path.join(out, 'screen.mjs')).href)).default;
const Print = (await import(pathToFileURL(path.join(out, 'print.mjs')).href)).default;
const { planMinutes } = await import(pathToFileURL(path.join(out, 'minutes.mjs')).href);

let n = 0;
const check = (label, fn) => { fn(); n += 1; console.log(`  OK  ${label}`); };

// a plan whose blocks add up to `sum` minutes; `extra` goes into the plan (session_minutes, the AI's total_minutes)
const plan = (sum, extra = {}) => {
  const teach = Math.max(1, sum - 10 - 2 - 4);
  return { plan_date: '2026-10-28', domain_id: 'numeracy', selected_competency_id: 'N2.3.2', groups: [{ label: 'progressor', count: 14, target_competency_id: 'N2.3.2' }],
    plan: { anchor: {}, worksheets: {}, ...extra, rotation_schedule: { total_minutes: extra.total_minutes, blocks: [
      { type: 'anchor', duration_minutes: 10 }, { type: 'setup', duration_minutes: 2 }, { type: 'transition', duration_minutes: 4 }, { type: 'teach', teach_group: 'progressor', duration_minutes: teach }] } } };
};
const chip = (p) => {
  globalThis.__auth = { currentPlan: p, setCurrentPlan() {}, teacher: { teacher_id: 'T1', employee_code: 'MPT101', enrolled_grades: ['grade_2'] }, selectedDomain: 'numeracy' };
  const h = ReactDOMServer.renderToStaticMarkup(React.createElement(Screen));
  const m = h.match(/data-testid="time-chip" data-recorded="(true|false)"[^>]*>⏱ (?:<!-- -->)?(\d+)(?:<!-- -->)? मिनट<span class="en en-inline" lang="en"[^>]*>min<\/span>/);
  return m ? { minutes: Number(m[2]), recorded: m[1] === 'true', html: h } : { minutes: null, html: h };
};
const printTime = (p) => {
  globalThis.__auth = { currentPlan: p, setCurrentPlan() {}, teacher: { teacher_id: 'T1', employee_code: 'MPT101', enrolled_grades: ['grade_2'] }, selectedDomain: 'numeracy', names: {} };
  const h = ReactDOMServer.renderToStaticMarkup(React.createElement(Print));
  const m = h.match(/data-testid="print-time">([^<]*(?:<!-- -->[^<]*)*)</);
  return m ? m[1].replace(/<!-- -->/g, '') : null;
};

console.log('what the chip reads');
check('the length the server recorded, not the AI\'s total_minutes: session_minutes 60 with the AI\'s total_minutes 90 shows "⏱ 60 मिनट"', () => {
  const c = chip(plan(90, { session_minutes: 60, total_minutes: 90 }));
  assert.equal(c.minutes, 60); assert.equal(c.recorded, true);
});
check('...whatever the blocks add up to (a recorded 45 stays 45 even if the blocks say 52)', () => {
  assert.equal(chip(plan(52, { session_minutes: 45 })).minutes, 45);
});
check('the AI\'s total_minutes alone (an older plan, no session_minutes) is never used: the blocks are', () => {
  const c = chip(plan(75, { total_minutes: 90 }));
  assert.equal(c.minutes, 75); assert.equal(c.recorded, false);
});

console.log('\nthe fallback for a plan made before the server recorded it');
check('no session_minutes, blocks adding up to 87: "⏱ 90 मिनट" (within 5 of a preset: the preset)', () => {
  const c = chip(plan(87)); assert.equal(c.minutes, 90); assert.equal(c.recorded, false);
});
check('the window, both ways and for each preset: 85, 92, 95 -> 90; 56, 64 -> 60; 40, 48, 50 -> 45', () => {
  for (const [sum, want] of [[85, 90], [92, 90], [95, 90], [56, 60], [64, 60], [40, 45], [48, 45], [50, 45]]) assert.equal(planMinutes(plan(sum)).minutes, want, `${sum}`);
});
check('further than 5 from every preset: the exact sum (52, 75, 84, 96, 120)', () => {
  for (const sum of [52, 75, 84, 96, 120]) assert.equal(planMinutes(plan(sum)).minutes, sum, `${sum}`);
});
check('nothing to go on (no blocks, no recorded length): no chip at all', () => {
  const p = plan(90); p.plan.rotation_schedule.blocks = [];
  assert.equal(planMinutes(p), null);
  assert.ok(!chip(p).html.includes('time-chip'));
});

console.log('\nwhere it shows');
check('in the title, next to "दैनिक योजना", with the English "min" hideable', () => {
  const h = chip(plan(90, { session_minutes: 60 })).html;
  assert.ok(/<h1>📋 [\s\S]*?दैनिक योजना[\s\S]*?data-testid="time-chip"[\s\S]*?<\/h1>/.test(h));
});
check('the printed plan reads the same length: recorded is exact, the fallback says "लगभग"', () => {
  assert.equal(printTime(plan(90, { session_minutes: 60, total_minutes: 90 })), 'योजना समय: 60 मिनट');
  assert.equal(printTime(plan(87)), 'योजना समय: लगभग 90 मिनट');
  assert.equal(printTime(plan(75)), 'योजना समय: लगभग 75 मिनट');
});
check('neither the chip nor the print page reads total_minutes', () => {
  for (const f of ['services/planMinutes.js', 'screens/YojanaScreen.jsx', 'screens/PlanPrint.jsx']) {
    const code = fs.readFileSync(path.join(src, f), 'utf8').split('\n').filter((l) => !/^\s*\/\/|^\s*\*/.test(l)).join('\n');
    assert.ok(!code.includes('total_minutes'), f);
  }
});

console.log(`\nOK: ${n} checks: the time chip shows the length the server recorded (the teacher's choice), and an older plan its blocks added up, rounded to a preset within 5 minutes`);
