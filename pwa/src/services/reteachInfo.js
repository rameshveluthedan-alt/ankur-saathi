// What the lesson screen says about a re-teach block (the re-teach as a group's MAIN block): its title, the pace, the children and the mistakes. PURE functions (no React, no network).

// The pace the teachers called realistic (Vaishnavi, 23 Oct): 2 + 6 + 7 + 4 + 8 = 27 minutes.
export const PACE = [
  { key: 'recall', hi: 'कल की बात', en: 'Recall', min: 2 },
  { key: 'i_do', hi: 'मैं करूँगा', en: 'I Do', min: 6 },
  { key: 'we_do', hi: 'हम करेंगे', en: 'We Do', min: 7 },
  { key: 'show_me', hi: 'जाँच', en: 'Show-me', min: 4 },
  { key: 'you_do', hi: 'तुम करोगे', en: 'You Do', min: 8 },
];
const BASE_TOTAL = PACE.reduce((a, p) => a + p.min, 0);

/**
 * The pace scaled to this block's length, in whole minutes that add up to exactly the block's duration (largest remainder), each part at least 1.
 * Returns null when there is no usable duration (under 10 minutes the parts would be too small to mean anything).
 */
export function pacePlan(duration) {
  const d = Math.round(Number(duration));
  if (!Number.isFinite(d) || d < 10) return null;
  const raw = PACE.map((p) => (p.min * d) / BASE_TOTAL);
  const mins = raw.map((r) => Math.max(1, Math.floor(r)));
  let left = d - mins.reduce((a, b) => a + b, 0);
  const order = raw.map((r, i) => [r - Math.floor(r), i]).sort((a, b) => b[0] - a[0]).map((x) => x[1]);
  for (let k = 0; left > 0; k = (k + 1) % order.length) { mins[order[k]] += 1; left -= 1; }
  for (let k = order.length - 1; left < 0; k = (k - 1 + order.length) % order.length) { if (mins[order[k]] > 1) { mins[order[k]] -= 1; left += 1; } }
  return { total: d, scaled: d !== BASE_TOTAL, parts: PACE.map((p, i) => ({ ...p, min: mins[i] })) };
}

/** Is this a re-teach block of the new kind (a teach block marked by the plan)? The old separate block (type 'reteach') has its own display. */
export const isReteachMain = (block) => !!(block && block.type === 'teach' && block.reteach === true);

/** The title of a re-teach block, in the style of the other blocks' titles: its Hindi and its English (the screen shows the English as a translation the "Hindi only" setting hides). */
export function reteachTitleParts(block, labels) {
  const l = (labels && labels[block.teach_group]) || {};
  return { hi: `🔄 पुनः शिक्षण: ${l.hi || block.teach_group} पढ़ाएँ`, en: `Re-teach ${l.en || ''}`.trim() };
}

/** The same title as one line of text. */
export function reteachTitle(block, labels) {
  const t = reteachTitleParts(block, labels);
  return `${t.hi} (${t.en})`;
}

/** What to show: the children (roll numbers: the teacher's own screen), the mistakes with how many children made each, and the pace. */
export function reteachSummary(block) {
  if (!isReteachMain(block)) return { isReteach: false, rolls: [], mistakes: [], pace: null };
  return {
    isReteach: true,
    rolls: Array.isArray(block.affected_rolls) ? block.affected_rolls : [],
    mistakes: Array.isArray(block.reteach_mistakes) ? block.reteach_mistakes : [],
    pace: pacePlan(block.duration_minutes),
  };
}
