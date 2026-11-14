import React, { useEffect, useState } from 'react';
import { getLang, setLang } from '../services/language';

// The language as React state: re-renders when it changes anywhere (this pill, the Profile screen), so text made with bi() follows at once.
export function useLang() {
  const [lang, set] = useState(getLang);
  useEffect(() => {
    const on = (e) => set(e.detail);
    window.addEventListener('ankur-lang', on);
    return () => window.removeEventListener('ankur-lang', on);
  }, []);
  return lang;
}

// The हिं / EN pill at the top right of every screen (the sign-in screen too). One tap shows the whole app in the other language.
// "Both" (Hindi with the English after it) is no longer offered on Profile (14 Nov); a phone that still has it shows neither half lit, and one tap ends it.
export default function LangSwitch() {
  const lang = useLang();
  const seg = (id, label, aria) => (
    <button type="button" data-testid={`lang-${id}`} aria-pressed={lang === id} aria-label={aria} onClick={() => setLang(id)}
      className={`lang-seg ${lang === id ? 'on' : ''}`}>{label}</button>
  );
  return (
    <div className="lang-switch" role="group" aria-label="भाषा / Language" data-testid="lang-switch">
      {seg('hi', 'हिं', 'हिंदी')}
      {seg('en', 'EN', 'English')}
    </div>
  );
}
