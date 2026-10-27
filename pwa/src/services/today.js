// "Today" as the teacher's phone sees it: the LOCAL date, as YYYY-MM-DD.
// Not new Date().toISOString(): that is the UTC date, which in India is still YESTERDAY until 05:30 in the morning,
// so a plan made or a review saved before then went to the wrong day. Every screen that sends a date uses this.
export function localToday(now = new Date()) {
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}
