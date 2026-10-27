import React from 'react';
import { paceLabel, manyErrors } from '../services/pace';

/**
 * One scored reading, as one line: "{correct} सही · {errors} गलतियाँ · रफ़्तार …". The two numbers are what the teacher entered; the pace label comes from the
 * server's classification through services/pace.js (never "reader" words). A zero is shown as "0 गलतियाँ", so every line has the same shape.
 * amber: many errors for the words read turn the errors part amber with ⚠ (the pace label is unchanged). Used on the Review; the Progress row has no amber.
 */
export default function FluencyLine({ roll, correct, errors, classification, amber = false }) {
  const pace = paceLabel(classification);
  const warn = amber && manyErrors(correct, errors);
  return (
    <span data-testid="fluency-line" data-classification={classification}>
      {roll != null && <>✓ रोल {roll}: </>}
      <span data-testid="fluency-correct">{correct} सही</span> ·{' '}
      <span data-testid="fluency-errors" className={warn ? 'many-errors' : undefined}>{errors} गलतियाँ{warn ? ' ⚠' : ''}</span> ·{' '}
      <span data-testid="fluency-pace">{pace ? pace.hi : '—'}</span>
      <span className="en" lang="en">{roll != null ? `Roll ${roll}: ` : ''}{correct} correct · {errors} errors · {pace ? pace.en : '—'}</span>
    </span>
  );
}
