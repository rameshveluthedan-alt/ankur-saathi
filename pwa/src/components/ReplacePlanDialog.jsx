import React, { useEffect, useRef } from 'react';
import Bi from './Bi';
import { GROUP_LABELS, GROUP_ORDER } from '../tiers';

/**
 * "Replace today's plan?" on the Plan screen. "नहीं, वही रखें" (keep) is the default: it has the focus, and tapping outside or pressing Escape also keeps.
 * kind: 'plan' (a plan exists: names what was recorded against it, from the server's evidence_by_group; groups with 0 are not listed)
 *       'unknown' (whether a plan exists could not be checked: generating may replace one).
 */
export default function ReplacePlanDialog({ kind = 'plan', evidence, onKeep, onReplace }) {
  const keepRef = useRef(null);
  useEffect(() => {
    if (keepRef.current) keepRef.current.focus();
    const onKey = (e) => { if (e.key === 'Escape') onKeep(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);
  const groups = GROUP_ORDER.filter((g) => evidence && evidence.has_evidence && (evidence.evidence_by_group || {})[g] > 0)
    .map((g) => ({ g, n: evidence.evidence_by_group[g], L: GROUP_LABELS[g] }));

  return (
    <div className="dialog-backdrop" data-testid="replace-backdrop" onClick={onKeep}>
      <div className="dialog card" role="dialog" aria-modal="true" aria-labelledby="replace-title" data-testid="replace-dialog" data-kind={kind}
        data-evidence={groups.length ? 'true' : 'false'} onClick={(e) => e.stopPropagation()}>
        <div id="replace-title" style={{ fontSize: '0.9375rem', lineHeight: 1.5 }}>
          {kind === 'unknown' ? (
            <Bi hi="आज की योजना की जाँच नहीं हो सकी। अगर योजना पहले से बनी है, तो नयी योजना बनाने पर पुरानी हट जाएगी। आगे बढ़ें?"
              en="Could not check for today's plan. If one is already made, a new one will replace it. Continue?" />
          ) : groups.length ? (
            <>
              <Bi hi="आपने इस योजना के लिए इन समूहों पर कुछ बच्चों का रिकॉर्ड पहले ही बना लिया है:" en="You've already recorded evidence against this plan for some children in these groups:" />
              <div data-testid="replace-groups" style={{ fontWeight: 700, margin: '6px 0' }}>
                {groups.map(({ g, n, L }, i) => <span key={g}>{i ? ' · ' : ''}<span className={`tier-${g}`} style={{ color: 'var(--tier-ink)' }}>{L.mark} {L.hi} — {n} बच्चे</span></span>)}
                <span className="en" lang="en">{groups.map(({ n, L }) => `${L.en} — ${n} ${n === 1 ? 'child' : 'children'}`).join(' · ')}</span>
              </div>
              <Bi hi="नया प्लान बनाने पर पुराना प्लान हट जाएगा। पुराने रिकॉर्ड आपके संग्रह में रहेंगे।" en="If you make a new plan, the old plan will go. The old records stay in your collection." />
              <div style={{ marginTop: 6 }}><Bi hi="बदलना चाहते हैं?" en="Do you want to replace it?" /></div>
            </>
          ) : (
            <Bi hi="आज की योजना पहले से बनी है। नयी योजना बनाने पर पुरानी हट जाएगी। बदलना चाहते हैं?" en="A plan is already made for today. Making a new one will replace it. Do you want to replace it?" />
          )}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 12 }}>
          <button ref={keepRef} type="button" className="btn btn-primary" data-testid="replace-keep" onClick={onKeep} style={{ flexDirection: 'column', gap: 0 }}>
            {kind === 'unknown' ? <Bi hi="नहीं, रुकें" en="No, wait" /> : <Bi hi="नहीं, वही रखें" en="No, keep this" />}
          </button>
          <button type="button" className="btn btn-secondary" data-testid="replace-yes" onClick={onReplace} style={{ flexDirection: 'column', gap: 0 }}>
            {kind === 'unknown' ? <Bi hi="हाँ, बनाएँ" en="Yes, make it" /> : <Bi hi="हाँ, बदलें" en="Yes, replace" />}
          </button>
        </div>
      </div>
    </div>
  );
}
