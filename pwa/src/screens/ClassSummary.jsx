import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { getClassSummary } from '../services/api';
import { GROUP_LABELS, GROUP_ORDER } from '../tiers';
import { localToday } from '../services/today';
import { backOrHome } from '../services/backHistory';
import { hiDate, enDate, classLine, classLineEn, CODE_NOTE, CODE_NOTE_EN } from '../services/printFormat';
import { ABBR } from '../services/reviewWays';
import Bi from '../components/Bi';
import { useLang } from '../components/LangSwitch';

/**
 * The class summary (29 Oct, at /progress/class): the teacher's own page for planning next week, over the last 4 weeks (the server's
 * GET /progress/class-summary). Per subject: the class now, what each group was taught and how it went, then the children to look at, the most common
 * mistakes with an activity, and each group's next step. The server sends roll numbers only; the NAMES are added here, from the copy this phone already
 * holds (as on the Review and Progress screens), so the printed page carries names: it says so at its foot.
 * The wording and the rule values: reviewed by Vaishnavi on 29 Oct (docs/HINDI_REVIEW_29OCT_REVIEWED_291026.csv).
 * In English too since 16 Nov: every line is a Hindi and an English span (components/Bi.jsx), so the हिं / EN setting decides what shows and prints.
 */
const SUBJECT = { numeracy: 'गणित', r1_literacy: 'हिंदी' };
const SUBJECT_EN = { numeracy: 'Maths', r1_literacy: 'Hindi' };
const NEXT_WHY = {
  advance: '⬆ आगे बढ़ें', advance_no_next: '⬆ आगे बढ़ें; अगला कौशल नहीं, इसलिए यही फिर', reteach: '🔄 दोहराएँ',
  not_sure: '❓ पक्का नहीं: यही कौशल फिर', recommended: 'कई बच्चों से गलती हुई: यही फिर',
};
const NEXT_WHY_EN = {
  advance: '⬆ Move on', advance_no_next: '⬆ Move on; there is no next skill, so this one again', reteach: '🔄 Teach again',
  not_sure: '❓ Not sure: this skill again', recommended: 'Many children made a mistake: this one again',
};
const groupsLine = (sizes, lang = 'hi') => GROUP_ORDER.filter((g) => sizes && sizes[g] != null).map((g) => `${GROUP_LABELS[g].mark} ${GROUP_LABELS[g][lang]} ${sizes[g]}`).join(' · ');
const G = (l) => `${GROUP_LABELS[l]?.mark || ''} ${GROUP_LABELS[l]?.hi || l}`;
const GE = (l) => `${GROUP_LABELS[l]?.mark || ''} ${GROUP_LABELS[l]?.en || l}`;
const pl = (n, one, many) => `${n} ${n === 1 ? one : many}`;             // English: 1 day, 2 days
const T = (hi, en) => <Bi hi={hi} en={en} inline />;
const skill = (id, hi, en) => [`${id}${hi ? ` ${hi}` : ''}`, `${id}${en || hi ? ` ${en || hi}` : ''}`];

