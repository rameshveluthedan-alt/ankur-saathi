import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { getMentorSummary } from '../services/api';
import { GROUP_LABELS, GROUP_ORDER } from '../tiers';
import { localToday } from '../services/today';
import { backOrHome } from '../services/backHistory';
import { hiDate, classLine } from '../services/printFormat';

/**
 * The mentor report (29 Oct, at /progress/mentor): one printable page for a block or cluster officer's visit, over the last 4 weeks (the server's
 * GET /progress/mentor). The talking points come first (one strength, up to two things to work on, one question), then how the teacher works, then how
 * the children moved, then the most common mistakes with an activity. How the teacher works comes BEFORE the children's levels: classes start from
 * different places, and the visit is for mentoring, not inspection. Hindi only, counts and roll numbers, never a name. The rules behind the points are
 * printed at the foot, so an officer can see where each point comes from.
 * NOTE: the wording and the rule values are the app's working ones, for Vaishnavi's review.
 */
const SUBJECT = { numeracy: 'गणित', r1_literacy: 'हिंदी' };
const groupsLine = (sizes) => GROUP_ORDER.filter((g) => sizes && sizes[g] != null).map((g) => `${GROUP_LABELS[g].mark} ${sizes[g]}`).join(' · ');

export default function MentorReport() {
  const { teacher } = useAuth();
  const navigate = useNavigate();
  const [m, setM] = useState(undefined);        // undefined: loading; null: could not load

  useEffect(() => {
    let cancelled = false;
    getMentorSummary(teacher.teacher_id, localToday()).then((x) => { if (!cancelled) setM(x); }).catch(() => { if (!cancelled) setM(null); });
    return () => { cancelled = true; };
  }, [teacher.teacher_id]);
  // printing shows this page alone (no banner, no bottom bar): the printed plan's own rule, "body.print-plan" in index.css
  useEffect(() => { document.body.classList.add('print-plan'); return () => document.body.classList.remove('print-plan'); }, []);

  const bar = (
    <div className="no-print" style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
      <button type="button" className="btn btn-secondary btn-small" data-testid="mentor-back" onClick={() => backOrHome(navigate, '/progress')}>← वापस</button>
      {m && <button type="button" className="btn btn-primary btn-small" data-testid="mentor-print" onClick={() => window.print()}>🖨️ प्रिंट करें</button>}
    </div>
  );
  if (m === undefined) return <div className="screen">{bar}<div className="loading"><div className="spinner" /></div></div>;
  if (!m) return <div className="screen">{bar}<p data-testid="mentor-failed">रिपोर्ट नहीं खुल सकी। इंटरनेट जाँचकर फिर कोशिश करें।</p></div>;

  const { practice: p, progress: g, points, rules: R } = m;
  const weeks = Math.round(m.period.days / 7);
  const code = teacher.employee_code || '';
  const place = m.school ? [m.school.school_code, [m.school.block, m.school.district].filter(Boolean).join(', ')].filter(Boolean).join(' · ') : (teacher.school_code || '');
  const subjects = Object.keys(SUBJECT).filter((d) => g.groups && g.groups[d]);

  return (
    <div className="screen plan-print mentor-report" data-testid="mentor-report">
      {bar}
      <div className="print-title" data-testid="mentor-title">{['मेंटर रिपोर्ट', place, code && `शिक्षक ${code}`, classLine(teacher.enrolled_grades)].filter(Boolean).join(' · ')}</div>
      <div data-testid="mentor-period">अवधि: {hiDate(m.period.start)} – {hiDate(m.period.end)} (पिछले {weeks} हफ़्ते)</div>
      <hr />

      <section className="mentor-points" data-testid="mentor-points">
        <div className="print-block-head">💬 बातचीत के बिंदु</div>
        {points.strength
          ? <div data-testid="point-strength">👍 {points.strength}</div>
          : <div data-testid="point-nothing">इस अवधि में कोई योजना नहीं बनी।</div>}
        {points.work.map((w, i) => <div key={i} data-testid={`point-work-${w.kind}`}>🎯 {w.hi}</div>)}
        <div data-testid="point-question">❓ {points.question}</div>
      </section>

      <section data-testid="mentor-practice">
        <div className="print-block-head">पढ़ाने का तरीका</div>
        <div>योजना बनी: <b>{p.plan_days}</b> दिन · समीक्षा पूरी (तीनों चरण): <b>{p.review_days}</b> दिन</div>
        <div>बच्चों का काम जाँचकर निर्णय: <b>{p.groups_taught}</b> में से <b>{p.groups_checked}</b> बार</div>
        <div data-testid="practice-match">पहला अनुमान जाँच से मेल खाया: {p.judgments_compared ? <><b>{p.judgments_compared}</b> में से <b>{p.judgments_matched}</b> बार</> : 'अभी तुलना के लिए पर्याप्त जाँच नहीं'}</div>
      </section>

      <section data-testid="mentor-progress">
        <div className="print-block-head">बच्चों की प्रगति</div>
        {subjects.map((d) => {
          const at = g.groups[d];
          return (
            <div key={d} data-testid={`progress-groups-${d}`}>
              {SUBJECT[d]}, समूह: {hiDate(at.start_date)} को {groupsLine(at.start)} → {hiDate(at.end_date)} को {groupsLine(at.end)}
            </div>
          );
        })}
        <div>कौशल हासिल किए: <b>{g.skills_achieved}</b> (कक्षा में {g.class_size} बच्चे)</div>
        {g.stuck.length > 0 && (
          <div data-testid="progress-stuck">{R.stuck_days}+ दिन एक ही कौशल: {g.stuck.map((s) => `${GROUP_LABELS[s.level]?.mark || ''} ${GROUP_LABELS[s.level]?.hi || s.level} ${s.skill_id} (${s.days} दिन)`).join(' · ')}</div>
        )}
        <div data-testid="progress-not-checked">{Math.round(R.not_checked_days / 7)} हफ़्ते से नहीं जाँचे: {g.not_checked.length ? `${g.not_checked.length} बच्चे (रोल ${g.not_checked.join(', ')})` : 'कोई नहीं'}</div>
      </section>

      {m.mistakes.length > 0 && (
        <section data-testid="mentor-mistakes">
          <div className="print-block-head">आम गलतियाँ</div>
          {m.mistakes.map((x) => (
            <div key={x.misconception_id} data-testid={`mistake-${x.misconception_id}`}>
              {x.skill_id} “{x.name_hi}”: {x.children} बच्चे{x.activity ? <> → गतिविधि: “{x.activity.title_hi}”</> : ''}
            </div>
          ))}
        </section>
      )}

      <hr />
      <div className="print-footer" data-testid="mentor-rules">
        नियम: एक ही कौशल {R.stuck_days}+ दिन = बात करने लायक · {R.not_checked_days} दिन से कोई नतीजा नहीं = “नहीं जाँचे” (कक्षा के {Math.round(R.not_checked_share * 100)}% या ज़्यादा हों तो बिंदु) ·
        जाँचकर निर्णय {Math.round(R.evidence_share * 100)}% से कम हों तो बिंदु · पहला अनुमान {Math.round(R.match_share * 100)}% से कम बार मेल खाए (कम से कम {R.match_min} तुलना) तो बिंदु
      </div>
      <div className="print-footer" data-testid="mentor-footer">🌱 अंकुर साथी · {m.period.end} · सिर्फ़ गिनती और रोल नंबर, कोई नाम नहीं</div>
    </div>
  );
}
