// The Plan screen when today's plan already exists (item 12): a status card instead of the picker, the skill and the time locked, "🪄 नई योजना बनाएँ" asks first,
// "हाँ, बदलें" only UNLOCKS (nothing is generated until Generate), "नहीं, वही रखें" keeps, "योजना खोलें →" opens this plan. A 404 is the open picker as before;
// a failed check never replaces silently. The REAL Plan and plan screens in a simulated browser with a fake server. That the server counts the evidence is
// tested in backend/tests/test_plan_routes.py.
//
//     cd pwa
//     npm install --save-dev jsdom@24     (once; see plan_screen.dom.test.mjs)
//     node tests/plan_load_existing.test.mjs
//
// Without jsdom the test says so and stops without failing.
import fs from 'node:fs'; import path from 'node:path'; import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
let JSDOM;
try { ({ JSDOM } = await import('jsdom')); } catch (e) { console.log('SKIPPED: jsdom is not installed. To run this test: cd pwa; npm install --save-dev jsdom@24'); process.exit(0); }
const here = path.dirname(fileURLToPath(import.meta.url)); const src = path.join(here, '..', 'src'); const out = path.join(here, `.tmp-existing-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));      // the temporary build folder is always removed, even if a check fails
const API = ['getCompetencies', 'getGroups', 'generatePlan', 'getGroupProposal', 'getLadder', 'getCachedPlan', 'openAuthedPage', 'worksheetPath', 'prepareOfflineCopy'];
const stubs = { '../App': 'export const useAuth = () => globalThis.__auth;', 'react-router-dom': 'export const useNavigate = () => globalThis.__navigate;',
  '../services/api': API.map((n) => `export const ${n} = (...a) => globalThis.__api.${n}(...a);`).join('\n') };
await build({ entryPoints: { plan: path.join(src, 'screens/PlanScreen.jsx'), yojana: path.join(src, 'screens/YojanaScreen.jsx') }, bundle: true, format: 'esm', platform: 'node', outdir: out,
  outExtension: { '.js': '.mjs' }, loader: { '.js': 'jsx', '.jsx': 'jsx' }, external: ['react', 'react-dom', 'react-dom/client'], logLevel: 'error',
  plugins: [{ name: 'stubs', setup(b) { b.onResolve({ filter: /^(\.\.\/App|react-router-dom|\.\.\/services\/api)$/ }, (a) => ({ path: a.path, namespace: 'stub' })); b.onLoad({ filter: /.*/, namespace: 'stub' }, (a) => ({ contents: stubs[a.path], loader: 'js' })); } }] });
const dom = new JSDOM('<!doctype html><div id="root"></div>', { url: 'http://localhost/', pretendToBeVisual: true });
for (const k of ['window', 'document', 'navigator', 'HTMLElement', 'HTMLInputElement', 'Element', 'Node', 'MouseEvent', 'KeyboardEvent', 'Event', 'localStorage']) Object.defineProperty(globalThis, k, { value: dom.window[k], configurable: true, writable: true });
globalThis.IS_REACT_ACT_ENVIRONMENT = true; globalThis.requestAnimationFrame = (f) => setTimeout(f, 0);
dom.window.Element.prototype.scrollIntoView = () => {};
const React = (await import('react')).default; const { act } = await import('react'); const { createRoot } = await import('react-dom/client');
const Plan = (await import(pathToFileURL(path.join(out, 'plan.mjs')).href)).default;
const Yojana = (await import(pathToFileURL(path.join(out, 'yojana.mjs')).href)).default;

// ── the fake server ──
const sk = (id) => ({ id, name_hi: `${id} का नाम`, name_en: id, grade_level: 'grade_2', coverage_tier: 'tested' });
const LADDER = { beginner: sk('N2.3.1'), progressor: sk('N2.3.2'), proficient: sk('N3.3.1'), options: { beginner: [sk('N2.3.1')], proficient: [sk('N3.3.1')] } };
const ZERO = { beginner: 0, progressor: 0, proficient: 0 };
const PLAN = (evidence = ZERO) => ({
  plan_date: '2026-10-28', domain_id: 'numeracy', selected_competency_id: 'N2.3.2', served_from: 'ai',
  groups: [{ label: 'beginner', count: 7, target_competency_id: 'N2.3.1' }, { label: 'progressor', count: 14, target_competency_id: 'N2.3.2' }, { label: 'proficient', count: 9, target_competency_id: 'N3.3.1' }],
  plan: { session_minutes: 90, anchor: { narration_hi: 'ANCHOR-बाज़ार का खेल' }, worksheets: { progressor: { problems: [{ number: 1 }] } },
    rotation_schedule: { blocks: [{ type: 'anchor', duration_minutes: 10 }, { type: 'teach', teach_group: 'progressor', duration_minutes: 30, script_hi: 'TEACH-पहले जोड़' }] } },
  has_evidence: Object.values(evidence).some((n) => n > 0), evidence_by_group: evidence,
});
const notFound = () => { const e = new Error('No plan found for this date'); e.status = 404; return e; };
let cached; let generateFails = null; const cachedCalls = []; const generateCalls = []; const navigations = []; let current = null;
globalThis.__navigate = (to) => navigations.push(to);
globalThis.__auth = { teacher: { teacher_id: 'T1', total_children: 30 }, selectedDomain: 'numeracy', setSelectedDomain() {}, setCurrentPlan: (p) => { current = p; }, get currentPlan() { return current; } };
globalThis.__api = {
  getCompetencies: async () => ({ competencies: [sk('N2.3.1'), sk('N2.3.2'), sk('N3.3.1')] }),
  getGroups: async () => ({ groups: [{ label: 'beginner', count: 7 }, { label: 'progressor', count: 14 }, { label: 'proficient', count: 9 }] }),
  getGroupProposal: async () => ({ has_history: false, groups: {}, previous_date: null }),
  getLadder: async () => LADDER,
  getCachedPlan: async (...a) => { cachedCalls.push(a); return cached(...a); },
  generatePlan: async (...a) => { generateCalls.push(a); if (generateFails) { const e = generateFails(); generateFails = null; throw e; } return PLAN(); },
  openAuthedPage: async () => {}, worksheetPath: () => '/w', prepareOfflineCopy: () => {},
};

let root;
const flush = async () => { for (let i = 0; i < 3; i += 1) await act(async () => { await new Promise((r) => setTimeout(r, 0)); }); };
const show = async (C) => { if (root) await act(async () => root.unmount()); root = createRoot(document.getElementById('root')); await act(async () => { root.render(React.createElement(C)); }); await flush(); };
const q = (sel) => document.querySelector(sel); const qa = (sel) => [...document.querySelectorAll(sel)];
const click = async (el) => { await act(async () => { el.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true })); }); await flush(); };
const text = () => document.getElementById('root').textContent;
const generateBtn = () => qa('button.btn-primary').find((b) => /Generate Plan/.test(b.textContent));
let n = 0; const check = (label, ok, extra = '') => { n += 1; console.log(`  ${ok ? 'OK  ' : 'FAIL'} ${label}${ok ? '' : '  ' + extra}`); if (!ok) process.exitCode = 1; };
const reset = () => { generateCalls.length = 0; navigations.length = 0; cachedCalls.length = 0; current = null; };

console.log('1-2. a plan exists: a status card, locked');
reset(); cached = async () => PLAN();
await show(Plan);
check('1. the card says "✓ आज की योजना बन चुकी है", with the skill and the time locked (🔒) and "योजना खोलें →"', /✓ आज की योजना बन चुकी है/.test(text()) && /N2\.3\.2\s*🔒/.test(q('[data-testid="locked-skill"]').textContent)
  && /90 मिनट\s*🔒/.test(q('[data-testid="locked-time"]').textContent) && !!q('[data-testid="open-plan"]'), text().slice(0, 300));
check('1. ...and none of the plan itself: no anchor, no teach block, no worksheet button', !text().includes('ANCHOR-') && !text().includes('TEACH-') && !q('.timeline-block') && !q('[data-testid^="worksheet-"]'));
check('1. ...and opening the screen made no plan (no POST to /plan/generate); it asked for today\'s plan in this subject', generateCalls.length === 0 && cachedCalls.length === 1 && cachedCalls[0][0] === 'T1' && cachedCalls[0][2] === 'numeracy' && /^\d{4}-\d{2}-\d{2}$/.test(cachedCalls[0][1]));
check('2. the skill and the time cannot be changed: no skill list, no time buttons, no group panel, no Generate bar; both lines say they are locked',
  !q('.competency-item') && !q('[data-testid="session-length"] input') && !q('[data-testid="edit-group-skills"]') && !generateBtn()
  && q('[data-testid="locked-skill"]').getAttribute('aria-disabled') === 'true' && q('[data-testid="locked-time"]').getAttribute('aria-disabled') === 'true');
check('the button reads "🪄 नई योजना बनाएँ"', /🪄 नई योजना बनाएँ/.test(q('[data-testid="replace-plan"]').textContent));

console.log('\n3, 7. the question, and keeping');
await click(q('[data-testid="replace-plan"]'));
check('3. "नई योजना बनाएँ" opens the question, and nothing is generated', !!q('[data-testid="replace-dialog"]') && generateCalls.length === 0);
check('...no evidence: "आज की योजना पहले से बनी है … क्या आप इसे बदलना चाहते हैं?" (gender-neutral), "नहीं, वही रखें" has the focus', /आज की योजना पहले से बनी है। नई योजना बनाने पर पुरानी हट जाएगी। क्या आप इसे बदलना चाहते हैं\?/.test(q('[data-testid="replace-dialog"]').textContent)
  && q('[data-testid="replace-dialog"]').dataset.evidence === 'false' && document.activeElement === q('[data-testid="replace-keep"]'));
await click(q('[data-testid="replace-keep"]'));
check('7. "नहीं, वही रखें" closes it: no POST, still locked', !q('[data-testid="replace-dialog"]') && generateCalls.length === 0 && !!q('[data-testid="plan-status"]') && !q('.competency-item'));
await click(q('[data-testid="replace-plan"]'));
await act(async () => { window.dispatchEvent(new dom.window.KeyboardEvent('keydown', { key: 'Escape' })); }); await flush();
check('...Escape keeps too', !q('[data-testid="replace-dialog"]') && !!q('[data-testid="plan-status"]') && generateCalls.length === 0);
await click(q('[data-testid="replace-plan"]'));
await click(q('[data-testid="replace-backdrop"]'));
check('...and so does a tap outside the box', !q('[data-testid="replace-dialog"]') && !!q('[data-testid="plan-status"]') && generateCalls.length === 0);

console.log('\n4. evidence recorded against the plan');
reset(); cached = async () => PLAN({ beginner: 4, progressor: 6, proficient: 0 });
await show(Plan);
await click(q('[data-testid="replace-plan"]'));
const dlg = () => q('[data-testid="replace-dialog"]').textContent;
check('4. the question names the groups and their counts: "● शुरुआती — 4 बच्चे · ▲ प्रगतिशील — 6 बच्चे", English "Beginner — 4 … Progressor — 6"',
  /● शुरुआती — 4 बच्चे/.test(dlg()) && /▲ प्रगतिशील — 6 बच्चे/.test(dlg()) && /Beginner — 4/.test(dlg()) && /Progressor — 6/.test(dlg()), dlg());
check('...a group with nothing recorded is not listed', !/दक्ष|Proficient/.test(q('[data-testid="replace-groups"]').textContent));
check('...and it says the records stay safe: "… दर्ज कर चुके हैं" (gender-neutral), "लेकिन आपके पुराने रिकॉर्ड सुरक्षित रहेंगे", "क्या आप बदलना चाहते हैं?"', /आप इस योजना के लिए इन समूहों पर कुछ बच्चों का रिकॉर्ड पहले ही दर्ज कर चुके हैं:/.test(dlg())
  && /नई योजना बनाने पर पुरानी हट जाएगी, लेकिन आपके पुराने रिकॉर्ड सुरक्षित रहेंगे।/.test(dlg()) && /क्या आप बदलना चाहते हैं\?/.test(dlg()) && !/प्लान/.test(dlg()));

console.log('\n5-6. "हाँ, बदलें" unlocks; Generate then makes ONE plan');
await click(q('[data-testid="replace-yes"]'));
check('5. the question closes and NOTHING is generated', !q('[data-testid="replace-dialog"]') && generateCalls.length === 0);
check('5. the skill list, the time buttons and the group panel are back (interactive), with the plan\'s skill and length already chosen',
  qa('.competency-item').length === 3 && qa('[data-testid="session-length"] input').every((i) => !i.disabled) && qa('[data-testid="session-length"] input').filter((i) => i.checked).map((i) => i.value).join() === '90'
  && !!q('[data-testid="edit-group-skills"]'));
check('5. the button is the normal one again ("📋 दैनिक योजना बनाएँ → N2.3.2", no "नई")', !!generateBtn() && /📋 दैनिक योजना बनाएँ/.test(generateBtn().textContent) && /N2\.3\.2/.test(generateBtn().textContent) && !/नई/.test(generateBtn().textContent));
check('5. the hint: "✓ अब आप बदलाव कर सकते हैं। नई योजना बनाने के लिए \'📋 दैनिक योजना बनाएँ\' दबाएँ।" (names the real button)', /✓ अब आप बदलाव कर सकते हैं। नई योजना बनाने के लिए '📋 दैनिक योजना बनाएँ' दबाएँ।/.test(q('[data-testid="unlock-hint"]').textContent));
check('...the plan that would be replaced is still named, and can still be opened', /अभी की योजना: N2\.3\.2/.test(q('[data-testid="plan-current"]').textContent) && !!q('[data-testid="plan-current"] [data-testid="open-plan"]'));
await click(generateBtn());
check('6. Generate then sends exactly ONE plan request, for N2.3.2 at 90 minutes, and goes to the plan', generateCalls.length === 1 && generateCalls[0][1] === 'N2.3.2' && generateCalls[0][4].sessionMinutes === 90 && navigations.at(-1) === '/yojana', JSON.stringify(generateCalls));
check('...the phone\'s own time choice was not overwritten by unlocking', localStorage.getItem('session_minutes') === null);
check('...and that request says replace: true (the teacher confirmed): the server replaces a plan only then', generateCalls[0][4].replace === true, JSON.stringify(generateCalls[0][4]));

console.log('\nthe hint can be closed');
reset(); cached = async () => PLAN();
await show(Plan); await click(q('[data-testid="replace-plan"]')); await click(q('[data-testid="replace-yes"]'));
await click(q('[data-testid="unlock-hint-close"]'));
check('✕ hides the hint; the screen stays unlocked', !q('[data-testid="unlock-hint"]') && qa('.competency-item').length === 3);

console.log('\n8. "योजना खोलें →"');
reset(); cached = async () => PLAN();
current = { domain_id: 'r1_literacy', selected_competency_id: 'L2.7.2', plan: {} };          // the app holds another subject's plan
await show(Plan);
await click(q('[data-testid="open-plan"]'));
check('8. it puts THIS plan in place (not the one the app held) and goes to दैनिक योजना', current && current.selected_competency_id === 'N2.3.2' && current.domain_id === 'numeracy' && navigations.at(-1) === '/yojana');
await show(Yojana);
check('8. ...where the plan is visible: a teach block for N2.3.2', qa('.timeline-block').some((b) => /N2\.3\.2/.test(b.textContent) && /TEACH-/.test(b.textContent)));

console.log('\nno plan, a failed check, another subject');
reset(); cached = async () => { throw notFound(); };
await show(Plan);
check('no plan today (404): the open picker as before, no card, no warning', !q('[data-testid="plan-status"]') && qa('.competency-item').length === 3 && !q('[data-testid="plan-check-failed"]'));
await click(qa('.competency-item')[1]); await flush();
await click(generateBtn());
check('...and Generate makes the plan at once, with no question, and WITHOUT replace (nothing to replace)', !q('[data-testid="replace-dialog"]') && generateCalls.length === 1 && !('replace' in generateCalls[0][4]), JSON.stringify(generateCalls[0] && generateCalls[0][4]));
reset(); cached = async () => { throw notFound(); };
await show(Plan);
cached = async () => PLAN({ beginner: 0, progressor: 2, proficient: 0 });          // meanwhile a plan was made on another phone
generateFails = () => { const e = new Error('इस दिन की योजना पहले से बनी है।'); e.status = 409; e.code = 'plan_exists'; return e; };
await click(qa('.competency-item')[1]); await flush();
await click(generateBtn());
check('a plan made meanwhile (the server answers 409 plan_exists): the screen loads it, locks, and asks, naming what was recorded; no raw error and no plan replaced',
  generateCalls.length === 1 && !generateCalls[0][4].replace && !!q('[data-testid="plan-status"]') && !!q('[data-testid="replace-dialog"]') && /▲ प्रगतिशील — 2 बच्चे/.test(q('[data-testid="replace-dialog"]').textContent));
await click(q('[data-testid="replace-yes"]')); await click(generateBtn());
check('...and "हाँ, बदलें" then Generate replaces it, saying replace: true', generateCalls.length === 2 && generateCalls[1][4].replace === true);
reset(); cached = async () => { const e = new Error('Server error'); e.status = 500; throw e; };
await show(Plan);
check('the check failed (500): "आज की योजना की जाँच नहीं हो सकी", with the picker open', !!q('[data-testid="plan-check-failed"]') && qa('.competency-item').length === 3);
await click(qa('.competency-item')[1]); await flush();
await click(generateBtn());
check('...Generate asks first (it may replace a plan we could not see), and sends nothing yet', q('[data-testid="replace-dialog"]') && q('[data-testid="replace-dialog"]').dataset.kind === 'unknown' && generateCalls.length === 0);
await click(q('[data-testid="replace-yes"]'));
check('..."हाँ, बनाएँ" then makes ONE plan, with replace: true (the teacher accepted that it may replace one)', generateCalls.length === 1 && generateCalls[0][4].replace === true);
reset(); cached = async (t, d, domain) => { if (domain === 'numeracy') return PLAN(); throw notFound(); };
globalThis.__auth.selectedDomain = 'r1_literacy';
await show(Plan);
check('each subject on its own: the Hindi tab asks for its own plan, and with none it is open even though maths is locked', cachedCalls.at(-1)[2] === 'r1_literacy' && !q('[data-testid="plan-status"]') && qa('.competency-item').length === 3);
globalThis.__auth.selectedDomain = 'numeracy';

await act(async () => root.unmount());
console.log(`\n${process.exitCode ? 'SOME CHECKS FAILED' : 'OK: ' + n + ' checks: with today\'s plan made, the Plan screen locks, asks before replacing, unlocks on yes without generating, and opens the plan'}`);
