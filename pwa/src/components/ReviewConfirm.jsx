import React from 'react';
import Bi from './Bi';
import { RESULT_MARK } from './ProgressToday';
import { isFluencySkill } from '../services/pace';
import FluencyLine from './FluencyLine';

// A child's result in words, as the Review's analysis already says it ("आज की जाँच में: प्राप्त / आंशिक / प्राप्त नहीं")
export const RESULT_WORD = {
  achieved: { hi: 'प्राप्त', en: 'Achieved' },
  partially_achieved: { hi: 'आंशिक', en: 'Partial' },
  not_achieved: { hi: 'प्राप्त नहीं', en: 'Not yet' },
};

const grey = { fontSize: '0.75rem', color: 'var(--text-secondary)' };

// A quick look at Progress in the middle of the review: Progress then shows "← समीक्षा पर लौटें", back to this same group. A small outlined button,
// so it reads as something to tap, without competing with the save buttons.
function ToProgress({ onOpen }) {
  return (
    <button type="button" className="btn btn-secondary btn-small" data-testid="to-progress" onClick={onOpen} style={{ marginTop: 8 }}>
      📊 <Bi hi="प्रगति देखें →" en="See progress" inline />
    </button>
  );
}

const OBS_CODE = { achieved: 'A', partially_achieved: 'PA', not_achieved: 'NA' };
// Hindi agrees with the number: 1 अवलोकन दर्ज हुआ / 2 अवलोकन दर्ज हुए; 1 नया / 2 नए; 1 बदला गया / 2 बदले गए
const recordedHi = (k) => (k === 1 ? 'दर्ज हुआ' : 'दर्ज हुए');
const newHi = (k) => (k === 1 ? 'नया' : 'नए');
const changedHi = (k) => (k === 1 ? 'बदला गया' : 'बदले गए');
const obsEn = (k) => (k === 1 ? 'observation' : 'observations');

/**
 * After the Observed save: what was just recorded, in the group's colour, above the children list (which stays usable: retap and submit again).
 * saved = { level, items: [{ roll_number, status }], result }: the children of the save that just completed, and the server's answer (result.results: per child
 * "new" / "changed" / "unchanged" with the previous status; result.not_found: roll numbers not in the class, never counted). Without result (an older server)
 * every child counts as new. Not shown after a failed save.
 */
export function ObservedSaved({ saved, onOpenProgress }) {
  if (!saved || !saved.items || !saved.items.length) return null;
  const res = saved.result && Array.isArray(saved.result.results) ? saved.result : null;
  const done = res ? res.results : saved.items.map((i) => ({ ...i, outcome: 'new', previous: null }));        // what was actually saved
  const notFound = res ? (res.not_found || []) : [];
  const count = (s) => done.filter((i) => i.status === s).length;
  const n = done.length;
  const nNew = done.filter((i) => i.outcome === 'new').length;
  const changed = done.filter((i) => i.outcome === 'changed');
  const nSame = done.filter((i) => i.outcome === 'unchanged').length;
  const naRolls = done.filter((i) => i.status === 'not_achieved').map((i) => i.roll_number).sort((a, b) => a - b);
  // the header says what happened: recorded, updated, both, or no change
  const head = nNew === 0 && changed.length === 0 ? { hi: 'कोई बदलाव नहीं', en: 'No change', kind: 'unchanged' }
    : changed.length === 0 ? { hi: `✓ ${nNew} अवलोकन ${recordedHi(nNew)}`, en: `${nNew} ${obsEn(nNew)} recorded`, kind: 'new' }
    : nNew === 0 ? { hi: `✓ ${changed.length} अवलोकन ${changedHi(changed.length)}`, en: `${changed.length} ${obsEn(changed.length)} updated`, kind: 'changed' }
    : { hi: `✓ ${nNew + changed.length} अवलोकन: ${nNew} ${newHi(nNew)}, ${changed.length} ${changedHi(changed.length)}`, en: `${nNew + changed.length} observations: ${nNew} new, ${changed.length} updated`, kind: 'mixed' };
  return (
    <div className={`saved-block tier-${saved.level}`} data-testid="observed-saved" role="status">
      <div style={{ fontWeight: 600, color: 'var(--tier-ink)' }} data-testid="observed-saved-count" data-n={n} data-kind={head.kind}>
        <Bi hi={head.hi} en={head.en} inline />
      </div>
      {changed.length > 0 && (
        <div style={{ ...grey, marginTop: 4 }} data-testid="saved-changes">
          <Bi hi="बदले" en="Changed" inline />: {changed.map((i) => `रोल ${i.roll_number} ${OBS_CODE[i.previous] || '?'} → ${OBS_CODE[i.status]}`).join(', ')}
        </div>
      )}
      {nSame > 0 && (nNew > 0 || changed.length > 0) && (
        <div style={{ ...grey, marginTop: 2 }} data-testid="saved-same"><Bi hi={`${nSame} पहले जैसे`} en={`${nSame} unchanged`} inline /></div>
      )}
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
      {notFound.length > 0 && (
        <div role="alert" style={{ fontSize: '0.75rem', color: 'var(--beginner-ink)', marginTop: 4 }} data-testid="saved-not-found">
          <Bi hi={`${notFound.map((r) => `रोल ${r}`).join(', ')} कक्षा में नहीं है, दर्ज नहीं हुआ`} en={`${notFound.map((r) => `Roll ${r}`).join(', ')}: not in the class, not recorded`} inline />
        </div>
      )}
      <ToProgress onOpen={onOpenProgress} />
    </div>
  );
}

/**
 * After a Reading-aloud save: the child just scored, in the group's colour, above the (empty again) entry form, and how many in the group are still to score.
 * saved = { level, skill, result, entry }: result is the SERVER's answer (roll_number, classification), entry the two numbers the teacher entered
 * ({ cwpm, errors }). A speed skill (L1.5.1, L2.5.1, L3.5.1) shows the numbers and the pace; any other reading skill keeps the A/PA/NA line.
 * left = how many children of this group are still to score today on this skill (from the server's coverage), hidden when 0.
 */
export function ReadingSaved({ saved, left, onOpenProgress }) {
  if (!saved || !saved.result) return null;
  const r = saved.result;
  const word = RESULT_WORD[r.classification];
  const entry = saved.entry || { cwpm: r.cwpm, errors: 0 };
  return (
    <div className={`saved-block tier-${saved.level}`} data-testid="reading-saved" role="status">
      <div style={{ fontWeight: 600, color: 'var(--tier-ink)' }} data-testid="reading-saved-line" data-classification={r.classification}>
        {isFluencySkill(saved.skill)
          ? <FluencyLine roll={r.roll_number} correct={entry.cwpm} errors={entry.errors} classification={r.classification} amber />
          : <>✓ रोल {r.roll_number}: {r.cwpm} CWPM · <span className="badge badge-result">{RESULT_MARK[r.classification] || '—'}</span>{' '}{word && <Bi hi={word.hi} en={word.en} inline />}</>}
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
