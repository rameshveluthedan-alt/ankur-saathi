// Plans with no connection (docs/drafts/OFFLINE_ASSEMBLER_PLAN.md, revised 23 Nov): the phone has the server prepare a plan for EVERY skill at
// 45 / 60 / 90 minutes, plus the suggested skill's own choice (its suggested group skills and re-teach), in small batches a low-end phone can
// hold; keeps them; downloads the full set again only when the library changes or weekly; finds the right one offline; sends plans made offline.
// A fake server and the memory store; no browser.
//
//     cd pwa
//     node tests/offline_plans.test.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';

const here = path.dirname(fileURLToPath(import.meta.url));
const src = path.join(here, '..', 'src');
const out = path.join(here, `.tmp-offline-plans-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));
fs.mkdirSync(out, { recursive: true });
const entry = path.join(out, 'entry.js');
fs.writeFileSync(entry, `export * from ${JSON.stringify(path.join(src, 'offline/offlinePlans.js'))};
export { memoryStore, openStore, requestPersistence } from ${JSON.stringify(path.join(src, 'offline/store.js'))};
export { initialRows, buildGenerateOptions } from ${JSON.stringify(path.join(src, 'services/groupSkills.js'))};`);
await build({ entryPoints: [entry], bundle: true, format: 'esm', platform: 'node', outfile: path.join(out, 'bundle.mjs'), loader: { '.js': 'jsx' }, logLevel: 'error' });
const m = await import(pathToFileURL(path.join(out, 'bundle.mjs')).href);

let failures = 0;
const check = (label, ok, extra) => { console.log(`  ${ok ? 'OK ' : 'FAIL'} ${label}${!ok && extra !== undefined ? '  ' + JSON.stringify(extra) : ''}`); if (!ok) failures += 1; };

console.log('keys and days');
check('a key is the same whatever the order of the groups and of the re-taught groups (and has no date: one copy serves any day)',
  m.planKey({ domain: 'numeracy', minutes: 45, competencyId: 'N2.3.2', groupSkills: { proficient: 'N3.3.1', beginner: 'N2.3.1' }, reteachGroups: ['progressor', 'beginner'] })
  === m.planKey({ domain: 'numeracy', minutes: '45', competencyId: 'N2.3.2', groupSkills: { beginner: 'N2.3.1', proficient: 'N3.3.1' }, reteachGroups: ['beginner', 'progressor'] }));
check('...and different for moving on and for a re-teach', m.planKey({ domain: 'numeracy', minutes: 60, competencyId: 'X', reteachGroups: [] })
  !== m.planKey({ domain: 'numeracy', minutes: 60, competencyId: 'X', reteachGroups: ['progressor'] }));
check('the next school day after Saturday 21 Nov 2026 is Monday (Sunday left out)', JSON.stringify(m.schoolDays('2026-11-21', 2)) === JSON.stringify(['2026-11-21', '2026-11-23']));

console.log('\nthe suggested skill');
const sk = (id, grade = 'grade_2') => ({ id, name_hi: id, grade_level: grade });
const proposal = {
  has_history: true, previous_date: '2026-11-20',
  groups: {
    beginner: { previous_target: sk('N2.3.1'), previous_decision: 'advance', proposed: sk('N2.2.9'), reason: 'advance', evidence: null },
    progressor: { previous_target: sk('N2.3.2'), previous_decision: null, proposed: sk('N2.3.2'), reason: 'recommended', evidence: null, recommendation: 'reteach' },
    proficient: { previous_target: sk('N3.3.1'), previous_decision: null, proposed: null, reason: 'no_decision', evidence: null },
  },
};
const ladders = { 'N2.3.2': { beginner: sk('N2.3.1'), progressor: sk('N2.3.2'), proficient: sk('N3.3.1'), options: { beginner: [], proficient: [] } } };
const ladderFor = async (id) => ladders[id] || { beginner: sk('N2.3.2'), progressor: sk(id), proficient: sk('N3.3.1'), options: { beginner: [], proficient: [] } };
const groups = [{ label: 'beginner', count: 8, roll_numbers: [1, 2] }, { label: 'progressor', count: 12, roll_numbers: [3, 4, 5] }, { label: 'proficient', count: 10, roll_numbers: [6] }];
check('the skill the last review points to for the Progressors', m.suggestedSkill(proposal) === 'N2.3.2');
check("a plan whose groups were not recorded: the previous plan's own skill", m.suggestedSkill({ has_history: true, previous_selected: 'N2.3.2', groups: {} }) === 'N2.3.2');
check('no history: nothing suggested', m.suggestedSkill({ has_history: false }) === null && m.suggestedSkill(null) === null);
const choices = await m.suggestedChoices({ proposal, groups, getLadder: ladderFor });
const own = m.buildGenerateOptions({ ...m.initialRows({ ladder: ladders['N2.3.2'], proposal, selectedId: 'N2.3.2' }), groups, ready: true });
check("its choice is EXACTLY what the Plan screen sends (its own initialRows and buildGenerateOptions): here a re-teach and a suggested Beginner skill",
  JSON.stringify(choices[0].groupSkills) === JSON.stringify(own.groupSkills) && JSON.stringify(choices[0].reteachGroups) === JSON.stringify(own.reteachGroups)
  && choices[0].reteachGroups.includes('progressor') && choices[0].groupSkills && choices[0].groupSkills.beginner === 'N2.2.9', { c: choices[0], own });
check('...and the same skill moving on with those group skills', choices.length === 2 && choices[1].reteachGroups.length === 0 && choices[1].groupSkills.beginner === 'N2.2.9');
check('a suggestion that is just the plain choice adds nothing (every skill has its plain plan)', (await m.suggestedChoices({ proposal: { has_history: true, previous_selected: 'N2.3.2', groups: {} }, groups, getLadder: ladderFor })).length === 0);

console.log('\npreparing: every skill, in small batches (low-end phones)');
const SKILLS = Array.from({ length: 30 }, (_, i) => ({ id: `N9.${i}.1` }));
const store = m.memoryStore();
let calls = []; let fail = null; let version = 'v1';
const api = {
  getCompetencies: async () => ({ competencies: SKILLS }),
  getGroupProposal: async () => proposal,
  getGroups: async () => ({ groups }),
  getLadder: ladderFor,
  prepareOfflinePlans: async (t, domain, its) => {
    calls.push(its.map((i) => i.key));
    if (fail && fail(calls.length, its)) { const e = new Error('offline'); e.name = 'NetworkError'; throw e; }
    return { library_version: version, plans: its.map((i) => (i.competency_id === 'N9.29.1' && i.session_minutes === 90 ? { key: i.key, ok: false, error: 'X' }
      : { key: i.key, ok: true, result: { plan_date: i.plan_date, selected_competency_id: i.competency_id, groups, plan: { session_minutes: i.session_minutes } } })) };
  },
};
let clock = Date.parse('2026-11-23T04:00:00Z');
const run = (o = {}) => m.refreshIfNeeded({ teacherId: 't1', domain: 'numeracy', today: '2026-11-23', api, store, emit: () => {}, batch: 25, pause: 0, now: () => clock, ...o });
let meta = await run();
const sizes = calls.map((c) => c.length);
check('the suggested choices first (2 x 3 lengths), then EVERY skill x 3 lengths in batches of at most 25', sizes[0] === 6 && sizes.slice(1).every((n) => n <= 25) && sizes.slice(1).reduce((a, b) => a + b, 0) === 90, sizes);
check('every skill is on the phone (one could not be built at one length: counted, not kept)', meta.status === 'ready' && meta.skills.length === 30 && meta.count === 6 + 89 && meta.failed === 1, { status: meta.status, n: meta.skills.length, count: meta.count, failed: meta.failed });
check("the status: ready (a plan can be made even without internet)", m.statusOf(meta).state === 'ready');
check('the suggested choice is remembered for when the group panel cannot load offline', meta.defaults && meta.defaults['N2.3.2'] && meta.defaults['N2.3.2'].reteachGroups.includes('progressor'));
check("the class's latest groups are kept (for the plan used offline)", JSON.stringify(meta.groups) === JSON.stringify(groups));
calls = [];
await run();
check('the same day again: nothing downloaded', calls.length === 0, calls.length);
calls = []; clock += 86400000;
await run({ today: '2026-11-24' });
check('a new day: only the suggested choices again (6), NOT the full set (data)', calls.length === 1 && calls[0].length === 6, calls.map((c) => c.length));
calls = [];
groups[0].roll_numbers = [1, 2, 7];
await run({ today: '2026-11-24' });
check('the groups changed (after a review): nothing downloaded; the latest groups kept', calls.length === 0 && (await store.get('meta', 'numeracy')).groups[0].roll_numbers.length === 3);
calls = []; version = 'v2'; clock += 86400000;
await run({ today: '2026-11-25' });
check('the library changed: the full set again', calls.length > 1 && calls.slice(1).reduce((a, c) => a + c.length, 0) === 90, calls.map((c) => c.length));
calls = []; clock += 8 * 86400000;
await run({ today: '2026-12-03' });
check('a week later: the full set again', calls.slice(1).reduce((a, c) => a + c.length, 0) === 90);

console.log('\nan interrupted download (a weak signal)');
const st2 = m.memoryStore();
calls = []; fail = (n) => n === 3;            // the second full batch fails
meta = await m.refreshIfNeeded({ teacherId: 't1', domain: 'numeracy', today: '2026-11-23', api, store: st2, emit: () => {}, batch: 25, pause: 0, now: () => clock });
check('what arrived is kept and usable: partial', m.statusOf(meta).state === 'partial' && meta.count > 0 && meta.lastError === 'NetworkError', { state: m.statusOf(meta).state, count: meta.count });
const firstBatch = new Set(calls[1]);
calls = []; fail = null;
meta = await m.refreshIfNeeded({ teacherId: 't1', domain: 'numeracy', today: '2026-11-23', api, store: st2, emit: () => {}, batch: 25, pause: 0, now: () => clock });
const asked = calls.flat();
check('the next try continues where it stopped (the batch already saved is not asked for again), and completes', !asked.some((k) => firstBatch.has(k)) && m.statusOf(meta).state === 'ready', { again: asked.filter((k) => firstBatch.has(k)).length, state: m.statusOf(meta).state });
check('no connection at all: what was prepared stays usable', m.statusOf(await m.refreshIfNeeded({ teacherId: 't1', domain: 'numeracy', today: '2026-11-23', store: st2, emit: () => {}, now: () => clock,
  api: { ...api, getCompetencies: async () => { const e = new Error('x'); e.name = 'NetworkError'; throw e; } } })).state === 'ready');
check('a refresh already running is shared, not started twice', await (async () => { const a = run({ force: true }); const b = run({ force: true }); const same = a === b; await a; return same; })());
check("one subject's download leaves the other subject's plans alone", await (async () => {
  await store.set('prepared', 'r1_literacy|60|L1.1.1||', { key: 'r1_literacy|60|L1.1.1||', domain: 'r1_literacy', kind: 'plain', epoch: 'x' });
  await run({ force: true });
  return !!(await store.get('prepared', 'r1_literacy|60|L1.1.1||'));
})());

check('plans kept by the first version (keys with a date, no kind) are removed by the next full download', await (async () => {
  await store.set('prepared', 'numeracy|2026-11-23|60|N2.3.2||', { key: 'numeracy|2026-11-23|60|N2.3.2||', domain: 'numeracy', result: {} });
  await run({ force: true });
  return !(await store.get('prepared', 'numeracy|2026-11-23|60|N2.3.2||'));
})());

console.log('\nfinding the plan offline');
const findIn = (o) => m.findPrepared(store, { domain: 'numeracy', minutes: 60, competencyId: 'N9.4.1', groupSkills: undefined, reteachGroups: [], ...o });
check('any skill at any length: its plain plan', !!(await findIn({})));
check("the suggested skill's own choice (re-teach, suggested Beginner skill)", !!(await findIn({ competencyId: 'N2.3.2', groupSkills: { beginner: 'N2.2.9' }, reteachGroups: ['progressor'] })));
check('a choice the teacher CHANGED in the panel and that was not prepared: nothing (never a different plan)', (await findIn({ groupSkills: { beginner: 'N1.1.1' }, allowPlain: false })) === null);
check('the panel loaded with the app\'s own suggestion for a skill (nothing changed): the plain plan is used', !!(await findIn({ groupSkills: { beginner: 'N1.1.1' }, allowPlain: true })));
check('a skill not downloaded: nothing', (await findIn({ competencyId: 'N0.0.0', allowPlain: true })) === null);
const meta2 = await store.get('meta', 'numeracy');
check("the panel could not load: the suggested skill's own choice, else the plain one", JSON.stringify(m.offlineChoice({ meta: meta2, competencyId: 'N2.3.2', panelReady: false }))
  === JSON.stringify({ groupSkills: { beginner: 'N2.2.9' }, reteachGroups: ['progressor'], allowPlain: true })
  && JSON.stringify(m.offlineChoice({ meta: meta2, competencyId: 'N9.4.1', panelReady: false })) === JSON.stringify({ reteachGroups: [], allowPlain: true }));
const rows = { beginner: { skillId: 'A', initialId: 'A', initialReteach: false }, progressor: { skillId: 'B', initialId: 'B', initialReteach: true } };
check('the panel as the app set it is not "edited"; a changed skill or tick is', !m.panelEdited(rows, { progressor: true })
  && m.panelEdited({ ...rows, beginner: { ...rows.beginner, skillId: 'C' } }, { progressor: true }) && m.panelEdited(rows, { progressor: false }));
const made = m.makeOfflinePlan({ plan_date: '2026-11-23', served_from: 'library', domain_id: 'numeracy', groups: [{ label: 'beginner', count: 2, roll_numbers: [1, 2], target_competency_id: 'N2.3.1' }], plan: { a: 1 } },
  { date: '2026-11-28', clientId: 'c1', teacherId: 'T1', groups: [{ label: 'beginner', roll_numbers: [1, 2, 7] }], now: new Date('2026-11-28T03:00:00Z') });
check('the plan used offline: dated for the day used, marked, with the latest groups (its skills unchanged), nothing else changed',
  made.plan_date === '2026-11-28' && made.served_from === 'library_offline' && made.plan.a === 1 && made.groups[0].count === 3 && made.groups[0].target_competency_id === 'N2.3.1'
  && JSON.stringify(made.offline) === JSON.stringify({ client_id: 'c1', prepared_for: '2026-11-23', made_at: '2026-11-28T03:00:00.000Z', sent: false, teacher_id: 'T1' }));
check('client ids are unique', m.newClientId() !== m.newClientId() && m.newClientId(() => 'x') === 'x');

console.log('\nsending (step 4)');
const st3 = m.memoryStore();
const offPlan = (date, cid, teacher = 'T1', domain = 'numeracy') => m.makeOfflinePlan({ plan_date: date, domain_id: domain, selected_competency_id: 'N2.3.2', groups: [{ label: 'beginner', roll_numbers: [1] }],
  explainability: { items: [] }, plan: { rotation_schedule: { blocks: [] }, worksheets: {} } }, { date, clientId: cid, teacherId: teacher });
await m.saveOfflinePlan(st3, offPlan('2026-11-26', 'b'));
await m.saveOfflinePlan(st3, offPlan('2026-11-25', 'a'));
await m.saveOfflinePlan(st3, offPlan('2026-11-27', 'c', 'T1', 'r1_literacy'));
const sentBodies = [];
const answers = { a: async () => ({ status: 'stored' }), b: async () => ({ status: 'duplicate' }), c: async () => { const e = new Error('x'); e.status = 409; e.code = 'plan_exists'; throw e; } };
let res = await m.sendWaiting({ teacherId: 'T1', store: st3, api: { uploadOfflinePlan: async (t, body) => { sentBodies.push(body); return answers[body.client_id](); } } });
check('oldest first; each sent with its client id, day, subject, skill, the day prepared for and the plan', JSON.stringify(sentBodies.map((b) => b.client_id)) === JSON.stringify(['a', 'b', 'c'])
  && sentBodies[0].plan_date === '2026-11-25' && sentBodies[0].competency_id === 'N2.3.2' && sentBodies[0].prepared_for === '2026-11-25' && sentBodies[0].result.plan && sentBodies[0].result.groups.length === 1);
check("stored, duplicate (a retry), and the server's plan kept: each removed from the phone", JSON.stringify(res.map((r) => r.status)) === JSON.stringify(['stored', 'duplicate', 'kept_server'])
  && (await m.waitingPlans(st3)).length === 0 && (await st3.keys('outbox')).length === 0);
await m.saveOfflinePlan(st3, offPlan('2026-11-28', 'd'));
await m.saveOfflinePlan(st3, offPlan('2026-11-29', 'e'));
let tries = 0;
res = await m.sendWaiting({ teacherId: 'T1', store: st3, api: { uploadOfflinePlan: async () => { tries += 1; const e = new Error('इंटरनेट नहीं'); e.name = 'NetworkError'; throw e; } } });
check('no connection: the first waits and the rest are not tried (sent next time)', tries === 1 && res.length === 1 && res[0].status === 'waiting' && (await m.waitingPlans(st3)).length === 2);
res = await m.sendWaiting({ teacherId: 'T1', store: st3, api: { uploadOfflinePlan: async (t, b) => { if (b.client_id === 'd') { const e = new Error('bad'); e.status = 400; throw e; } return { status: 'stored' }; } } });
check('a plan the server refuses (400) stays on the phone, is never sent again, and does not stop the others', JSON.stringify(res.map((r) => r.status)) === JSON.stringify(['refused', 'stored'])
  && (await m.waitingPlans(st3)).length === 0 && (await st3.keys('outbox')).length === 1);
res = await m.sendWaiting({ teacherId: 'T1', store: st3, api: { uploadOfflinePlan: async () => { throw new Error('never'); } } });
check('...and is not tried again', res.length === 0);
await m.saveOfflinePlan(st3, offPlan('2026-11-30', 'f', 'T2'));
check("another teacher's plan is never sent with this teacher's sign-in", (await m.waitingPlans(st3, 'T1')).length === 0 && (await m.waitingPlans(st3, 'T2')).length === 1);
await m.dropOthersPlans(st3, 'T1');
check("...and is removed when this teacher signs in on the phone (it is the other class's data)", (await m.waitingPlans(st3, 'T2')).length === 0);
await m.clearOutbox(st3);
check('signing out (after being asked) removes the plans made offline', (await st3.keys('outbox')).length === 0);
await m.saveOfflinePlan(st3, made);
await m.saveOfflinePlan(st3, { ...made, offline: { ...made.offline, client_id: 'c2' } });
check('one offline plan per subject and day (a second made the same day replaces the first)', (await m.waitingPlans(st3)).length === 1 && (await m.getOfflinePlan(st3, 'numeracy', '2026-11-28')).offline.client_id === 'c2');

console.log('\nstatus states and sign-out');
check('nothing kept: missing', m.statusOf(undefined).state === 'missing');
check('while preparing: preparing, with how far', JSON.stringify(m.statusOf({ preparing: true, done: 50, total: 303 })) === JSON.stringify({ state: 'preparing', done: 50, total: 303, skills: [] }));
check('ready with no plan kept counts as missing', m.statusOf({ status: 'ready', count: 0 }).state === 'missing');
await m.clearOfflinePlans(store);
check('sign-out removes every prepared plan and the status', (await store.keys('prepared')).length === 0 && (await store.get('meta', 'numeracy')) === undefined);
check('with no IndexedDB the memory store is used (nothing breaks)', (await m.openStore(null)).kind === 'memory');
check('persistence asked for when the browser offers it', await m.requestPersistence({ storage: { persisted: async () => false, persist: async () => true } }) === true);
check('...and no error when it does not', await m.requestPersistence({}) === false);

if (failures) { console.log(`\nFAILED (${failures})`); process.exit(1); }
console.log('\nOK: every skill is prepared in small batches, downloaded again only when the library changes or weekly, found offline, and plans made offline are sent');
