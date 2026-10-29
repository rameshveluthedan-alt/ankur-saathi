import React from 'react';
import Bi from './Bi';
import { GROUP_LABELS, GROUP_ORDER } from '../tiers';
import FluencyLine from './FluencyLine';
import { isFluencySkill, paceLabel } from '../services/pace';

// The decision words are the ones the teacher taps at the Review (services/groupSkills.js DECISION_LABELS), so a decision reads the same on both screens.
export const DECISION_TEXT = {
  advance: { hi: '⬆ आगे बढ़ें', en: 'Advance' },
  reteach: { hi: '🔄 दोहराएँ', en: 'Re-teach' },
  not_sure: { hi: '❓ पक्का नहीं', en: 'Not sure' },
};
// a result recorded for one child: a code, like a skill id (the same neutral badge as the Review)
export const RESULT_MARK = { achieved: '✓ A', partially_achieved: '~ PA', not_achieved: '✗ NA' };

const grey = { fontSize: '0.75rem', color: 'var(--text-secondary)' };

/**
 * "Today" on the Progress screen: ONE card with a row per group (its colour edge and shape), from the dashboard's today[subject]:
 * the A/PA/NA counts of today's sample and how many of the group were assessed, the decision recorded at today's review, and two rare lines
 * (the decision disagrees with today's evidence; advanced but there is no next skill). A group nobody was assessed in today shows one grey line only.
 */
export function TodayCard({ today }) {
  if (!today) return null;
  return (
    <div className="card" data-testid="today-card" style={{ padding: '10px 12px' }}>
      <div style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: 4 }}>
        <Bi hi="आज के नमूने में" en="In today's sample" inline />
      </div>
      {!today.has_plan && <div style={grey} data-testid="today-no-plan"><Bi hi="आज इस विषय की योजना नहीं बनी।" en="No plan for this subject today." /></div>}
      {GROUP_ORDER.map((label) => <TodayRow key={label} label={label} g={(today.by_level || {})[label]} />)}
    </div>
  );
}

function TodayRow({ label, g }) {
  const L = GROUP_LABELS[label];
  if (!g) return null;
  const decision = g.decision ? DECISION_TEXT[g.decision] : null;
  return (
    <div className={`today-row tier-${label}`} data-testid={`today-${label}`}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
        <span className={`badge badge-${label}`}>{L.hi}<span className="en en-inline" lang="en" style={{ color: 'inherit' }}>{L.en}</span></span>
        {g.skill_id && <span style={{ ...grey, fontFamily: 'monospace' }}>{g.skill_id}</span>}
      </div>
      {g.assessed === 0 ? (
        <div style={{ ...grey, marginTop: 4 }} data-testid={`today-none-${label}`}><Bi hi="आज किसी का आकलन नहीं हुआ" en="No assessment today" inline /></div>
      ) : (
        <>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap', marginTop: 4 }} data-testid={`today-counts-${label}`}>
            <span className="badge badge-result" data-testid="count-a">✓ A: {g.a}</span>
            <span className="badge badge-result" data-testid="count-pa">~ PA: {g.pa}</span>
            <span className="badge badge-result" data-testid="count-na">✗ NA: {g.na}</span>
            <span style={grey} data-testid="count-of">{g.group_size} में से {g.assessed} बच्चों का आकलन<span className="en en-inline" lang="en">assessed {g.assessed} of {g.group_size}</span></span>
          </div>
          {decision ? (
            <div data-testid={`today-decision-${label}`} data-decision={g.decision}
              style={{ fontSize: '0.8125rem', fontWeight: 600, marginTop: 4, color: g.decision === 'reteach' ? 'var(--reteach)' : 'var(--tier-ink)' }}>
              <Bi hi={`आपका निर्णय: ${decision.hi}`} en={`Your decision: ${decision.en}`} inline />
            </div>
          ) : (
            <div style={{ ...grey, marginTop: 4 }} data-testid={`today-decision-${label}`} data-decision="none"><Bi hi="आज कोई निर्णय दर्ज नहीं" en="No decision recorded today" inline /></div>
          )}
          {g.conflict && (
            <div style={{ fontSize: '0.75rem', color: '#8A5A00', marginTop: 2 }} data-testid={`today-conflict-${label}`}>
              <Bi hi="⚠ आपका निर्णय और आज की जाँच मेल नहीं खाते" en="Your decision disagrees with today's evidence" />
            </div>
          )}
          {g.advance_no_next && (
            <div style={{ ...grey, marginTop: 2 }} data-testid={`today-no-next-${label}`}>
              <Bi hi="⬆ आगे बढ़ाया; अगला कौशल अभी नहीं है, इसलिए यही कौशल फिर सिखाया जाएगा" en="Advanced; no next skill yet, so the same one will be taught again" />
            </div>
          )}
        </>
      )}
    </div>
  );
}

