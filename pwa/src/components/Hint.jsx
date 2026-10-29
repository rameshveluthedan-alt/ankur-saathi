import React, { useId, useState } from 'react';

/**
 * A tappable "ⓘ" that opens a line or two of explanation under it. Instead of a hover tooltip (title=…), which a phone never shows: a teacher taps it.
 * The button is a 44 px target; the text is read out by a screen reader when it opens.
 */
export default function Hint({ testid, label, children }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <div data-testid={testid} style={{ margin: '2px 0 8px' }}>
      <button type="button" className={`hint-btn${label ? ' with-label' : ''}`} aria-expanded={open} aria-controls={id} aria-label={label ? undefined : 'समझाएँ (Explain)'}
        onClick={(e) => { e.stopPropagation(); setOpen((o) => !o); }}>ⓘ{label && <span className="hint-label"> {label}</span>}</button>
      {open && <div id={id} className="hint-text" role="note">{children}</div>}
    </div>
  );
}
