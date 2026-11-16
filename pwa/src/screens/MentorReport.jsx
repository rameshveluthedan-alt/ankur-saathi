import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { getMentorSummary } from '../services/api';
import { GROUP_LABELS, GROUP_ORDER } from '../tiers';
import { localToday } from '../services/today';
import { backOrHome } from '../services/backHistory';
import { hiDate, enDate, classLine, classLineEn, CODE_NOTE, CODE_NOTE_EN, MARKS_NOTE, MARKS_NOTE_EN } from '../services/printFormat';
import Bi from '../components/Bi';

/**
 * The mentor report (29 Oct, at /progress/mentor): one printable page for a block or cluster officer's visit, over the last 4 weeks (the server's
 * GET /progress/mentor). The talking points come first (one strength, up to two things to work on, one question), then how the teacher works, then how
 * the children moved, then the most common mistakes with an activity. How the teacher works comes BEFORE the children's levels: classes start from
 * different places, and the visit is for mentoring, not inspection. Counts and roll numbers, never a name. The rules behind the points are
 * printed at the foot, so an officer can see where each point comes from.
 * The wording and the rule values: reviewed by Vaishnavi on 29 Oct (docs/HINDI_REVIEW_29OCT_REVIEWED_291026.csv).
 * In English too since 16 Nov: every line is a Hindi and an English span (components/Bi.jsx), so the हिं / EN setting decides what shows and prints;
 * the server sends the talking points in both languages.
 */
