import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { getCompetencies, getGroups, generatePlan } from '../services/api';

const GRADE_LABELS = { balvatika: 'BV', grade_1: 'G1', grade_2: 'G2', grade_3: 'G3' };
const GRADE_LABELS_HI = { balvatika: 'बालवाटिका', grade_1: 'कक्षा 1', grade_2: 'कक्षा 2', grade_3: 'कक्षा 3' };
const GRADE_ORDER = ['balvatika', 'grade_1', 'grade_2', 'grade_3'];
// Generating a plan takes about a minute (measured: 59-82 s). Tell the teacher, and reassure if it runs long.
const SLOW_AFTER_S = 100;

// How much of the knowledge base stands behind a skill (see docs/COVERAGE.md)
const TIERS = {
  tested:       { icon: '✔', hi: 'परखा हुआ', en: 'Tested', color: '#1B6B43', bg: '#E4F4EA',
                  what: 'Passed every automatic check with the real AI, using an exact anchor from the bank.' },
  ai_written:   { icon: '◐', hi: 'AI-लिखित सामग्री', en: 'AI-written content', color: '#8A5A00', bg: '#FFF1CC',
                  what: 'The plan works, but part of it (the opening activity or the passage) is adapted or written by the AI, so it is less validated.' },
  experimental: { icon: '⚠', hi: 'प्रयोगात्मक', en: 'Experimental', color: '#A12A1E', bg: '#FCE4E1',
                  what: 'It failed in testing or the checks still flag problems. Expect to edit it.' },
  untested:     { icon: '○', hi: 'अभी परखा नहीं', en: 'Not yet tested', color: '#555', bg: '#EDEDED',
                  what: 'Not yet run through the real AI.' },
};
const TIER_ORDER = ['tested', 'ai_written', 'experimental', 'untested'];
const fmtClock = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
const GROUP_LABELS = {
  beginner: { hi: 'शुरुआती', en: 'Beginner' },
  progressor: { hi: 'प्रगतिशील', en: 'Progressor' },
  proficient: { hi: 'दक्ष', en: 'Proficient' },
};

