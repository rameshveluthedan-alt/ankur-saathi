// Plans with no connection, step 2 (docs/drafts/OFFLINE_ASSEMBLER_PLAN.md): which plans the phone prepares, preparing them through the server,
// keeping them, refreshing them, and the status line's states. A fake server and the memory store; no browser.
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
check('a key is the same whatever the order of the groups and of the re-taught groups',
  m.planKey({ domain: 'numeracy', date: '2026-11-24', minutes: 45, competencyId: 'N2.3.2', groupSkills: { proficient: 'N3.3.1', beginner: 'N2.3.1' }, reteachGroups: ['progressor', 'beginner'] })
  === m.planKey({ domain: 'numeracy', date: '2026-11-24', minutes: '45', competencyId: 'N2.3.2', groupSkills: { beginner: 'N2.3.1', proficient: 'N3.3.1' }, reteachGroups: ['beginner', 'progressor'] }));
check('...and different for moving on and for a re-teach', m.planKey({ domain: 'numeracy', date: 'd', minutes: 60, competencyId: 'X', reteachGroups: [] })
  !== m.planKey({ domain: 'numeracy', date: 'd', minutes: 60, competencyId: 'X', reteachGroups: ['progressor'] }));
check('three school days from Saturday 21 Nov 2026: Saturday, Monday, Tuesday (Sunday left out)',
  JSON.stringify(m.schoolDays('2026-11-21', 3)) === JSON.stringify(['2026-11-21', '2026-11-23', '2026-11-24']), m.schoolDays('2026-11-21', 3));

console.log('\nwhich plans');
const sk = (id, grade = 'grade_2') => ({ id, name_hi: id, grade_level: grade });
const proposal = {
  has_history: true, previous_date: '2026-11-20',
  groups: {
    beginner: { previous_target: sk('N2.3.1'), previous_decision: 'advance', proposed: sk('N2.3.2'), reason: 'advance', evidence: null },
    progressor: { previous_target: sk('N2.3.2'), previous_decision: null, proposed: sk('N2.3.2'), reason: 'recommended', evidence: null, recommendation: 'reteach' },
    proficient: { previous_target: sk('N3.3.1'), previous_decision: null, proposed: null, reason: 'no_decision', evidence: null },
  },
};
const ladders = {
  'N2.3.2': { beginner: sk('N2.3.1'), progressor: sk('N2.3.2'), proficient: sk('N3.3.1'), options: { beginner: [], proficient: [sk('N3.3.1', 'grade_3'), sk('N2.4.1'), sk('N2.3.3'), sk('N2.3.4'), sk('N2.3.5')] } },
};
const ladderFor = async (id) => ladders[id] || { beginner: sk('N2.3.2'), progressor: sk(id), proficient: sk('N3.3.1'), options: { beginner: [], proficient: [] } };
const groups = [{ label: 'beginner', count: 8 }, { label: 'progressor', count: 12 }, { label: 'proficient', count: 10 }];
check('the suggested skill is the one the last review points to for the Progressors', m.suggestedSkill(proposal) === 'N2.3.2');
check('no history: nothing to suggest', m.suggestedSkill({ has_history: false }) === null && m.suggestedSkill(null) === null);
const { skills, choices } = await m.likelyChoices({ proposal, groups, getLadder: ladderFor });
check('the suggested skill and the next 3 on its ladder', JSON.stringify(skills) === JSON.stringify(['N2.3.2', 'N3.3.1', 'N2.4.1', 'N2.3.3']), skills);
const own = m.buildGenerateOptions({ ...m.initialRows({ ladder: ladders['N2.3.2'], proposal, selectedId: 'N2.3.2' }), groups, ready: true });
const first = choices[0];
check("the suggested skill's choice is EXACTLY what the Plan screen sends (its own initialRows and buildGenerateOptions)",
  JSON.stringify(first.groupSkills) === JSON.stringify(own.groupSkills) && JSON.stringify(first.reteachGroups) === JSON.stringify(own.reteachGroups), { first, own });
check('...here a re-teach of the Progressors (the evidence recommends it)', first.reteachGroups.includes('progressor'));
check('...and the same skill moving on is prepared too', choices[1].competencyId === 'N2.3.2' && choices[1].reteachGroups.length === 0);
check('5 choices in all (the suggested skill twice, 3 ahead once)', choices.length === 5, choices.length);
const items = m.itemsFor('numeracy', choices, m.schoolDays('2026-11-23', 3));
check('45 plans per subject (5 choices x 3 lengths x 3 days): 90 for both, under the 120 a request allows', items.length === 45);
check('every item carries its key and the request fields', items.every((i) => i.key.startsWith('numeracy|') && i.competency_id && i.plan_date && [45, 60, 90].includes(i.session_minutes) && Array.isArray(i.reteach_groups)));

