import React, { useState, useEffect } from 'react';
import { useAuth } from '../App';
import { getProgressDashboard, downloadClassReport, downloadOfficerReport } from '../services/api';

const BPP = {
  beginner: { hi: 'शुरुआती', en: 'Beginner', color: 'var(--beginner)' },
  progressor: { hi: 'प्रगतिशील', en: 'Progressor', color: 'var(--progressor)' },
  proficient: { hi: 'दक्ष', en: 'Proficient', color: 'var(--proficient)' },
};

export default function ProgressScreen() {
  const { teacher, selectedDomain, setSelectedDomain, names } = useAuth();
  const nameOf = (roll) => (names && names[roll]) ? ` · ${names[roll]}` : '';
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedChild, setSelectedChild] = useState(null);

  useEffect(() => {
    setLoading(true);
    getProgressDashboard(teacher.teacher_id)
      .then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [teacher.teacher_id]);

  if (loading) return <div className="screen"><div className="loading"><div className="spinner" /><span>प्रगति लोड हो रही (Loading progress)...</span></div></div>;
  if (!data) return <div className="screen"><div className="empty-state"><div className="empty-icon">📊</div><p>डेटा उपलब्ध नहीं (No data available)</p></div></div>;

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
        <h1>📊 प्रगति <span style={{fontSize:'0.75rem',color:'var(--text-secondary)',fontWeight:400}}>Progress</span></h1>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 2 }}>
          <button type="button" data-testid="class-report" onClick={() => downloadClassReport(teacher.teacher_id).catch(e => alert(e.message))}
            style={{ background: 'none', border: 'none', padding: 0, fontSize: '0.75rem', color: 'var(--green-dark)', fontFamily: 'inherit' }}>
            📥 कक्षा रिपोर्ट, नामों के साथ (Class report)
          </button>
          <button type="button" data-testid="mlo-report" onClick={() => downloadOfficerReport(teacher.teacher_id).catch(e => alert(e.message))}
            style={{ background: 'none', border: 'none', padding: 0, fontSize: '0.65rem', color: 'var(--text-secondary)', fontFamily: 'inherit' }}>
            📥 अधिकारी रिपोर्ट, सिर्फ़ रोल नंबर (Officer report)
          </button>
        </div>
      </div>

      <div className="domain-tabs">
        <button className={`domain-tab ${selectedDomain === 'numeracy' ? 'active' : ''}`}
          onClick={() => setSelectedDomain('numeracy')}>गणित (Numeracy)</button>
        <button className={`domain-tab ${selectedDomain === 'r1_literacy' ? 'active' : ''}`}
          onClick={() => setSelectedDomain('r1_literacy')}>हिंदी (Literacy)</button>
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
              <div style={{ fontSize: '0.6rem', color: 'var(--text-light)' }}>{BPP[level].en}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Daily work that no longer matches a child's level. A flag changes NOTHING: a level changes only through an assessment. */}
      {domainFlags.length > 0 && (
        <>
          <h2 style={{ margin: '12px 0 4px' }}>🔎 दोबारा आकलन पर विचार करें (Consider re-assessing)</h2>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: '0 0 8px' }}>
            स्तर सिर्फ़ आकलन से बदलता है। इन बच्चों का आकलन पहले करना ठीक रहेगा। (Levels change only through an assessment. These children are worth assessing first.)
          </p>
          {domainFlags.map(f => (
            <div key={f.child_id} className="card" data-testid={`flag-${f.direction}`}
              style={{ borderLeft: `4px solid ${f.direction === 'higher' ? 'var(--proficient)' : '#C9A227'}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <strong>Roll {f.roll_number}{nameOf(f.roll_number)}</strong>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: f.direction === 'higher' ? 'var(--proficient)' : '#8A5A00' }}>
                  {f.direction === 'higher' ? '⬆ अच्छा प्रदर्शन (Doing well)' : '⬇ कठिनाई (Struggling)'}
                </span>
              </div>
              <p style={{ fontSize: '0.8125rem', margin: '6px 0 0', color: 'var(--text-secondary)' }}>{f.evidence_hi}</p>
            </div>
          ))}
        </>
      )}

      {/* Children list */}
      <h2 style={{ margin: '12px 0 8px' }}>👥 बच्चों की प्रगति (Children Progress) — {children.length}</h2>
      {children.map(c => {
        const bpp = selectedDomain === 'numeracy' ? c.numeracy_bpp : c.literacy_bpp;
        const compId = selectedDomain === 'numeracy' ? c.numeracy_competency_id : c.literacy_competency_id;
        const compName = selectedDomain === 'numeracy' ? c.numeracy_competency_name_hi : c.literacy_competency_name_hi;
        return (
          <div key={c.roll_number} className="card" style={{ padding: 10, cursor: 'pointer' }}
            onClick={() => setSelectedChild(selectedChild === c.roll_number ? null : c.roll_number)}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong style={{ fontSize: '1rem' }}>Roll {c.roll_number}{nameOf(c.roll_number)}</strong>
                <span style={{ fontSize: '0.6875rem', color: 'var(--text-light)', marginLeft: 6 }}>
                  {c.enrolled_grade === 'grade_1' ? 'कक्षा 1 (Gr1)' : c.enrolled_grade === 'grade_2' ? 'कक्षा 2 (Gr2)' : 'कक्षा 3 (Gr3)'}
                </span>
                {asOf(c) && <span style={{ fontSize: '0.625rem', color: 'var(--text-light)', marginLeft: 6 }} data-testid={`as-of-${c.roll_number}`} title="level as of">· स्तर: {asOf(c)}</span>}
              </div>
              <span className={`badge badge-${bpp || 'beginner'}`}>
                {BPP[bpp]?.hi || '—'} <span style={{fontSize:'0.55rem'}}>({BPP[bpp]?.en || '—'})</span>
              </span>
            </div>
            {selectedChild === c.roll_number && (
              <div style={{ marginTop: 8, fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                <div>लक्ष्य (Lakshya): <strong>{compId}</strong></div>
                <div>{compName}</div>
                <div style={{ marginTop: 4 }}>
                  गणित (Num): <span className={`badge badge-${c.numeracy_bpp || 'beginner'}`} style={{ fontSize: '0.55rem' }}>{BPP[c.numeracy_bpp]?.en || '—'}</span>
                  {' · '}
                  हिंदी (Lit): <span className={`badge badge-${c.literacy_bpp || 'beginner'}`} style={{ fontSize: '0.55rem' }}>{BPP[c.literacy_bpp]?.en || '—'}</span>
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
