// A short message on the screen instead of a pop-up (alert) that blocks the whole page.
// notify(text, 'success' | 'error' | 'info'): components/Notices.jsx shows it. A success goes away by itself; an error stays until it is tapped away.
const listeners = new Set();
let nextId = 1;

export function notify(text, kind = 'info') {
  const n = { id: nextId++, text: String(text ?? ''), kind };
  listeners.forEach((fn) => fn(n));
  return n.id;
}

export const onNotify = (fn) => { listeners.add(fn); return () => listeners.delete(fn); };

export const SUCCESS_MS = 5000;
