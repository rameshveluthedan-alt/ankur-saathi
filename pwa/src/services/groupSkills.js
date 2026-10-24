// Each group's skill for the day, and the choice to re-teach. PURE functions (no React, no network), so the rules can be tested on their own.
//
// A group moves on its own path (Teaching at the Right Level): the Beginners and the Proficients can be set to a skill of their own, and a group can re-teach yesterday's skill while the others move on.
// What the screen starts with comes from the teacher's decisions at the last review (Advance / Re-teach / Not sure). The teacher can change anything: the final decision is theirs.

export const GROUPS = ['beginner', 'progressor', 'proficient'];

const GRADE_RANK = { balvatika: 0, grade_1: 1, grade_2: 2, grade_3: 3 };

/**
 * The Beginners are never AHEAD of the day's skill and the Proficients never BEHIND it, in grade (the server refuses it too).
 * Found on the click-through: with N0.1.1 (Balvatika sorting) chosen for the day, the Beginners were given N2.3.2 because yesterday's review had said Advance.
 * By GRADE, not sort_order: sort_order is only a skill's place inside its strand. The same grade, or a grade that is not known, fits.
 */
export function fitsDay(label, skillGrade, dayGrade) {
  const a = GRADE_RANK[skillGrade];
  const b = GRADE_RANK[dayGrade];
  if (a === undefined || b === undefined) return true;
  if (label === 'beginner') return a <= b;
  if (label === 'proficient') return a >= b;
  return true;
}

// The same words the Review screen uses for the three decisions
export const DECISION_LABELS = {
  advance: { hi: '▲ आगे बढ़ें', en: 'Advance' },
  reteach: { hi: '🔄 दोहराएँ', en: 'Re-teach' },
  not_sure: { hi: '❓ पक्का नहीं', en: 'Not sure' },
};

// A group that is not sure, or that was to re-teach, STAYS on its skill: re-teaching means the same skill as yesterday.
const STAYS = ['reteach', 'not_sure'];
// ...and so does a group for which no decision was recorded but the evidence recommends a re-teach (at least a third of those assessed made a mistake: the server works that out).

/**
 * The rows the panel starts with.
 *  ladder:   {beginner, progressor, proficient} the skills the plan derives for the selected skill (GET /plan/ladder/{id})
 *  proposal: the answer of GET /plan/proposal (or null when it could not be fetched)
 *  selectedId: the skill the teacher chose: the Progressors' skill
 * Returns { rows, reteach }. A row: { skillId, source ('selected' | 'review' | 'recommendation' | 'derived' | 'teacher'), initialId, initialSource, derivedId, previous, decision, reason, evidence, recommendation, conflict }.
 */
export function initialRows({ ladder, proposal, selectedId }) {
  const dayGrade = ladder && ladder.progressor ? ladder.progressor.grade_level : null;
  const rows = {};
  const reteach = {};
  for (const label of GROUPS) {
    const prop = proposal && proposal.has_history ? (proposal.groups || {})[label] || null : null;
    const previous = prop ? prop.previous_target : null;
    const decision = prop ? prop.previous_decision : null;
    const reason = prop ? prop.reason : null;
    const derivedId = label === 'progressor' ? selectedId : (ladder && ladder[label] ? ladder[label].id : selectedId);
    let skillId = derivedId;
    let source = label === 'progressor' ? 'selected' : 'derived';
    let ignored = null;
    if (label !== 'progressor' && prop && prop.proposed) {
      if (fitsDay(label, prop.proposed.grade_level, dayGrade)) {
        skillId = prop.proposed.id;
        source = reason === 'recommended' ? 'recommendation' : 'review';
      } else {
        ignored = prop.proposed;       // the suggestion is about a skill that does not fit TODAY's (the day's skill is not the one yesterday's decision was about): the group follows the day's skill, and the screen says so
      }
    }
    rows[label] = {
      skillId, source, initialId: skillId, initialSource: source, derivedId, previous, decision, reason, ignored, previousReteach: !!(prop && prop.previous_reteach),
      evidence: prop ? prop.evidence || null : null, recommendation: prop ? prop.recommendation || null : null, conflict: !!(prop && prop.conflict),
    };
    reteach[label] = !!(previous && skillId === previous.id && (STAYS.includes(decision) || reason === 'recommended'));
    rows[label].initialReteach = reteach[label];
  }
  return { rows, reteach };
}

/** Does this group stay on the skill it was taught yesterday? (A re-teach only makes sense then.) */
export function staysOnYesterdaysSkill(row) {
  return !!(row && row.previous && row.skillId === row.previous.id);
}

/** The teacher picked a skill for a group: the row, with its source updated (the suggestion again counts as the suggestion). */
export function withSkill(row, skillId) {
  return { ...row, skillId, source: skillId === row.initialId ? row.initialSource : 'teacher', beforeReteachId: null };
}

