import React from 'react';

/**
 * The group panel as a DRAWER in the bottom bar, above the Generate button.
 * It opens and closes in place: the page does not scroll, so the teacher never loses their place in the long skill list
 * (the first version put the panel at the top of the page and the button scrolled up to it).
 * Closed: one line with each group's skill. Open: the panel (it scrolls inside the drawer) and a button to close it.
 */
export default function GroupSkillsDrawer({ open, onToggle, summary, disabled, children }) {
  return (
    <div data-testid="group-skills-drawer">
      {open && (
        <div data-testid="group-skills-drawer-body"
          style={{ maxHeight: 'min(55vh, 440px)', overflowY: 'auto', overscrollBehavior: 'contain', marginBottom: 6, borderRadius: 8 }}>
          {children}
        </div>
      )}
      <button type="button" className="btn btn-secondary btn-small" data-testid="edit-group-skills" aria-expanded={open ? 'true' : 'false'}
        onClick={onToggle} disabled={disabled} style={{ width: '100%', marginBottom: 6, fontSize: '0.7rem' }}>
        {open ? '▼ बंद करें: कौशल सूची पर लौटें (Close: back to the skill list)' : `समूहों के कौशल: ${summary} — देखें/बदलें ▲`}
      </button>
    </div>
  );
}
