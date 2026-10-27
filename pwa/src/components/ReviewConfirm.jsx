import React from 'react';
import Bi from './Bi';
import { RESULT_MARK } from './ProgressToday';

// A child's result in words, as the Review's analysis already says it ("आज की जाँच में: प्राप्त / आंशिक / प्राप्त नहीं")
export const RESULT_WORD = {
  achieved: { hi: 'प्राप्त', en: 'Achieved' },
  partially_achieved: { hi: 'आंशिक', en: 'Partial' },
  not_achieved: { hi: 'प्राप्त नहीं', en: 'Not yet' },
};

const grey = { fontSize: '0.75rem', color: 'var(--text-secondary)' };

// The quiet way on: the Progress tab has every result of today and the group's decision
function ToProgress({ onOpen }) {
  return (
    <button type="button" className="demo-link" data-testid="to-progress" onClick={onOpen}
      style={{ display: 'block', background: 'none', border: 'none', padding: '6px 0 0', minHeight: 36, textAlign: 'left', fontFamily: 'inherit', ...grey }}>
      <Bi hi="प्रगति टैब पर आज के सभी नतीजे और समूह-निर्णय देखें →" en="See all of today's results and the group decision on Progress →" />
    </button>
  );
}

/**
 * After the Observed save: what was just recorded, in the group's colour, above the children list (which stays usable: retap and submit again).
 * saved = { level, items: [{ roll_number, status }] }: the children of the save that just completed. Not shown after a failed save.
 */
export function ObservedSaved({ saved, onOpenProgress }) {
  if (!saved || !saved.items || !saved.items.length) return null;
  const count = (s) => saved.items.filter((i) => i.status === s).length;
  const n = saved.items.length;
  const naRolls = saved.items.filter((i) => i.status === 'not_achieved').map((i) => i.roll_number).sort((a, b) => a - b);
  return (
    <div className={`saved-block tier-${saved.level}`} data-testid="observed-saved" role="status">
      <div style={{ fontWeight: 600, color: 'var(--tier-ink)' }} data-testid="observed-saved-count" data-n={n}>
        <Bi hi={`✓ ${n} अवलोकन दर्ज हुए`} en={`${n} observations recorded`} inline />
      </div>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 4 }}>
        <span className="badge badge-result" data-testid="saved-a">✓ A: {count('achieved')}</span>
        <span className="badge badge-result" data-testid="saved-pa">~ PA: {count('partially_achieved')}</span>
        <span className="badge badge-result" data-testid="saved-na">✗ NA: {count('not_achieved')}</span>
      </div>
      {naRolls.length > 0 && (
        <div style={{ ...grey, marginTop: 4 }} data-testid="saved-na-rolls">
          ✗ NA<span className="en en-inline" lang="en">not yet</span>: {naRolls.map((r) => `रोल ${r}`).join(', ')}
        </div>
      )}
      <ToProgress onOpen={onOpenProgress} />
    </div>
  );
}

/**
 * After a Reading-aloud save: the child just scored, in the group's colour, above the (empty again) entry form, and how many in the group are still to score.
 * saved = { level, result }: result is the SERVER's answer (roll_number, cwpm, classification); the result is never worked out on the phone.
 * left = how many children of this group are still to score today on this skill (from the server's coverage), hidden when 0.
 */
export function ReadingSaved({ saved, left, onOpenProgress }) {
  if (!saved || !saved.result) return null;
  const r = saved.result;
  const word = RESULT_WORD[r.classification];
  return (
    <div className={`saved-block tier-${saved.level}`} data-testid="reading-saved" role="status">
      <div style={{ fontWeight: 600, color: 'var(--tier-ink)' }} data-testid="reading-saved-line" data-classification={r.classification}>
        ✓ रोल {r.roll_number}: {r.cwpm} CWPM · <span className="badge badge-result">{RESULT_MARK[r.classification] || '—'}</span>{' '}
        {word && <Bi hi={word.hi} en={word.en} inline />}
      </div>
      {left > 0 && (
        <div style={{ ...grey, marginTop: 4 }} data-testid="reading-left" data-left={left}>
          <Bi hi={`इस समूह में ${left} और बच्चे बाकी`} en={`${left} more children in this group to go`} inline />
        </div>
      )}
      <ToProgress onOpen={onOpenProgress} />
    </div>
  );
}

/** A failed save, in place (the block above is not shown). */
export function SaveError({ message, testid }) {
  if (!message) return null;
  return <p role="alert" data-testid={testid} style={{ color: 'var(--beginner-ink)', fontSize: '0.8125rem', margin: '6px 0' }}>{message}</p>;
}
