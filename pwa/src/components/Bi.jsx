import React from 'react';

/**
 * Hindi first, its English translation after it, the same way on every screen.
 * Stacked by default (the English on its own smaller line); inline puts it on the same line.
 * The English is a .en span: the "Hindi only" setting (services/language.js) hides it. Never put text there that has no Hindi.
 */
export default function Bi({ hi, en, inline }) {
  return <>{hi}{en && <span className={inline ? 'en en-inline' : 'en'} lang="en">{en}</span>}</>;
}
