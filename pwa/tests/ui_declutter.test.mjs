// The hackathon evaluators' suggestions of 12 Nov: the session as tabs (services/planSlots.js), the CSV reports and the worksheets shown inside the app
// (screens/ReportView.jsx, screens/PageViewer.jsx: before, a silent download and a pop-up tab that did not work on a desktop), one colour per group
// and never a group's colour for anything else, and the हिं / EN pill on every screen. No browser and no server.
//
//     cd pwa
//     node tests/ui_declutter.test.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';

const here = path.dirname(fileURLToPath(import.meta.url));
const src = path.join(here, '..', 'src');
const out = path.join(here, `.tmp-declutter-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));
await build({
  entryPoints: { slots: path.join(src, 'services/planSlots.js'), report: path.join(src, 'screens/ReportView.jsx') },
  bundle: true, format: 'esm', platform: 'node', outdir: out, outExtension: { '.js': '.mjs' }, loader: { '.js': 'jsx', '.jsx': 'jsx' }, logLevel: 'error',
  external: ['react', 'react-dom', 'react-router-dom'],
  plugins: [{ name: 'stubs', setup(b) {
    b.onResolve({ filter: /^\.\.\/(App|services\/api|services\/notify|services\/errors)$/ }, (a) => ({ path: a.path, namespace: 'stub' }));
    b.onLoad({ filter: /.*/, namespace: 'stub' }, () => ({ contents: 'export const useAuth = () => ({}); export const fetchAuthedPage = async () => ""; export const downloadAuthed = async () => {}; export const notify = () => {}; export const friendlyError = (e) => String(e);', loader: 'js' }));
  } }],
});
const { planSlots, stripParts } = await import(pathToFileURL(path.join(out, 'slots.mjs')).href);
const { parseCsv, REPORTS } = await import(pathToFileURL(path.join(out, 'report.mjs')).href);
const read = (f) => fs.readFileSync(path.join(src, f), 'utf8');

let n = 0;
const check = (label, fn) => { fn(); n += 1; console.log(`  OK  ${label}`); };

console.log('the session as tabs: one slot per main block');
const B = [
  { type: 'anchor', duration_minutes: 10, time_start: '0:00' },
  { type: 'setup', duration_minutes: 2, script_hi: 'सेटअप' },
  { type: 'teach', teach_group: 'beginner', duration_minutes: 29 },
  { type: 'transition', duration_minutes: 2 },
  { type: 'teach', teach_group: 'progressor', duration_minutes: 22, reteach: true },
  { type: 'reteach', teach_group: 'proficient', duration_minutes: 22 },
  { type: 'transition', duration_minutes: 1 },
];
check('the anchor, then each group: setup and transitions ride on the slot before them', () => {
  const s = planSlots(B, { hasAnchor: true });
  assert.deepEqual(s.map((x) => [x.kind, x.group, x.minutes, x.after.length]), [['anchor', null, 10, 1], ['teach', 'beginner', 29, 1], ['teach', 'progressor', 22, 0], ['reteach', 'proficient', 22, 1]]);
});
check('a re-teach is marked, whether it is a reteach block or a teach block with reteach: true', () => {
  assert.deepEqual(planSlots(B).map((x) => x.reteach), [false, false, true, true]);
});
check('an anchor activity with no anchor block still gets its tab, first', () => {
  const s = planSlots(B.slice(2), { hasAnchor: true });
  assert.equal(s[0].kind, 'anchor');
  assert.equal(s.length, 4);
});
check('short blocks before the first main block are not lost; no blocks, no slots', () => {
  assert.equal(planSlots([{ type: 'setup', duration_minutes: 2 }, { type: 'teach', teach_group: 'beginner', duration_minutes: 20 }])[0].after.length, 1);
  assert.deepEqual(planSlots(null), []);
});
check('the strip: every timed block, its share of the session', () => {
  const p = stripParts(B);
  assert.equal(p.length, 7);
  assert.ok(Math.abs(p.reduce((t, x) => t + x.share, 0) - 1) < 1e-9);
  assert.equal(p[2].group, 'beginner');
});

console.log('\nthe CSV reports as a table in the app');
check('commas, quoted fields with commas and line breaks, doubled quotes, a BOM, CRLF and empty lines', () => {
  assert.deepEqual(parseCsv('﻿roll,name\r\n1,"Rao, A"\r\n2,"say ""hi"""\n\n3,"two\nlines"\n'), [['roll', 'name'], ['1', 'Rao, A'], ['2', 'say "hi"'], ['3', 'two\nlines']]);
  assert.deepEqual(parseCsv(''), []);
});
check('the two reports: the class report (with names) and the officer data (roll numbers only)', () => {
  assert.equal(REPORTS.class.path('T1'), '/progress/export/class/T1');
  assert.equal(REPORTS.officer.path('T1'), '/progress/export/T1');
});
check('the Class progress buttons open /report in the app; nothing downloads by itself', () => {
  const p = read('screens/ProgressScreen.jsx');
  assert.ok(p.includes("navigate('/report', { state: { kind: 'class' } })") && p.includes("navigate('/report', { state: { kind: 'officer' } })"));
  assert.ok(!/downloadClassReport|downloadOfficerReport/.test(p));
});

console.log('\nthe worksheets inside the app');
check('the plan\'s worksheet buttons open /page (no pop-up tab), and /page and /report are routes', () => {
  const y = read('screens/YojanaScreen.jsx'); const app = read('App.jsx');
  assert.ok(/navigate\('\/page', \{ state: \{ path: sheetUrl\(level\)/.test(y) && !y.includes('openAuthedPage'));
  assert.ok(app.includes('<Route path="/page" element={<PageViewer />} />') && app.includes('<Route path="/report" element={<ReportView />} />'));
});
check('the page viewer shows the server page in a frame with its own Print, and hides the page\'s second print bar', () => {
  const v = read('screens/PageViewer.jsx');
  assert.ok(v.includes('srcDoc=') && v.includes('.print-bar{display:none!important}') && v.includes('contentWindow.print()') && v.includes('data-testid="page-print"'));
});

console.log('\none colour per group, and never for anything else');
check('errors use --danger and notices --info, never a group\'s colour', () => {
  const files = [];
  const walk = (d) => fs.readdirSync(d, { withFileTypes: true }).forEach((e) => (e.isDirectory() ? walk(path.join(d, e.name)) : /\.jsx$/.test(e.name) && files.push(path.join(d, e.name))));
  walk(src);
  const bad = files.flatMap((f) => fs.readFileSync(f, 'utf8').split('\n').map((l, i) => [path.relative(src, f), i + 1, l]))
    .filter(([, , l]) => /(error|role="alert"|discrepancy|विसंगति|names-note|register-done|pin-changed|suggested-skill)/i.test(l) && /var\(--(beginner|progressor|proficient)/.test(l));
  assert.deepEqual(bad.map(([f, i]) => `${f}:${i}`), []);
  const css = read('index.css');
  assert.match(css, /--danger:\s*#[0-9A-Fa-f]{6}/);
  assert.match(css, /--info:\s*#[0-9A-Fa-f]{6}/);
});
check('the old amber notices (close to the Progressors\' yellow) are gone from the screens', () => {
  for (const f of ['screens/YojanaScreen.jsx', 'screens/ReviewScreen.jsx', 'screens/PlanScreen.jsx', 'screens/AccountScreen.jsx']) assert.ok(!/#8A5A00|#FFF4D6|#FFF8E1|#FFF1CC/.test(read(f)), f);
});
check('the plan screen marks groups with the coloured shapes (GroupMark), not the 🟠🟡🟢 emoji', () => {
  const y = read('screens/YojanaScreen.jsx');
  assert.ok(y.includes('<GroupMark') && !/🟠|🟡|🟢|\.emoji/.test(y));
});

check('no per-skill test label on the plan screen either (14 Nov: "अभी परखा नहीं" was out of date, L2.7.2 too after its real runs and review)', () => {
  const y = read('screens/YojanaScreen.jsx');
  assert.ok(!/plan\.coverage/.test(y) && !y.includes('अभी परखा नहीं') && !y.includes('chip-flag'));
});

check('the photo result shows what each mistake means beside its code, and "time/times" (15 Nov: "L2.7.2-M1 — 3 occurrences" meant nothing to a teacher)', () => {
  const r = read('screens/ReviewScreen.jsx');
  assert.ok(r.includes('analysisResult.misconception_names') && r.includes('data-testid={`mistake-name-${m.id}`}') && r.includes("en={m.total_occurrences === 1 ? 'time' : 'times'}"));
  assert.ok(r.includes('<Bi hi="गलती" en="Mistake" inline />') && !r.includes('en="Misconceptions Detected"'));
});

check('the class summary prints "पढ़ाए गए कौशल" with a key for ⬆ / 🔄 / ❓, and "हर बच्चा कहाँ है" (A / PA / NA per child and skill, – not checked); "आकलन", not "समीक्षा" (15 Nov)', () => {
  const c = read('screens/ClassSummary.jsx');
  assert.ok(c.includes('<b>पढ़ाए गए कौशल</b>') && c.includes('⬆ आगे बढ़ें · 🔄 दोहराएँ · ❓ पक्का नहीं') && c.includes('<b>हर बच्चा कहाँ है</b>'));
  assert.ok(c.includes('className="where-table"') && c.includes("({ a: 'A', pa: 'PA', na: 'NA' })[r.results[k]] || '–'") && !c.includes('समीक्षा'));
});
check('the mentor report prints "कौशल के नतीजे": A / PA / NA counts and "not yet checked" per skill taught (15 Nov)', () => {
  const m = read('screens/MentorReport.jsx');
  assert.ok(m.includes('कौशल के नतीजे') && m.includes('A {k.a} · PA {k.pa} · NA {k.na} · अभी नहीं जाँचे {k.not_checked}'));
});

console.log('\nthe dictation sentences: for the teacher only');
check('a dictation group\'s slot has a "बोलकर लिखवाएँ" fold with the sheet\'s sentences, and the printed plan a line with them', () => {
  const y = read('screens/YojanaScreen.jsx'); const pp = read('screens/PlanPrint.jsx');
  assert.ok(y.includes("ws.sheet_kind === 'dictation'") && y.includes('ws.dictation_sentences') && y.includes('testid={`dictation-${level}`}') && y.includes('ये वाक्य बोर्ड पर न लिखें'));
  assert.ok(pp.includes("ws.sheet_kind === 'dictation'") && pp.includes('testid="print-dictation"'));
});

console.log('\nthe language pill');
check('on every screen, the sign-in too, and not printed', () => {
  const app = read('App.jsx');
  assert.ok((app.match(/<LangSwitch \/>/g) || []).length >= 4);
  assert.match(read('index.css'), /@media print \{ \.lang-switch \{ display: none; \} \}/);
});

console.log(`\nOK: ${n} checks: the session is tabs, the reports and worksheets open inside the app, the group colours mean only the groups, and the language pill is everywhere`);
