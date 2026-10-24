// What the lesson screen's header says about the groups: which skill each group is on, and which group is re-teaching. PURE functions (no React, no network).

export const GROUP_ORDER = ['beginner', 'progressor', 'proficient'];
export const GROUP_SHORT = { beginner: 'शु', progressor: 'प्र', proficient: 'द' };
export const GROUP_HI = { beginner: 'शुरुआती', progressor: 'प्रगतिशील', proficient: 'दक्ष' };
export const GROUP_EMOJI = { beginner: '🟠', progressor: '🟡', proficient: '🟢' };

/**
 * The groups that are re-teaching in this plan: a teach block marked `reteach` (the re-teach as the group's main block), or, in plans made the old way,
 * the separate re-teach block (type 'reteach') that names its group.
 */
export function reteachGroupsOf(blocks) {
  const out = new Set();
  (blocks || []).forEach((b) => {
    if (b && b.teach_group && ((b.type === 'teach' && b.reteach) || b.type === 'reteach')) out.add(b.teach_group);
  });
  return out;
}

/**
 * The lines for the top right of the lesson screen.
 *  differ: the groups are on DIFFERENT skills (then each group's skill is listed; if they are all on the same skill the day's one skill is enough)
 *  lines: [{ label, short, emoji, skillId, name_hi, reteach }] in the order Beginner, Progressor, Proficient
 *  reteachLabels: the groups that re-teach (listed even when everyone is on the same skill)
 */
export function groupSkillLines({ groups, blocks, selectedId }) {
  const re = reteachGroupsOf(blocks);
  const byLabel = {};
  (groups || []).forEach((g) => { byLabel[g.label] = g; });
  const lines = GROUP_ORDER.filter((l) => byLabel[l]).map((l) => ({
    label: l, short: GROUP_SHORT[l], emoji: GROUP_EMOJI[l],
    skillId: byLabel[l].target_competency_id || (l === 'progressor' ? selectedId : null),
    name_hi: byLabel[l].target_competency_name_hi || '', reteach: re.has(l),
  }));
  const ids = new Set(lines.map((x) => x.skillId).filter(Boolean));
  return { differ: ids.size > 1, lines, reteachLabels: GROUP_ORDER.filter((l) => re.has(l)) };
}