console.log('\npreparing, refreshing, failing');
const store = m.memoryStore();
const calls = [];
let fail = false;
const api = {
  getGroupProposal: async () => proposal,
  getGroups: async () => ({ groups }),
  getLadder: ladderFor,
  prepareOfflinePlans: async (t, domain, its) => {
    calls.push(its.length);
    if (fail) { const e = new Error('offline'); e.name = 'NetworkError'; throw e; }
    return { library_version: 'abc123def456', plans: its.map((i, n) => (n === 0 ? { key: i.key, ok: false, error: 'X' } : { key: i.key, ok: true, result: { plan: { session_minutes: i.session_minutes }, selected_competency_id: i.competency_id } })) };
  },
};
const emitted = [];
const run = (o = {}) => m.refreshIfNeeded({ teacherId: 't1', domain: 'numeracy', today: '2026-11-23', api, store, emit: (d) => emitted.push(d), ...o });
let meta = await run();
check('prepared: one request of 45; the plans kept under their keys', calls.length === 1 && calls[0] === 45 && (await store.keys('prepared')).length === 44, { calls, n: (await store.keys('prepared')).length });
check('the status: ready, with its skills and the last day prepared', JSON.stringify(m.statusOf(meta)) === JSON.stringify({ state: 'ready', skills: ['N2.3.2', 'N3.3.1', 'N2.4.1', 'N2.3.3'], until: '2026-11-25', preparedFor: '2026-11-23' }), m.statusOf(meta));
check('a choice the server could not build is counted, not kept', meta.failed === 1 && meta.libraryVersion === 'abc123def456');
check('the status line is told (before and after)', emitted.length >= 2);
await run();
check('the same day, the same suggestions: NOT prepared again', calls.length === 1, calls);
proposal.groups.proficient.previous_decision = 'reteach';
await run();
check('the suggestions changed (a review was saved): prepared again', calls.length === 2, calls);
await run({ force: true });
check('"download now" prepares again whatever', calls.length === 3);
await run({ today: '2026-11-24' });
check('a new day: prepared again', calls.length === 4);
fail = true;
meta = await run({ force: true });
check('no connection: what was prepared stays (still ready), and the failure is noted', m.statusOf(meta).state === 'ready' && meta.lastError === 'NetworkError' && (await store.keys('prepared')).length === 44, meta);
fail = false;
await store.setMany('prepared', [['r1_literacy|x', { key: 'r1_literacy|x' }]]);
await run({ force: true });
check("preparing one subject leaves the other subject's plans alone", (await store.keys('prepared')).includes('r1_literacy|x'));
meta = await m.refreshIfNeeded({ teacherId: 't1', domain: 'r1_literacy', today: '2026-11-23', store, emit: () => {},
  api: { ...api, getGroupProposal: async () => ({ has_history: false, groups: {} }) } });
check('a subject with no plan yet: nothing can be suggested (the line says to make one plan online first)', m.statusOf(meta).state === 'no_history' && !(await store.keys('prepared')).includes('r1_literacy|x'));
check('a refresh already running is shared, not started twice', await (async () => { const a = run({ force: true }); const b = run({ force: true }); const same = a === b; await a; return same; })());

console.log('\nstatus states and sign-out');
check('nothing kept: missing', m.statusOf(undefined).state === 'missing');
check('while preparing: preparing', m.statusOf({ preparing: true }).state === 'preparing');
check('ready with no plan kept counts as missing', m.statusOf({ status: 'ready', count: 0 }).state === 'missing');
await m.clearOfflinePlans(store);
check('sign-out removes every prepared plan and the status', (await store.keys('prepared')).length === 0 && (await store.get('meta', 'numeracy')) === undefined);
check('with no IndexedDB the memory store is used (nothing breaks)', (await m.openStore(null)).kind === 'memory');
check('persistence asked for when the browser offers it', await m.requestPersistence({ storage: { persisted: async () => false, persist: async () => true } }) === true);
check('...and no error when it does not', await m.requestPersistence({}) === false);

if (failures) { console.log(`\nFAILED (${failures})`); process.exit(1); }
console.log('\nOK: the phone prepares the plans it may need (the screen\'s own choices), keeps and refreshes them, and removes them at sign-out');
