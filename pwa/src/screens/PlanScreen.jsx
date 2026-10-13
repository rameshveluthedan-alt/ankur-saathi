import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { getCompetencies, getGroups, generatePlan } from '../services/api';

const GRADE_LABELS = { balvatika: 'BV', grade_1: 'G1', grade_2: 'G2', grade_3: 'G3' };
const GRADE_ORDER = ['balvatika', 'grade_1', 'grade_2', 'grade_3'];

export default function PlanScreen() {
  const { teacher, selectedDomain, setSelectedDomain, setCurrentPlan } = useAuth();
  const navigate = useNavigate();

  const [competencies, setCompetencies] = useState([]);
  const [groups, setGroups] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [gradeFilter, setGradeFilter] = useState(null);

  // Load competencies when domain changes
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

  const today = new Date().toISOString().split('T')[0];

  const handleGenerate = async () => {
    if (!selectedId) return;
    setGenerating(true);
    try {
      const plan = await generatePlan(teacher.teacher_id, selectedId, selectedDomain, today);
      setCurrentPlan(plan);
      navigate('/yojana');
    } catch (e) {
      alert('योजना बनाने में समस्या: ' + e.message);
    }
    setGenerating(false);
  };

  const filtered = gradeFilter
    ? competencies.filter(c => c.grade_level === gradeFilter)
    : competencies;

  // Group competencies by grade
  const grouped = {};
  filtered.forEach(c => {
    if (!grouped[c.grade_level]) grouped[c.grade_level] = [];
    grouped[c.grade_level].push(c);
  });

  return (
    <div className="screen">
      <div className="screen-header">
        <h1>🎯 योजना बनाएँ</h1>
      </div>

      {/* Domain selector */}
      <div className="domain-tabs">
        <button className={`domain-tab ${selectedDomain === 'numeracy' ? 'active' : ''}`}
          onClick={() => setSelectedDomain('numeracy')}>
          गणित
        </button>
        <button className={`domain-tab ${selectedDomain === 'r1_literacy' ? 'active' : ''}`}
          onClick={() => setSelectedDomain('r1_literacy')}>
          हिंदी
        </button>
      </div>

      {/* Current groups summary */}
      {groups.length > 0 && (
        <div className="card" style={{ padding: 12 }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: 6 }}>
            वर्तमान समूह
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {groups.map(g => (
              <div key={g.label} style={{ flex: 1, textAlign: 'center' }}>
                <span className={`badge badge-${g.label}`}>
                  {g.label === 'beginner' ? 'शुरुआती' : g.label === 'progressor' ? 'प्रगतिशील' : 'दक्ष'}
                </span>
                <div style={{ fontSize: '1.25rem', fontWeight: 700, marginTop: 4 }}>{g.count}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Grade filter */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 12, flexWrap: 'wrap' }}>
        <button
          className={`btn-small ${!gradeFilter ? 'btn-primary' : 'btn-secondary'}`}
          style={{ padding: '4px 10px', fontSize: '0.75rem', borderRadius: 6, border: '1px solid var(--border)', background: !gradeFilter ? 'var(--green-dark)' : 'var(--surface)', color: !gradeFilter ? 'white' : 'var(--text)', cursor: 'pointer', fontFamily: 'inherit' }}
          onClick={() => setGradeFilter(null)}
        >सभी</button>
        {GRADE_ORDER.map(g => (
          <button key={g}
            style={{ padding: '4px 10px', fontSize: '0.75rem', borderRadius: 6, border: '1px solid var(--border)', background: gradeFilter === g ? 'var(--green-dark)' : 'var(--surface)', color: gradeFilter === g ? 'white' : 'var(--text)', cursor: 'pointer', fontFamily: 'inherit' }}
            onClick={() => setGradeFilter(g)}
          >{GRADE_LABELS[g]}</button>
        ))}
      </div>

      {/* Competency list */}
      {loading ? (
        <div className="loading"><div className="spinner" /><span>लक्ष्य लोड हो रहे हैं...</span></div>
      ) : (
        <div>
          {GRADE_ORDER.filter(g => grouped[g]).map(grade => (
            <div key={grade}>
              <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', padding: '8px 0 4px', textTransform: 'uppercase' }}>
                {GRADE_LABELS[grade]} — {grade === 'balvatika' ? 'बालवाटिका' : `कक्षा ${grade.split('_')[1]}`}
              </div>
              {grouped[grade].map(c => (
                <div
                  key={c.id}
                  className={`competency-item ${selectedId === c.id ? 'recommended' : ''}`}
                  onClick={() => setSelectedId(c.id)}
                >
                  <span className="competency-id">{c.id}</span>
                  <span className="competency-name">{c.name_hi || c.name_en}</span>
                  <span className="grade-tag">
                    {c.assessment_modality === 'observed' ? '✓' : c.assessment_modality === 'oral_reading' ? '🎤' : '📝'}
                  </span>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}

      {/* Generate button — fixed at bottom */}
      {selectedId && (
        <div style={{ position: 'fixed', bottom: 'calc(var(--nav-height) + var(--safe-bottom) + 8px)', left: 16, right: 16, maxWidth: 448, margin: '0 auto' }}>
          <button className="btn btn-primary" onClick={handleGenerate} disabled={generating}>
            {generating ? (
              <><div className="spinner" style={{ width: 20, height: 20, borderWidth: 2 }} /> योजना बन रही है...</>
            ) : (
              <>📋 दैनिक योजना बनाएँ → {selectedId}</>
            )}
          </button>
        </div>
      )}
    </div>
  );
}
