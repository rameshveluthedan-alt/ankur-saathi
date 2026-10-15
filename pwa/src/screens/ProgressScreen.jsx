import React, { useState, useEffect } from 'react';
import { useAuth } from '../App';
import { getProgressDashboard, applyLevelChange, exportMLOCsv } from '../services/api';

const BPP = {
  beginner: { hi: 'शुरुआती', en: 'Beginner', color: 'var(--beginner)' },
  progressor: { hi: 'प्रगतिशील', en: 'Progressor', color: 'var(--progressor)' },
  proficient: { hi: 'दक्ष', en: 'Proficient', color: 'var(--proficient)' },
};

export default function ProgressScreen() {
  const { teacher, selectedDomain, setSelectedDomain } = useAuth();
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

  const { bpp_summary, children, level_change_recommendations } = data;
  const ds = bpp_summary.find(s => s.domain_id === selectedDomain) || { beginner_count: 0, progressor_count: 0, proficient_count: 0 };
  const total = ds.beginner_count + ds.progressor_count + ds.proficient_count;
  const domainRecs = level_change_recommendations?.[selectedDomain] || [];

  const handleLevelChange = async (rec) => {
    try {
      await applyLevelChange(teacher.teacher_id, rec.child_id, selectedDomain, rec.to_level);
      const d = await getProgressDashboard(teacher.teacher_id);
      setData(d);
    } catch (e) { alert('Error: ' + e.message); }
  };

  return (
    <div className="screen">
      <div className="screen-header">
        <h1>📊 प्रगति <span style={{fontSize:'0.75rem',color:'var(--text-secondary)',fontWeight:400}}>Progress</span></h1>
        <a href={exportMLOCsv(teacher.teacher_id)} download
          style={{ fontSize: '0.75rem', color: 'var(--green-dark)', textDecoration: 'none' }}>
          📥 CSV (MLO Report)
        </a>
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

      {/* Level changes */}
      {domainRecs.length > 0 && (
        <>
          <h2 style={{ margin: '12px 0 8px' }}>⬆⬇ स्तर परिवर्तन सुझाव (Level Change Recommendations)</h2>
          {domainRecs.map((rec, i) => (
            <div key={i} className="card" style={{ borderLeft: `4px solid ${rec.direction === 'up' ? 'var(--proficient)' : 'var(--beginner)'}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <strong>Roll {rec.roll_number}</strong>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginLeft: 8 }}>
                    {rec.consecutive_days} दिन (days)
                  </span>
                </div>
                <div>
                  <span className={`badge badge-${rec.from_level}`}>{BPP[rec.from_level]?.hi}</span>
                  <span style={{ margin: '0 4px' }}>→</span>
                  <span className={`badge badge-${rec.to_level}`}>{BPP[rec.to_level]?.hi}</span>
                </div>
              </div>
              <p style={{ fontSize: '0.8125rem', margin: '6px 0', color: 'var(--text-secondary)' }}>{rec.evidence_hi}</p>
              <div style={{ display: 'flex', gap: 8 }}>
                <button className="btn btn-primary btn-small" onClick={() => handleLevelChange(rec)}>✓ स्वीकार (Accept)</button>
                <button className="btn btn-secondary btn-small" onClick={() => {}}>✗ बाद में (Later)</button>
              </div>
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
                <strong style={{ fontSize: '1rem' }}>Roll {c.roll_number}</strong>
                <span style={{ fontSize: '0.6875rem', color: 'var(--text-light)', marginLeft: 6 }}>
                  {c.enrolled_grade === 'grade_1' ? 'कक्षा 1 (Gr1)' : c.enrolled_grade === 'grade_2' ? 'कक्षा 2 (Gr2)' : 'कक्षा 3 (Gr3)'}
                </span>
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
