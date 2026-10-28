// The REAL Plan screen in a simulated browser, with a fake server whose answers the test releases by hand. It checks what no static render can:
// the group panel is a drawer in the bottom bar that opens in place (the page never scrolls), choosing another skill clears the previous skill's groups at once and keeps
// Generate disabled until the new ones arrive, an answer that arrives late for an earlier skill is ignored, and a failed fetch does not leave Generate stuck.
//
//     cd pwa
//     npm install --save-dev jsdom@24     (once: it is only used by this test; version 24 works with Node 18 and up, the newest jsdom needs a very recent Node)
//     node tests/plan_screen.dom.test.mjs
//
// Without jsdom the test says so and stops without failing.
import fs from 'node:fs'; import path from 'node:path'; import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
let JSDOM;
try { ({ JSDOM } = await import('jsdom')); } catch (e) { console.log('SKIPPED: jsdom is not installed. To run this test: cd pwa; npm install --save-dev jsdom@24'); process.exit(0); }
const here = path.dirname(fileURLToPath(import.meta.url)); const src = path.join(here, '..', 'src'); const out = path.join(here, `.tmp-screen-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));
const stubs = { '../App': 'export const useAuth = () => globalThis.__auth;', 'react-router-dom': 'export const useNavigate = () => globalThis.__navigate;',
  '../services/api': 'export const getCompetencies = (...a) => globalThis.__api.getCompetencies(...a); export const getGroups = (...a) => globalThis.__api.getGroups(...a); export const generatePlan = (...a) => globalThis.__api.generatePlan(...a); export const getGroupProposal = (...a) => globalThis.__api.getGroupProposal(...a); export const getLadder = (...a) => globalThis.__api.getLadder(...a); export const getCachedPlan = async () => { const e = new Error("No plan found for this date"); e.status = 404; throw e; };' };
await build({ entryPoints: { screen: path.join(src, 'screens/PlanScreen.jsx') }, bundle: true, format: 'esm', platform: 'node', outdir: out, outExtension: { '.js': '.mjs' }, loader: { '.js': 'jsx', '.jsx': 'jsx' }, external: ['react', 'react-dom', 'react-dom/client'], logLevel: 'error',
  plugins: [{ name: 'stubs', setup(b) { b.onResolve({ filter: /^(\.\.\/App|react-router-dom|\.\.\/services\/api)$/ }, (a) => ({ path: a.path, namespace: 'stub' })); b.onLoad({ filter: /.*/, namespace: 'stub' }, (a) => ({ contents: stubs[a.path], loader: 'js' })); } }] });
const dom = new JSDOM('<!doctype html><div id="root"></div>', { url: 'http://localhost/', pretendToBeVisual: true });
for (const k of ['window', 'document', 'navigator', 'HTMLElement', 'Element', 'Node', 'MouseEvent', 'Event']) Object.defineProperty(globalThis, k, { value: dom.window[k], configurable: true, writable: true });
globalThis.IS_REACT_ACT_ENVIRONMENT = true; globalThis.requestAnimationFrame = (f) => setTimeout(f, 0);
let scrolled = 0; dom.window.Element.prototype.scrollIntoView = function () { scrolled += 1; }; dom.window.alert = () => {};
const React = (await import('react')).default; const { act } = await import('react'); const { createRoot } = await import('react-dom/client');
const Screen = (await import(pathToFileURL(path.join(out, 'screen.mjs')).href)).default;

const sk = (id, hi = id) => ({ id, name_hi: hi, name_en: id, grade_level: { 0: 'balvatika', 1: 'grade_1', 2: 'grade_2', 3: 'grade_3' }[id[1]] });
const LADDER = { 'N2.3.2': { beginner: sk('N2.3.1'), progressor: sk('N2.3.2'), proficient: sk('N3.3.1'), options: { beginner: [sk('N2.3.1')], proficient: [sk('N3.3.1')] } },
                 'N1.1.1': { beginner: sk('N0.1.2'), progressor: sk('N1.1.1'), proficient: sk('N1.1.1'), options: { beginner: [sk('N0.1.2')], proficient: [] } } };
const deferred = () => { let resolve, reject; const promise = new Promise((a, b) => { resolve = a; reject = b; }); return { promise, resolve, reject }; };
let pending = {}; const generateCalls = [];
globalThis.__auth = { teacher: { teacher_id: 'T1' }, selectedDomain: 'numeracy', setSelectedDomain() {}, setCurrentPlan() {} };
globalThis.__navigate = () => {};
globalThis.__api = {
  getCompetencies: async () => ({ competencies: [{ ...sk('N1.1.1', 'पैटर्न'), coverage_tier: 'untested' }, { ...sk('N2.3.2', 'जोड़'), coverage_tier: 'tested' }] }),
  getGroups: async () => ({ groups: [{ label: 'beginner', count: 7 }, { label: 'progressor', count: 14 }, { label: 'proficient', count: 9 }] }),
  getGroupProposal: async () => ({ has_history: false, groups: {}, previous_date: null }),
  getLadder: (id) => { pending[id] = deferred(); return pending[id].promise; },
  generatePlan: async (...a) => { generateCalls.push(a); return { plan: {} }; },
};
const root = createRoot(document.getElementById('root'));
const flush = async () => { await act(async () => { await new Promise((r) => setTimeout(r, 0)); }); };
const q = (sel) => document.querySelector(sel); const qa = (sel) => [...document.querySelectorAll(sel)];
const generateBtn = () => qa('button.btn-primary').find((b) => /Generate|लोड हो रहे/.test(b.textContent));
const card = (id) => qa('.competency-item').find((e) => e.textContent.includes(id));
const click = async (el) => { await act(async () => { el.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true })); }); };
const release = async (id, value) => { await act(async () => { pending[id].resolve(value); await new Promise((r) => setTimeout(r, 0)); }); };
let n = 0; const check = (label, ok, extra = '') => { n += 1; console.log(`  ${ok ? 'OK  ' : 'FAIL'} ${label}${ok ? '' : '  ' + extra}`); if (!ok) process.exitCode = 1; };

await act(async () => { root.render(React.createElement(Screen)); }); await flush();
console.log('choosing a skill');
await click(card('N2.3.2'));
check('right after choosing, while the groups are coming: Generate is disabled and says the groups are loading, and there is no group summary yet', generateBtn() && generateBtn().disabled && /लोड हो रहे/.test(generateBtn().textContent) && !q('[data-testid="edit-group-skills"]'), generateBtn() && generateBtn().textContent);
await release('N2.3.2', LADDER['N2.3.2']);
check('when they arrive: the summary shows each group\'s skill and Generate is enabled for N2.3.2', /शु N2\.3\.1 · प्र N2\.3\.2 · द N3\.3\.1/.test(q('[data-testid="edit-group-skills"]').textContent) && !generateBtn().disabled && /N2\.3\.2/.test(generateBtn().textContent), q('[data-testid="edit-group-skills"]') && q('[data-testid="edit-group-skills"]').textContent);

console.log('the drawer');
check('the panel is NOT on the page until the drawer is opened (it used to sit at the top of the page)', !q('[data-testid="group-skills-panel"]'));
await click(q('[data-testid="edit-group-skills"]'));
check('opening it shows the panel inside the bottom bar, in place', !!q('[data-testid="group-skills-drawer-body"] [data-testid="group-skills-panel"]') && q('[data-testid="edit-group-skills"]').getAttribute('aria-expanded') === 'true');
check('...and the page does NOT scroll (no scrollIntoView, scroll position unchanged): the teacher keeps their place in the skill list', scrolled === 0 && dom.window.scrollY === 0, `scrolled ${scrolled}`);
check('Generate is still there, enabled, while the drawer is open', !!generateBtn() && !generateBtn().disabled);
await click(q('[data-testid="edit-group-skills"]'));
check('closing it hides the panel again, and the summary line is back', !q('[data-testid="group-skills-panel"]') && /देखें\/बदलें/.test(q('[data-testid="edit-group-skills"]').textContent));

console.log('choosing ANOTHER skill (the race)');
await click(q('[data-testid="edit-group-skills"]'));
await click(card('N1.1.1'));
check('choosing another skill with the drawer open closes the drawer', !q('[data-testid="group-skills-drawer-body"]'));
check('the PREVIOUS skill\'s groups are gone at once: no summary, nothing of N2.3.1 / N3.3.1 on the bar, and Generate is disabled', !q('[data-testid="edit-group-skills"]') && generateBtn().disabled && !/N2\.3\.1|N3\.3\.1/.test(document.body.textContent.split('Generate').pop() || ''), generateBtn().textContent);
await release('N1.1.1', LADDER['N1.1.1']);
check('the new skill\'s groups arrive: Beginners N0.1.2 (the hard prerequisite), Progressors and Proficients N1.1.1', /शु N0\.1\.2 · प्र N1\.1\.1 · द N1\.1\.1/.test(q('[data-testid="edit-group-skills"]').textContent), q('[data-testid="edit-group-skills"]').textContent);
await click(generateBtn());
await flush();
check('Generate sends N1.1.1 with NOTHING left over from the first skill (no group skills, no re-teach; today\'s time is not a group choice)', generateCalls.length === 1 && generateCalls[0][1] === 'N1.1.1' && JSON.stringify(generateCalls[0][4]) === '{"reteachGroups":[],"sessionMinutes":90}', JSON.stringify(generateCalls[0]));

console.log('answers arriving out of order');
await click(card('N2.3.2')); await click(card('N1.1.1'));
await release('N1.1.1', LADDER['N1.1.1']); await release('N2.3.2', LADDER['N2.3.2']);
check('two skills chosen quickly and the FIRST answer arrives LAST: the screen keeps the last skill\'s groups', /शु N0\.1\.2 · प्र N1\.1\.1/.test(q('[data-testid="edit-group-skills"]').textContent), q('[data-testid="edit-group-skills"]') && q('[data-testid="edit-group-skills"]').textContent);

console.log('tapping the Plan tab again (found on the click-through: it did nothing)');
const fire = async (detail) => act(async () => { dom.window.dispatchEvent(new dom.window.CustomEvent('ankur-tab-reselect', { detail })); });
await click(q('[data-testid="edit-group-skills"]'));
check('(the drawer is open and N1.1.1 is chosen)', !!q('[data-testid="group-skills-drawer-body"]'));
await fire('/yojana');
check('another tab being tapped again does not touch this screen: the drawer stays open and the choice stays', !!q('[data-testid="group-skills-drawer-body"]') && !!q('[data-testid="edit-group-skills"]'));
await fire('/');
check('tapping the Plan tab again closes the drawer and clears the choice: no summary line, no Generate bar', !q('[data-testid="group-skills-drawer-body"]') && !q('[data-testid="edit-group-skills"]') && !generateBtn());
check('...and the skill list is still there to choose from', !!card('N1.1.1') && !!card('N2.3.2'));
await click(card('N2.3.2')); await release('N2.3.2', LADDER['N2.3.2']);
check('a skill can be chosen again straight away, and its groups load', /शु N2\.3\.1 · प्र N2\.3\.2 · द N3\.3\.1/.test(q('[data-testid="edit-group-skills"]').textContent));
const gen = deferred(); globalThis.__api.generatePlan = (...a) => { generateCalls.push(a); return gen.promise; };
await click(generateBtn());
await fire('/');
check('while a plan is being generated the tab does NOT interrupt it: the bar is still there, still generating', !!qa('button.btn-primary').find((b) => /Generating/.test(b.textContent)));
await act(async () => { gen.resolve({ plan: {} }); await new Promise((r) => setTimeout(r, 0)); });
globalThis.__api.generatePlan = async (...a) => { generateCalls.push(a); return { plan: {} }; };
await fire('/');      // back to choosing, so the next scenario starts from a clean list

console.log('the groups cannot be fetched');
await click(card('N2.3.2'));
await act(async () => { pending['N2.3.2'].reject(new Error('offline')); await new Promise((r) => setTimeout(r, 0)); });
check('the fetch fails: no group summary, but Generate is NOT stuck: it is enabled and makes the plan the old way (the plan decides)', !q('[data-testid="edit-group-skills"]') && !generateBtn().disabled && /→ N2\.3\.2/.test(generateBtn().textContent), generateBtn().textContent);
await click(generateBtn()); await flush();
const lastCall = generateCalls[generateCalls.length - 1];
check('...and it sends no group choices at all (only today\'s time, which does not depend on the groups)', generateCalls.length === 3 && lastCall[1] === 'N2.3.2' && JSON.stringify(lastCall[4]) === '{"sessionMinutes":90}', JSON.stringify(lastCall));
console.log('the re-teach box is the decision, and the skill follows it (on the REAL screen, with the seeded demo\'s suggestions)');
await act(async () => { root.unmount(); });
const ZERO = { assessed: 0, with_mistakes: 0, needed: 0, very_small: false, recommend: false, rolls: [], mistakes: [] };
const seeded = { has_history: true, previous_date: '2026-10-23', groups: {
  beginner: { previous_target: sk('N2.3.1'), previous_decision: 'advance', proposed: sk('N2.3.2'), reason: 'advance', alternatives: [], evidence: ZERO, recommendation: null, conflict: false, previous_reteach: false },
  progressor: { previous_target: sk('N2.3.2'), previous_decision: null, proposed: sk('N2.3.2'), reason: 'recommended', alternatives: [], evidence: { assessed: 14, with_mistakes: 6, needed: 5, very_small: false, recommend: true, rolls: [16, 19], mistakes: [] }, recommendation: 'reteach', conflict: false, previous_reteach: false },
  proficient: { previous_target: sk('N3.3.1'), previous_decision: null, proposed: null, reason: 'no_decision', alternatives: [], evidence: ZERO, recommendation: null, conflict: false, previous_reteach: false } } };
globalThis.__api.getGroupProposal = async () => seeded;
const root2 = createRoot(document.getElementById('root')); await act(async () => { root2.render(React.createElement(Screen)); }); await flush();
await click(card('N2.3.2')); await release('N2.3.2', LADDER['N2.3.2']);
await click(q('[data-testid="edit-group-skills"]'));
const bsel = () => q('[data-testid="group-skill-select-beginner"]');
const pick = async (sel, value) => act(async () => { Object.getOwnPropertyDescriptor(dom.window.HTMLSelectElement.prototype, 'value').set.call(sel, value); sel.dispatchEvent(new dom.window.Event('change', { bubbles: true })); });
check('the Beginners start on N2.3.2 (the Advance suggestion); there is NO checkbox for them, and their list offers "re-teach N2.3.1"', bsel().value === 'N2.3.2' && !q('[data-testid="reteach-toggle-beginner"]') && [...bsel().options].some((o) => o.value === 'reteach:N2.3.1'));
await pick(bsel(), 'reteach:N2.3.1');
check('choosing it puts the Beginners on yesterday\'s skill, re-teaching: the list shows it and a one-line caption appears', bsel().value === 'reteach:N2.3.1' && !!q('[data-testid="reteach-on-beginner"]'));
check('yesterday\'s N2.3.1 is offered ONLY as a re-teach: there is no plain N2.3.1 in the Beginners\' list (they moved on, and "the same lesson again" is not a choice)', ![...bsel().options].some((o) => o.value === 'N2.3.1'));
await click(q('[data-testid="restore-suggestion-beginner"]'));
check('the back-to-the-suggestion button restores BOTH the skill and the re-teach setting', bsel().value === 'N2.3.2' && !q('[data-testid="reteach-on-beginner"]') && !q('[data-testid="restore-suggestion-beginner"]'));
const xsel = () => q('[data-testid="group-skill-select-proficient"]');
check('the Proficients, with no decision and no evidence, are on N3.3.1 as a normal lesson: the plain entry IS there (it is what they are on, labelled a normal lesson) and the re-teach entry is offered', xsel().value === 'N3.3.1' && [...xsel().options].some((o) => o.value === 'reteach:N3.3.1') && /नया पाठ/.test([...xsel().options].find((o) => o.value === 'N3.3.1').textContent));
await pick(xsel(), 'reteach:N3.3.1');
check('once they re-teach, the plain N3.3.1 is gone from their list', ![...xsel().options].some((o) => o.value === 'N3.3.1') && xsel().value === 'reteach:N3.3.1');
await click(q('[data-testid="restore-suggestion-proficient"]'));
check('and the back-to-the-suggestion button brings them back to the normal lesson', xsel().value === 'N3.3.1' && !q('[data-testid="reteach-on-proficient"]'));
await pick(bsel(), 'reteach:N2.3.1');
await pick(bsel(), 'reteach:N2.3.1');
await click(q('[data-testid="edit-group-skills"]'));
check('closed again, the summary line shows the re-teach for the Beginners and the Progressors', /शु N2\.3\.1🔄 · प्र N2\.3\.2🔄 · द N3\.3\.1/.test(q('[data-testid="edit-group-skills"]').textContent), q('[data-testid="edit-group-skills"]').textContent);
await click(generateBtn()); await flush();
const lastGen = generateCalls[generateCalls.length - 1];
check('Generate sends both groups for re-teach and NO group skill (N2.3.1 is what the plan derives for the Beginners), with today\'s time (90 here: nothing chosen on this device)', JSON.stringify(lastGen[4]) === '{"reteachGroups":["beginner","progressor"],"sessionMinutes":90}', JSON.stringify(lastGen[4]));

console.log('no network (found on the first cloud test: Generate showed the browser\'s "Failed to fetch" and nothing said why)');
await click(card('N2.3.2')); await release('N2.3.2', LADDER['N2.3.2']);
check('(online, a skill is chosen: Generate is enabled and no offline reason is shown)', generateBtn() && !generateBtn().disabled && !q('[data-testid="generate-offline"]'));
globalThis.fetch = async () => ({ ok: true, status: 200 });          // the server answers the app's tiny /health probe, so "back online" can be confirmed
const setOnLine = async (on) => act(async () => { Object.defineProperty(dom.window.navigator, 'onLine', { value: on, configurable: true }); dom.window.dispatchEvent(new dom.window.Event(on ? 'online' : 'offline')); });
await setOnLine(false);
check('offline: Generate is DISABLED and the screen says why, in Hindi and English (making a plan needs the internet)', generateBtn().disabled && !!q('[data-testid="generate-offline"]') && /इंटरनेट/.test(q('[data-testid="generate-offline"]').textContent) && /needs the internet/.test(q('[data-testid="generate-offline"]').textContent));
const callsBefore = generateCalls.length; await click(generateBtn());
check('...and tapping it does nothing (no request is made)', generateCalls.length === callsBefore);
await setOnLine(true); await flush(); await flush();                  // the browser's "online" starts a probe; the app is believed online only when it answers
check('back online: the reason disappears and Generate is enabled again', !q('[data-testid="generate-offline"]') && !generateBtn().disabled, `reason shown: ${!!q('[data-testid="generate-offline"]')}, Generate disabled: ${generateBtn() && generateBtn().disabled}, navigator.onLine: ${dom.window.navigator.onLine}`);

console.log(`\n${process.exitCode ? 'SOME CHECKS FAILED' : 'OK: ' + n + ' checks on the real Plan screen: the group panel is a drawer that opens in place, and the previous skill\'s groups never outlive a new choice'}`);
