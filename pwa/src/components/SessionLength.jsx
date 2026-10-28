import React from 'react';
import Bi from './Bi';
import { SESSION_MINUTES } from '../services/preferences';

/**
 * "Today's time" on the Plan screen: three big radio buttons (45 / 60 / 90 minutes), each a 44 px tap target. The chosen one fills with the brand green,
 * not a group colour: it is about the whole session. The plan is laid out for the chosen time (sent with each plan request).
 */
export default function SessionLength({ value, onChange, disabled }) {
  return (
    <fieldset data-testid="session-length" disabled={disabled} style={{ border: 'none', padding: 0, margin: '0 0 12px', minWidth: 0 }}>
      <legend style={{ fontSize: '0.8125rem', fontWeight: 600, padding: 0, marginBottom: 4 }}><Bi hi="आज का समय" en="Today's time" inline /></legend>
      <div style={{ display: 'flex', gap: 8 }}>
        {SESSION_MINUTES.map((m) => {
          const on = value === m;
          return (
            <label key={m} className="session-choice" data-testid={`session-${m}`} data-checked={on ? 'true' : 'false'}
              style={{ position: 'relative', flex: 1, minHeight: 44, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4, borderRadius: 8, cursor: disabled ? 'default' : 'pointer',
                       border: `2px solid ${on ? 'var(--green-dark)' : 'var(--border)'}`, background: on ? 'var(--green-dark)' : 'var(--surface)', color: on ? 'white' : 'var(--text)',
                       fontSize: '0.875rem', fontWeight: on ? 700 : 400 }}>
              <input type="radio" name="session_minutes" value={m} checked={on} onChange={() => onChange(m)}
                style={{ position: 'absolute', opacity: 0, width: 1, height: 1, margin: 0 }} />
              {m} मिनट<span className="en en-inline" lang="en" style={{ color: 'inherit' }}>min</span>
            </label>
          );
        })}
      </div>
      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 4 }}>
        <Bi hi="कम समय हो तो कम गतिविधियाँ और छोटी वर्कशीट" en="Less time, fewer activities and a shorter worksheet." inline />
      </div>
    </fieldset>
  );
}
