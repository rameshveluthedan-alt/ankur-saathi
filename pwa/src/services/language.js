// Which language the screens show: a setting of this device, switched from the हिं / EN pill at the top of every screen (components/LangSwitch.jsx)
// or on the Profile screen. Three modes:
//   'hi'   Hindi only (the default): every .en span is hidden.
//   'en'   English only: the Hindi that HAS an English translation (a .hi span, written by components/Bi.jsx) is hidden and the English takes its place
//          at the same size. Text with no translation (the plan's own Hindi content, skill names without English) stays Hindi.
//   'both' Hindi with the English after it (the earlier default).
// Kept in localStorage, so it survives a reload, a sign-out and offline use. The earlier "Hindi only" checkbox (ankur_hindi_only) is read as 'hi'.
export const LANG_KEY = 'ankur_lang';
const OLD_KEY = 'ankur_hindi_only';
export const LANGS = ['hi', 'en', 'both'];
export const DEFAULT_LANG = 'hi';

export const getLang = () => {
  try {
    const v = localStorage.getItem(LANG_KEY);
    if (LANGS.includes(v)) return v;
    if (localStorage.getItem(OLD_KEY) === '1') return 'hi';
  } catch { /* private mode */ }
  return DEFAULT_LANG;
};

let current = null;                 // the mode on screen (also when storage is refused)
const mode = () => current || getLang();

export const applyLanguage = (lang = getLang()) => {
  current = lang;
  if (typeof document !== 'undefined') {
    const cl = document.body.classList;
    cl.toggle('hide-en', lang === 'hi');
    cl.toggle('lang-en', lang === 'en');
    if (document.documentElement) document.documentElement.lang = lang === 'en' ? 'en' : 'hi';
  }
  if (typeof window !== 'undefined' && window.dispatchEvent && typeof CustomEvent !== 'undefined') window.dispatchEvent(new CustomEvent('ankur-lang', { detail: lang }));
};

export const setLang = (lang) => {
  if (!LANGS.includes(lang)) return;
  try { localStorage.setItem(LANG_KEY, lang); localStorage.removeItem(OLD_KEY); } catch { /* private mode: applies until reload */ }
  applyLanguage(lang);
};

// For text that cannot carry a .hi/.en span (a pop-up, a confirm box, a message kept as a string, a placeholder):
// the Hindi, the English, or "हिंदी (English)" in both.
export const bi = (hi, en) => {
  if (!en) return hi;
  const m = mode();
  return m === 'en' ? en : m === 'both' ? `${hi} (${en})` : hi;
};

// kept for the screens and tests written before the three modes
export const getHindiOnly = () => getLang() === 'hi';
export const setHindiOnly = (on) => setLang(on ? 'hi' : 'both');
