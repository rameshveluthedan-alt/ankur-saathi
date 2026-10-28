// The printed plan (screens/PlanPrint.jsx, at /plan/print): one A4 page the teacher carries. Hindi only, the same for every teacher, roll numbers but never a name, and every
// line held to a fixed allowance so the page stays within its budget. The signal panel is the SAME component as on the plan screen, in its compact form.
// The real page is rendered with fixture plans; its HTML is read with jsdom (no browser, no server). Whether it truly fits one A4 sheet is checked by hand with a real print.
//
//     cd pwa
//     node tests/plan_print.test.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
import React from 'react';
import ReactDOMServer from 'react-dom/server';
let JSDOM;
try { ({ JSDOM } = await import('jsdom')); } catch (e) { console.log('SKIPPED: jsdom is not installed. To run this test: cd pwa; npm install --save-dev jsdom@24'); process.exit(0); }

const here = path.dirname(fileURLToPath(import.meta.url));
const src = path.join(here, '..', 'src');
const out = path.join(here, `.tmp-print-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));      // the temporary build folder is always removed, even if a check fails
const stubs = {
  '../App': 'export const useAuth = () => globalThis.__auth;',
  'react-router-dom': 'export const useNavigate = () => () => {};',
  '../services/api': 'export const getCachedPlan = async () => { throw new Error("none"); }; export const openAuthedPage = async () => {}; export const worksheetPath = (...a) => "/w/" + a.join("/"); export const prepareOfflineCopy = () => {};',
};
await build({
  entryPoints: { print: path.join(src, 'screens/PlanPrint.jsx'), screen: path.join(src, 'screens/YojanaScreen.jsx') },
  bundle: true, format: 'esm', platform: 'node', outdir: out, outExtension: { '.js': '.mjs' }, loader: { '.js': 'jsx', '.jsx': 'jsx' }, external: ['react', 'react-dom'], logLevel: 'error',
  plugins: [{ name: 'stubs', setup(b) { b.onResolve({ filter: /^(\.\.\/App|react-router-dom|\.\.\/services\/api)$/ }, (a) => ({ path: a.path, namespace: 'stub' })); b.onLoad({ filter: /.*/, namespace: 'stub' }, (a) => ({ contents: stubs[a.path], loader: 'js' })); } }],
});
const store = {}; globalThis.localStorage = { getItem: (k) => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); }, removeItem: (k) => { delete store[k]; } };
const printMod = await import(pathToFileURL(path.join(out, 'print.mjs')).href);
const Print = printMod.default; const { PRINT_LINE_BUDGET } = printMod;
const Screen = (await import(pathToFileURL(path.join(out, 'screen.mjs')).href)).default;
const printSrc = fs.readFileSync(path.join(src, 'screens/PlanPrint.jsx'), 'utf8');
const screenSrc = fs.readFileSync(path.join(src, 'screens/YojanaScreen.jsx'), 'utf8');
const css = fs.readFileSync(path.join(src, 'index.css'), 'utf8');

let n = 0;
const check = (label, fn) => { fn(); n += 1; console.log(`  OK  ${label}`); };

// ── fixtures ──
const maths = (core, extra_count = 2) => ({ shape: 'maths_questions', signal_curated: true, maths_questions: { core, extra_count } });
const cfu3 = [{ question_hi: 'पहला प्रश्न: 27 + 15 कितना?', expected_hi: '42' }, { question_hi: 'दूसरा प्रश्न छपना नहीं चाहिए', expected_hi: 'x' }, { question_hi: 'तीसरा प्रश्न छपना नहीं चाहिए', expected_hi: 'y' }];
const tp = { i_do_hi: 'IDO-शिक्षक पहले दिखाएँ', we_do_hi: 'WEDO-साथ में करें', you_do_hi: 'YOUDO-बच्चे खुद करें' };
const teach = (g, extra = {}) => ({ type: 'teach', teach_group: g, duration_minutes: 22, time_start: '0:12', script_hi: `${g} की एक पंक्ति`, talking_points: tp, other_groups_hi: 'बाकी दोनों समूह पिछला अभ्यास करें', ...extra });
const PLAN = (blocksExtra = {}, planExtra = {}) => ({
  plan_date: '2026-10-28', domain_id: 'numeracy', selected_competency_id: 'N2.3.2',
  groups: [{ label: 'beginner', count: 7, target_competency_id: 'N2.3.1' }, { label: 'progressor', count: 14, target_competency_id: 'N2.3.2' }, { label: 'proficient', count: 9, target_competency_id: 'N3.3.1' }],
  plan: {
    anchor: { title_hi: 'बाज़ार का खेल', narration_hi: 'लंबी कहानी जो छपनी नहीं चाहिए' },
    worksheets: { beginner: { problems: [{ number: 1 }] }, progressor: { problems: [{ number: 1 }] }, proficient: { problems: [{ number: 1 }] } },
    review_prompts: { photo_sample_rolls: [], observation_reminders_hi: ['शुरुआती समूह में तीली से गिनती देखें'] },
    rotation_schedule: { blocks: [
      { type: 'anchor', duration_minutes: 10 }, { type: 'setup', duration_minutes: 2 },
      teach('progressor', { reteach: true, affected_rolls: [7, 12], reteach_mistakes: [{ misconception_id: 'N2.3.2-M1', name_hi: 'हासिल भूलना', children: 2 }], cfu: cfu3, signal: maths(['Q1', 'Q2', 'Q3']), ...(blocksExtra.progressor || {}) }),
      { type: 'transition', duration_minutes: 2 },
      teach('beginner', { signal: { shape: 'writing_prompt', signal_curated: false, writing_prompt: { prompt: 'अपने परिवार के बारे में तीन वाक्य लिखो' } }, ...(blocksExtra.beginner || {}) }),
      { type: 'transition', duration_minutes: 2 },
      teach('proficient', { signal: { shape: null, signal_curated: false }, ...(blocksExtra.proficient || {}) }),
    ] },
    ...planExtra,
  },
});
const auth = (plan, extra = {}) => ({ currentPlan: plan, setCurrentPlan() {}, selectedDomain: 'numeracy', names: { 7: 'सीता देवी', 12: 'रामू' },
  teacher: { teacher_id: 'T1', employee_code: 'MPT101', school_code: 'S1', enrolled_grades: ['grade_2'] }, ...extra });
const render = (C, a) => { globalThis.__auth = a; return ReactDOMServer.renderToStaticMarkup(React.createElement(C)); };
const doc = (html) => new JSDOM(`<!doctype html><body>${html}</body>`).window.document;
const page = (d) => d.querySelector('[data-testid="plan-print"]');
// the printed text only (the back and print buttons are not printed)
const printedText = (d) => { const p = page(d).cloneNode(true); p.querySelectorAll('.no-print').forEach((e) => e.remove()); return p.textContent; };

const html = render(Print, auth(PLAN()));
const d = doc(html);
const text = printedText(d);

console.log('the blocks');
check('1. all three teach blocks are on the page, in the plan\'s order', () => {
  assert.deepEqual([...d.querySelectorAll('section[data-testid^="print-block-"]')].map((e) => e.dataset.testid), ['print-block-progressor', 'print-block-beginner', 'print-block-proficient']);
});
check('each block names the group (shape and name), its skill and its minutes', () => {
  const h = d.querySelector('[data-testid="print-block-progressor"] [data-testid="print-block-head"]').textContent;
  assert.ok(/▲ प्रगतिशील पढ़ाएँ — N2\.3\.2 · 22 मि\./.test(h), h);
  assert.ok(/● शुरुआती पढ़ाएँ — N2\.3\.1/.test(d.querySelector('[data-testid="print-block-beginner"]').textContent));
});

console.log('\nthe signal panel: the screen\'s own component');
check('2. the print page imports the SAME SignalPanel as the plan screen, and writes no question list of its own', () => {
  const imp = /import SignalPanel(?:, \{[^}]*\})? from '\.\.\/components\/SignalPanel';/;
  assert.ok(imp.test(printSrc) && imp.test(screenSrc));
  assert.ok(!/\.map\(\s*\(?\s*q\b|core\.map|questions?\.map|maths_questions\.core\.map/.test(printSrc), 'no second rendering of the questions');
});
check('...the same three questions appear on the screen and on the print page', () => {
  const qs = (h) => [...doc(h).querySelectorAll('[data-testid="core-question"]')].map((e) => e.textContent.replace(/^\d+\.\s*/, ''));
  assert.deepEqual(qs(html), ['Q1', 'Q2', 'Q3']);
  assert.deepEqual(qs(render(Screen, auth(PLAN()))), ['Q1', 'Q2', 'Q3']);
});
check('...and the print page asks for the compact form (title, then the questions on one line; the extras are in the worksheet line)', () => {
  assert.ok(/<SignalPanel signal=\{block\.signal\} compact \/>/.test(printSrc));
  const panel = d.querySelector('[data-testid="print-block-progressor"] [data-testid="signal-panel"]');
  assert.ok(panel.dataset.compact === 'true' && !panel.querySelector('[data-testid="extra-line"]') && panel.querySelector('.print-line-1[data-testid="core-questions"]'));
  assert.ok(/लेखन कार्य: अपने परिवार/.test(d.querySelector('[data-testid="print-block-beginner"] [data-testid="writing-prompt"]').textContent));
  assert.ok(!d.querySelector('[data-testid="print-block-proficient"] [data-testid="signal-panel"]'), 'shape null: no panel');
});

console.log('\nwhat is left out');
check('3. no I do / We do / You do: neither their headings nor their text', () => {
  assert.ok(!/मैं करूँगा|हम करेंगे|तुम करोगे|I Do|We Do|You Do|IDO-|WEDO-|YOUDO-/.test(text));
});
check('the anchor is its title only, not its narration', () => {
  assert.ok(/एंकर गतिविधि: बाज़ार का खेल · 10 मि\./.test(text) && !text.includes('लंबी कहानी'));
});
check('4. no child\'s name, although the app holds them ("सीता देवी" is roll 7): the roll numbers are there', () => {
  assert.ok(!text.includes('सीता') && !text.includes('रामू'));
  assert.ok(/रोल 7, 12/.test(text));
  assert.ok(!/names/.test(printSrc.replace(/never a child's name/, '')), 'the page never reads the names');
});

console.log('\nthe line limits');
check('5. the re-teach note is ONE line: rolls and the first mistake, cut with "…" when longer', () => {
  const longNote = { affected_rolls: Array.from({ length: 30 }, (_, i) => i + 1), reteach_mistakes: [{ name_hi: 'बहुत लंबी गलती का नाम '.repeat(8), children: 9 }, { name_hi: 'दूसरी गलती छपनी नहीं चाहिए', children: 3 }] };
  const dl = doc(render(Print, auth(PLAN({ progressor: longNote }))));
  const notes = dl.querySelectorAll('[data-testid="print-reteach"]');
  assert.equal(notes.length, 1);
  assert.ok(notes[0].classList.contains('print-line-1') && notes[0].dataset.lines === '1');
  assert.ok(/🔄 पुनः शिक्षण: रोल 1, 2/.test(notes[0].textContent) && !notes[0].textContent.includes('दूसरी गलती'));
  assert.match(css, /\.print-line-1\s*\{[^}]*white-space:\s*nowrap[^}]*overflow:\s*hidden[^}]*text-overflow:\s*ellipsis/);
});
check('6. the understanding check prints the FIRST question only', () => {
  const c = d.querySelectorAll('[data-testid="print-block-progressor"] [data-testid="print-cfu"]');
  assert.equal(c.length, 1);
  assert.ok(/समझ की जाँच: पहला प्रश्न/.test(c[0].textContent) && !text.includes('दूसरा प्रश्न') && !text.includes('तीसरा प्रश्न'));
});
check('"बाकी" is the plan\'s own text (other_groups_hi), on one line', () => {
  const o = d.querySelector('[data-testid="print-block-progressor"] [data-testid="print-others"]');
  assert.ok(o.textContent === 'बाकी: बाकी दोनों समूह पिछला अभ्यास करें' && o.classList.contains('print-line-1'));
});
check(`7. worst case (long script, re-teach note, "बाकी", questions, reminders on every block): every printed piece of text is inside a line with an allowance, and the allowances add up to at most ${PRINT_LINE_BUDGET}`, () => {
  const long = (s) => s.repeat(12);
  const worst = (g) => ({ script_hi: long('बहुत लंबी पंक्ति '), other_groups_hi: long('बाकी समूह बहुत लंबा काम करेंगे '), reteach: true, affected_rolls: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
    reteach_mistakes: [{ name_hi: long('लंबी गलती '), children: 5 }], cfu: [{ question_hi: long('लंबा प्रश्न ') }, { question_hi: 'दूसरा' }],
    signal: g === 'beginner' ? { shape: 'writing_prompt', writing_prompt: { prompt: long('लंबा लेखन कार्य ') } } : maths([long('12 + 34 = ? '), '56 + 27 = ?', '48 + 37 = ?'], 3) });
  const dw = doc(render(Print, auth(PLAN({ beginner: worst('beginner'), progressor: worst('progressor'), proficient: worst('proficient') },
    { review_prompts: { observation_reminders_hi: [long('लंबी याद '), 'दूसरी याद'] } }), { teacher: { teacher_id: 'T1', employee_code: 'MPT101', enrolled_grades: ['balvatika', 'grade_1', 'grade_2', 'grade_3'] } })));
  const p = page(dw).cloneNode(true);
  p.querySelectorAll('.no-print').forEach((e) => e.remove());
  const lines = [...p.querySelectorAll('[data-lines]')].filter((e) => !e.parentElement.closest('[data-lines]'));       // the outermost allowances (a panel holds its own lines)
  const total = lines.reduce((a, e) => a + Number(e.dataset.lines), 0);
  assert.ok(total <= PRINT_LINE_BUDGET, `${total} lines`);
  assert.ok(lines.every((e) => ['1', '2'].includes(e.dataset.lines)), 'every allowance is one or two lines');
  for (const b of p.querySelectorAll('section[data-testid^="print-block-"]')) {        // the spec's budget per block: about 8 lines
    const used = [...b.querySelectorAll('[data-lines]')].filter((e) => !e.parentElement.closest('[data-lines]')).reduce((a, e) => a + Number(e.dataset.lines), 0);
    assert.ok(used <= 8, `${b.dataset.testid}: ${used} lines`);
  }
  lines.forEach((e) => e.remove());
  assert.equal(p.textContent.trim(), '', 'text outside any line allowance');
  // each allowance is enforced: one-line items cut with "…", two-line items clamped, the compact panel = a title line and a one-line question row
  for (const e of page(dw).querySelectorAll('[data-lines="1"]')) assert.ok(e.classList.contains('print-line-1'), e.outerHTML.slice(0, 80));
  for (const e of page(dw).querySelectorAll('[data-lines="2"]:not([data-testid="print-signal"])')) assert.ok(e.classList.contains('print-line-2'), e.outerHTML.slice(0, 80));
  for (const e of page(dw).querySelectorAll('[data-testid="print-signal"]')) {
    const inner = [...e.querySelectorAll('[data-testid="signal-panel"] > *')];
    assert.ok(inner.length <= 2 && inner.every((x) => x.classList.contains('signal-title') || x.classList.contains('print-line-1') || x.classList.contains('print-line-2')), e.innerHTML.slice(0, 120));
    if (e.querySelector('[data-shape="writing_prompt"]')) assert.ok(inner.length === 1 && inner[0].classList.contains('print-line-2'));
  }
  assert.match(css, /\.print-line-2\s*\{[^}]*-webkit-line-clamp:\s*2/);
  assert.ok(lines.length && total >= 30, `a real worst case fills most of the budget (${total})`);
});

console.log('\nthe same page for every teacher');
check('8. "छोटी स्क्रीन" does not change the print page (familiar_mode true and false render identically)', () => {
  store.familiar_mode = 'true'; const a = render(Print, auth(PLAN()));
  store.familiar_mode = 'false'; const b = render(Print, auth(PLAN()));
  delete store.familiar_mode;
  assert.equal(a, b);
  assert.ok(!/familiar|getFamiliarMode/i.test(printSrc));
});
check('Hindi only, whatever the "सिर्फ़ हिंदी" setting: no English translation spans on the page', () => {
  assert.ok(!page(d).querySelector('.en') && !/getHindiOnly|<Bi\b/.test(printSrc));
});

console.log('\nheader, review, worksheets, footer');
check('the header: teacher code, class, date in Hindi, main skill; then "लगभग" and the sum of the blocks\' minutes', () => {
  assert.equal(d.querySelector('[data-testid="print-head"]').textContent, 'MPT101 · कक्षा 2 · 28 अक्टू॰ 2026 · N2.3.2');
  assert.equal(d.querySelector('[data-testid="print-time"]').textContent, 'योजना समय: लगभग 82 मिनट');
});
check('once the plan records its own length, the exact value without "लगभग"', () => {
  assert.equal(doc(render(Print, auth(PLAN({}, { session_minutes: 45 })))).querySelector('[data-testid="print-time"]').textContent, 'योजना समय: 45 मिनट');
});
check('the review rows: the plan\'s observation reminders, photos chosen on the Review screen, and reading aloud only for a reading-speed skill', () => {
  assert.ok(/अवलोकन: शुरुआती समूह में तीली से गिनती देखें/.test(text) && /फ़ोटो: समीक्षा स्क्रीन पर चुने जाएँगे/.test(text) && !text.includes('पढ़कर सुनाना'));
  const lit = PLAN(); lit.groups[1].target_competency_id = 'L2.5.1';
  assert.ok(/पढ़कर सुनाना: समीक्षा स्क्रीन पर/.test(printedText(doc(render(Print, auth(lit))))));
});
check('one worksheet line: the core and extra counts from the signal, the writing prompt, and "वर्कशीट देखें" for a block without a panel', () => {
  assert.equal(d.querySelector('[data-testid="print-worksheets"]').textContent, 'वर्कशीट: ● शुरुआती लेखन कार्य · ▲ प्रगतिशील 3 मुख्य + 2 · ■ दक्ष: वर्कशीट देखें');
});
check('the footer, like the worksheets\'', () => {
  assert.equal(d.querySelector('[data-testid="print-footer"]').textContent, '🌱 अंकुर साथी · 2026-10-28 · योजना N2.3.2');
});

console.log('\nreaching it');
check('the plan screen has ONE "🖨️ प्रिंट" button in its title row, opening /plan/print', () => {
  const sh = render(Screen, auth(PLAN()));
  assert.equal((sh.match(/data-testid="open-print"/g) || []).length, 1);
  assert.ok(/class="screen-header plan-title"[\s\S]*?data-testid="open-print"[^>]*>🖨️ प्रिंट</.test(sh));
  assert.ok(/navigate\('\/plan\/print'\)/.test(screenSrc));
});
check('the app has the /plan/print route, with no bottom bar there; the back and print buttons are not printed', () => {
  const app = fs.readFileSync(path.join(src, 'App.jsx'), 'utf8');
  assert.ok(/<Route path="\/plan\/print" element=\{<PlanPrint \/>\} \/>/.test(app) && /if \(path === '\/plan\/print'\) return null;/.test(app));
  assert.ok(d.querySelector('.no-print [data-testid="print-back"]') && d.querySelector('.no-print [data-testid="print-now"]'));
  assert.match(css, /@media print\s*\{[\s\S]*?@page\s*\{\s*size:\s*A4/);
});

console.log(`\nOK: ${n} checks: the printed plan is one A4 page: the three blocks with the screen's own signal panel, no talking points, no names, every line within its allowance`);