const SUBJECT = { numeracy: 'गणित', r1_literacy: 'हिंदी' };
const SUBJECT_EN = { numeracy: 'Maths', r1_literacy: 'Hindi' };
const TITLE = 'मेंटर रिपोर्ट';
const groupsLine = (sizes) => GROUP_ORDER.filter((g) => sizes && sizes[g] != null).map((g) => `${GROUP_LABELS[g].mark} ${sizes[g]}`).join(' · ');
const pl = (n, one, many) => `${n} ${n === 1 ? one : many}`;             // English: 1 day, 2 days
const T = (hi, en) => <Bi hi={hi} en={en} inline />;

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
      <button type="button" className="btn btn-secondary btn-small" data-testid="mentor-back" onClick={() => backOrHome(navigate, '/progress')}>← {T('वापस', 'Back')}</button>
      {m && <button type="button" className="btn btn-primary btn-small" data-testid="mentor-print" onClick={() => window.print()}>🖨️ {T('प्रिंट करें', 'Print')}</button>}
    </div>
  );
  if (m === undefined) return <div className="screen">{bar}<div className="loading"><div className="spinner" /></div></div>;
  if (!m) return <div className="screen">{bar}<p data-testid="mentor-failed">{T('रिपोर्ट नहीं खुल सकी। इंटरनेट जाँचकर फिर कोशिश करें।', 'The report could not be opened. Check the internet and try again.')}</p></div>;

  const { practice: p, progress: g, points, rules: R } = m;
  const weeks = Math.round(m.period.days / 7);
  const code = teacher.employee_code || '';
  const place = m.school ? [m.school.school_code, [m.school.block, m.school.district].filter(Boolean).join(', ')].filter(Boolean).join(' · ') : (teacher.school_code || '');
  const subjects = Object.keys(SUBJECT).filter((d) => g.groups && g.groups[d]);
  const notChecked = g.not_checked.length;

  return (
    <div className="screen plan-print mentor-report" data-testid="mentor-report">
      {bar}
      <div className="print-title" data-testid="mentor-title">{T([TITLE, place, code && `शिक्षक ${code}`, classLine(teacher.enrolled_grades)].filter(Boolean).join(' · '),
        ['Mentor report', place, code && `Teacher ${code}`, classLineEn(teacher.enrolled_grades)].filter(Boolean).join(' · '))}</div>
      <div data-testid="mentor-period">{T(`अवधि: ${hiDate(m.period.start)} – ${hiDate(m.period.end)} (पिछले ${weeks} हफ़्ते)`,
        `Period: ${enDate(m.period.start)} – ${enDate(m.period.end)} (the last ${weeks} weeks)`)}</div>
      <hr />

      <section className="mentor-points" data-testid="mentor-points">
        <div className="print-block-head">💬 {T('बातचीत के बिंदु', 'Talking points')}</div>
        {points.strength
          ? <div data-testid="point-strength">👍 {T(points.strength, points.strength_en)}</div>
          : <div data-testid="point-nothing">{T('इस अवधि में कोई योजना नहीं बनी।', 'No plan was made in this period.')}</div>}
        {points.work.map((w, i) => <div key={i} data-testid={`point-work-${w.kind}`}>🎯 {T(w.hi, w.en)}</div>)}
        <div data-testid="point-question">❓ {T(points.question, points.question_en)}</div>
      </section>

      <section data-testid="mentor-practice">
        <div className="print-block-head">{T('पढ़ाने का तरीका', 'How the teacher works')}</div>
        <div>{T(<>योजना बनी: <b>{p.plan_days}</b> दिन · आकलन पूरा (अगली कक्षा का निर्णय दर्ज): <b>{p.review_days}</b> दिन</>,
          <>Plans made: <b>{p.plan_days}</b> {p.plan_days === 1 ? 'day' : 'days'} · Assessment completed (the next class's decision recorded): <b>{p.review_days}</b> {p.review_days === 1 ? 'day' : 'days'}</>)}</div>
        <div>{T(<>बच्चों का काम जाँचकर निर्णय: <b>{p.groups_taught}</b> में से <b>{p.groups_checked}</b> बार</>,
          <>Decisions after checking the children's work: <b>{p.groups_checked}</b> of <b>{p.groups_taught}</b> times</>)}</div>
      </section>

      <section data-testid="mentor-progress">
        <div className="print-block-head">{T('बच्चों की प्रगति', "Children's progress")}</div>
        {subjects.map((d) => {
          const at = g.groups[d];
          return (
            <div key={d} data-testid={`progress-groups-${d}`}>
              {T(`${SUBJECT[d]}, समूह: ${hiDate(at.start_date)} को ${groupsLine(at.start)} → ${hiDate(at.end_date)} को ${groupsLine(at.end)}`,
                `${SUBJECT_EN[d]}, groups: on ${enDate(at.start_date)} ${groupsLine(at.start)} → on ${enDate(at.end_date)} ${groupsLine(at.end)}`)}
            </div>
          );
        })}
        <div>{T(<>कौशल हासिल किए: <b>{g.skills_achieved}</b> (कक्षा में {g.class_size} बच्चे)</>,
          <>Skills achieved: <b>{g.skills_achieved}</b> ({g.class_size} children in the class)</>)}</div>
        {g.stuck.length > 0 && (
          <div data-testid="progress-stuck">{T(`${R.stuck_days}+ दिन एक ही कौशल: ${g.stuck.map((s) => `${GROUP_LABELS[s.level]?.mark || ''} ${GROUP_LABELS[s.level]?.hi || s.level} ${s.skill_id} (${s.days} दिन)`).join(' · ')}`,
            `The same skill on ${R.stuck_days}+ days: ${g.stuck.map((s) => `${GROUP_LABELS[s.level]?.mark || ''} ${GROUP_LABELS[s.level]?.en || s.level} ${s.skill_id} (${pl(s.days, 'day', 'days')})`).join(' · ')}`)}</div>
        )}
        <div data-testid="progress-not-checked">{T(`${Math.round(R.not_checked_days / 7)} हफ़्ते से नहीं जाँचे: ${notChecked ? `${notChecked} बच्चे (रोल ${g.not_checked.join(', ')})` : 'कोई नहीं'}`,
          `Not checked for ${Math.round(R.not_checked_days / 7)} weeks: ${notChecked ? `${pl(notChecked, 'child', 'children')} (roll ${g.not_checked.join(', ')})` : 'none'}`)}</div>
      </section>

      {/* results by skill taught (15 Nov): the children's newest result in the period, as counts; and how many it was taught to have none yet */}
      {(g.skill_results || []).length > 0 && (
        <section data-testid="mentor-skill-results">
          <div className="print-block-head">{T('कौशल के नतीजे', 'Results by skill')}</div>
          {g.skill_results.map((k) => (
            <div key={`${k.domain_id}-${k.skill_id}`} data-testid={`skill-result-${k.skill_id}`}>
              {T(<>{k.skill_id}{k.skill_name_hi ? ` ${k.skill_name_hi}` : ''}: A {k.a} · PA {k.pa} · NA {k.na} · अभी नहीं जाँचे {k.not_checked}</>,
                <>{k.skill_id}{(k.skill_name_en || k.skill_name_hi) ? ` ${k.skill_name_en || k.skill_name_hi}` : ''}: A {k.a} · PA {k.pa} · NA {k.na} · not checked yet {k.not_checked}</>)}
            </div>
          ))}
        </section>
      )}

      {m.mistakes.length > 0 && (
        <section data-testid="mentor-mistakes">
          <div className="print-block-head">{T('आम गलतियाँ', 'Common mistakes')}</div>
          {m.mistakes.map((x) => (
            <div key={x.misconception_id} data-testid={`mistake-${x.misconception_id}`}>
              {T(`${x.skill_id} “${x.name_hi}”: ${x.children} बच्चे${x.activity ? ` → गतिविधि: “${x.activity.title_hi}”` : ''}`,
                `${x.skill_id} “${x.name_en || x.name_hi}”: ${pl(x.children, 'child', 'children')}${x.activity ? ` → activity: “${x.activity.title_en || x.activity.title_hi}”` : ''}`)}
            </div>
          ))}
        </section>
      )}

      <hr />
      <div className="print-footer" data-testid="mentor-rules">
        {T(<>नियम: एक ही कौशल {R.stuck_days}+ दिन = बात करने लायक · {R.not_checked_days} दिन से कोई नतीजा नहीं = “नहीं जाँचे” (कक्षा के {Math.round(R.not_checked_share * 100)}% या ज़्यादा हों तो बिंदु) ·
          जाँचकर निर्णय {Math.round(R.evidence_share * 100)}% से कम हों तो बिंदु (कम से कम {R.evidence_min} समूह)</>,
        <>Rules: the same skill on {R.stuck_days}+ days = worth talking about · no result for {R.not_checked_days} days = “not checked” (a point if {Math.round(R.not_checked_share * 100)}% of the class or more) ·
          a point if under {Math.round(R.evidence_share * 100)}% of decisions follow a check (at least {R.evidence_min} groups)</>)}
      </div>
      <div className="print-footer" data-testid="mentor-key">{T(`${MARKS_NOTE} · ${CODE_NOTE}`, `${MARKS_NOTE_EN} · ${CODE_NOTE_EN}`)}</div>
      <div className="print-footer" data-testid="mentor-footer">{T(`🌱 अंकुर साथी · ${m.period.end} · सिर्फ़ गिनती और रोल नंबर, कोई नाम नहीं`,
        `🌱 Ankur Saathi · ${m.period.end} · Counts and roll numbers only, no names`)}</div>
    </div>
  );
}
