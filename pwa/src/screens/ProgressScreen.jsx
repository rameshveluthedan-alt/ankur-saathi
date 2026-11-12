import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { getProgressDashboard } from '../services/api';
import Bi from '../components/Bi';
import { localToday } from '../services/today';
import { TodayCard, ChildToday, LookAtChildren } from '../components/ProgressToday';
import AbbrKey from '../components/AbbrKey';

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
  // opened from a save on the Review ("प्रगति टैब पर … देखें →"): the way back to it, where the review was left (services/reviewPlace.js)
  const location = useLocation();
  const navigate = useNavigate();
  const back = location.state && location.state.from === 'review' ? (
    <button type="button" className="btn btn-secondary btn-small" data-testid="back-to-review" onClick={() => navigate('/review')} style={{ marginBottom: 8 }}>
      ← <Bi hi="समीक्षा पर लौटें" en="Back to the review" inline />
    </button>
  ) : null;

  useEffect(() => {
    setLoading(true);
    getProgressDashboard(teacher.teacher_id, localToday())      // "today" is the phone's date, the same date the Review saved under
      .then(d => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [teacher.teacher_id]);

  if (loading) return <div className="screen">{back}<div className="loading"><div className="spinner" /><span><Bi hi="प्रगति लोड हो रही..." en="Loading progress" inline /></span></div></div>;
  if (!data) return <div className="screen">{back}<div className="empty-state"><div className="empty-icon">📊</div><p><Bi hi="डेटा उपलब्ध नहीं" en="No data available" inline /></p></div></div>;

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
      {back}
      <div className="screen-header">
        <h1>📊 <Bi hi="कक्षा की प्रगति" en="Class progress" inline /></h1>
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
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }} className="hi">{BPP[level].hi}</div>
              <div className="en" lang="en">{BPP[level].en}</div>
            </div>
          ))}
        </div>
      </div>

      {/* What was recorded TODAY in this subject: one card, a row per group */}
      <TodayCard today={data.today && data.today[selectedDomain]} />
      <AbbrKey testid="abbr-progress" />

      {/* Daily work that no longer matches a child's level. A flag changes NOTHING: a level changes only through an assessment. */}
      <LookAtChildren flags={domainFlags} nameOf={nameOf} />

      {/* Children list */}
      <h2 style={{ margin: '12px 0 8px' }}>👥 <Bi hi="बच्चों की प्रगति" en="Children's progress" inline /> — {children.length}</h2>
      {children.map(c => {
        const bpp = selectedDomain === 'numeracy' ? c.numeracy_bpp : c.literacy_bpp;
        const compId = selectedDomain === 'numeracy' ? c.numeracy_competency_id : c.literacy_competency_id;
        const compName = selectedDomain === 'numeracy' ? c.numeracy_competency_name_hi : c.literacy_competency_name_hi;
        return (
          <div key={c.roll_number} className="card" style={{ padding: 10, cursor: 'pointer' }}
            onClick={() => setSelectedChild(selectedChild === c.roll_number ? null : c.roll_number)}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong style={{ fontSize: '1rem' }}><Bi hi="रोल" en="Roll" inline /> {c.roll_number}{nameOf(c.roll_number)}</strong>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginLeft: 6 }}>
                  <Bi hi="कक्षा" en="Grade" inline /> {c.enrolled_grade === 'grade_1' ? '1' : c.enrolled_grade === 'grade_2' ? '2' : '3'}
                </span>
                {asOf(c) && <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginLeft: 6 }} data-testid={`as-of-${c.roll_number}`} title="level as of">· <Bi hi="स्तर" en="level as of" inline />: {asOf(c)}</span>}
              </div>
              <span className={`badge badge-${bpp || 'beginner'}`}>
                {BPP[bpp] ? <span className="hi">{BPP[bpp].hi}</span> : '—'}{BPP[bpp] && <span className="en en-inline" lang="en" style={{ fontSize: '0.625rem' }}>{BPP[bpp].en}</span>}
              </span>
            </div>
            {/* what was recorded for this child today, if anything; the level above stays what it was */}
            <ChildToday today={selectedDomain === 'numeracy' ? c.numeracy_today : c.literacy_today} />
            {selectedChild === c.roll_number && (
              <div style={{ marginTop: 8, fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
                <div><Bi hi="लक्ष्य" en="Target skill" inline />: <strong>{compId}</strong></div>
                <div>{compName}</div>
                <div style={{ marginTop: 4 }}>
                  <Bi hi="गणित" en="Num" inline />: <span className={`badge badge-${c.numeracy_bpp || 'beginner'}`}>{BPP[c.numeracy_bpp] ? <Bi hi={BPP[c.numeracy_bpp].hi} en={BPP[c.numeracy_bpp].en} inline /> : '—'}</span>
                  {' · '}
                  <Bi hi="हिंदी" en="Lit" inline />: <span className={`badge badge-${c.literacy_bpp || 'beginner'}`}>{BPP[c.literacy_bpp] ? <Bi hi={BPP[c.literacy_bpp].hi} en={BPP[c.literacy_bpp].en} inline /> : '—'}</span>
                </div>
              </div>
            )}
          </div>
        );
      })}

      {/* the reports, at the foot (in the header they pushed the title onto two lines): the two pages to read first (the teacher's own, then the officer's); the CSV files are data */}
      <div className="card" data-testid="reports" style={{ marginTop: 16 }}>
        <div style={{ fontWeight: 700, marginBottom: 6 }}>📄 <Bi hi="रिपोर्ट" en="Reports" inline /></div>
        <button type="button" className="btn btn-secondary" data-testid="open-class" onClick={() => navigate('/progress/class')} style={{ flexDirection: 'column', gap: 0 }}>
          <Bi hi="📋 कक्षा सारांश (आपके लिए)" en="Class summary (for you)" />
        </button>
        <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: '4px 0 8px' }}>
          <Bi hi="पिछले 4 हफ़्ते: क्या पढ़ाया, किन बच्चों पर ध्यान दें, अगला कदम। नामों के साथ।" en="The last 4 weeks: what was taught, the children to look at, the next step. With names." inline />
        </p>
        <button type="button" className="btn btn-secondary" data-testid="open-mentor" onClick={() => navigate('/progress/mentor')} style={{ flexDirection: 'column', gap: 0 }}>
          <Bi hi="💬 मेंटर रिपोर्ट (अधिकारी की विज़िट के लिए)" en="Mentor report (for an officer's visit)" />
        </button>
        <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: '4px 0 8px' }}>
          <Bi hi="पिछले 4 हफ़्ते: बातचीत के बिंदु, पढ़ाने का तरीका, बच्चों की प्रगति। सिर्फ़ रोल नंबर, कोई नाम नहीं।" en="The last 4 weeks: talking points, how you teach, the children's progress. Roll numbers only, no names." inline />
        </p>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}><Bi hi="डेटा तालिका (CSV के रूप में डाउनलोड भी):" en="Data table (also downloadable as CSV):" inline /></div>
        <button type="button" data-testid="class-report" onClick={() => navigate('/report', { state: { kind: 'class' } })}
          style={{ display: 'block', background: 'none', border: 'none', padding: '4px 0', minHeight: 36, fontSize: '0.75rem', color: 'var(--green-dark)', fontFamily: 'inherit', textAlign: 'left' }}>
          📥 <span className="hi">कक्षा रिपोर्ट, नामों के साथ</span><span className="en en-inline" lang="en" style={{ color: 'inherit' }}>Class report, with names</span>
        </button>
        <button type="button" data-testid="mlo-report" onClick={() => navigate('/report', { state: { kind: 'officer' } })}
          style={{ display: 'block', background: 'none', border: 'none', padding: '4px 0', minHeight: 36, fontSize: '0.75rem', color: 'var(--green-dark)', fontFamily: 'inherit', textAlign: 'left' }}>
          📥 <span className="hi">अधिकारी डेटा, सिर्फ़ रोल नंबर</span><span className="en en-inline" lang="en">Officer data, roll numbers only</span>
        </button>
      </div>

      <div style={{ height: 80 }} />
    </div>
  );
}
