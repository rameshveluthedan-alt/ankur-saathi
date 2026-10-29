// UI review, point 6: "⭐ सुझाया गया" at the top of the Plan screen's skill list: the Progressors' skill the last review points to (GET /plan/proposal), with the
// reason, and one tap to choose it. Nothing when there is no suggestion, when it is not in this subject's list, or when today's plan already exists (locked).
// The REAL Plan screen in a simulated browser with a fake server.
//
//     cd pwa
//     npm install --save-dev jsdom@24     (once; see plan_screen.dom.test.mjs)
//     node tests/plan_suggested_skill.test.mjs
//
// Without jsdom the test says so and stops without failing.
import fs from 'node:fs'; import path from 'node:path'; import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
let JSDOM;
try { ({ JSDOM } = await import('jsdom')); } catch (e) { console.log('SKIPPED: jsdom is not installed. To run this test: cd pwa; npm install --save-dev jsdom@24'); process.exit(0); }
const here = path.dirname(fileURLToPath(import.meta.url)); const src = path.join(here, '..', 'src'); const out = path.join(here, `.tmp-suggest-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));      // the temporary build folder is always removed, even if a check fails
const API = ['getCompetencies', 'getGroups', 'generatePlan', 'getGroupProposal', 'getLadder', 'getCachedPlan'];
const stubs = { '../App': 'export const useAuth = () => globalThis.__auth;', 'react-router-dom': 'export const useNavigate = () => () => {};',
  '../services/api': API.map((n) => `export const ${n} = (...a) => globalThis.__api.${n}(...a);`).join('\n') };
await build({ entryPoints: { plan: path.join(src, 'screens/PlanScreen.jsx') }, bundle: true, format: 'esm', platform: 'node', outdir: out, outExtension: { '.js': '.mjs' },
  loader: { '.js': 'jsx', '.jsx': 'jsx' }, external: ['react', 'react-dom', 'react-dom/client'], logLevel: 'error',
  plugins: [{ name: 'stubs', setup(b) { b.onResolve({ filter: /^(\.\.\/App|react-router-dom|\.\.\/services\/api)$/ }, (a) => ({ path: a.path, namespace: 'stub' })); b.onLoad({ filter: /.*/, namespace: 'stub' }, (a) => ({ contents: stubs[a.path], loader: 'js' })); } }] });
const dom = new JSDOM('<!doctype html><div id="root"></div>', { url: 'http://localhost/', pretendToBeVisual: true });
for (const k of ['window', 'document', 'navigator', 'HTMLElement', 'HTMLInputElement', 'Element', 'Node', 'MouseEvent', 'Event', 'localStorage']) Object.defineProperty(globalThis, k, { value: dom.window[k], configurable: true, writable: true });
globalThis.IS_REACT_ACT_ENVIRONMENT = true; globalThis.requestAnimationFrame = (f) => setTimeout(f, 0);
dom.window.Element.prototype.scrollIntoView = () => {};
const React = (await import('react')).default; const { act } = await import('react'); const { createRoot } = await import('react-dom/client');
const Plan = (await import(pathToFileURL(path.join(out, 'plan.mjs')).href)).default;

const sk = (id, grade = 'grade_2') => ({ id, name_hi: `${id} का नाम`, name_en: id, grade_level: grade, coverage_tier: 'tested' });
const SKILLS = [sk('N1.1.1', 'grade_1'), sk('N2.3.1'), sk('N2.3.2'), sk('N2.3.3')];
const LADDER = { beginner: sk('N2.3.2'), progressor: sk('N2.3.3'), proficient: sk('N2.3.3'), options: { beginner: [], proficient: [] } };
const proposalWith = (proposed, reason, has = true) => ({ has_history: has, previous_date: '2026-10-24', groups: has ? { progressor: { proposed: proposed ? { id: proposed, name_hi: `${proposed} का नाम` } : null, reason } } : {} });
const notFound = () => { const e = new Error('No plan found for this date'); e.status = 404; return e; };
let proposal; let cached; const generateCalls = [];
globalThis.__auth = { teacher: { teacher_id: 'T1', total_children: 30 }, selectedDomain: 'numeracy', setSelectedDomain() {}, setCurrentPlan() {} };
globalThis.__api = {
  getCompetencies: async () => ({ competencies: SKILLS }),
  getGroups: async () => ({ groups: [{ label: 'beginner', count: 7 }, { label: 'progressor', count: 14 }, { label: 'proficient', count: 9 }] }),
  getGroupProposal: async () => proposal, getLadder: async () => LADDER, getCachedPlan: async () => cached(),
  generatePlan: async (...a) => { generateCalls.push(a); return { plan: {} }; },
};
let root;
const flush = async () => { for (let i = 0; i < 3; i += 1) await act(async () => { await new Promise((r) => setTimeout(r, 0)); }); };
const show = async () => { if (root) await act(async () => root.unmount()); root = createRoot(document.getElementById('root')); await act(async () => { root.render(React.createElement(Plan)); }); await flush(); };
const q = (sel) => document.querySelector(sel); const qa = (sel) => [...document.querySelectorAll(sel)];
const click = async (el) => { await act(async () => { el.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true })); }); await flush(); };
const card = () => q('[data-testid="suggested-skill"]');
const generateBtn = () => qa('button.btn-primary').find((b) => /Generate Plan/.test(b.textContent));
let n = 0; const check = (label, ok, extra = '') => { n += 1; console.log(`  ${ok ? 'OK  ' : 'FAIL'} ${label}${ok ? '' : '  ' + extra}`); if (!ok) process.exitCode = 1; };

console.log('a suggestion from the last review');
proposal = proposalWith('N2.3.3', 'advance'); cached = async () => { throw notFound(); };
await show();
check('"⭐ सुझाया गया" shows the Progressors\' proposed skill with its name, above the skill list', card() && card().dataset.skill === 'N2.3.3' && /⭐ सुझाया गया/.test(card().textContent) && /N2\.3\.3 — N2\.3\.3 का नाम/.test(card().textContent)
  && (card().compareDocumentPosition(q('.competency-item')) & dom.window.Node.DOCUMENT_POSITION_FOLLOWING));
check('...with the reason and the review\'s date: "पिछली समीक्षा (24 …): प्रगतिशील: ⬆ आगे बढ़ें"', /पिछली समीक्षा \(24 [^)]+\): प्रगतिशील: ⬆ आगे बढ़ें/.test(q('[data-testid="suggested-why"]').textContent), q('[data-testid="suggested-why"]').textContent);
await click(qa('button').find((b) => b.textContent.trim().startsWith('G1')));           // the grade filter on Grade 1: N2.3.3 is not in the list on screen
await click(q('[data-testid="choose-suggested"]'));
check('"यही चुनें" chooses it, exactly as the list does (the grade filter is cleared so it is visible), and the card says "✓ चुना गया"',
  !!generateBtn() && /N2\.3\.3/.test(generateBtn().textContent) && q('.competency-item.recommended') && /N2\.3\.3/.test(q('.competency-item.recommended').textContent)
  && /✓ चुना गया/.test(card().textContent) && q('[data-testid="choose-suggested"]').disabled);
await click(generateBtn());
check('...and Generate makes the plan for it', generateCalls.length === 1 && generateCalls[0][1] === 'N2.3.3');

console.log('\nthe reasons');
for (const [reason, re] of [['reteach', /प्रगतिशील: 🔄 दोहराएँ/], ['not_sure', /प्रगतिशील: ❓ पक्का नहीं/], ['advance_no_next', /अगला कौशल नहीं है, इसलिए यही फिर/], ['recommended', /पिछली जाँच \(24 [^)]+\): प्रगतिशील के कई बच्चों से गलती हुई/]]) {
  proposal = proposalWith('N2.3.2', reason); await show();
  check(`${reason}: "${re.source.replace(/\\/g, '')}"`, card() && card().dataset.reason === reason && re.test(q('[data-testid="suggested-why"]').textContent), card() && q('[data-testid="suggested-why"]').textContent);
}

console.log('\nno card');
for (const [label, p] of [['no earlier plan', proposalWith(null, 'no_decision', false)], ['no decision and no warning sign', proposalWith(null, 'no_decision')], ['a skill not in this subject\'s list', proposalWith('L2.7.2', 'advance')], ['the proposal could not be fetched', null]]) {
  proposal = p; await show();
  check(`${label}: no card, the list as before`, !card() && qa('.competency-item').length === SKILLS.length);
}
proposal = proposalWith('N2.3.3', 'advance');
cached = async () => ({ plan_date: '2026-10-28', domain_id: 'numeracy', selected_competency_id: 'N2.3.2', groups: [], plan: { session_minutes: 90, rotation_schedule: { blocks: [] } }, has_evidence: false, evidence_by_group: {} });
await show();
check('today\'s plan already exists: the screen is locked, so no card', !card() && !!q('[data-testid="plan-status"]'));

await act(async () => root.unmount());
console.log(`\n${process.exitCode ? 'SOME CHECKS FAILED' : 'OK: ' + n + ' checks: the Plan screen suggests the skill the last review points to, says why, and chooses it in one tap'}`);
