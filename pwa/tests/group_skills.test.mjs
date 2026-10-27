// Each group's skill for the day: the rules (pure functions) and what the panel shows. No browser and no server.
//
//     cd pwa
//     node tests/group_skills.test.mjs
//
// It needs only what the PWA already has: react, react-dom, and esbuild (which comes with vite).
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
import React from 'react';
import ReactDOMServer from 'react-dom/server';

const here = path.dirname(fileURLToPath(import.meta.url));
const src = path.join(here, '..', 'src');
const out = path.join(here, `.tmp-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));      // the temporary build folder is always removed, even if a check fails
await build({
  entryPoints: { logic: path.join(src, 'services/groupSkills.js'), panel: path.join(src, 'components/GroupSkillsPanel.jsx'), drawer: path.join(src, 'components/GroupSkillsDrawer.jsx') },
  bundle: true, format: 'esm', platform: 'node', outdir: out, outExtension: { '.js': '.mjs' }, loader: { '.js': 'jsx', '.jsx': 'jsx' }, external: ['react', 'react-dom'], logLevel: 'error',
});
const logic = await import(pathToFileURL(path.join(out, 'logic.mjs')).href);
const { default: Panel } = await import(pathToFileURL(path.join(out, 'panel.mjs')).href);
const { default: Drawer } = await import(pathToFileURL(path.join(out, 'drawer.mjs')).href);
const { initialRows, buildGenerateOptions, withSkill, staysOnYesterdaysSkill, summarize, acceptReteach, skillChoices, fitsDay, canReturnToYesterday, panelStatus, toggleReteach, reteachChoice, selectValue, chooseOption, visibleChoices } = logic;

let n = 0;
const check = (label, fn) => { fn(); n += 1; console.log(`  OK  ${label}`); };
const GRADE = { 0: 'balvatika', 1: 'grade_1', 2: 'grade_2', 3: 'grade_3' };
const sk = (id, hi = id) => ({ id, name_hi: hi, name_en: id, grade_level: GRADE[id[1]] || 'grade_2' });      // the grade is in the id: N0 Balvatika, N1 Grade 1, ...
// what the server sends for N2.3.2: the derived skills, and the lists the teacher may choose from (foundations for the Beginners, what builds on it for the Proficients)
const ladder = { beginner: sk('N2.3.1'), progressor: sk('N2.3.2'), proficient: sk('N3.3.1'), options: { beginner: [sk('N2.3.1'), sk('N1.3.1'), sk('N1.2.4')], proficient: [sk('N3.3.1'), sk('N3.5.2'), sk('N3.3.6')] } };
const groups = [{ label: 'beginner', count: 3 }, { label: 'progressor', count: 3 }, { label: 'proficient', count: 2 }];
// the example from the design discussion: the teacher decided Advance / Re-teach / Advance at the last review
const proposal = { has_history: true, previous_date: '2026-10-22', groups: {
  beginner: { previous_target: sk('N2.3.1'), previous_decision: 'advance', proposed: sk('N2.3.2'), reason: 'advance', alternatives: [] },
  progressor: { previous_target: sk('N2.3.2'), previous_decision: 'reteach', proposed: sk('N2.3.2'), reason: 'reteach', alternatives: [] },
  proficient: { previous_target: sk('N3.3.1'), previous_decision: 'advance', proposed: sk('N3.5.2'), reason: 'advance', alternatives: [] },
} };

console.log('the rules');
check('no earlier plan: every group follows the skill chosen, nothing is re-taught, nothing is overridden', () => {
  const { rows, reteach } = initialRows({ ladder, proposal: { has_history: false, groups: {} }, selectedId: 'N2.3.2' });
  assert.deepEqual([rows.beginner.skillId, rows.progressor.skillId, rows.proficient.skillId], ['N2.3.1', 'N2.3.2', 'N3.3.1']);
  assert.deepEqual(['beginner', 'progressor', 'proficient'].map((l) => rows[l].source), ['derived', 'selected', 'derived']);
  assert.deepEqual(reteach, { beginner: false, progressor: false, proficient: false });
  assert.deepEqual(buildGenerateOptions({ rows, reteach, groups, ready: true }), { groupSkills: undefined, reteachGroups: [] });
});
check('a proposal that could not be fetched (null) behaves the same', () => {
  const { rows } = initialRows({ ladder, proposal: null, selectedId: 'N2.3.2' });
  assert.equal(rows.beginner.skillId, 'N2.3.1');
});
const ex = initialRows({ ladder, proposal, selectedId: 'N2.3.2' });
check('the design example: Beginners advance to N2.3.2, Progressors stay on N2.3.2 and re-teach, Proficients take the graph\'s next skill', () => {
  assert.deepEqual([ex.rows.beginner.skillId, ex.rows.progressor.skillId, ex.rows.proficient.skillId], ['N2.3.2', 'N2.3.2', 'N3.5.2']);
  assert.deepEqual(['beginner', 'progressor', 'proficient'].map((l) => ex.rows[l].source), ['review', 'selected', 'review']);
  assert.deepEqual(ex.reteach, { beginner: false, progressor: true, proficient: false });
});
check('what is sent: only the skills that DIFFER from the derived ones, and the groups to re-teach', () => {
  assert.deepEqual(buildGenerateOptions({ rows: ex.rows, reteach: ex.reteach, groups, ready: true }), { groupSkills: { beginner: 'N2.3.2', proficient: 'N3.5.2' }, reteachGroups: ['progressor'] });
});
check('a skill the teacher picks that equals the derived one is NOT sent (it stays marked as derived)', () => {
  const rows = { ...ex.rows, beginner: withSkill(ex.rows.beginner, 'N2.3.1') };
  assert.equal(buildGenerateOptions({ rows, reteach: ex.reteach, groups, ready: true }).groupSkills.beginner, undefined);
  assert.equal(rows.beginner.source, 'teacher');
});
check('choosing the suggestion again counts as the suggestion, not as the teacher\'s own choice', () => {
  const changed = withSkill(ex.rows.proficient, 'N3.3.1');
  assert.equal(withSkill(changed, 'N3.5.2').source, 'review');
});
check('the day\'s skill is NOT yesterday\'s: the Progressors\' re-teach is off by default (a re-teach is the same skill)', () => {
  const other = initialRows({ ladder: { ...ladder, progressor: sk('N2.3.3') }, proposal, selectedId: 'N2.3.3' });
  assert.equal(other.rows.progressor.skillId, 'N2.3.3');
  assert.equal(other.reteach.progressor, false);
  assert.equal(staysOnYesterdaysSkill(other.rows.progressor), false);
  assert.equal(staysOnYesterdaysSkill(ex.rows.progressor), true);
});
check('"not sure" keeps the group on its skill and re-teach is on by default; Advance never turns it on', () => {
  const p2 = JSON.parse(JSON.stringify(proposal));
  p2.groups.beginner = { previous_target: sk('N2.3.1'), previous_decision: 'not_sure', proposed: sk('N2.3.1'), reason: 'not_sure', alternatives: [] };
  const r = initialRows({ ladder, proposal: p2, selectedId: 'N2.3.2' });
  assert.equal(r.rows.beginner.skillId, 'N2.3.1');
  assert.equal(r.reteach.beginner, true);
  assert.equal(ex.reteach.beginner, false);
});
check('a group with no decision recorded gets the derived skill, with no suggestion', () => {
  const p3 = JSON.parse(JSON.stringify(proposal));
  p3.groups.proficient = { previous_target: sk('N3.3.1'), previous_decision: null, proposed: null, reason: 'no_decision', alternatives: [] };
  const r = initialRows({ ladder, proposal: p3, selectedId: 'N2.3.2' });
  assert.equal(r.rows.proficient.skillId, 'N3.3.1');
  assert.equal(r.rows.proficient.source, 'derived');
  assert.equal(r.reteach.proficient, false);
});
check('a group with no children is never sent for re-teach', () => {
  const g0 = [{ label: 'beginner', count: 3 }, { label: 'progressor', count: 0 }, { label: 'proficient', count: 2 }];
  assert.deepEqual(buildGenerateOptions({ rows: ex.rows, reteach: ex.reteach, groups: g0, ready: true }).reteachGroups, []);
});
check('if the panel could not be shown NOTHING is sent: the plan decides, as before', () => {
  assert.deepEqual(buildGenerateOptions({ rows: ex.rows, reteach: ex.reteach, groups, ready: false }), {});
  assert.deepEqual(buildGenerateOptions({ rows: null, reteach: {}, groups, ready: true }), {});
});
check('the summary line has one entry per group, with the re-teach marked', () => {
  const s = summarize(ex.rows, ex.reteach);
  assert.deepEqual(s.map((x) => [x.label, x.skillId, x.reteach]), [['beginner', 'N2.3.2', false], ['progressor', 'N2.3.2', true], ['proficient', 'N3.5.2', false]]);
});

console.log('what the panel shows');
const comps = [sk('N2.3.1', 'बिना हासिल जोड़'), sk('N2.3.2', 'हासिल वाला जोड़'), sk('N3.3.1', '3 अंकों का जोड़'), sk('N3.5.2', 'परिमाप')];
const render = (rows, reteach, hasHistory = true, extra = {}) => ReactDOMServer.renderToStaticMarkup(
  React.createElement(Panel, { groups, competencies: comps, ladder, selectedId: 'N2.3.2', rows, setRows: () => {}, reteach, setReteach: () => {}, onSelectSkill: () => {}, hasHistory, disabled: false, ...extra }));
const selectOf = (h, label) => h.split(`data-testid="group-skill-select-${label}"`)[1].split('</select>')[0];
const html = render(ex.rows, ex.reteach);
check('three group rows, a skill choice for the Beginners and the Proficients, and the Progressors\' skill as plain text', () => {
  for (const l of ['beginner', 'progressor', 'proficient']) assert.ok(html.includes(`data-testid="group-row-${l}"`), l);
  assert.ok(html.includes('data-testid="group-skill-select-beginner"') && html.includes('data-testid="group-skill-select-proficient"'));
  assert.ok(!html.includes('group-skill-select-progressor') && html.includes('data-testid="group-skill-progressor"'));
});
check('the Beginners\' choice is on the suggested skill, N2.3.2, and the Proficients\' on N3.5.2', () => {
  assert.match(html, /<option value="N2\.3\.2" selected="">/);
  assert.match(html, /<option value="N3\.5\.2" selected="">/);
});
check('the last plan\'s skill and the teacher\'s decision are shown in the review screen\'s own words', () => {
  assert.ok(html.includes('पिछली योजना: N2.3.1') && html.includes('पिछली योजना: N2.3.2') && html.includes('पिछली योजना: N3.3.1'));
  assert.ok(!html.includes('कल: N2'), 'never "yesterday": the last plan can be days ago');
  assert.ok(html.includes('▲ आगे बढ़ें') && html.includes('🔄 दोहराएँ'));
});
check('the last plan is named by its date, which is often not yesterday', () => {
  const dated = render(ex.rows, ex.reteach, true, { previousDate: '2026-10-24' });
  const shown = new Date('2026-10-24T00:00:00').toLocaleDateString('hi-IN', { day: 'numeric', month: 'short' });
  assert.ok(dated.includes(`पिछली योजना (${shown}): N2.3.2`), shown);
});
check('the Progressors keep a re-teach BOX (ticked, with what it means); the Beginners and Proficients have NO box: their list holds the decision', () => {
  assert.match(html, /data-testid="reteach-toggle-progressor"[^>]*checked=""|checked=""[^>]*data-testid="reteach-toggle-progressor"/);
  assert.ok(!html.includes('reteach-toggle-beginner') && !html.includes('reteach-toggle-proficient'));
  assert.match(selectOf(html, 'beginner'), /<option value="N2\.3\.2" selected="">/);       // the Beginners are on the Advance suggestion, not re-teaching
  assert.ok(html.includes('मुख्य ब्लॉक कल की गलतियों को दोबारा समझाएगा'));
});
check('the sources are named: from the review, from the chosen skill, the teacher\'s own', () => {
  assert.ok(html.includes('आपके कल के निर्णय से') && html.includes('आपका चुना कौशल'));
  const changed = { ...ex.rows, beginner: withSkill(ex.rows.beginner, 'N2.3.1') };
  const h2 = render(changed, ex.reteach);
  assert.ok(h2.includes('आपकी पसंद') && h2.includes('सुझाव पर लौटें'));
});
check('no earlier plan: the panel says so, and offers no re-teach box (there is nothing to re-teach)', () => {
  const fresh = initialRows({ ladder, proposal: { has_history: false, groups: {} }, selectedId: 'N2.3.2' });
  const h4 = render(fresh.rows, fresh.reteach, false);
  assert.ok(h4.includes('पिछली योजना नहीं मिली') && !h4.includes('reteach-toggle'));
});
check('a group with no children is not offered a re-teach, and while generating everything is disabled', () => {
  const g0 = [{ label: 'beginner', count: 0 }, { label: 'progressor', count: 3 }, { label: 'proficient', count: 2 }];
  const h5 = render(ex.rows, ex.reteach, true, { groups: g0 });
  assert.ok(!selectOf(h5, 'beginner').includes('reteach:') && h5.includes('reteach-toggle-progressor'));
  const h6 = render(ex.rows, ex.reteach, true, { disabled: true });
  for (const testid of ['group-skill-select-beginner', 'group-skill-select-proficient', 'reteach-toggle-progressor']) {
    assert.ok(new RegExp(`<(select|input)[^>]*disabled=""[^>]*data-testid="${testid}"|<(select|input)[^>]*data-testid="${testid}"[^>]*disabled=""`).test(h6), testid);
  }
});
console.log('the app\'s own recommendation from the children\'s evidence');
const ev = (assessed, wrong, over = {}) => ({ assessed, with_mistakes: wrong, needed: Math.ceil(assessed / 3), very_small: assessed > 0 && assessed < 4, recommend: assessed >= 4 && wrong >= Math.ceil(assessed / 3), rolls: [5, 6].slice(0, wrong), mistakes: wrong ? [{ misconception_id: 'N2.3.2-M1', name_hi: 'हासिल भूलना', children: wrong }] : [], ...over });
const entry = (target, decision, proposed, reason, evidence, recommendation, conflict = false) => ({ previous_target: sk(target), previous_decision: decision, proposed: proposed ? sk(proposed) : null, reason, alternatives: [], evidence, recommendation, conflict });
const recProposal = { has_history: true, groups: {
  beginner: entry('N2.3.1', null, 'N2.3.1', 'recommended', ev(4, 2), 'reteach'),
  progressor: entry('N2.3.2', null, 'N2.3.2', 'recommended', ev(6, 2), 'reteach'),
  proficient: entry('N3.3.1', null, null, 'no_decision', ev(2, 2), 'very_small'),
} };
const rec = initialRows({ ladder, proposal: recProposal, selectedId: 'N2.3.2' });
check('no decision was recorded but the evidence recommends a re-teach: the group stays on yesterday\'s skill and the box is ticked, from the evidence', () => {
  assert.equal(rec.rows.beginner.skillId, 'N2.3.1');
  assert.equal(rec.rows.beginner.source, 'recommendation');
  assert.deepEqual(rec.reteach, { beginner: true, progressor: true, proficient: false });
});
check('a very small group is shown the numbers but nothing is ticked, and its skill is the derived one', () => {
  assert.equal(rec.rows.proficient.skillId, 'N3.3.1');
  assert.equal(rec.rows.proficient.source, 'derived');
  assert.equal(rec.rows.proficient.recommendation, 'very_small');
  assert.equal(rec.rows.proficient.evidence.assessed, 2);
});
check('the Progressors are not ticked if the day\'s skill is not yesterday\'s, even when the evidence recommends it (the panel will offer yesterday\'s skill)', () => {
  const other = initialRows({ ladder: { ...ladder, progressor: sk('N2.3.3') }, proposal: recProposal, selectedId: 'N2.3.3' });
  assert.equal(other.reteach.progressor, false);
});
const conflictProposal = { has_history: true, groups: { ...recProposal.groups, progressor: entry('N2.3.2', 'advance', 'N3.3.1', 'advance', ev(6, 2), 'reteach', true) } };
const cf = initialRows({ ladder, proposal: conflictProposal, selectedId: 'N2.3.2' });
check('the teacher chose Advance against the evidence: the TEACHER\'S decision stands (nothing is ticked), and the conflict is kept so the screen can ask', () => {
  assert.equal(cf.reteach.progressor, false);
  assert.equal(cf.rows.progressor.conflict, true);
  assert.equal(cf.rows.progressor.recommendation, 'reteach');
});
check('accepting "re-teach instead?": the Progressors on yesterday\'s skill just tick; on another skill they must choose yesterday\'s; the other groups go back to yesterday\'s skill; with no yesterday there is nothing to do', () => {
  assert.deepEqual(acceptReteach({ label: 'progressor', row: cf.rows.progressor, selectedId: 'N2.3.2' }), { type: 'tick' });
  assert.deepEqual(acceptReteach({ label: 'progressor', row: cf.rows.progressor, selectedId: 'N2.3.3' }), { type: 'select', skillId: 'N2.3.2' });
  assert.deepEqual(acceptReteach({ label: 'beginner', row: ex.rows.beginner, selectedId: 'N2.3.2' }), { type: 'skill', skillId: 'N2.3.1' });
  assert.equal(acceptReteach({ label: 'beginner', row: { previous: null }, selectedId: 'N2.3.2' }), null);
});
check('what is sent when a recommended re-teach is kept: the group stays on yesterday\'s skill, which is sent only if it differs from the derived one', () => {
  const o = buildGenerateOptions({ rows: rec.rows, reteach: rec.reteach, groups, ready: true });
  assert.deepEqual(o.reteachGroups, ['beginner', 'progressor']);
  assert.equal(o.groupSkills, undefined);
});

console.log('what the panel shows of the evidence');
const hRec = render(rec.rows, rec.reteach);
check('what the last review found: how many of those assessed made a mistake, which children (the teacher\'s own screen) and which mistake', () => {
  assert.ok(hRec.includes('कल की जाँच में: 6 में से <b>2</b> बच्चों ने गलती की') || /6 में से <!-- -->\s*<b>2<\/b>/.test(hRec) || hRec.includes('6 में से'), 'evidence line');
  assert.ok(hRec.includes('(रोल 5, 6)') && hRec.includes('हासिल भूलना (2)'));
});
check('the recommendation says how many are needed, and a very small group says it is too small to suggest anything', () => {
  assert.ok(hRec.includes('data-testid="recommendation-progressor"') && hRec.includes('कम से कम 2 बच्चों ने गलती की'));
  assert.ok(hRec.includes('बहुत छोटा समूह: केवल 2 बच्चे जाँचे गए'));
});
check('the source is named when the suggestion comes from the evidence', () => { assert.ok(hRec.includes('कल की जाँच के सुझाव से')); });
check('"most children got it" is said when the evidence does not recommend a re-teach (and is not a very small group)', () => {
  const calm = initialRows({ ladder, proposal: { has_history: true, groups: { ...recProposal.groups, beginner: entry('N2.3.1', 'advance', 'N2.3.2', 'advance', ev(4, 1), null) } }, selectedId: 'N2.3.2' });
  assert.ok(render(calm.rows, calm.reteach).includes('अधिकतर बच्चों ने सही किया: दोहराने का सुझाव नहीं है'));
});
const hCf = render(cf.rows, cf.reteach);
check('Advance against the evidence: the panel asks once, with a button to re-teach instead; once ticked the question goes away', () => {
  assert.ok(hCf.includes('data-testid="conflict-progressor"') && hCf.includes('आपने आगे बढ़ना चुना था') && hCf.includes('data-testid="accept-reteach-progressor"'));
  const ticked = render(cf.rows, { ...cf.reteach, progressor: true });
  assert.ok(!ticked.includes('data-testid="conflict-progressor"'));
});
check('no evidence from the last review: no evidence block at all (a group nobody was assessed in)', () => {
  const none = initialRows({ ladder, proposal: { has_history: true, groups: { ...recProposal.groups, proficient: entry('N3.3.1', 'advance', 'N3.5.2', 'advance', ev(0, 0), null) } }, selectedId: 'N2.3.2' });
  assert.ok(!render(none.rows, none.reteach).includes('data-testid="evidence-proficient"'));
});

console.log('which skills a group may be given, and when a re-teach may be ticked (found on the first click-through)');
const idsOf = (gs) => gs.flatMap((g) => g.ids);
check('the Beginners may take today\'s skill and its foundations only (the N3.6.1 a tester picked is not offered); the Proficients today\'s skill and what builds on it only (not the N0.2.1 a tester picked)', () => {
  const b = skillChoices({ label: 'beginner', ladder, row: ex.rows.beginner, selectedId: 'N2.3.2' });
  const x = skillChoices({ label: 'proficient', ladder, row: ex.rows.proficient, selectedId: 'N2.3.2' });
  assert.deepEqual(b.map((g) => g.key), ['today', 'foundation']);
  assert.deepEqual(idsOf(b), ['N2.3.2', 'N2.3.1', 'N1.3.1', 'N1.2.4']);
  assert.deepEqual(x.map((g) => g.key), ['today', 'next']);
  assert.deepEqual(idsOf(x), ['N2.3.2', 'N3.3.1', 'N3.5.2', 'N3.3.6']);
  assert.ok(!idsOf(b).includes('N3.6.1') && !idsOf(x).includes('N0.2.1'));
});
check('yesterday\'s skill and the suggestion are offered, even outside the lists, when they are not ahead of the day\'s skill (Beginners), and the skill the group is on is always in the list', () => {
  const far = initialRows({ ladder, proposal: { has_history: true, groups: { beginner: entry('N1.1.1', 'reteach', 'N1.1.1', 'reteach', ev(0, 0), null), progressor: entry('N2.3.2', null, null, 'no_decision', ev(0, 0), null), proficient: entry('N3.3.1', null, null, 'no_decision', ev(0, 0), null) } }, selectedId: 'N2.3.2' });
  const b = skillChoices({ label: 'beginner', ladder, row: far.rows.beginner, selectedId: 'N2.3.2' });
  assert.deepEqual(b.map((g) => g.key), ['today', 'foundation', 'kept']);
  assert.deepEqual(b[2].ids, ['N1.1.1']);
  assert.ok(idsOf(b).includes(far.rows.beginner.skillId));
});
const html2 = render(ex.rows, ex.reteach);
check('on the screen: the Beginners\' list has only today\'s skill and foundations, the Proficients\' only today\'s skill and what builds on it, each under its own heading', () => {
  const b = selectOf(html2, 'beginner'); const x = selectOf(html2, 'proficient');
  assert.ok(b.includes('value="reteach:N2.3.1"') && !b.includes('value="N2.3.1"') && b.includes('value="N1.3.1"') && !b.includes('N3.6.1') && !b.includes('N3.5.2'));      // yesterday's N2.3.1: only as a re-teach
  assert.ok(x.includes('value="reteach:N3.3.1"') && !x.includes('value="N3.3.1"') && x.includes('value="N3.5.2"') && !x.includes('N0.2.1') && !x.includes('value="N2.3.1"'));      // likewise N3.3.1
  assert.ok(b.includes('आधार कौशल') && x.includes('आगे के कौशल') && b.includes('आज का कौशल'));
});
check('ONE LIST holds the decision: for the Beginners, who advanced to N2.3.2 (yesterday N2.3.1), N2.3.1 is offered ONLY as "re-teach N2.3.1" (a plain "same lesson again" is not a choice); no box, no button', () => {
  const rows = { ...ex.rows, beginner: withSkill(ex.rows.beginner, 'N2.3.2') };      // the Beginners advanced to N2.3.2: yesterday they were on N2.3.1
  const h = render(rows, { ...ex.reteach, beginner: false });
  const sel = selectOf(h, 'beginner');
  assert.ok(sel.includes('value="reteach:N2.3.1"') && sel.includes('🔄 दोहराएँ: N2.3.1') && sel.includes('कल का कौशल दोहराएँ'));
  assert.ok(!/<option value="N2\.3\.1"/.test(sel), sel.slice(0, 700));
  assert.ok(!h.includes('reteach-toggle-beginner') && !h.includes('go-back-reteach-beginner') && !h.includes('reteach-not-today-beginner') && !h.includes('reteach-goes-back'));
  const pbox = html2.match(/<input[^>]*data-testid="reteach-toggle-progressor"[^>]*>/)[0];      // the Progressors ARE on yesterday's skill: just a box
  assert.ok(!/disabled=""/.test(pbox) && !html2.includes('go-back-reteach-progressor'));
});
check('the Progressors on another day\'s skill than yesterday\'s: the box is disabled and the button chooses yesterday\'s skill (which changes the day\'s skill)', () => {
  const rows = { ...ex.rows, progressor: { ...ex.rows.progressor, skillId: 'N2.3.3' } };
  const h = render(rows, { ...ex.reteach, progressor: false }, true, { selectedId: 'N2.3.3' });
  assert.ok(/disabled=""/.test(h.match(/<input[^>]*data-testid="reteach-toggle-progressor"[^>]*>/)[0]) && h.includes('N2.3.2 चुनकर दोहराएँ'));
});
check('the button does the whole job for a group: the Beginners go back to yesterday\'s skill AND the box is ticked', () => {
  const a = acceptReteach({ label: 'beginner', row: withSkill(ex.rows.beginner, 'N2.3.2'), selectedId: 'N2.3.2' });
  assert.deepEqual(a, { type: 'skill', skillId: 'N2.3.1' });
  const back = withSkill(withSkill(ex.rows.beginner, 'N2.3.2'), a.skillId);
  assert.equal(staysOnYesterdaysSkill(back), true);
});
check('a re-teach for a group that is not on yesterday\'s skill is never SENT, even if the box were ticked', () => {
  const rows = { ...ex.rows, beginner: withSkill(ex.rows.beginner, 'N2.3.2') };
  assert.deepEqual(buildGenerateOptions({ rows, reteach: { beginner: true, progressor: true, proficient: false }, groups, ready: true }).reteachGroups, ['progressor']);
});

console.log('the day\'s skill is not the one yesterday\'s decisions were about (found on the click-through: N0.1.1 chosen, the Beginners were given N2.3.2)');
check('the rule by grade: the Beginners are never ahead, the Proficients never behind, the same grade fits, an unknown grade fits', () => {
  assert.equal(fitsDay('beginner', 'grade_2', 'balvatika'), false);
  assert.equal(fitsDay('beginner', 'balvatika', 'grade_2'), true);
  assert.equal(fitsDay('beginner', 'grade_2', 'grade_2'), true);
  assert.equal(fitsDay('proficient', 'balvatika', 'grade_2'), false);
  assert.equal(fitsDay('proficient', 'grade_3', 'grade_2'), true);
  assert.equal(fitsDay('proficient', undefined, 'grade_2'), true);
  assert.equal(fitsDay('beginner', 'grade_9', 'grade_2'), true);
});
const day0 = { beginner: sk('N0.1.1'), progressor: sk('N0.1.1'), proficient: sk('N0.1.1'), options: { beginner: [], proficient: [] } };
const demoProposal = { has_history: true, groups: {
  beginner: entry('N2.3.1', 'advance', 'N2.3.2', 'advance', ev(0, 0), null),
  progressor: entry('N2.3.2', null, 'N2.3.2', 'recommended', ev(14, 6), 'reteach'),
  proficient: entry('N3.3.1', null, null, 'no_decision', ev(0, 0), null),
} };
const u = initialRows({ ladder: day0, proposal: demoProposal, selectedId: 'N0.1.1' });
check('N0.1.1 chosen: the Beginners follow the day\'s skill, N0.1.1, and NOT the Advance suggestion N2.3.2 (Grade 2, ahead of a Balvatika day); the suggestion is kept to be explained', () => {
  assert.equal(u.rows.beginner.skillId, 'N0.1.1');
  assert.equal(u.rows.beginner.source, 'derived');
  assert.equal(u.rows.beginner.ignored.id, 'N2.3.2');
});
check('the bar above Generate then reads N0.1.1 for all three groups, which is what the tester expected', () => {
  assert.deepEqual(summarize(u.rows, u.reteach).map((x) => x.skillId), ['N0.1.1', 'N0.1.1', 'N0.1.1']);
});
check('nothing is sent: no group skill (every group is on the derived skill) and no re-teach (the day\'s skill is not yesterday\'s)', () => {
  assert.deepEqual(buildGenerateOptions({ rows: u.rows, reteach: u.reteach, groups, ready: true }), { groupSkills: undefined, reteachGroups: [] });
});
const hu = render(u.rows, u.reteach, true, { selectedId: 'N0.1.1', ladder: day0 });
check('the panel says why the suggestion was not used, in Hindi and English', () => {
  assert.ok(hu.includes('data-testid="ignored-beginner"') && hu.includes('सुझाया कौशल N2.3.2 आज के कौशल से मेल नहीं खाता') && hu.includes('शुरुआती समूह आज के कौशल से आगे नहीं जा सकता'));
  assert.ok(hu.includes('does not fit today'));
});
check('the Beginners\' list offers only N0.1.1: yesterday\'s N2.3.1 and the suggestion N2.3.2 are not offered, because they are ahead of the day\'s skill', () => {
  const sel = hu.split('data-testid="group-skill-select-beginner"')[1].split('</select>')[0];
  assert.ok(sel.includes('value="N0.1.1"') && !sel.includes('N2.3.1') && !sel.includes('N2.3.2'));
});
check('the Beginners are NOT offered "re-teach N2.3.1" (it would put them ahead of the day\'s skill): no such entry, a plain reason, no button, no box', () => {
  assert.ok(!selectOf(hu, 'beginner').includes('reteach:') && !hu.includes('reteach-toggle-beginner'));
  assert.ok(hu.includes('data-testid="reteach-not-today-beginner"') && !hu.includes('go-back-reteach-beginner'));
  assert.equal(canReturnToYesterday({ label: 'beginner', row: u.rows.beginner, ladder: day0 }), false);
  assert.equal(reteachChoice({ label: 'beginner', row: u.rows.beginner, ladder: day0 }), null);
  assert.equal(acceptReteach({ label: 'beginner', row: u.rows.beginner, selectedId: 'N0.1.1', ladder: day0 }), null);
});
check('the Progressors can always go back (the day\'s skill itself becomes yesterday\'s), and the others\' suggestions that fit are still used', () => {
  assert.equal(canReturnToYesterday({ label: 'progressor', row: u.rows.progressor, ladder: day0 }), true);
  const ahead = initialRows({ ladder: day0, proposal: { has_history: true, groups: { ...demoProposal.groups, proficient: entry('N3.3.1', 'advance', 'N3.5.2', 'advance', ev(0, 0), null) } }, selectedId: 'N0.1.1' });
  assert.equal(ahead.rows.proficient.skillId, 'N3.5.2');
  assert.equal(ahead.rows.proficient.ignored, null);
});
check('on the day the suggestion is about (N2.3.2) nothing changes: the Beginners advance to N2.3.2', () => {
  const same = initialRows({ ladder, proposal: demoProposal, selectedId: 'N2.3.2' });
  assert.equal(same.rows.beginner.skillId, 'N2.3.2');
  assert.equal(same.rows.beginner.ignored, null);
});

console.log('what yesterday\'s plan did, and which plan the suggestions come from (found on the click-through: a Progressor re-teach left no trace)');
const withReteach = { has_history: true, previous_date: '2026-10-23', groups: {
  beginner: { ...entry('N2.3.1', null, null, 'no_decision', ev(0, 0), null), previous_reteach: false },
  progressor: { ...entry('N2.3.2', null, null, 'no_decision', ev(0, 0), null), previous_reteach: true },
  proficient: { ...entry('N3.3.1', null, null, 'no_decision', ev(0, 0), null), previous_reteach: false },
} };
const rr = initialRows({ ladder, proposal: withReteach, selectedId: 'N2.3.2' });
const hr = render(rr.rows, rr.reteach, true, { previousDate: '2026-10-23' });
check('the group that re-taught yesterday says so on its "yesterday" line, and only that group', () => {
  assert.equal(rr.rows.progressor.previousReteach, true);
  assert.equal(rr.rows.beginner.previousReteach, false);
  assert.ok(hr.includes('data-testid="previous-reteach-progressor"') && hr.includes('कल पुनः शिक्षण हुआ') && hr.includes('Re-taught yesterday'));
  assert.ok(!hr.includes('previous-reteach-beginner') && !hr.includes('previous-reteach-proficient'));
});
check('it says WHICH plan the suggestions come from (the date), in Hindi and English', () => {
  assert.ok(hr.includes('सुझाव 2026-10-23 की योजना') && hr.includes('Suggestions come from the plan of 2026-10-23'));
});
check('without a date (an older server) it still says "the last plan"; and with no earlier plan the old sentence is unchanged', () => {
  assert.ok(render(rr.rows, rr.reteach, true, {}).includes('सुझाव पिछली योजना'));
  assert.ok(render(rr.rows, rr.reteach, false, {}).includes('पिछली योजना नहीं मिली'));
});
check('a proposal from an older server, without previous_reteach, shows nothing and does not fail', () => {
  const old = initialRows({ ladder, proposal, selectedId: 'N2.3.2' });
  assert.equal(old.rows.progressor.previousReteach, false);
  assert.ok(!render(old.rows, old.reteach).includes('previous-reteach'));
});

console.log('the drawer (found on the click-through: the panel was at the top of the page and the button scrolled up to it, so the place in the skill list was lost)');
check('closed: one line with each group\'s skill and a way to open it; the panel is not shown', () => {
  const h = ReactDOMServer.renderToStaticMarkup(React.createElement(Drawer, { open: false, onToggle() {}, summary: 'शु N2.3.1 · प्र N2.3.2 · द N3.3.1' }, React.createElement('i', { id: 'inside' })));
  assert.ok(h.includes('समूहों के कौशल: शु N2.3.1 · प्र N2.3.2 · द N3.3.1') && h.includes('देखें/बदलें') && h.includes('aria-expanded="false"'));
  assert.ok(!h.includes('group-skills-drawer-body') && !h.includes('id="inside"'));
});
check('open: the panel sits inside a drawer that scrolls inside itself (it never pushes the page), with a button that says how to go back to the skill list', () => {
  const h = ReactDOMServer.renderToStaticMarkup(React.createElement(Drawer, { open: true, onToggle() {}, summary: 'x' }, React.createElement('i', { id: 'inside' })));
  assert.ok(h.includes('data-testid="group-skills-drawer-body"') && h.includes('id="inside"') && h.includes('aria-expanded="true"'));
  assert.ok(h.includes('overflow-y:auto') && h.includes('max-height:min(55vh, 440px)') && h.includes('कौशल सूची पर लौटें'));
});
check('while a plan is being generated the drawer\'s button is disabled', () => {
  assert.ok(/disabled=""/.test(ReactDOMServer.renderToStaticMarkup(React.createElement(Drawer, { open: false, onToggle() {}, summary: 'x', disabled: true }))));
});
check('what the panel is doing for the chosen skill: nothing chosen, loading (rows not there yet), ready, or failed', () => {
  assert.equal(panelStatus({ selectedId: null, rows: null, failed: false }), 'none');
  assert.equal(panelStatus({ selectedId: 'N2.3.2', rows: null, failed: false }), 'loading');
  assert.equal(panelStatus({ selectedId: 'N2.3.2', rows: { beginner: {} }, failed: false }), 'ready');
  assert.equal(panelStatus({ selectedId: 'N2.3.2', rows: null, failed: true }), 'failed');
});

console.log('the re-teach box is the decision, and the skill follows it (asked on the click-through: why is it different for the Beginners?)');
const adv = { ...ex.rows, beginner: withSkill(ex.rows.beginner, 'N2.3.2') };       // the Beginners advanced to N2.3.2; yesterday N2.3.1
check('ticking puts a Beginner group back on yesterday\'s skill and remembers where it was; unticking puts it back', () => {
  const t = toggleReteach({ label: 'beginner', row: adv.beginner, checked: true, selectedId: 'N2.3.2', ladder });
  assert.deepEqual([t.row.skillId, t.row.beforeReteachId, t.reteach], ['N2.3.1', 'N2.3.2', true]);
  const u = toggleReteach({ label: 'beginner', row: t.row, checked: false, selectedId: 'N2.3.2', ladder });
  assert.deepEqual([u.row.skillId, u.row.beforeReteachId, u.reteach], ['N2.3.2', null, false]);
  assert.equal(u.row.source, 'review');       // back on the Advance suggestion, said to come from the teacher's decision
});
check('the same for the Proficients (Advance had moved them to N3.5.2; yesterday N3.3.1)', () => {
  const row = withSkill(ex.rows.proficient, 'N3.5.2');
  const t = toggleReteach({ label: 'proficient', row, checked: true, selectedId: 'N2.3.2', ladder });
  assert.deepEqual([t.row.skillId, t.reteach], ['N3.3.1', true]);
  assert.equal(toggleReteach({ label: 'proficient', row: t.row, checked: false, selectedId: 'N2.3.2', ladder }).row.skillId, 'N3.5.2');
});
check('a group already on yesterday\'s skill: ticking only switches the re-teach on, unticking leaves the skill where it is (same skill, taught as a normal lesson)', () => {
  const onYesterdays = initialRows({ ladder, proposal: { has_history: true, groups: { ...proposal.groups, proficient: entry('N3.3.1', null, null, 'no_decision', ev(0, 0), null) } }, selectedId: 'N2.3.2' }).rows.proficient;
  assert.equal(onYesterdays.skillId, 'N3.3.1');       // no decision: the derived skill, which IS yesterday's
  const t = toggleReteach({ label: 'proficient', row: onYesterdays, checked: true, selectedId: 'N2.3.2', ladder });
  assert.deepEqual([t.row.skillId, t.reteach, t.row.beforeReteachId], ['N3.3.1', true, undefined]);
  const u = toggleReteach({ label: 'proficient', row: t.row, checked: false, selectedId: 'N2.3.2', ladder });
  assert.deepEqual([u.row.skillId, u.reteach], ['N3.3.1', false]);
});
check('picking a skill in the list yourself while ticked forgets the remembered skill (and ends the re-teach, as before)', () => {
  const t = toggleReteach({ label: 'beginner', row: adv.beginner, checked: true, selectedId: 'N2.3.2', ladder });
  assert.equal(withSkill(t.row, 'N1.3.1').beforeReteachId, null);
});
check('not possible: going back would put the Beginners AHEAD of the day\'s skill (N0.1.1 day, yesterday N2.3.1), or there is no yesterday', () => {
  assert.equal(toggleReteach({ label: 'beginner', row: u0row(), checked: true, selectedId: 'N0.1.1', ladder: day0 }), null);
  assert.equal(toggleReteach({ label: 'beginner', row: { ...adv.beginner, previous: null }, checked: true, selectedId: 'N2.3.2', ladder }), null);
});
function u0row() { return initialRows({ ladder: day0, proposal: demoProposal, selectedId: 'N0.1.1' }).rows.beginner; }
check('the Progressors: their skill IS the day\'s skill, so ticking works only when that is yesterday\'s already; otherwise it is not done silently (the explicit button changes the day\'s skill)', () => {
  assert.equal(toggleReteach({ label: 'progressor', row: ex.rows.progressor, checked: true, selectedId: 'N2.3.2', ladder }).reteach, true);
  assert.equal(toggleReteach({ label: 'progressor', row: ex.rows.progressor, checked: true, selectedId: 'N2.3.3', ladder }), null);
});
check('after choosing "re-teach N2.3.1" for the Beginners, the list shows it, a caption says what it means, the summary says so, and Generate sends the re-teach and no group skill (N2.3.1 is what the plan derives)', () => {
  const t = chooseOption({ label: 'beginner', row: adv.beginner, value: 'reteach:N2.3.1', selectedId: 'N2.3.2', ladder });
  const rows = { ...adv, beginner: t.row }; const re = { ...ex.reteach, beginner: t.reteach };
  const h = render(rows, re);
  assert.match(selectOf(h, 'beginner'), /<option value="reteach:N2\.3\.1" selected="">/);
  assert.ok(h.includes('data-testid="reteach-on-beginner"') && h.includes('मुख्य ब्लॉक कल की गलतियों को दोबारा समझाएगा'));
  assert.deepEqual(summarize(rows, re).map((x) => [x.skillId, x.reteach]), [['N2.3.1', true], ['N2.3.2', true], ['N3.5.2', false]]);
  assert.deepEqual(buildGenerateOptions({ rows, reteach: re, groups, ready: true }), { groupSkills: { proficient: 'N3.5.2' }, reteachGroups: ['beginner', 'progressor'] });
});
check('when going back is NOT possible the box is disabled with ONE plain sentence (the redundant first sentence is gone) and no button', () => {
  const hu2 = render(u0row() && initialRows({ ladder: day0, proposal: demoProposal, selectedId: 'N0.1.1' }).rows, { beginner: false, progressor: false, proficient: false }, true, { selectedId: 'N0.1.1', ladder: day0 });
  assert.ok(hu2.includes('कल का कौशल (N2.3.1) आज के कौशल से आगे है, इसलिए इस समूह के लिए आज दोहराना संभव नहीं'));
  assert.ok(!hu2.includes('कल वाले कौशल N2.3.1 पर होना चाहिए') && !hu2.includes('go-back-reteach-beginner'));
});

console.log('one dropdown holds both decisions (asked on the click-through: if yesterday decided, why a box AND a list?)');
check('the re-teach entry exists only where it can be chosen: not for the Progressors, not without a yesterday, not when it would put the group on the wrong side of the day\'s skill', () => {
  assert.deepEqual(reteachChoice({ label: 'beginner', row: adv.beginner, ladder }), { value: 'reteach:N2.3.1', id: 'N2.3.1' });
  assert.equal(reteachChoice({ label: 'progressor', row: ex.rows.progressor, ladder }), null);
  assert.equal(reteachChoice({ label: 'beginner', row: { ...adv.beginner, previous: null }, ladder }), null);
  assert.equal(reteachChoice({ label: 'beginner', row: initialRows({ ladder: day0, proposal: demoProposal, selectedId: 'N0.1.1' }).rows.beginner, ladder: day0 }), null);
});
check('what the list shows: the re-teach entry when the group re-teaches yesterday\'s skill, otherwise the skill', () => {
  const back = chooseOption({ label: 'beginner', row: adv.beginner, value: 'reteach:N2.3.1', selectedId: 'N2.3.2', ladder });
  assert.equal(selectValue({ label: 'beginner', row: back.row, reteachOn: back.reteach }), 'reteach:N2.3.1');
  assert.equal(selectValue({ label: 'beginner', row: adv.beginner, reteachOn: false }), 'N2.3.2');
  assert.equal(selectValue({ label: 'progressor', row: ex.rows.progressor, reteachOn: true }), 'N2.3.2');       // the Progressors never use the list for it
});
check('choosing: the re-teach entry = yesterday\'s skill + re-teach; ANY plain skill, even yesterday\'s, is a NORMAL lesson; another skill after a re-teach ends it', () => {
  const back = chooseOption({ label: 'beginner', row: adv.beginner, value: 'reteach:N2.3.1', selectedId: 'N2.3.2', ladder });
  assert.deepEqual([back.row.skillId, back.reteach], ['N2.3.1', true]);
  const normal = chooseOption({ label: 'beginner', row: back.row, value: 'N2.3.1', selectedId: 'N2.3.2', ladder });
  assert.deepEqual([normal.row.skillId, normal.reteach], ['N2.3.1', false]);
  const other = chooseOption({ label: 'beginner', row: back.row, value: 'N1.3.1', selectedId: 'N2.3.2', ladder });
  assert.deepEqual([other.row.skillId, other.reteach, other.row.source], ['N1.3.1', false, 'teacher']);
  assert.equal(chooseOption({ label: 'beginner', row: initialRows({ ladder: day0, proposal: demoProposal, selectedId: 'N0.1.1' }).rows.beginner, value: 'reteach:N2.3.1', selectedId: 'N0.1.1', ladder: day0 }), null);
});
check('a Beginner group whose decision was RE-TEACH opens on the re-teach entry (and the summary says so); the Proficients likewise', () => {
  const rp = initialRows({ ladder, proposal: { has_history: true, groups: { ...proposal.groups, beginner: entry('N2.3.1', 'reteach', 'N2.3.1', 'reteach', ev(4, 3), 'reteach'), proficient: entry('N3.3.1', 'not_sure', 'N3.3.1', 'not_sure', ev(0, 0), null) } }, selectedId: 'N2.3.2' });
  const h = render(rp.rows, rp.reteach);
  assert.match(selectOf(h, 'beginner'), /<option value="reteach:N2\.3\.1" selected="">/);
  assert.match(selectOf(h, 'proficient'), /<option value="reteach:N3\.3\.1" selected="">/);
  assert.equal(rp.rows.beginner.initialReteach, true);
});

console.log('yesterday\'s skill as a plain entry: not a choice (asked on the click-through: is "the same lesson again" ever needed if re-teach is offered?)');
check('a group that MOVED ON does not get yesterday\'s skill as a plain entry; it stays in the other groups of the list untouched', () => {
  const g = visibleChoices({ label: 'beginner', ladder, row: adv.beginner, selectedId: 'N2.3.2', reteachOn: false });
  const ids = g.flatMap((x) => x.ids);
  assert.ok(!ids.includes('N2.3.1') && ids.includes('N2.3.2'), ids);
  assert.ok(g.every((x) => x.ids.length > 0));
});
const sameSkill = (() => {                                       // the Proficients are on yesterday's N3.3.1 again, with no decision and no evidence: the app's default is a normal lesson
  const lad = { ...ladder, proficient: sk('N3.3.1') };
  const r = initialRows({ ladder: lad, proposal: { has_history: true, groups: { ...proposal.groups, proficient: entry('N3.3.1', null, null, 'no_decision', ev(0, 0), null) } }, selectedId: 'N2.3.2' });
  return { lad, r };
})();
check('a group that is on yesterday\'s skill by DEFAULT (no decision, no evidence) still shows it as a plain entry, labelled a normal lesson, because it is the current choice; the re-teach entry is offered beside it', () => {
  const h = render(sameSkill.r.rows, sameSkill.r.reteach, true, { ladder: sameSkill.lad });
  const sel = selectOf(h, 'proficient');
  assert.equal(sameSkill.r.reteach.proficient, false);
  assert.ok(/<option value="N3\.3\.1" selected="">N3\.3\.1 · [^<]* — नया पाठ \(दोहराव नहीं\)<\/option>/.test(sel), sel.slice(0, 600));
  assert.ok(sel.includes('value="reteach:N3.3.1"'));
});
check('once that group re-teaches, the plain entry is gone (it is no longer the current choice) and the re-teach entry is selected; the suggestion button restores the default', () => {
  const t = chooseOption({ label: 'proficient', row: sameSkill.r.rows.proficient, value: 'reteach:N3.3.1', selectedId: 'N2.3.2', ladder: sameSkill.lad });
  const h = render({ ...sameSkill.r.rows, proficient: t.row }, { ...sameSkill.r.reteach, proficient: t.reteach }, true, { ladder: sameSkill.lad });
  const sel = selectOf(h, 'proficient');
  assert.ok(!/<option value="N3\.3\.1"/.test(sel) && /<option value="reteach:N3\.3\.1" selected="">/.test(sel));
  assert.equal(t.row.initialReteach, false);
});
check('where a re-teach is NOT offered nothing is hidden (the Beginners on a Balvatika skill: yesterday\'s skill is not in their list at all)', () => {
  const dayRows = initialRows({ ladder: day0, proposal: demoProposal, selectedId: 'N0.1.1' }).rows;
  assert.deepEqual(visibleChoices({ label: 'beginner', ladder: day0, row: dayRows.beginner, selectedId: 'N0.1.1', reteachOn: false }), skillChoices({ label: 'beginner', ladder: day0, row: dayRows.beginner, selectedId: 'N0.1.1' }));
});

fs.rmSync(out, { recursive: true, force: true });
console.log(`\nOK: ${n} checks. Each group's skill is proposed from the review decisions, the teacher can change it, and only real differences are sent.`);
