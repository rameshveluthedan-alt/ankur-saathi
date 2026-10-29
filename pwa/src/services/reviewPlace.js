// Where the teacher is in today's review (step, the steps already reached, the way of checking, the group, the decisions on screen), so leaving the Review
// (the Progress pointer, a tab) and coming back lands in the same place. Kept for this browser tab only (sessionStorage: it survives a reload, not closing
// the tab), one review at a time, for one teacher, day and subject. No names, no photos: only the place.
const KEY = 'ankur_review_place';

export const placeKey = (teacherId, date, domain) => `${teacherId}|${date}|${domain}`;

export function loadPlace(key) {
  try {
    const p = JSON.parse(sessionStorage.getItem(KEY) || 'null');
    return p && p.key === key ? p : null;          // another teacher, day or subject: start fresh
  } catch { return null; }
}

export function savePlace(key, place) {
  try { sessionStorage.setItem(KEY, JSON.stringify({ ...place, key })); } catch { /* storage unavailable: the Review still works, it just starts at step 1 */ }
}

export function clearPlace() {
  try { sessionStorage.removeItem(KEY); } catch { /* nothing to clear */ }
}
