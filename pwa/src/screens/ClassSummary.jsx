import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { getClassSummary } from '../services/api';
import { GROUP_LABELS, GROUP_ORDER } from '../tiers';
import { localToday } from '../services/today';
import { backOrHome } from '../services/backHistory';
import { hiDate, classLine } from '../services/printFormat';

/**
 * The class summary (29 Oct, at /progress/class): the teacher's own page for planning next week, over the last 4 weeks (the server's
 * GET /progress/class-summary). Per subject: the class now, what each group was taught and how it went, then the children to look at, the most common
 * mistakes with an activity, and each group's next step. The server sends roll numbers only; the NAMES are added here, from the copy this phone already
 * holds (as on the Review and Progress screens), so the printed page carries names: it says so at its foot.
 * NOTE: the wording and the rule values are the app's working ones, for Vaishnavi's review.
 */
const SUBJECT = { numeracy: 'गणित', r1_literacy: 'हिंदी' };
const NEXT_WHY = {
  advance: '⬆ आगे बढ़ें', advance_no_next: '⬆ आगे बढ़ें; अगला कौशल नहीं, इसलिए यही फिर', reteach: '🔄 दोहराएँ',
  not_sure: '❓ पक्का नहीं: वही फिर', recommended: 'कई बच्चों से गलती हुई: वही फिर',
};
const groupsLine = (sizes) => GROUP_ORDER.filter((g) => sizes && sizes[g] != null).map((g) => `${GROUP_LABELS[g].mark} ${GROUP_LABELS[g].hi} ${sizes[g]}`).join(' · ');
const G = (l) => `${GROUP_LABELS[l]?.mark || ''} ${GROUP_LABELS[l]?.hi || l}`;

