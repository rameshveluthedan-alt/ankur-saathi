import React from 'react';
import { GROUP_LABELS } from '../tiers';
import Bi from './Bi';

// A group's mark in its own colour (● Beginners, ▲ Progressors, ■ Proficient), the same on every screen; with `name`, the group's name after it.
// The shape carries the meaning too, so the groups never depend on colour alone.
export default function GroupMark({ group, name = false, inline = true }) {
  const L = GROUP_LABELS[group];
  if (!L) return null;
  return (
    <span className={`gmark tier-${group}`} data-group={group}>
      <span className="gmark-shape" aria-hidden="true">{L.mark}</span>
      {name && <> <Bi hi={L.hi} en={L.en} inline={inline} /></>}
    </span>
  );
}
