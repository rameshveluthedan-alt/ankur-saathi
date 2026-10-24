// The problems a teacher copies to the board: problems 1..required_count of the group's WORKSHEET, read from the plan itself, so the lesson and the sheet cannot disagree.
// (The model refers to worksheet problems only BY NUMBER: the system may replace a problem's numbers after the model writes, so the plan text cannot list them.)
// Numeracy only: a literacy sheet holds passages and questions, not sums to copy. Returns { items: ['36 + 27', ...], required } or null (then nothing is shown).
const MAX_LEN = 26;       // a sum is short; a word problem is not, and is left to the sheet

export function boardProblems(plan, group, domain) {
  if (domain !== 'numeracy' || !plan || !group) return null;
  const sheet = plan.worksheets && plan.worksheets[group];
  const all = sheet && Array.isArray(sheet.problems) ? sheet.problems : [];
  if (all.length === 0) return null;
  const required = Number.isInteger(sheet.required_count) && sheet.required_count > 0 ? Math.min(sheet.required_count, all.length) : all.length;
  const items = all.slice(0, required).map((p) => String((p && p.problem_hi) || '').replace(/\s*=\s*(_+|\?)?\s*$/, '').trim());
  if (items.length < 2 || items.some((t) => !t || t.length > MAX_LEN || !/\d/.test(t))) return null;
  return { items, required: items.length };
}
