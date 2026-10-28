// Settings of this device that change how a plan is made or shown (the language setting is in language.js).
// Kept in localStorage: they survive a reload, a sign-out and offline use, and are never sent to the server as a preference.

// How long the teacher has today, from the Plan screen's time picker. The last choice is preselected next time; 90 on first use.
// It goes to the server only with each plan request (session_minutes), where it is the plan's teaching time.
export const SESSION_MINUTES = [45, 60, 90];
export const DEFAULT_SESSION_MINUTES = 90;
const SESSION_KEY = 'session_minutes';

export const getSessionMinutes = () => {
  try {
    const n = Number(localStorage.getItem(SESSION_KEY));
    return SESSION_MINUTES.includes(n) ? n : DEFAULT_SESSION_MINUTES;       // nothing stored, or a value this app no longer offers: the default
  } catch { return DEFAULT_SESSION_MINUTES; }
};

export const setSessionMinutes = (n) => {
  if (!SESSION_MINUTES.includes(n)) return;
  try { localStorage.setItem(SESSION_KEY, String(n)); } catch { /* private mode: applies until reload */ }
};

// "छोटी स्क्रीन" (Shorter screen), on the Profile screen: the plan screen folds each teach block's one-line script under "आज की गतिविधि" and the anchor card to its
// title row. The block's title, its re-teach note and its signal panel never fold. Off by default. Stored as 'true' / 'false' under "familiar_mode" (the internal name).
const FAMILIAR_KEY = 'familiar_mode';

export const getFamiliarMode = () => {
  try { return localStorage.getItem(FAMILIAR_KEY) === 'true'; } catch { return false; }
};

export const setFamiliarMode = (on) => {
  try { localStorage.setItem(FAMILIAR_KEY, on ? 'true' : 'false'); } catch { /* private mode: applies until reload */ }
};