/**
 * What to send with the plan request.
 *  ready: the panel was shown. If it could not be (the proposal or the ladder failed to load) nothing is sent and the plan decides, as before.
 * group_skills carries only the skills that DIFFER from what the plan would derive, so a derived skill stays marked as derived.
 * reteach_groups is always sent when the panel was shown (an empty list means: move on with every group), and never includes a group with no children.
 */
export function buildGenerateOptions({ rows, reteach, groups, ready }) {
  if (!ready || !rows) return {};
  const groupSkills = {};
  for (const label of ['beginner', 'proficient']) {
    const r = rows[label];
    if (r && r.skillId && r.skillId !== r.derivedId) groupSkills[label] = r.skillId;
  }
  const counted = (groups || []).filter((g) => g.count > 0).map((g) => g.label);
  // a re-teach is the SAME skill as yesterday: a group that is not on it is never sent (the panel does not let it be ticked, and the server refuses it too)
  const reteachGroups = GROUPS.filter((l) => reteach && reteach[l] && (counted.length === 0 || counted.includes(l)) && (!rows[l] || !rows[l].previous || staysOnYesterdaysSkill(rows[l])));
  return { groupSkills: Object.keys(groupSkills).length ? groupSkills : undefined, reteachGroups };
}

/** A short line for the bar above the Generate button: [{label, skillId, reteach}] */
export function summarize(rows, reteach) {
  if (!rows) return [];
  return GROUPS.map((label) => ({ label, skillId: rows[label].skillId, reteach: !!(reteach && reteach[label]) }));
}

/**
 * The teacher accepts the app's question "re-teach instead?" for a group. What the screen must do:
 *  { type: 'tick' }                       the Progressors already have yesterday's skill: just tick the box
 *  { type: 'select', skillId }            the Progressors' skill IS the day's skill: choose yesterday's skill (and tick the box once it is chosen)
 *  { type: 'skill', skillId }             the Beginners / Proficients: put the group's skill back to yesterday's, and tick the box
 *  null                                   there is no yesterday to go back to
 */
export function acceptReteach({ label, row, selectedId, ladder }) {
  const prevId = row && row.previous && row.previous.id;
  if (!prevId) return null;
  if (label === 'progressor') return prevId === selectedId ? { type: 'tick' } : { type: 'select', skillId: prevId };
  if (!canReturnToYesterday({ label, row, ladder })) return null;
  return { type: 'skill', skillId: prevId };
}

/**
 * Can this group go back to yesterday's skill today? Not when that would put the Beginners AHEAD of the day's skill, or the Proficients BEHIND it.
 * The Progressors always can: the day's skill itself becomes yesterday's.
 */
export function canReturnToYesterday({ label, row, ladder }) {
  if (!row || !row.previous) return false;
  if (label === 'progressor') return true;
  return fitsDay(label, row.previous.grade_level, ladder && ladder.progressor ? ladder.progressor.grade_level : null);
}

/**
 * The skills the teacher may choose for the Beginners or the Proficients, in groups for the list.
 * The Beginners work on today's skill or a FOUNDATION of it; the Proficients on today's skill or one that BUILDS on it (ladder.options, from the server, nearest first);
 * and a group may always stay where it was yesterday or take the suggestion. Nothing else is offered: a Grade 3 skill for the Beginners, or a Balvatika skill for the Proficients, is not a choice.
 * The skill the group is on now is always in the list.
 */
export function skillChoices({ label, ladder, row, selectedId }) {
  const related = ladder && ladder.options && ladder.options[label] ? ladder.options[label].map((x) => x.id) : [];
  const yesterdayOk = canReturnToYesterday({ label, row, ladder });      // yesterday's skill is only offered where the group may go back to it
  const seen = new Set();
  const take = (ids) => ids.filter((id) => id && !seen.has(id) && seen.add(id));
  const groups = [
    { key: 'today', hi: 'आज का कौशल', en: "Today's skill", ids: take([selectedId]) },
    label === 'beginner'
      ? { key: 'foundation', hi: 'आधार कौशल', en: 'Foundations', ids: take(related) }
      : { key: 'next', hi: 'आगे के कौशल', en: 'What builds on it', ids: take(related) },
    { key: 'kept', hi: 'कल का / सुझाया कौशल', en: "Yesterday's / suggested", ids: take([yesterdayOk && row.previous.id, row && row.initialId, row && row.skillId]) },
  ];
  return groups.filter((g) => g.ids.length);
}

