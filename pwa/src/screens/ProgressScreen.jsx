import React, { useState, useEffect } from 'react';
import { useAuth } from '../App';
import { getProgressDashboard, downloadClassReport, downloadOfficerReport } from '../services/api';
import Bi from '../components/Bi';
import { notify } from '../services/notify';
import { localToday } from '../services/today';
import { TodayCard, ChildToday, LookAtChildren } from '../components/ProgressToday';

const BPP = {
  beginner: { hi: 'शुरुआती', en: 'Beginner', color: 'var(--beginner-ink)' },
  progressor: { hi: 'प्रगतिशील', en: 'Progressor', color: 'var(--progressor-ink)' },
  proficient: { hi: 'दक्ष', en: 'Proficient', color: 'var(--proficient-ink)' },
};

export default function ProgressScreen() {
  const { teacher, selectedDomain, setSelectedDomain, names } = useAuth();
  const nameOf = (roll) => (names && names[roll]) ? ` · ${names[roll]}` : '';
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedChild, setSelectedChild] = useState(null);

  useEffect(() => {
    setLoading(true);
    getProgressDashboard(teacher.teacher_id, localToday())      // "today" is the phone's date, the same date the Review saved under
      .then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [teacher.teacher_id]);

  if (loading) return <div className="screen"><div className="loading"><div className="spinner" /><span><Bi hi="प्रगति लोड हो रही..." en="Loading progress" inline /></span></div></div>;
  if (!data) return <div className="screen"><div className="empty-state"><div className="empty-icon">📊</div><p><Bi hi="डेटा उपलब्ध नहीं" en="No data available" inline /></p></div></div>;

  const { bpp_summary, children, reassessment_flags } = data;
  const ds = bpp_summary.find(s => s.domain_id === selectedDomain) || { beginner_count: 0, progressor_count: 0, proficient_count: 0 };
  const total = ds.beginner_count + ds.progressor_count + ds.proficient_count;
  const domainFlags = reassessment_flags?.[selectedDomain] || [];
  // when a child's level was last set (registration, baseline or a periodic round)
  const asOf = (c) => {
    const v = selectedDomain === 'numeracy' ? c.numeracy_level_as_of : c.literacy_level_as_of;
    return v ? new Date(v).toLocaleDateString('hi-IN', { day: 'numeric', month: 'short' }) : '';
  };

  return (
    <div className="screen">
      <div className="screen-header">
        <h1>📊 <Bi hi="प्रगति" en="Progress" inline /></h1>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 2 }}>
          <button type="button" data-testid="class-report" onClick={() => downloadClassReport(teacher.teacher_id).catch(e => notify(e.message, 'error'))}
            style={{ background: 'none', border: 'none', padding: '4px 0', minHeight: 36, fontSize: '0.75rem', color: 'var(--green-dark)', fontFamily: 'inherit', textAlign: 'right' }}>
            📥 कक्षा रिपोर्ट, नामों के साथ<span className="en en-inline" lang="en" style={{ color: 'inherit' }}>Class report</span>
          </button>
          <button type="button" data-testid="mlo-report" onClick={() => downloadOfficerReport(teacher.teacher_id).catch(e => notify(e.message, 'error'))}
            style={{ background: 'none', border: 'none', padding: '4px 0', minHeight: 36, fontSize: '0.75rem', color: 'var(--text-secondary)', fontFamily: 'inherit', textAlign: 'right' }}>
            📥 अधिकारी रिपोर्ट, सिर्फ़ रोल नंबर<span className="en en-inline" lang="en">Officer report</span>
          </button>
        </div>
      </div>

      <div className="domain-tabs">
        <button className={`domain-tab ${selectedDomain === 'numeracy' ? 'active' : ''}`}
          onClick={() => setSelectedDomain('numeracy')}><Bi hi="गणित" en="Numeracy" inline /></button>
        <button className={`domain-tab ${selectedDomain === 'r1_literacy' ? 'active' : ''}`}
          onClick={() => setSelectedDomain('r1_literacy')}><Bi hi="हिंदी" en="Literacy" inline /></button>
      </div>

      {/* B/P/P bar */}
      <div className="card">
        <div style={{ display: 'flex', height: 24, borderRadius: 12, overflow: 'hidden', marginBottom: 12 }}>
          {total > 0 && <>
            <div style={{ width: `${ds.beginner_count / total * 100}%`, background: 'var(--beginner)', transition: 'width 0.3s' }} />
            <div style={{ width: `${ds.progressor_count / total * 100}%`, background: 'var(--progressor)', transition: 'width 0.3s' }} />
            <div style={{ width: `${ds.proficient_count / total * 100}%`, background: 'var(--proficient)', transition: 'width 0.3s' }} />
          </>}
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-around', textAlign: 'center' }}>
          {['beginner', 'progressor', 'proficient'].map(level => (
            <div key={level}>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: BPP[level].color }}>{ds[`${level}_count`]}</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{BPP[level].hi}</div>
              <div className="en" lang="en">{BPP[level].en}</div>
            </div>
          ))}
        </div>
      </div>

      {/* What was recorded TODAY in this subject: one card, a row per group */}
      <TodayCard today={data.today && data.today[selectedDomain]} />

      {/* Daily work that no longer matches a child's level. A flag changes NOTHING: a level changes only through an assessment. */}
      <LookAtChildren flags={domainFlags} nameOf={nameOf} />

      {/* Children list */}
      <h2 style={{ margin: '12px 0 8px' }}>👥 बच्चों की प्रगति<span className="en en-inline" lang="en">Children Progress</span> — {children.length}</h2>
      {children.map(c => {
        const bpp = selectedDomain === 'numeracy' ? c.numeracy_bpp : c.literacy_bpp;
        const compId = selectedDomain === 'numeracy' ? c.numeracy_competency_id : c.literacy_competency_id;
        const compName = selectedDomain === 'numeracy' ? c.numeracy_competency_name_hi : c.literacy_competency_name_hi;
        return (
          <div key={c.roll_number} className="card" style={{ padding: 10, cursor: 'pointer' }}
            onClick={() => setSelectedChild(selectedChild === c.roll_number ? null : c.roll_number)}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong style={{ fontSize: '1rem' }}>रोल {c.roll_number}{nameOf(c.roll_number)}</strong>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginLeft: 6 }}>
                  {c.enrolled_grade === 'grade_1' ? 'कक्षा 1' : c.enrolled_grade === 'grade_2' ? 'कक्षा 2' : 'कक्षा 3'}
                </span>
                {asOf(c) && <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginLeft: 6 }} data-testid={`as-of-${c.roll_number}`} title="level as of">· स्तर: {asOf(c)}</span>}
              </div>
              <span className={`badge badge-${bpp || 'beginner'}`}>
                {BPP[bpp]?.hi || '—'}{BPP[bpp] && <span className="en en-inline" lang="en" style={{ fontSize: '0.625rem' }}>{BPP[bpp].en}</span>}
              </span>
            </div>
            {/* what was recorded for this child today, if anything; the level above stays what it was */}
            <ChildToday today={selectedDomain === 'numeracy' ? c.numeracy_today : c.literacy_today} />
            {selectedChild === c.roll_number && (
              <div style={{ marginTop: 8, fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                <div>लक्ष्य<span className="en en-inline" lang="en">Lakshya</span>: <strong>{compId}</strong></div>
                <div>{compName}</div>
                <div style={{ marginTop: 4 }}>
                  गणित<span className="en en-inline" lang="en">Num</span>: <span className={`badge badge-${c.numeracy_bpp || 'beginner'}`}>{BPP[c.numeracy_bpp]?.hi || '—'}</span>
                  {' · '}
                  हिंदी<span className="en en-inline" lang="en">Lit</span>: <span className={`badge badge-${c.literacy_bpp || 'beginner'}`}>{BPP[c.literacy_bpp]?.hi || '—'}</span>
                </div>
              </div>
            )}
          </div>
        );
      })}

      <div style={{ height: 80 }} />
    </div>
  );
}
