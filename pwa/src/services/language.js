// "Hindi only": a setting of this device (the Profile screen). It hides the English translations (every .en span) and nothing else:
// skill ids, roll numbers and English-only text stay. Kept in localStorage, so it survives a reload, a sign-out and offline use.
const KEY = 'ankur_hindi_only';

export const getHindiOnly = () => {
  try { return localStorage.getItem(KEY) === '1'; } catch { return false; }
};

export const applyLanguage = (on = getHindiOnly()) => {
  if (typeof document !== 'undefined') document.body.classList.toggle('hide-en', !!on);
};

// For text that cannot carry a .en span (a pop-up, a confirm box, a message kept as a string): "हिंदी (English)", or only the Hindi when the setting is on.
export const bi = (hi, en) => (getHindiOnly() || !en ? hi : `${hi} (${en})`);

export const setHindiOnly = (on) => {
  try { if (on) localStorage.setItem(KEY, '1'); else localStorage.removeItem(KEY); } catch { /* private mode: applies until reload */ }
  applyLanguage(on);
};
