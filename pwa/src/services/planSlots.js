// The lesson's session slots, for the tabs on "आज की योजना" (one tab per slot instead of one long timeline: the hackathon evaluators' suggestion, 12 Nov).
// PURE (no React), so the rule is tested on its own (tests/plan_slots.test.mjs).
//
// A slot is one MAIN block (the anchor, a group's teaching, a re-teach) with the short blocks that follow it (setup, transition) attached as `after`:
// they are the move to the next slot, read at the end of this one. Short blocks before the first main block go to the first slot.
// With an anchor activity in the plan but no anchor block in the schedule, an anchor slot is put first, so the activity always has its tab.
const MAIN = new Set(['anchor', 'teach', 'reteach']);

export function planSlots(blocks, { hasAnchor = false } = {}) {
  const slots = [];
  const before = [];
  (Array.isArray(blocks) ? blocks : []).forEach((block, index) => {
    if (block && MAIN.has(block.type)) slots.push({ key: `${block.type}-${index}`, kind: block.type, block, index, after: [] });
    else if (slots.length) slots[slots.length - 1].after.push(block);
    else before.push(block);
  });
  if (hasAnchor && !slots.some((s) => s.kind === 'anchor')) slots.unshift({ key: 'anchor', kind: 'anchor', block: { type: 'anchor', duration_minutes: 10, time_start: '0:00' }, index: -1, after: [] });
  if (before.length && slots.length) slots[0].after.unshift(...before);
  return slots.map((s) => ({ ...s, group: s.kind === 'anchor' ? null : s.block.teach_group || null, reteach: s.kind === 'reteach' || !!s.block.reteach,
    minutes: Number(s.block.duration_minutes) || 0, start: s.block.time_start || null }));
}

// The session as one strip of coloured parts, each part as long as its time: every block, the short ones grey
export function stripParts(blocks) {
  const list = (Array.isArray(blocks) ? blocks : []).filter((b) => b && Number(b.duration_minutes) > 0);
  const total = list.reduce((t, b) => t + Number(b.duration_minutes), 0);
  return list.map((b) => ({ type: b.type, group: b.teach_group || null, reteach: b.type === 'reteach' || !!b.reteach, share: total ? Number(b.duration_minutes) / total : 0 }));
}