export default function ClassSummary() {
  const { teacher, names } = useAuth();
  const navigate = useNavigate();
  const [s, setS] = useState(undefined);        // undefined: loading; null: could not load
  // a child as the teacher knows them: the roll number, and the name if this phone holds it
  const kid = (r) => (names && names[r] ? `${r} ${names[r]}` : `रोल ${r}`);
  const kids = (rolls) => rolls.map(kid).join(', ');

  useEffect(() => {
    let cancelled = false;
    getClassSummary(teacher.teacher_id, localToday()).then((x) => { if (!cancelled) setS(x); }).catch(() => { if (!cancelled) setS(null); });
    return () => { cancelled = true; };
  }, [teacher.teacher_id]);
  // printing shows this page alone (no banner, no bottom bar): the printed plan's own rule, "body.print-plan" in index.css
  useEffect(() => { document.body.classList.add('print-plan'); return () => document.body.classList.remove('print-plan'); }, []);

  const bar = (
    <div className="no-print" style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
      <button type="button" className="btn btn-secondary btn-small" data-testid="class-back" onClick={() => backOrHome(navigate, '/progress')}>← वापस</button>
      {s && <button type="button" className="btn btn-primary btn-small" data-testid="class-print" onClick={() => window.print()}>🖨️ प्रिंट करें</button>}
    </div>
  );
  if (s === undefined) return <div className="screen">{bar}<div className="loading"><div className="spinner" /></div></div>;
  if (!s) return <div className="screen">{bar}<p data-testid="class-failed">रिपोर्ट नहीं खुल सकी। इंटरनेट जाँचकर फिर कोशिश करें।</p></div>;

  const R = s.rules;
  const weeks = Math.round(s.period.days / 7);
  const subjects = Object.keys(SUBJECT).filter((d) => s.subjects[d]);
  const anyStuck = subjects.some((d) => s.subjects[d].stuck.length);

  return (
    <div className="screen plan-print mentor-report class-summary" data-testid="class-summary">
      {bar}
      <div className="print-title" data-testid="class-title">{['कक्षा सारांश', teacher.employee_code || teacher.school_code, classLine(teacher.enrolled_grades)].filter(Boolean).join(' · ')}</div>
      <div data-testid="class-period">अवधि: {hiDate(s.period.start)} – {hiDate(s.period.end)} (पिछले {weeks} हफ़्ते)</div>
      <hr />

      {subjects.map((d) => {
        const x = s.subjects[d];
        return (
          <section key={d} data-testid={`class-subject-${d}`}>
            <div className="print-block-head">{SUBJECT[d]}</div>
            <div data-testid={`now-${d}`}>कक्षा अभी: {groupsLine(x.groups_now)} · कौशल हासिल किए: <b>{x.skills_achieved}</b></div>
            {x.taught.length ? x.taught.map((t) => (
              <div key={`${t.level}-${t.skill_id}`} data-testid={`taught-${d}-${t.level}-${t.skill_id}`}>
                {G(t.level)}: {t.skill_id}{t.skill_name_hi ? ` ${t.skill_name_hi}` : ''} · {t.days} दिन · ⬆ {t.finals.advance} · 🔄 {t.finals.reteach} · ❓ {t.finals.not_sure}
              </div>
            )) : <div data-testid={`taught-none-${d}`}>इस अवधि में कोई योजना नहीं बनी।</div>}
            {Object.keys(x.next).length > 0 && (
              <div data-testid={`next-${d}`}>
                <b>अगला कदम:</b> {GROUP_ORDER.filter((l) => x.next[l]).map((l) => {
                  const n = x.next[l];
                  return <span key={l} data-testid={`next-${d}-${l}`}>{' '}{G(l)}: {n.skill_id ? `${n.skill_id}${n.skill_name_hi ? ` ${n.skill_name_hi}` : ''} (${NEXT_WHY[n.reason] || n.reason})` : 'पिछली समीक्षा में निर्णय नहीं; योजना बनाते समय चुनें'};</span>;
                })}
              </div>
            )}
          </section>
        );
      })}

      <section data-testid="class-look">
        <div className="print-block-head">👀 इन बच्चों पर ध्यान दें</div>
        {anyStuck && subjects.flatMap((d) => s.subjects[d].stuck.map((st) => (
          <div key={`${d}-${st.level}-${st.skill_id}`} data-testid={`stuck-${st.level}-${st.skill_id}`}>
            {G(st.level)}, {st.skill_id} ({st.days} दिन पढ़ाया, अभी हासिल नहीं): {kids(st.rolls)}
          </div>
        )))}
        <div data-testid="look-not-checked">{Math.round(R.not_checked_days / 7)} हफ़्ते से नहीं जाँचे: {s.not_checked.length ? kids(s.not_checked) : 'कोई नहीं'}</div>
        <div data-testid="look-na">{R.na_days}+ दिन “अभी नहीं” (NA): {s.not_achieved_again.length ? s.not_achieved_again.map((c) => `${kid(c.roll)} (${c.skills.join(', ')})`).join(', ') : 'कोई नहीं'}</div>
      </section>

      {s.mistakes.length > 0 && (
        <section data-testid="class-mistakes">
          <div className="print-block-head">आम गलतियाँ</div>
          {s.mistakes.map((m) => (
            <div key={m.misconception_id} data-testid={`class-mistake-${m.misconception_id}`}>
              {m.skill_id} “{m.name_hi}”: {kids(m.rolls)}{m.activity ? <> → गतिविधि: “{m.activity.title_hi}”</> : ''}
            </div>
          ))}
        </section>
      )}

      <hr />
      <div className="print-footer" data-testid="class-rules">
        नियम: “अभी हासिल नहीं” = समूह को {R.stuck_days}+ दिन वही कौशल पढ़ाया और बच्चे का सबसे नया नतीजा A नहीं · “नहीं जाँचे” = {R.not_checked_days} दिन से कोई नतीजा नहीं · NA {R.na_days} या ज़्यादा दिन
      </div>
      <div className="print-footer" data-testid="class-footer">🌱 अंकुर साथी · {s.period.end} · इस पन्ने पर बच्चों के नाम हैं (इसी फ़ोन से): इसे सँभालकर रखें</div>
    </div>
  );
}