export default function PlanScreen() {
  const { teacher, selectedDomain, setSelectedDomain, setCurrentPlan } = useAuth();
  const navigate = useNavigate();
  const [competencies, setCompetencies] = useState([]);
  const [groups, setGroups] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [gradeFilter, setGradeFilter] = useState(null);

  useEffect(() => {
    setLoading(true);
    setSelectedId(null);
    Promise.all([
      getCompetencies(selectedDomain),
      getGroups(teacher.teacher_id, selectedDomain),
    ]).then(([compData, groupData]) => {
      setCompetencies(compData.competencies || []);
      setGroups(groupData.groups || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [selectedDomain, teacher.teacher_id]);

  // running timer while a plan is being generated (counts from the real clock, so a throttled tab stays accurate)
  useEffect(() => {
    if (!generating) { setElapsed(0); return undefined; }
    const start = Date.now();
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - start) / 1000)), 1000);
    return () => clearInterval(id);
  }, [generating]);

  const today = new Date().toISOString().split('T')[0];

  const handleGenerate = async () => {
    if (!selectedId) return;
    setGenerating(true);
    try {
      const plan = await generatePlan(teacher.teacher_id, selectedId, selectedDomain, today);
      setCurrentPlan(plan);
      navigate('/yojana');
    } catch (e) {
      alert('योजना बनाने में समस्या (Plan generation error): ' + e.message);
    }
    setGenerating(false);
  };

  const tierCounts = {};
  competencies.forEach(c => { const t = c.coverage_tier || 'untested'; tierCounts[t] = (tierCounts[t] || 0) + 1; });
  const selectedSkill = competencies.find(c => c.id === selectedId);
  const selectedTier = selectedSkill ? (selectedSkill.coverage_tier || 'untested') : null;

  const filtered = gradeFilter ? competencies.filter(c => c.grade_level === gradeFilter) : competencies;
  const grouped = {};
  filtered.forEach(c => { if (!grouped[c.grade_level]) grouped[c.grade_level] = []; grouped[c.grade_level].push(c); });

  return (
    <div className="screen">
      <div className="screen-header">
        <h1>🎯 योजना बनाएँ <span style={{fontSize:'0.75rem',color:'var(--text-secondary)',fontWeight:400}}>Select Lakshya</span></h1>
      </div>

      <div className="domain-tabs">
        <button className={`domain-tab ${selectedDomain === 'numeracy' ? 'active' : ''}`}
          onClick={() => setSelectedDomain('numeracy')}>गणित (Numeracy)</button>
        <button className={`domain-tab ${selectedDomain === 'r1_literacy' ? 'active' : ''}`}
          onClick={() => setSelectedDomain('r1_literacy')}>हिंदी (Literacy)</button>
      </div>

      {groups.length > 0 && (
        <div className="card" style={{ padding: 12 }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: 6 }}>वर्तमान समूह (Current Groups)</div>
          <div style={{ display: 'flex', gap: 8 }}>
            {groups.map(g => (
              <div key={g.label} style={{ flex: 1, textAlign: 'center' }}>
                <span className={`badge badge-${g.label}`}>{GROUP_LABELS[g.label]?.hi}</span>
                <div style={{ fontSize: '0.6rem', color: 'var(--text-light)' }}>{GROUP_LABELS[g.label]?.en}</div>
                <div style={{ fontSize: '1.25rem', fontWeight: 700, marginTop: 4 }}>{g.count}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {!loading && competencies.length > 0 && (
        <div className="card" style={{ padding: 12 }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: 6 }}>
            ज्ञान-आधार कवरेज (Knowledge-base coverage): हर कौशल के लिए योजना बनती है; लेबल बताता है कि उसके पीछे कितनी जाँची हुई सामग्री है।
          </div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {TIER_ORDER.filter(t => tierCounts[t]).map(t => (
              <span key={t} style={{ background: TIERS[t].bg, color: TIERS[t].color, borderRadius: 10, padding: '2px 8px', fontSize: '0.7rem', fontWeight: 600 }}>
                {TIERS[t].icon} {TIERS[t].hi} ({TIERS[t].en}) · {tierCounts[t]}
              </span>
            ))}
          </div>
          <details style={{ marginTop: 6 }}>
            <summary style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>इन लेबलों का मतलब (What the labels mean)</summary>
            {TIER_ORDER.map(t => (
              <div key={t} style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: 4 }}>
                <b style={{ color: TIERS[t].color }}>{TIERS[t].icon} {TIERS[t].en}</b>: {TIERS[t].what}
              </div>
            ))}
          </details>
        </div>
      )}

      <div style={{ display: 'flex', gap: 4, marginBottom: 12, flexWrap: 'wrap' }}>
        <button style={{ padding: '4px 10px', fontSize: '0.75rem', borderRadius: 6, border: '1px solid var(--border)', background: !gradeFilter ? 'var(--green-dark)' : 'var(--surface)', color: !gradeFilter ? 'white' : 'var(--text)', cursor: 'pointer', fontFamily: 'inherit' }}
          onClick={() => setGradeFilter(null)}>सभी (All)</button>
        {GRADE_ORDER.map(g => (
          <button key={g} style={{ padding: '4px 10px', fontSize: '0.75rem', borderRadius: 6, border: '1px solid var(--border)', background: gradeFilter === g ? 'var(--green-dark)' : 'var(--surface)', color: gradeFilter === g ? 'white' : 'var(--text)', cursor: 'pointer', fontFamily: 'inherit' }}
            onClick={() => setGradeFilter(g)}>{GRADE_LABELS[g]}</button>
        ))}
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /><span>लक्ष्य लोड हो रहे हैं (Loading competencies)...</span></div>
      ) : (
        <div>
          {GRADE_ORDER.filter(g => grouped[g]).map(grade => (
            <div key={grade}>
              <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', padding: '8px 0 4px' }}>
                {GRADE_LABELS[grade]} — {GRADE_LABELS_HI[grade]}
              </div>
              {grouped[grade].map(c => (
                <div key={c.id} className={`competency-item ${selectedId === c.id ? 'recommended' : ''}`}
                  onClick={() => setSelectedId(c.id)}>
                  <span className="competency-id">{c.id}</span>
                  <span className="competency-name">
                    {c.name_hi || c.name_en}
                    {c.name_hi && <span style={{display:'block',fontSize:'0.7rem',color:'var(--text-light)'}}>{c.name_en}</span>}
                    {(() => { const T = TIERS[c.coverage_tier || 'untested']; return (
                      <span title={c.coverage_note || T.what} style={{ display: 'inline-block', marginTop: 3, background: T.bg, color: T.color, borderRadius: 8, padding: '1px 7px', fontSize: '0.62rem', fontWeight: 600 }}>
                        {T.icon} {T.hi}
                      </span>); })()}
                  </span>
                  <span className="grade-tag">
                    {c.assessment_modality === 'observed' ? '✓' : c.assessment_modality === 'oral_reading' ? '🎤' : '📝'}
                  </span>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}

      {selectedId && (
        <div style={{ position: 'fixed', bottom: 'calc(var(--nav-height) + var(--safe-bottom) + 8px)', left: 16, right: 16, maxWidth: 448, margin: '0 auto',
                      background: 'var(--bg)', borderRadius: 12, padding: 6, boxShadow: '0 -2px 10px rgba(0,0,0,0.08)' }}>
          {!generating && selectedTier && selectedTier !== 'tested' && (
            <div style={{ fontSize: '0.7rem', textAlign: 'center', background: TIERS[selectedTier].bg, color: TIERS[selectedTier].color, borderRadius: 8, padding: '4px 8px', marginBottom: 6 }}>
              {TIERS[selectedTier].icon} {TIERS[selectedTier].hi}: {selectedSkill.coverage_note || TIERS[selectedTier].what}
            </div>
          )}
          {generating && (
            <div style={{ fontSize: '0.75rem', textAlign: 'center', background: 'var(--green-bg)', borderRadius: 8, padding: '6px 10px', marginBottom: 6, color: 'var(--text-secondary)' }}>
              {elapsed < SLOW_AFTER_S
                ? 'लगभग 1–1.5 मिनट लगते हैं। कृपया इस पेज को खुला रखें। (Takes about 1–1.5 minutes. Please keep this page open.)'
                : 'थोड़ा और समय लग रहा है, कृपया प्रतीक्षा करें। (Taking a little longer. Please keep waiting.)'}
            </div>
          )}
          <button className="btn btn-primary" onClick={handleGenerate} disabled={generating}
            style={generating ? { opacity: 1, cursor: 'wait' } : undefined}>
            {generating ? (
              <><div className="spinner" style={{ width: 20, height: 20, borderWidth: 2 }} /> योजना बन रही है (Generating)... {fmtClock(elapsed)}</>
            ) : (
              <>📋 दैनिक योजना बनाएँ (Generate Plan) → {selectedId}</>
            )}
          </button>
        </div>
      )}
    </div>
  );
}
