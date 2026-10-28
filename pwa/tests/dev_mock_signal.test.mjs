// The LAB PHONE TEST mock (services/devMockSignal.js): with VITE_MOCK_SIGNAL=1 the fetch wrapper (api.js request) puts a `signal` on each teach block of a plan
// that has none, in the server's contract, so the signal panel can be tried before the server sends it. Without the setting nothing changes. No browser and no server.
// (A normal `vite build` leaves the mock out entirely: checked by building once with and once without the setting.)
//
//     cd pwa
//     node tests/dev_mock_signal.test.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';

const here = path.dirname(fileURLToPath(import.meta.url));
const src = path.join(here, '..', 'src');
const out = path.join(here, `.tmp-mock-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));      // the temporary build folder is always removed, even if a check fails
const bundle = (name, env) => build({ entryPoints: { [name]: path.join(src, 'services/api.js') }, bundle: true, format: 'esm', platform: 'node', outdir: out, outExtension: { '.js': '.mjs' },
  logLevel: 'error', define: { 'import.meta.env': JSON.stringify(env) } });
await bundle('api_mock', { VITE_MOCK_SIGNAL: '1' });
await bundle('api_plain', {});
await build({ entryPoints: { mock: path.join(src, 'services/devMockSignal.js') }, bundle: true, format: 'esm', platform: 'node', outdir: out, outExtension: { '.js': '.mjs' }, logLevel: 'error' });
const mock = await import(pathToFileURL(path.join(out, 'mock.mjs')).href);
const apiMock = await import(pathToFileURL(path.join(out, 'api_mock.mjs')).href);
const apiPlain = await import(pathToFileURL(path.join(out, 'api_plain.mjs')).href);

let n = 0;
const check = async (label, fn) => { await fn(); n += 1; console.log(`  OK  ${label}`); };

const teach = (g, extra = {}) => ({ type: 'teach', teach_group: g, duration_minutes: 15, ...extra });
const reply = (domain, blocks) => ({ domain_id: domain, plan_date: '2026-10-28', plan: { rotation_schedule: { blocks } } });
const three = () => [{ type: 'anchor' }, teach('progressor'), { type: 'transition' }, teach('beginner'), teach('proficient')];
const sig = (r, g) => r.plan.rotation_schedule.blocks.find((b) => b.teach_group === g).signal;

console.log('the mock');
await check('maths: every teach block gets three core questions and extra_count 2, in the server\'s contract', () => {
  const r = mock.withMockSignal(reply('numeracy', three()));
  for (const g of ['beginner', 'progressor', 'proficient']) {
    const s = sig(r, g);
    assert.equal(s.shape, 'maths_questions'); assert.equal(typeof s.signal_curated, 'boolean');
    assert.equal(s.maths_questions.core.length, 3); assert.equal(s.maths_questions.extra_count, 2);
    assert.ok(!('writing_prompt' in s), 'only the key matching the shape');
  }
});
await check('literacy: the Beginners get a writing prompt and the others shape null (so a phone shows both)', () => {
  const r = mock.withMockSignal(reply('r1_literacy', three()));
  assert.equal(sig(r, 'beginner').shape, 'writing_prompt'); assert.ok(sig(r, 'beginner').writing_prompt.prompt.length > 5);
  assert.equal(sig(r, 'progressor').shape, null); assert.equal(sig(r, 'proficient').shape, null);
});
await check('a block that already has a signal (the server\'s, even shape null) is never touched: once the server sends it, the mock does nothing', () => {
  const real = { shape: null, signal_curated: false };
  const own = { shape: 'maths_questions', signal_curated: false, maths_questions: { core: ['A', 'B', 'C'], extra_count: 1 } };
  const r = mock.withMockSignal(reply('numeracy', [teach('progressor', { signal: own }), teach('beginner', { signal: real })]));
  assert.deepEqual(sig(r, 'progressor'), own); assert.deepEqual(sig(r, 'beginner'), real);
});
await check('other blocks are left alone, and the reply itself is not changed (a new object is returned)', () => {
  const orig = reply('numeracy', three()); const before = JSON.stringify(orig);
  const r = mock.withMockSignal(orig);
  assert.equal(JSON.stringify(orig), before);
  assert.ok(r.plan.rotation_schedule.blocks.filter((b) => b.type !== 'teach').every((b) => !('signal' in b)));
  assert.equal(r.mock_signal, true);
  assert.equal(mock.withMockSignal({ detail: 'x' }).detail, 'x', 'a reply that is not a plan passes through');
});
await check('only the plan addresses: POST /plan/generate and GET /plan/{teacher}/{date}/{subject}', () => {
  for (const p of ['/plan/generate?teacher_id=T1', '/plan/T1/2026-10-28/numeracy']) assert.ok(mock.isPlanPath(p), p);
  for (const p of ['/plan/competencies/numeracy', '/plan/groups/T1/numeracy', '/plan/proposal/T1/numeracy?plan_date=2026-10-28', '/plan/ladder/N2.3.2', '/progress/dashboard/T1']) assert.ok(!mock.isPlanPath(p), p);
});

console.log('\nthe fetch wrapper');
const serve = (body) => { globalThis.fetch = async () => ({ ok: true, status: 200, json: async () => JSON.parse(JSON.stringify(body)) }); };
await check('with VITE_MOCK_SIGNAL=1: a stored plan comes back with the mock signal on its teach blocks', async () => {
  serve(reply('numeracy', three()));
  const r = await apiMock.getCachedPlan('T1', '2026-10-28', 'numeracy');
  assert.equal(sig(r, 'progressor').shape, 'maths_questions');
});
await check('...and a new plan (POST /plan/generate) too', async () => {
  serve(reply('r1_literacy', three()));
  const r = await apiMock.generatePlan('T1', 'L2.7.2', 'r1_literacy', '2026-10-28', { sessionMinutes: 45 });
  assert.equal(sig(r, 'beginner').shape, 'writing_prompt');
});
await check('...but other replies are untouched (the groups list)', async () => {
  serve({ groups: [{ label: 'beginner', count: 7 }] });
  assert.deepEqual(await apiMock.getGroups('T1', 'numeracy'), { groups: [{ label: 'beginner', count: 7 }] });
});
await check('without the setting (every normal build): the plan comes back exactly as the server sent it', async () => {
  serve(reply('numeracy', three()));
  const r = await apiPlain.getCachedPlan('T1', '2026-10-28', 'numeracy');
  assert.ok(r.plan.rotation_schedule.blocks.every((b) => !('signal' in b)) && !('mock_signal' in r));
});

console.log(`\nOK: ${n} checks: the lab mock fills in a signal only with VITE_MOCK_SIGNAL=1, only on plans, and never over the server's own`);
