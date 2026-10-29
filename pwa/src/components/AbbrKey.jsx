import React from 'react';
import Bi from './Bi';
import { ABBR } from '../services/reviewWays';

/**
 * The key to A / PA / NA (29 Oct): one small grey line, once per screen, wherever the letters are shown without their meaning (the Review's observing
 * list and final decision, the saved box, the Class progress card). The wording is Vaishnavi's reviewed meaning, from one place (services/reviewWays.js).
 */
export default function AbbrKey({ testid = 'abbr-key', style }) {
  return (
    <p className="abbr-key" data-testid={testid} style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', margin: '4px 0', ...style }}>
      <Bi hi={ABBR.hi} en={ABBR.en} inline />
    </p>
  );
}
