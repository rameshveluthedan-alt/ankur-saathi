import React from 'react';

/**
 * Hindi and its English translation, the same way on every screen. The language setting (services/language.js) decides which shows:
 * Hindi only hides the .en span, English only hides the .hi span (the English then takes the Hindi's place and size), both shows both.
 * Stacked by default (in "both", the English on its own smaller line); inline puts it on the same line.
 * Never put text in `en` that has no Hindi.
 */
export default function Bi({ hi, en, inline }) {
  if (!en) return <>{hi}</>;
  return <><span className="hi">{hi}</span><span className={inline ? 'en en-inline' : 'en'} lang="en">{en}</span></>;
}
