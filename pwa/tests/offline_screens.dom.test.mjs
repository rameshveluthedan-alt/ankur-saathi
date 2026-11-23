// Plans with no connection, step 3 (docs/drafts/OFFLINE_ASSEMBLER_PLAN.md): the REAL Plan and Teach screens in a simulated browser, offline,
// with the phone's store holding a prepared plan. Offline: the prepared skills are marked, the others greyed; Generate opens the prepared plan
// (the skill's default choice when the group panel cannot load), saves it to be sent, and the Teach screen labels it and shows its worksheets
// in the app; a reload with no connection still finds it. Online: the "⚡" quick plan asks the server for a library plan.
//
//     cd pwa
//     node tests/offline_screens.dom.test.mjs
import fs from 'node:fs'; import path from 'node:path'; import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
let JSDOM;
try { ({ JSDOM } = await import('jsdom')); } catch (e) { console.log('SKIPPED: jsdom is not installed. To run this test: cd pwa; npm install --save-dev jsdom@24'); process.exit(0); }
const here = path.dirname(fileURLToPath(import.meta.url)); const src = path.join(here, '..', 'src'); const out = path.join(here, `.tmp-offline-screens-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));
fs.mkdirSync(out, { recursive: true });
const API = ['getCompetencies', 'getGroups', 'generatePlan', 'getGroupProposal', 'getLadder', 'getCachedPlan', 'worksheetPath', 'prepareOfflineCopy', 'getReviewChannels',
  'openAuthedPage', 'prepareOfflinePlans', 'uploadOfflinePlan', 'adminSchool', 'adminTeachers', 'adminResetPin', 'adminUnlock', 'adminRecordConsent', 'changePin', 'setToken'];
const stubs = { '../App': 'export const useAuth = () => globalThis.__auth;',
  'react-router-dom': 'export const useNavigate = () => (...a) => globalThis.__navs.push(a); export const useLocation = () => ({ pathname: "/", state: null });',
  '../services/api': API.map((n) => `export const ${n} = (...a) => globalThis.__api.${n}(...a);`).join('\n') };
const entry = path.join(out, 'entry.js');
fs.writeFileSync(entry, [`export { default as Plan } from ${JSON.stringify(path.join(src, 'screens/PlanScreen.jsx'))};`,
  `export { default as Yojana } from ${JSON.stringify(path.join(src, 'screens/YojanaScreen.jsx'))};`,
  `export { default as Account } from ${JSON.stringify(path.join(src, 'screens/AccountScreen.jsx'))};`,
  `export { sendOffline, SENT_EVENT } from ${JSON.stringify(path.join(src, 'offline/prepareNow.js'))};`,
  `export { appStore } from ${JSON.stringify(path.join(src, 'offline/store.js'))};`,
  `export * as off from ${JSON.stringify(path.join(src, 'offline/offlinePlans.js'))};`,
  `export { localToday } from ${JSON.stringify(path.join(src, 'services/today.js'))};`,
  `export { onNotify } from ${JSON.stringify(path.join(src, 'services/notify.js'))};`].join('\n'));
await build({ entryPoints: { all: entry }, bundle: true, format: 'esm', platform: 'node', outdir: out, outExtension: { '.js': '.mjs' }, loader: { '.js': 'jsx', '.jsx': 'jsx' },
  external: ['react', 'react-dom', 'react-dom/client'], logLevel: 'error',
  plugins: [{ name: 'stubs', setup(b) { b.onResolve({ filter: /^(\.\.\/App|react-router-dom|\.\.\/services\/api)$/ }, (a) => ({ path: a.path, namespace: 'stub' })); b.onLoad({ filter: /.*/, namespace: 'stub' }, (a) => ({ contents: stubs[a.path], loader: 'js' })); } }] });
const dom = new JSDOM('<!doctype html><div id="root"></div>', { url: 'http://localhost/', pretendToBeVisual: true });
for (const k of ['window', 'document', 'navigator', 'HTMLElement', 'HTMLInputElement', 'Element', 'Node', 'MouseEvent', 'Event', 'CustomEvent', 'localStorage', 'sessionStorage']) Object.defineProperty(globalThis, k, { value: dom.window[k], configurable: true, writable: true });
globalThis.IS_REACT_ACT_ENVIRONMENT = true; globalThis.requestAnimationFrame = (f) => setTimeout(f, 0);
dom.window.Element.prototype.scrollIntoView = () => {};
const React = (await import('react')).default; const { act } = await import('react'); const { createRoot } = await import('react-dom/client');
const M = await import(pathToFileURL(path.join(out, 'all.mjs')).href);

const today = M.localToday();
const sk = (id, grade = 'grade_2') => ({ id, name_hi: `${id} का नाम`, name_en: id, grade_level: grade, assessment_modality: 'written' });
const SKILLS = [sk('N1.1.1', 'grade_1'), sk('N2.3.2'), sk('N2.3.3')];
const groups = [{ label: 'beginner', count: 7, roll_numbers: [1, 2], target_competency_id: 'N2.2.9', target_competency_name_hi: 'क' },
                { label: 'progressor', count: 14, roll_numbers: [3, 4], target_competency_id: 'N2.3.2', target_competency_name_hi: 'ख' },
                { label: 'proficient', count: 9, roll_numbers: [5], target_competency_id: 'N3.3.1', target_competency_name_hi: 'ग' }];
const prepared = {
  plan_date: today, domain_id: 'numeracy', selected_competency_id: 'N2.3.2', served_from: 'library', groups,
  plan: { session_minutes: 90, served_from: 'library', anchor: { title_hi: 'बाज़ार', narration_hi: 'कहानी' }, prep_hi: [],
          rotation_schedule: { blocks: [{ type: 'anchor', time_start: '0:00', duration_minutes: 10 }, { type: 'teach', teach_group: 'beginner', time_start: '0:10', duration_minutes: 30, talking_points: { i_do_hi: 'दिखाएँ' } }] },
          worksheets: { beginner: { instructions_hi: 'जोड़ें।', required_count: 3, problems: [1, 2, 3, 4].map((i) => ({ number: i, problem_hi: `1${i} + 5`, answer: String(15 + i) })) } },
          explainability: { items: [] }, review_prompts: {} },
};
const store = await M.appStore();
const choice = { groupSkills: { beginner: 'N2.2.9' }, reteachGroups: ['progressor'] };       // the suggestion: a different Beginner skill and a re-teach
// a download under way: N2.3.2 has arrived (its plain plan, and the suggested choice: a different Beginner skill and a re-teach), N1.1.1 not yet
await store.set('meta', 'numeracy', { domain: 'numeracy', status: 'partial', count: 2, skills: ['N2.3.2'], total: 9, defaults: { 'N2.3.2': choice }, groups });
await store.set('prepared', M.off.planKey({ domain: 'numeracy', minutes: 90, competencyId: 'N2.3.2', ...choice }), { result: prepared });
await store.set('prepared', M.off.planKey({ domain: 'numeracy', minutes: 90, competencyId: 'N2.3.2' }), { result: { ...prepared, plan: { ...prepared.plan, anchor: { title_hi: 'सादा' } } } });

let current = null; const generateCalls = []; const uploads = []; let loggedOut = 0; const calls = { channels: 0, copy: 0 }; globalThis.__navs = [];
let online = false;
const netError = () => { const e = new Error('इंटरनेट नहीं है'); e.name = 'NetworkError'; e.offline = true; return e; };
globalThis.__auth = { logout: () => { loggedOut += 1; }, teacher: { teacher_id: 'T1' }, selectedDomain: 'numeracy', setSelectedDomain() {}, get currentPlan() { return current; }, setCurrentPlan: (p) => { current = p; }, names: {} };
globalThis.__api = {
  getCompetencies: async () => ({ competencies: SKILLS }),
  getGroups: async () => ({ groups }),
  getGroupProposal: async () => { if (!online) throw netError(); return { has_history: false, groups: {} }; },
  getLadder: async () => { if (!online) throw netError(); return { beginner: sk('N2.3.1'), progressor: sk('N2.3.2'), proficient: sk('N3.3.1'), options: { beginner: [], proficient: [] } }; },
  getCachedPlan: async () => { if (!online) throw netError(); const e = new Error('none'); e.status = 404; throw e; },
  generatePlan: async (...a) => { generateCalls.push(a); return { ...prepared, served_from: 'library' }; },
  prepareOfflinePlans: async () => ({ plans: [], library_version: 'x' }),
  uploadOfflinePlan: async (t, body) => { uploads.push(body); return { status: 'stored' }; },
  adminSchool: async () => ({}), adminTeachers: async () => ({ teachers: [] }), adminResetPin: async () => ({}), adminUnlock: async () => ({}), adminRecordConsent: async () => ({}), changePin: async () => ({}), setToken: () => {},
  worksheetPath: () => '/api/worksheet/x', openAuthedPage: () => {},
  prepareOfflineCopy: () => { calls.copy += 1; }, getReviewChannels: async () => { calls.channels += 1; return {}; },
};
const notices = []; M.onNotify((n) => notices.push(n));
globalThis.fetch = async () => { if (!online) throw new TypeError('Failed to fetch'); return { ok: true, status: 200, json: async () => ({}) }; };      // the app's own check (network.js probe of /health)
const setOnline = async (on) => { online = on; await act(async () => { Object.defineProperty(dom.window.navigator, 'onLine', { value: on, configurable: true }); dom.window.dispatchEvent(new dom.window.Event(on ? 'online' : 'offline')); }); };
let root;
const flush = async () => { for (let i = 0; i < 4; i += 1) await act(async () => { await new Promise((r) => setTimeout(r, 0)); }); };
const show = async (C) => { if (root) await act(async () => root.unmount()); root = createRoot(document.getElementById('root')); await act(async () => { root.render(React.createElement(C)); }); await flush(); };
const q = (sel) => document.querySelector(sel); const qa = (sel) => [...document.querySelectorAll(sel)];
const click = async (el) => { await act(async () => { el.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true })); }); await flush(); };
const item = (id) => qa('.competency-item').find((e) => e.textContent.includes(id));
const generateBtn = () => qa('button.btn-primary').find((b) => /आज की योजना बनाएँ/.test(b.textContent));
let n = 0; const check = (label, ok, extra = '') => { n += 1; console.log(`  ${ok ? 'OK  ' : 'FAIL'} ${label}${ok ? '' : '  ' + extra}`); if (!ok) process.exitCode = 1; };

console.log('the Plan screen with no connection');
await setOnline(false);
await show(M.Plan);
check('a skill already on the phone looks as usual (no badge: every skill comes once the download completes)', item('N2.3.2').dataset.offline === 'ready' && !item('N2.3.2').style.opacity);
check('a skill whose plan has not arrived yet is greyed', item('N1.1.1').dataset.offline === 'unavailable' && item('N1.1.1').style.opacity === '0.45');
await click(item('N1.1.1'));
check('tapping a greyed skill does not choose it, and says why (never a dead end)', !generateBtn() && notices.some((x) => /अभी फ़ोन पर नहीं आई/.test(x.text || x)), JSON.stringify(notices));
await click(item('N2.3.2'));
check('the prepared skill can be chosen; the line says the prepared plan opens; no "⚡" offline', /फ़ोन पर पहले से तैयार योजना खुलेगी/.test(q('[data-testid="generate-offline"]').textContent)
  && q('[data-testid="generate-offline"]').dataset.ready === 'true' && generateBtn() && !generateBtn().disabled && !q('[data-testid="quick-plan"]'));
await click(generateBtn());
if (q('[data-testid="replace-dialog"]')) await click(q('[data-testid="replace-yes"]'));           // offline the app cannot check for a plan already made: it asks first
check('Generate opens the PREPARED plan for the skill\'s default choice (the panel could not load offline: a different Beginner skill and a re-teach)',
  current && current.served_from === 'library_offline' && current.plan_date === today && current.selected_competency_id === 'N2.3.2' && current.plan.worksheets.beginner.problems.length === 4, JSON.stringify(current && current.served_from));
check('...marked as made offline, with a client id, the day it was prepared for, not yet sent', current.offline && current.offline.client_id && current.offline.prepared_for === today && current.offline.sent === false);
check('...saved on the phone to be sent', !!(await M.off.getOfflinePlan(store, 'numeracy', today)) && (await M.off.waitingPlans(store)).length === 1);
check('...and the Teach screen opens', globalThis.__navs.some((a) => a[0] === '/yojana'));
check('no server call to generate was made', generateCalls.length === 0);
await click(q('[data-testid="session-45"]'));
const before = current;
await click(generateBtn());
if (q('[data-testid="replace-dialog"]')) await click(q('[data-testid="replace-yes"]'));
check('a choice that was not prepared (45 minutes here): a clear message, no plan', current === before && notices.some((x) => /इस चुनाव की बिना-इंटरनेट योजना/.test(x.text || x)), JSON.stringify(notices.slice(-1)));

console.log('\nthe Teach screen with the offline plan');
await show(M.Yojana);
check('the plan is labelled "📴 बिना इंटरनेट के बनी योजना" (sent when there is internet), with the library note', /बिना इंटरनेट के बनी योजना/.test(q('[data-testid="offline-plan-banner"]').textContent) && !!q('[data-testid="library-banner"]'));
check('nothing is asked of the server for it (it is not there yet): no review channels, no offline page copies', calls.channels === 0 && calls.copy === 0, JSON.stringify(calls));
await click(q('[data-testid="worksheet-beginner"]'));
const sheet = q('[data-testid="worksheet-inapp-beginner"]');
check('📝 shows the worksheet IN THE APP (its page is on the server only): instructions and every problem', sheet && /जोड़ें।/.test(sheet.textContent) && qa('[data-testid="worksheet-inapp-problems"] li').length === 4 && !globalThis.__navs.some((a) => a[0] === '/page'));
check('...answers hidden until asked for, then shown', !q('[data-testid="worksheet-inapp-answer"]') && await (async () => { await click(q('[data-testid="worksheet-inapp-answers"]')); return qa('[data-testid="worksheet-inapp-answer"]').length === 4; })());
current = null;
await show(M.Yojana);
check('the app reopened with no connection: the plan made offline is found on the phone', current && current.served_from === 'library_offline' && !!q('[data-testid="offline-plan-banner"]'));

console.log('\nsigning out with a plan not yet sent');
const confirms = []; dom.window.confirm = (t) => { confirms.push(t); return false; };
await show(M.Account);
await click(q('[data-testid="logout"]'));
check('sign-out asks first, and SAYS a plan made with no internet is not yet sent and would be lost', confirms.length === 1 && /अभी सर्वर पर नहीं भेजी गई/.test(confirms[0]) && /हमेशा के लिए हट जाएगी/.test(confirms[0]) && loggedOut === 0, confirms[0]);

console.log('\nonline: the plan is sent');
await setOnline(true);
await flush();
const sentEvents = []; dom.window.addEventListener(M.SENT_EVENT, (e) => sentEvents.push(e.detail));
await act(async () => { await M.sendOffline('T1'); });
check('back online, the plan made offline is sent once, with its client id', uploads.length === 1 && uploads[0].client_id === current.offline.client_id && uploads[0].plan_date === today, JSON.stringify(uploads.map((u) => u.client_id)));
check('...the teacher is told it was sent', notices.some((x) => /सर्वर पर भेज दी गई/.test(x.text || x)));
check('...the screens are told (so the one holding it shows the stored plan)', sentEvents.length === 1 && sentEvents[0][0].status === 'stored');
check('...and it is no longer waiting on the phone', (await M.off.waitingPlans(store)).length === 0);
await show(M.Account);
await click(q('[data-testid="logout"]'));
check('sign-out now asks the usual question (nothing waiting)', confirms.length === 2 && !/अभी सर्वर पर नहीं भेजी गई/.test(confirms[1]), confirms[1]);

console.log('\nonline: the "⚡" quick plan');
await flush();
current = null;
await show(M.Plan);
await click(item('N2.3.2'));
check('online the main button and the "⚡" quick plan are both there', !!generateBtn() && !!q('[data-testid="quick-plan"]') && /AI के बिना/.test(q('[data-testid="quick-plan"]').textContent));
await click(q('[data-testid="quick-plan"]'));
check('"⚡" asks the server for a library plan (source "library")', generateCalls.length === 1 && generateCalls[0][4].source === 'library', JSON.stringify(generateCalls[0] && generateCalls[0][4]));
await click(item('N2.3.2'));
await click(generateBtn());
check('the main button asks for the AI plan, as before (no source)', generateCalls.length === 2 && !('source' in generateCalls[1][4]), JSON.stringify(generateCalls[1] && generateCalls[1][4]));

await act(async () => root.unmount());
console.log(`\n${process.exitCode ? 'SOME CHECKS FAILED' : 'OK: ' + n + ' checks: with no connection the prepared plans can be opened, are labelled, show their worksheets in the app and are kept to be sent; online the quick plan is a choice'}`);
