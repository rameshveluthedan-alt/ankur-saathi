import React from 'react';
import Bi from './Bi';

// A feature that works but is still being tested or built: said on the screen where it is used, so nobody takes it for finished
// (the hackathon evaluators, 12 Nov: "clearly flag those under development"). What is known about each one is in docs/KNOWN_ISSUES.md.
export default function PilotFlag({ hi, en, testid }) {
  return (
    <div className="pilot-flag" data-testid={testid || 'pilot-flag'} role="note">
      <span className="pilot-chip">🧪 <Bi hi="पायलट" en="Pilot" inline /></span> <Bi hi={hi} en={en} inline />
    </div>
  );
}
