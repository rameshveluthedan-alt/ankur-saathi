import React from 'react';
import { GROUP_LABELS } from '../tiers';

/**
 * The skill a group is checked on, the same on every Review step: "● शुरुआती · N0.1.1 · रंग, आकार या माप से छाँटना".
 * withGroup={false} where the card already shows the group's badge (steps 1 and 3): then only "N0.1.1 · …".
 */
export default function SkillLine({ level, skillId, name, withGroup = true, testid }) {
  if (!skillId) return null;
  const L = GROUP_LABELS[level] || {};
  return (
    <div className="skill-line" data-testid={testid} data-skill={skillId}>
      {withGroup && <>{L.mark} {L.hi}<span className="en en-inline" lang="en">{L.en}</span> · </>}
      <span style={{ fontFamily: 'monospace', fontWeight: 700 }}>{skillId}</span>{name ? <> · {name}</> : null}
    </div>
  );
}