export default function ClassSummary() {
  const { teacher, names } = useAuth();
  const navigate = useNavigate();
  const lang = useLang();
  const [s, setS] = useState(undefined);        // undefined: loading; null: could not load
  // a child as the teacher knows them: the roll number, and the name if this phone holds it
  const kid = (r) => (names && names[r] ? `${r} ${names[r]}` : `रोल ${r}`);
  const kidEn = (r) => (names && names[r] ? `${r} ${names[r]}` : `Roll ${r}`);
  const kids = (rolls) => rolls.map(kid).join(', ');
  const kidsEn = (rolls) => rolls.map(kidEn).join(', ');

  useEffect(() => {
    let cancelled = false;
    getClassSummary(teacher.teacher_id, localToday()).then((x) => { if (!cancelled) setS(x); }).catch(() => { if (!cancelled) setS(null); });
    return () => { cancelled = true; };
  }, [teacher.teacher_id]);
  // printing shows this page alone (no banner, no bottom bar): the printed plan's own rule, "body.print-plan" in index.css
  useEffect(() => { document.body.classList.add('print-plan'); return () => document.body.classList.remove('print-plan'); }, []);

  const bar = (
    <div className="no-print" style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
      <button type="button" className="btn btn-secondary btn-small" data-testid="class-back" onClick={() => backOrHome(navigate, '/progress')}>← {T('वापस', 'Back')}</button>
      {s && <button type="button" className="btn btn-primary btn-small" data-testid="class-print" onClick={() => window.print()}>🖨️ {T('प्रिंट करें', 'Print')}</button>}
    </div>
  );
  if (s === undefined) return <div className="screen">{bar}<div className="loading"><div className="spinner" /></div></div>;
  if (!s) return <div className="screen">{bar}<p data-testid="class-failed">{T('रिपोर्ट नहीं खुल सकी। इंटरनेट जाँचकर फिर कोशिश करें।', 'The report could not be opened. Check the internet and try again.')}</p></div>;

  const R = s.rules;
  const weeks = Math.round(s.period.days / 7);
  const subjects = Object.keys(SUBJECT).filter((d) => s.subjects[d]);
  const anyStuck = subjects.some((d) => s.subjects[d].stuck.length);
  const code = teacher.employee_code || teacher.school_code;

  return (
    <div className="screen plan-print mentor-report class-summary" data-testid="class-summary">
      {bar}
      <div className="print-title" data-testid="class-title">{T(['कक्षा सारांश', code, classLine(teacher.enrolled_grades)].filter(Boolean).join(' · '),
        ['Class summary', code, classLineEn(teacher.enrolled_grades)].filter(Boolean).join(' · '))}</div>
      <div data-testid="class-period">{T(`अवधि: ${hiDate(s.period.start)} – ${hiDate(s.period.end)} (पिछले ${weeks} हफ़्ते)`,
        `Period: ${enDate(s.period.start)} – ${enDate(s.period.end)} (the last ${weeks} weeks)`)}</div>
      <hr />

      {subjects.map((d) => {
        const x = s.subjects[d];
        return (
          <section key={d} data-testid={`class-subject-${d}`}>
            <div className="print-block-head">{T(SUBJECT[d], SUBJECT_EN[d])}</div>
            <div data-testid={`now-${d}`}>{T(<>कक्षा अभी: {groupsLine(x.groups_now)} · हासिल (A) नतीजे: <b>{x.skills_achieved}</b></>,
              <>Class now: {groupsLine(x.groups_now, 'en')} · Achieved results (A): <b>{x.skills_achieved}</b></>)}</div>
            {/* the skills taught as a TABLE (16 Nov): one row per group and skill; the days taught and the decisions recorded, and the days with none */}
            {x.taught.length ? (
              <div style={{ marginTop: 4 }} data-testid={`taught-${d}`}>
                <b>{T('पढ़ाए गए कौशल', 'Skills taught')}</b>
                <table className="where-table sum-table">
                  <thead><tr>
                    <th>{T('समूह', 'Group')}</th><th className="skill-cell">{T('कौशल', 'Skill')}</th><th>{T('पढ़ाए गए दिन', 'Days taught')}</th>
                    <th>⬆ {T('आगे बढ़ें', 'Move on')}</th><th>🔄 {T('दोहराएँ', 'Teach again')}</th><th>❓ {T('पक्का नहीं', 'Not sure')}</th><th>{T('निर्णय नहीं', 'No decision')}</th>
                  </tr></thead>
                  <tbody>{x.taught.map((t) => {
                    const [kh, ke] = skill(t.skill_id, t.skill_name_hi, t.skill_name_en);
                    const f = t.finals || {};
                    const none = Math.max(t.days - (f.advance || 0) - (f.reteach || 0) - (f.not_sure || 0), 0);
                    const n = (v) => (v ? v : '–');
                    return (
                      <tr key={`${t.level}-${t.skill_id}`} data-testid={`taught-${d}-${t.level}-${t.skill_id}`}>
                        <td>{T(G(t.level), GE(t.level))}</td><td className="skill-cell">{T(kh, ke)}</td><td>{t.days}</td>
                        <td>{n(f.advance)}</td><td>{n(f.reteach)}</td><td>{n(f.not_sure)}</td><td>{n(none)}</td>
                      </tr>
                    );
                  })}</tbody>
                </table>
              </div>
            ) : <div data-testid={`taught-none-${d}`}>{T('इस अवधि में कोई योजना नहीं बनी।', 'No plan was made in this period.')}</div>}
            {Object.keys(x.next).length > 0 && (
              <div data-testid={`next-${d}`}>
                <b>{T('अगला कदम:', 'Next step:')}</b> {GROUP_ORDER.filter((l) => x.next[l]).map((l) => {
                  const n = x.next[l];
                  const [kh, ke] = skill(n.skill_id, n.skill_name_hi, n.skill_name_en);
                  return <span key={l} data-testid={`next-${d}-${l}`}>{' '}{n.skill_id
                    ? T(`${G(l)}: ${kh} (${NEXT_WHY[n.reason] || n.reason});`, `${GE(l)}: ${ke} (${NEXT_WHY_EN[n.reason] || n.reason});`)
                    : T(`${G(l)}: पिछले आकलन में निर्णय नहीं; योजना बनाते समय चुनें;`, `${GE(l)}: no decision at the last assessment; choose when planning;`)}</span>;
                })}
              </div>
            )}
            {/* where each child is (15 Nov): the newest result in the period on each skill taught; "–" not checked yet */}
            {x.children && x.children.skills && x.children.skills.length > 0 && (
              <div data-testid={`where-${d}`} style={{ marginTop: 6 }}>
                {T(<><b>हर बच्चा कहाँ है</b> <span style={{ fontWeight: 400, fontSize: '0.85em' }}>(पिछले {weeks} हफ़्तों का सबसे नया नतीजा; – = अभी नहीं जाँचा)</span></>,
                  <><b>Where each child is</b> <span style={{ fontWeight: 400, fontSize: '0.85em' }}>(the newest result in the last {weeks} weeks; – = not checked yet)</span></>)}
                <table className="where-table">
                  <thead><tr><th>{T('बच्चा', 'Child')}</th>{x.children.skills.map((k) => (
                    <th key={k} title={(lang === 'en' && (x.children.skill_names_en || {})[k]) || x.children.skill_names_hi[k] || ''}>{k}</th>))}</tr></thead>
                  <tbody>{x.children.rows.map((r) => (
                    <tr key={r.roll} data-testid={`where-${d}-${r.roll}`}>
                      <td>{T(kid(r.roll), kidEn(r.roll))}</td>
                      {x.children.skills.map((k) => <td key={k} className={`res-${r.results[k] || 'none'}`}>{({ a: 'A', pa: 'PA', na: 'NA' })[r.results[k]] || '–'}</td>)}
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            )}
          </section>
        );
      })}

      <section data-testid="class-look">
        <div className="print-block-head">👀 {T('इन बच्चों पर ध्यान दें', 'Children to look at')}</div>
        {anyStuck && subjects.flatMap((d) => s.subjects[d].stuck.map((st) => (
          <div key={`${d}-${st.level}-${st.skill_id}`} data-testid={`stuck-${st.level}-${st.skill_id}`}>
            {T(`${G(st.level)}, ${st.skill_id} (${st.days} दिन पढ़ाया, अभी हासिल नहीं): ${kids(st.rolls)}`,
              `${GE(st.level)}, ${st.skill_id} (taught on ${pl(st.days, 'day', 'days')}, not achieved yet): ${kidsEn(st.rolls)}`)}
          </div>
        )))}
        <div data-testid="look-not-checked">{T(`${Math.round(R.not_checked_days / 7)} हफ़्ते से नहीं जाँचे: ${s.not_checked.length ? kids(s.not_checked) : 'कोई नहीं'}`,
          `Not checked for ${Math.round(R.not_checked_days / 7)} weeks: ${s.not_checked.length ? kidsEn(s.not_checked) : 'none'}`)}</div>
        <div data-testid="look-na">{T(`${R.na_days}+ दिन “अभी नहीं” (NA): ${s.not_achieved_again.length ? s.not_achieved_again.map((c) => `${kid(c.roll)} (${c.skills.join(', ')})`).join(', ') : 'कोई नहीं'}`,
          `“Not yet” (NA) on ${R.na_days}+ days: ${s.not_achieved_again.length ? s.not_achieved_again.map((c) => `${kidEn(c.roll)} (${c.skills.join(', ')})`).join(', ') : 'none'}`)}</div>
      </section>

      {s.mistakes.length > 0 && (
        <section data-testid="class-mistakes">
          <div className="print-block-head">{T('आम गलतियाँ', 'Common mistakes')}</div>
          {s.mistakes.map((m) => (
            <div key={m.misconception_id} data-testid={`class-mistake-${m.misconception_id}`}>
              {T(`${m.skill_id} “${m.name_hi}”: ${kids(m.rolls)}${m.activity ? ` → गतिविधि: “${m.activity.title_hi}”` : ''}`,
                `${m.skill_id} “${m.name_en || m.name_hi}”: ${kidsEn(m.rolls)}${m.activity ? ` → activity: “${m.activity.title_en || m.activity.title_hi}”` : ''}`)}
            </div>
          ))}
        </section>
      )}

      <hr />
      <div className="print-footer" data-testid="class-rules">
        {T(`नियम: “अभी हासिल नहीं” = समूह को ${R.stuck_days}+ दिन वही कौशल पढ़ाया और बच्चे का सबसे नया नतीजा A नहीं · “नहीं जाँचे” = ${R.not_checked_days} दिन से कोई नतीजा नहीं · NA ${R.na_days} या ज़्यादा दिन`,
          `Rules: “not achieved yet” = the group was taught the same skill on ${R.stuck_days}+ days and the child's newest result is not A · “not checked” = no result for ${R.not_checked_days} days · NA on ${R.na_days} or more days`)}
      </div>
      <div className="print-footer" data-testid="class-key">{T(`${ABBR.hi} · ${CODE_NOTE}`, `${ABBR.en} · ${CODE_NOTE_EN}`)}</div>
      <div className="print-footer" data-testid="class-footer">{T(`🌱 अंकुर साथी · ${s.period.end} · इस पन्ने पर बच्चों के नाम हैं (इसी फ़ोन से): इसे सँभालकर रखें`,
        `🌱 Ankur Saathi · ${s.period.end} · This page shows children's names (from this phone): keep it safe`)}</div>
    </div>
  );
}
