// "Hindi only": a setting of this device (the Profile screen). It hides the English translations (every .en span) and nothing else:
// skill ids, roll numbers and English-only text stay. Kept in localStorage, so it survives a reload, a sign-out and offline use.
const KEY = 'ankur_hindi_only';

export const getHindiOnly = () => {
  try { return localStorage.getItem(KEY) === '1'; } catch { return false; }
};

export const applyLanguage = (on = getHindiOnly()) => {
  if (typeof document !== 'undefined') document.body.classList.toggle('hide-en', !!on);
};

export const setHindiOnly = (on) => {
  try { if (on) localStorage.setItem(KEY, '1'); else localStorage.removeItem(KEY); } catch { /* private mode: applies until reload */ }
  applyLanguage(on);
};