/**
 * What the group panel is doing for the chosen skill: 'none' (no skill chosen), 'loading' (a skill was just chosen and its groups are being fetched:
 * the screen must NOT show or use the PREVIOUS skill's groups meanwhile), 'ready', or 'failed' (the fetch failed: the plan is made without the panel, as before).
 */
export function panelStatus({ selectedId, rows, failed }) {
  if (!selectedId) return 'none';
  if (rows) return 'ready';
  return failed ? 'failed' : 'loading';
}

/**
 * The teacher ticks or unticks the re-teach box of a group. THE BOX IS THE DECISION AND THE SKILL FOLLOWS IT (found on the click-through: for the Beginners, who had moved on,
 * the box was disabled and a separate button did the job, while the other groups just had a box: two ways to make one decision).
 *  - Beginners and Proficients: ticking puts the group back on YESTERDAY'S skill (that is what a re-teach is) and remembers the skill it was on; unticking puts it back on that skill
 *    (or leaves it where it is, when it was already on yesterday's skill). Not possible when going back would put the Beginners ahead of the day's skill or the Proficients behind it.
 *  - Progressors: their skill IS the day's skill chosen in the list, and changing it changes every group's skill; so ticking only works when the day's skill is yesterday's already,
 *    otherwise the day's skill must be changed on purpose (acceptReteach 'select').
 * Returns { row, reteach }, or null when it is not possible.
 */
export function toggleReteach({ label, row, checked, selectedId, ladder }) {
  if (!row || !row.previous) return null;
  if (!checked) {
    if (label !== 'progressor' && row.beforeReteachId && row.beforeReteachId !== row.skillId) return { row: withSkill(row, row.beforeReteachId), reteach: false };
    return { row: { ...row, beforeReteachId: null }, reteach: false };
  }
  if (label === 'progressor') return row.previous.id === selectedId ? { row, reteach: true } : null;
  if (!canReturnToYesterday({ label, row, ladder })) return null;
  if (row.skillId === row.previous.id) return { row, reteach: true };
  return { row: { ...withSkill(row, row.previous.id), beforeReteachId: row.skillId }, reteach: true };
}

// ---- ONE DROPDOWN for the Beginners and the Proficients: it holds BOTH decisions, which skill and whether to RE-TEACH it (asked on the click-through: why a box AND a list?) ----
// The list has an entry "re-teach yesterday's skill" (value 'reteach:N2.3.1') beside the plain skills. The plain entry for yesterday's skill is a NORMAL lesson (for example the second day
// of a skill that takes two days). The state stays as before (rows[label].skillId and reteach[label]): only the way it is chosen changed. The Progressors keep their box: their skill is the day's skill.
export const RETEACH_PREFIX = 'reteach:';

/** The "re-teach yesterday's skill" entry of the list, or null when it cannot be offered (the Progressors, no yesterday, or going back would put the group on the wrong side of the day's skill). */
export function reteachChoice({ label, row, ladder }) {
  if (label === 'progressor' || !row || !row.previous) return null;
  if (!canReturnToYesterday({ label, row, ladder })) return null;
  return { value: RETEACH_PREFIX + row.previous.id, id: row.previous.id };
}

/** What the dropdown shows now: the re-teach entry when the group re-teaches yesterday's skill, otherwise its skill. */
export function selectValue({ label, row, reteachOn }) {
  if (!row) return '';
  if (label !== 'progressor' && reteachOn && row.previous && row.skillId === row.previous.id) return RETEACH_PREFIX + row.skillId;
  return row.skillId;
}

/** The teacher picks an entry of the list. Returns { row, reteach } or null. The re-teach entry puts the group on yesterday's skill and switches the re-teach on; ANY plain skill, yesterday's too, is a normal lesson. */
export function chooseOption({ label, row, value, selectedId, ladder }) {
  if (String(value).startsWith(RETEACH_PREFIX)) return toggleReteach({ label, row, checked: true, selectedId, ladder });
  return { row: withSkill(row, value), reteach: false };
}

/**
 * The plain skills the list shows. Where a re-teach is offered, yesterday's skill as a PLAIN entry would be "the same lesson again", which is a re-teach in all but name, so it is NOT offered as a choice
 * (asked on the click-through). It stays only while it is what the group is on (the default of a group with no decision and no evidence), because the list must be able to show the current choice;
 * the "back to the suggestion" button returns to it. Groups left empty are dropped.
 */
export function visibleChoices({ label, ladder, row, selectedId, reteachOn }) {
  const groups = skillChoices({ label, ladder, row, selectedId });
  if (!reteachChoice({ label, row, ladder })) return groups;
  const current = selectValue({ label, row, reteachOn });
  const yesterday = row.previous.id;
  return groups.map((g) => ({ ...g, ids: g.ids.filter((id) => id !== yesterday || id === current) })).filter((g) => g.ids.length > 0);
}
