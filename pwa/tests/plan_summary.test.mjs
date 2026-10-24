// The top right of the lesson screen: which skill each group is on (when they differ), and which group is re-teaching. No browser and no server.
//
//     cd pwa
//     node tests/plan_summary.test.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';
import React from 'react';
import ReactDOMServer from 'react-dom/server';

const here = path.dirname(fileURLToPath(import.meta.url));
const src = path.join(here, '..', 'src');
const out = path.join(here, `.tmp-summary-${process.pid}`);
process.on('exit', () => fs.rmSync(out, { recursive: true, force: true }));      // the temporary build folder is always removed, even if a check fails
await build({
  entryPoints: { logic: path.join(src, 'services/planSummary.js'), view: path.join(src, 'components/PlanGroupSkills.jsx') },
  bundle: true, format: 'esm', platform: 'node', outdir: out, outExtension: { '.js': '.mjs' }, loader: { '.js': 'jsx', '.jsx': 'jsx' }, external: ['react', 'react-dom'], logLevel: 'error',
});
const { groupSkillLines, reteachGroupsOf } = await import(pathToFileURL(path.join(out, 'logic.mjs')).href);
const { default: View } = await import(pathToFileURL(path.join(out, 'view.mjs')).href);

let n = 0;
const check = (label, fn) => { fn(); n += 1; console.log(`  OK  ${label}`); };
const grp = (label, id, name = `नाम ${id}`, count = 3) => ({ label, count, target_competency_id: id, target_competency_name_hi: name });
const differing = [grp('beginner', 'N2.3.1'), grp('progressor', 'N2.3.2'), grp('proficient', 'N3.3.1')];
const same = [grp('beginner', 'N2.3.2'), grp('progressor', 'N2.3.2'), grp('proficient', 'N2.3.2')];
const teach = (g, extra = {}) => ({ type: 'teach', teach_group: g, ...extra });
const render = (groups, blocks) => ReactDOMServer.renderToStaticMarkup(React.createElement(View, { planDate: '2026-10-23', selectedId: 'N2.3.2', groups, blocks }));

console.log('which groups re-teach');
check('a teach block marked as a re-teach (the re-teach as the group\'s main block) names its group', () => {
  assert.deepEqual([...reteachGroupsOf([teach('beginner'), teach('progressor', { reteach: true }), teach('proficient')])], ['progressor']);
});
check('a plan made the old way has a separate re-teach block that names its group, and that counts too', () => {
  assert.deepEqual([...reteachGroupsOf([{ type: 'reteach', teach_group: 'beginner' }, teach('progressor')])], ['beginner']);
});
check('nothing marks a group when: reteach is false, the block names no group, or the flag is on a block that is not a teach block', () => {
  assert.equal(reteachGroupsOf([teach('beginner', { reteach: false }), { type: 'reteach', teach_group: null }, { type: 'anchor', teach_group: 'proficient', reteach: true }]).size, 0);
  assert.equal(reteachGroupsOf(undefined).size, 0);
});

console.log('the lines');
check('different skills: one line per group, always in the order Beginner, Progressor, Proficient, with the skill id and its Hindi name', () => {
  const s = groupSkillLines({ groups: [differing[2], differing[0], differing[1]], blocks: [], selectedId: 'N2.3.2' });
  assert.equal(s.differ, true);
  assert.deepEqual(s.lines.map((l) => [l.label, l.skillId]), [['beginner', 'N2.3.1'], ['progressor', 'N2.3.2'], ['proficient', 'N3.3.1']]);
  assert.equal(s.lines[0].name_hi, 'नाम N2.3.1');
});
check('all groups on the same skill: not "different"', () => { assert.equal(groupSkillLines({ groups: same, blocks: [], selectedId: 'N2.3.2' }).differ, false); });
check('no groups at all: nothing different, no lines', () => {
  const s = groupSkillLines({ groups: [], blocks: [], selectedId: 'N2.3.2' });
  assert.deepEqual([s.differ, s.lines.length], [false, 0]);
});

console.log('what the top right shows');
const h1 = render(differing, [teach('beginner'), teach('progressor'), teach('proficient')]);
check('different skills, no re-teach: the date, and a line per group with its skill (the single "· N2.3.2" after the date is gone)', () => {
  assert.ok(h1.includes('2026-10-23') && h1.includes('data-testid="plan-skill-beginner"') && h1.includes('N2.3.1') && h1.includes('N3.3.1'));
  assert.ok(!h1.includes('2026-10-23</div>') || !h1.includes('· N2.3.2'));
  assert.ok(!h1.includes('पुनः शिक्षण'));
});
check('the group\'s skill name is in the line\'s tooltip', () => { assert.ok(h1.includes('title="नाम N2.3.1"')); });
const h2 = render(differing, [teach('beginner'), teach('progressor', { reteach: true }), teach('proficient')]);
check('the Progressors re-teach: "🔄 पुनः शिक्षण Re-teach" is on the Progressors\' line, and only there', () => {
  assert.ok(h2.includes('data-testid="plan-reteach-progressor"') && h2.includes('🔄 पुनः शिक्षण') && h2.includes('Re-teach'));
  assert.ok(!h2.includes('plan-reteach-beginner') && !h2.includes('plan-reteach-proficient'));
  const progLine = h2.split('data-testid="plan-skill-progressor"')[1].split('data-testid="plan-skill-proficient"')[0];
  assert.ok(progLine.includes('N2.3.2') && progLine.includes('पुनः शिक्षण'));
});
const h3 = render(differing, [{ type: 'reteach', teach_group: 'beginner' }, teach('beginner'), teach('progressor'), teach('proficient')]);
check('a plan made the old way (a separate re-teach block) shows the same tag on that group', () => { assert.ok(h3.includes('data-testid="plan-reteach-beginner"') && !h3.includes('plan-reteach-progressor')); });
const h4 = render(same, [teach('beginner'), teach('progressor'), teach('proficient')]);
check('everyone on the same skill and no re-teach: just the date and the one skill, as before', () => {
  assert.ok(h4.includes('2026-10-23') && h4.includes('· N2.3.2') && !h4.includes('plan-skill-') && !h4.includes('plan-reteach'));
});
const h5 = render(same, [teach('beginner'), teach('progressor', { reteach: true }), teach('proficient', { reteach: true })]);
check('everyone on the same skill but two groups re-teach: the one skill, and the re-teach is still named, with the groups', () => {
  assert.ok(h5.includes('· N2.3.2') && h5.includes('data-testid="plan-reteach-all"') && h5.includes('प्रगतिशील, दक्ष') && h5.includes('Re-teach'));
});
check('no group information (an old stored plan): the date and the one skill, and no error', () => {
  const h6 = render(undefined, undefined);
  assert.ok(h6.includes('2026-10-23') && h6.includes('· N2.3.2'));
});

fs.rmSync(out, { recursive: true, force: true });
console.log(`\nOK: ${n} checks. The top right shows each group's skill when they differ, and a Re-teach tag against the group that re-teaches.`);