/**
 * One line under a child's row: what was recorded for the child TODAY, if anything. Nothing at all when nothing was recorded (not "absent", not "not yet").
 * A speed reading skill (L1.5.1, L2.5.1, L3.5.1) scored by reading aloud shows the two numbers and the pace label, as on the Review (no amber here:
 * the row has less room); every other result shows the A/PA/NA badge.
 */
export function ChildToday({ today }) {
  if (!today) return null;
  const fluency = isFluencySkill(today.skill_id) && today.cwpm != null && !!paceLabel(today.status);
  if (!fluency && !RESULT_MARK[today.status]) return null;
  return (
    <div data-testid="child-today" data-status={today.status} data-kind={fluency ? 'fluency' : 'badge'} style={{ ...grey, marginTop: 4 }}>
      <Bi hi={`आज ${today.skill_id} पर`} en={`Today on ${today.skill_id}`} inline />:{' '}
      {fluency
        ? <FluencyLine correct={today.cwpm} errors={today.errors ?? 0} classification={today.status} />
        : <span className="badge badge-result">{RESULT_MARK[today.status]}</span>}
    </div>
  );
}

/**
 * "Children to look at": children whose recent daily work no longer matches their level (the same flags as before). Honest about what it is:
 * daily evidence never changes a level by itself, and there is no re-assessment screen yet, so it asks the teacher to LOOK, in two short lists.
 */
export function LookAtChildren({ flags, nameOf = () => '' }) {
  if (!flags || !flags.length) return null;
  const parts = [
    { dir: 'higher', hi: '⬆ अच्छा प्रदर्शन कर रहे हैं — एक छोटा दोबारा आकलन?', en: 'Doing well — a short re-assessment?', edge: 'var(--proficient)' },
    { dir: 'lower', hi: '⬇ कठिनाई में हैं — थोड़ी मदद की ज़रूरत?', en: 'Struggling — needs a bit of help?', edge: '#C9A227' },
  ];
  return (
    <div data-testid="look-at">
      <h2 style={{ margin: '12px 0 2px' }}>🔎 <Bi hi="इन बच्चों पर एक नज़र" en="Children to look at" inline /></h2>
      <p style={{ ...grey, margin: '0 0 8px' }}>
        <Bi hi="रोज़ की जाँच से बच्चे का स्तर अपने आप नहीं बदलता। ये कुछ बच्चे हैं जिन पर आप एक नज़र डाल सकते हैं।"
          en="Daily evidence doesn't change a child's level on its own. These are a few children you may want to look at." />
      </p>
      {parts.map((p) => {
        const list = flags.filter((f) => f.direction === p.dir);
        if (!list.length) return null;
        return (
          <div key={p.dir} data-testid={`look-at-${p.dir}`}>
            <h3 style={{ fontSize: '0.875rem', margin: '8px 0 4px' }}><Bi hi={p.hi} en={p.en} inline /></h3>
            {list.map((f) => (
              <div key={f.child_id} className="card" data-testid={`flag-${f.direction}`} style={{ borderLeft: `4px solid ${p.edge}`, padding: 10 }}>
                <strong>रोल {f.roll_number}{nameOf(f.roll_number)}</strong>
                <p style={{ fontSize: '0.8125rem', margin: '4px 0 0', color: 'var(--text-secondary)' }}>{f.evidence_hi}</p>
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
}
