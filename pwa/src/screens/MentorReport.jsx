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

      {/* 16 Nov: tables, and labels that say what is counted ("0 days completed" next to "5 of 12 checked" read as a contradiction) */}
      <section data-testid="mentor-practice">
        <div className="print-block-head">{T('पढ़ाने का तरीका', 'How the teacher works')}</div>
        <table className="where-table sum-table">
          <tbody>
            <tr data-testid="practice-plans"><td className="text-cell">{T('योजना बनी (दिन)', 'Days with a plan')}</td><td className="num-cell"><b>{p.plan_days}</b></td></tr>
            <tr data-testid="practice-decided"><td className="text-cell">{T('हर समूह के लिए अगली कक्षा का निर्णय दर्ज (दिन)', "Days with a next-class decision for every group")}</td>
              <td className="num-cell"><b>{p.review_days}</b> {T(`/ ${p.plan_days}`, `of ${p.plan_days}`)}</td></tr>
            <tr data-testid="practice-checked"><td className="text-cell">{T('समूह-पाठ जिनमें बच्चों का काम जाँचा गया', "Group lessons where children's work was checked")}</td>
              <td className="num-cell"><b>{p.groups_checked}</b> {T(`/ ${p.groups_taught}`, `of ${p.groups_taught}`)}</td></tr>
          </tbody>
        </table>
      </section>

      <section data-testid="mentor-progress">
        <div className="print-block-head">{T('बच्चों की प्रगति', "Children's progress")}</div>
        {subjects.map((d) => {
          const at = g.groups[d];
          return (
            <div key={d} data-testid={`progress-groups-${d}`} style={{ marginBottom: 4 }}>
              {T(`${SUBJECT[d]}: समूहों में बच्चे`, `${SUBJECT_EN[d]}: children in each group`)}
              <table className="where-table sum-table">
                <thead><tr><th>{T('समूह', 'Group')}</th><th>{T(hiDate(at.start_date), enDate(at.start_date))}</th><th>{T(hiDate(at.end_date), enDate(at.end_date))}</th></tr></thead>
                <tbody>{GROUP_ORDER.filter((l) => (at.start || {})[l] != null || (at.end || {})[l] != null).map((l) => (
                  <tr key={l}><td>{GROUP_LABELS[l].mark} {T(GROUP_LABELS[l].hi, GROUP_LABELS[l].en)}</td><td>{(at.start || {})[l] ?? '–'}</td><td>{(at.end || {})[l] ?? '–'}</td></tr>
                ))}</tbody>
              </table>
            </div>
          );
        })}
        {/* an achieved RESULT (a child x a skill marked A), not a skill: "18 skills achieved" read as 18 skills */}
        <div data-testid="progress-achieved">{T(<>हासिल (A) नतीजे: <b>{g.skills_achieved}</b> · कक्षा में {g.class_size} बच्चे</>,
          <>Achieved results (A): <b>{g.skills_achieved}</b> · {g.class_size} children in the class</>)}</div>
        {g.stuck.length > 0 && (
          <div data-testid="progress-stuck">{T(`${R.stuck_days}+ दिन एक ही कौशल: ${g.stuck.map((s) => `${GROUP_LABELS[s.level]?.mark || ''} ${GROUP_LABELS[s.level]?.hi || s.level} ${s.skill_id} (${s.days} दिन)`).join(' · ')}`,
            `The same skill on ${R.stuck_days}+ days: ${g.stuck.map((s) => `${GROUP_LABELS[s.level]?.mark || ''} ${GROUP_LABELS[s.level]?.en || s.level} ${s.skill_id} (${pl(s.days, 'day', 'days')})`).join(' · ')}`)}</div>
        )}
        {/* the size of it, for an officer; the roll numbers only when there are a few */}
        <div data-testid="progress-not-checked">{T(`${Math.round(R.not_checked_days / 7)} हफ़्ते से नहीं जाँचे: ${notChecked ? `${g.class_size} में से ${notChecked} बच्चे${notChecked <= 8 ? ` (रोल ${g.not_checked.join(', ')})` : ''}` : 'कोई नहीं'}`,
          `Not checked for ${Math.round(R.not_checked_days / 7)} weeks: ${notChecked ? `${notChecked} of ${pl(g.class_size, 'child', 'children')}${notChecked <= 8 ? ` (roll ${g.not_checked.join(', ')})` : ''}` : 'none'}`)}</div>
      </section>

      {/* results by skill taught (15 Nov): the children's newest result in the period, as counts; and how many it was taught to have none yet */}
      {(g.skill_results || []).length > 0 && (
        <section data-testid="mentor-skill-results">
          <div className="print-block-head">{T('कौशल के नतीजे', 'Results by skill')}</div>
          <table className="where-table sum-table">
            <thead><tr><th className="skill-cell">{T('कौशल', 'Skill')}</th><th>A</th><th>PA</th><th>NA</th><th>{T('अभी नहीं जाँचे', 'Not checked yet')}</th></tr></thead>
            <tbody>{g.skill_results.map((k) => (
              <tr key={`${k.domain_id}-${k.skill_id}`} data-testid={`skill-result-${k.skill_id}`}>
                <td className="skill-cell">{T(`${k.skill_id}${k.skill_name_hi ? ` ${k.skill_name_hi}` : ''}`, `${k.skill_id}${(k.skill_name_en || k.skill_name_hi) ? ` ${k.skill_name_en || k.skill_name_hi}` : ''}`)}</td>
                <td>{k.a}</td><td>{k.pa}</td><td>{k.na}</td><td>{k.not_checked}</td>
              </tr>
            ))}</tbody>
          </table>
        </section>
      )}

      {m.mistakes.length > 0 && (
        <section data-testid="mentor-mistakes">
          <div className="print-block-head">{T('आम गलतियाँ', 'Common mistakes')}</div>
          <table className="where-table sum-table">
            <thead><tr><th className="text-cell">{T('गलती', 'Mistake')}</th><th>{T('बच्चे', 'Children')}</th><th className="text-cell">{T('सुझाई गई गतिविधि', 'Suggested activity')}</th></tr></thead>
            <tbody>{m.mistakes.map((x) => (
              <tr key={x.misconception_id} data-testid={`mistake-${x.misconception_id}`}>
                <td className="text-cell">{T(`${x.skill_id} “${x.name_hi}”`, `${x.skill_id} “${x.name_en || x.name_hi}”`)}</td>
                <td>{x.children}</td>
                <td className="text-cell">{x.activity ? T(x.activity.title_hi, x.activity.title_en || x.activity.title_hi) : '–'}</td>
              </tr>
            ))}</tbody>
          </table>
        </section>
      )}

      <hr />
      {/* 16 Nov: the rules say what they are for (how the talking points are chosen); a readable date */}
      <div className="print-footer" data-testid="mentor-rules">
        {T(<>बातचीत के बिंदु कैसे चुने जाते हैं: कोई समूह {R.stuck_days} या ज़्यादा दिन एक ही कौशल पर · कक्षा के {Math.round(R.not_checked_share * 100)}% या ज़्यादा बच्चों का {R.not_checked_days} दिन से कोई नतीजा नहीं ·
          {Math.round(R.evidence_share * 100)}% से कम समूह-पाठों में निर्णय से पहले बच्चों का काम जाँचा गया (कम से कम {R.evidence_min} समूह-पाठ)</>,
        <>How the talking points are chosen: a group on the same skill for {R.stuck_days} or more days · {Math.round(R.not_checked_share * 100)}% or more of the class with no result in {R.not_checked_days} days ·
          under {Math.round(R.evidence_share * 100)}% of group lessons checked before deciding (at least {R.evidence_min} lessons)</>)}
      </div>
      <div className="print-footer" data-testid="mentor-key">{T(`${MARKS_NOTE} · ${CODE_NOTE}`, `${MARKS_NOTE_EN} · ${CODE_NOTE_EN}`)}</div>
      <div className="print-footer" data-testid="mentor-footer">{T(`🌱 अंकुर साथी · ${hiDate(m.period.end)} · सिर्फ़ गिनती और रोल नंबर, कोई नाम नहीं`,
        `🌱 Ankur Saathi · ${enDate(m.period.end)} · Counts and roll numbers only, no names`)}</div>
    </div>
  );
}
