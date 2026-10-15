import React, { useState, useRef } from 'react';
import { useAuth } from '../App';
import { recordDecisions, recordObserved, recordORF, analysePhotos } from '../services/api';

const GROUP_LABELS = {
  beginner: { hi: 'शुरुआती', en: 'Beginner' },
  progressor: { hi: 'प्रगतिशील', en: 'Progressor' },
  proficient: { hi: 'दक्ष', en: 'Proficient' },
};

export default function ReviewScreen() {
  const { teacher, currentPlan, selectedDomain } = useAuth();
  const [step, setStep] = useState(1);
  const [decisions, setDecisions] = useState({});
  const [channel, setChannel] = useState(null);
  const [photos, setPhotos] = useState([]);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [observedItems, setObservedItems] = useState([]);
  const [orfEntry, setOrfEntry] = useState({ roll_number: '', cwpm: '', error_count: '', passage_id: 'RP-004' });
  const fileInput = useRef(null);

  const today = new Date().toISOString().split('T')[0];
  const groups = currentPlan?.groups || [];

  const handleDecision = (groupLabel, decision) => {
    setDecisions(d => ({ ...d, [groupLabel]: d[groupLabel] === decision ? null : decision }));
  };

  const submitDecisions = async () => {
    setLoading(true);
    try {
      await recordDecisions(teacher.teacher_id, today, selectedDomain, decisions);
      setStep(2);
    } catch (e) { alert('Error: ' + e.message); }
    setLoading(false);
  };

  const handlePhotoCapture = (e) => {
    const files = Array.from(e.target.files);
    setPhotos(prev => [...prev, ...files].slice(0, 6));
  };

  const submitPhotos = async () => {
    if (!photos.length || !currentPlan) return;
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append('teacher_id', teacher.teacher_id);
      fd.append('session_date', today);
      fd.append('domain_id', selectedDomain);
      fd.append('competency_id', currentPlan.selected_competency_id);
      fd.append('worksheet_level', 'progressor');
      fd.append('teacher_pre_judgment', decisions.progressor || '');
      photos.forEach(p => fd.append('photos', p));
      const result = await analysePhotos(teacher.teacher_id, fd);
      setAnalysisResult(result);
      setStep(3);
    } catch (e) { alert('विश्लेषण में समस्या (Analysis error): ' + e.message); }
    setLoading(false);
  };

  const addObservedItem = (rollNumber, competencyId, status) => {
    setObservedItems(prev => [...prev.filter(i => !(i.roll_number === rollNumber && i.competency_id === competencyId)),
      { roll_number: parseInt(rollNumber), competency_id: competencyId, status }
    ]);
  };

  const submitObserved = async () => {
    if (!observedItems.length) return;
    setLoading(true);
    try {
      await recordObserved(teacher.teacher_id, today, observedItems);
      alert(`✅ ${observedItems.length} अवलोकन दर्ज हुए (observations recorded)`);
      setObservedItems([]);
    } catch (e) { alert('Error: ' + e.message); }
    setLoading(false);
  };

  const submitORF = async () => {
    if (!orfEntry.roll_number || !orfEntry.cwpm) return;
    setLoading(true);
    try {
      const result = await recordORF(teacher.teacher_id, {
        session_date: today, roll_number: parseInt(orfEntry.roll_number),
        passage_id: orfEntry.passage_id, cwpm: parseInt(orfEntry.cwpm),
        error_count: parseInt(orfEntry.error_count || 0),
      });
      alert(`✅ Roll ${orfEntry.roll_number}: ${orfEntry.cwpm} CWPM → ${result.classification}`);
      setOrfEntry({ roll_number: '', cwpm: '', error_count: '', passage_id: 'RP-004' });
    } catch (e) { alert('Error: ' + e.message); }
    setLoading(false);
  };

  return (
    <div className="screen">
      <div className="screen-header">
        <h1>📷 समीक्षा <span style={{fontSize:'0.75rem',color:'var(--text-secondary)',fontWeight:400}}>Review</span></h1>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          चरण (Step) {step}/3
        </span>
      </div>

      {/* STEP 1: Decisions */}
      {step === 1 && (
        <>
          <h2 style={{ marginBottom: 4 }}>आज हर समूह कैसा रहा?</h2>
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: 16 }}>
            How did each group do today? Record your judgment before AI analysis.
          </p>

          {groups.map(g => (
            <div key={g.label} className="card">
              <div className="card-header">
                <div>
                  <span className={`badge badge-${g.label}`}>{GROUP_LABELS[g.label]?.hi}</span>
                  <span style={{ fontSize: '0.65rem', color: 'var(--text-light)', marginLeft: 4 }}>{GROUP_LABELS[g.label]?.en}</span>
                </div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{g.count} बच्चे</span>
              </div>
              <div className="decision-row">
                <button className={`decision-btn advance ${decisions[g.label] === 'advance' ? 'selected' : ''}`}
                  onClick={() => handleDecision(g.label, 'advance')}>
                  ▲ आगे बढ़ें<br/><span style={{fontSize:'0.6rem'}}>Advance</span>
                </button>
                <button className={`decision-btn reteach ${decisions[g.label] === 'reteach' ? 'selected' : ''}`}
                  onClick={() => handleDecision(g.label, 'reteach')}>
                  🔄 दोहराएँ<br/><span style={{fontSize:'0.6rem'}}>Re-teach</span>
                </button>
                <button className={`decision-btn ${decisions[g.label] === 'not_sure' ? 'selected' : ''}`}
                  onClick={() => handleDecision(g.label, 'not_sure')}>
                  ❓ पक्का नहीं<br/><span style={{fontSize:'0.6rem'}}>Not sure</span>
                </button>
              </div>
            </div>
          ))}

          <button className="btn btn-primary" onClick={submitDecisions} disabled={loading} style={{ marginTop: 8 }}>
            {loading ? 'दर्ज हो रहा (Recording)...' : 'दर्ज करें → साक्ष्य कैप्चर (Record → Capture Evidence)'}
          </button>
        </>
      )}

      {/* STEP 2: Evidence capture */}
      {step === 2 && (
        <>
          <h2 style={{ marginBottom: 4 }}>साक्ष्य कैप्चर करें</h2>
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: 12 }}>Capture Evidence</p>

          <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            {[
              { id: 'observed', icon: '✓', hi: 'अवलोकन', en: 'Observed' },
              { id: 'photo', icon: '📸', hi: 'फ़ोटो', en: 'Photo' },
              { id: 'orf', icon: '🎤', hi: 'पठन प्रवाह', en: 'ORF' },
            ].map(ch => (
              <button key={ch.id} className={`domain-tab ${channel === ch.id ? 'active' : ''}`}
                onClick={() => setChannel(ch.id)}>
                {ch.icon} {ch.hi}<br/><span style={{fontSize:'0.6rem'}}>{ch.en}</span>
              </button>
            ))}
          </div>

          {/* Observed */}
          {channel === 'observed' && (
            <div className="card">
              <h3 style={{ marginBottom: 4 }}>✓ शिक्षक अवलोकन (Teacher Observation)</h3>
              <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: 12 }}>
                Tap A / PA / NA for each child
              </p>
              <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                <input type="number" placeholder="Roll No." min="1" max="30"
                  style={{ flex: 1, padding: 8, borderRadius: 6, border: '1px solid var(--border)', fontFamily: 'inherit' }} id="obs-roll" />
                <input type="text" placeholder="Comp ID (N1.2.4)"
                  style={{ flex: 1, padding: 8, borderRadius: 6, border: '1px solid var(--border)', fontFamily: 'inherit' }} id="obs-comp" />
              </div>
              <div className="decision-row">
                {[['achieved','✓ A (Achieved)'],['partially_achieved','~ PA (Partial)'],['not_achieved','✗ NA (Not Achieved)']].map(([s,label]) => (
                  <button key={s} className="decision-btn" onClick={() => {
                    const roll = document.getElementById('obs-roll').value;
                    const comp = document.getElementById('obs-comp').value;
                    if (roll && comp) addObservedItem(roll, comp, s);
                  }}>{label}</button>
                ))}
              </div>
              {observedItems.length > 0 && (
                <div style={{ marginTop: 8, fontSize: '0.8125rem' }}>
                  <strong>{observedItems.length} दर्ज (recorded):</strong>{' '}
                  {observedItems.map(i => `R${i.roll_number}:${i.status[0].toUpperCase()}`).join(', ')}
                </div>
              )}
              <button className="btn btn-primary" onClick={submitObserved} disabled={loading || !observedItems.length} style={{ marginTop: 8 }}>
                {loading ? 'दर्ज हो रहा...' : `✓ ${observedItems.length} अवलोकन जमा करें (Submit)`}
              </button>
            </div>
          )}

          {/* Photo */}
          {channel === 'photo' && (
            <div className="card">
              <h3 style={{ marginBottom: 4 }}>📸 वर्कशीट फ़ोटो (Worksheet Photos)</h3>
              <div className="capture-area" onClick={() => fileInput.current?.click()}>
                <div className="capture-icon">📷</div>
                <p>वर्कशीट की फ़ोटो लें या चुनें</p>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-light)' }}>Tap to capture or select (max 6)</p>
                <input ref={fileInput} type="file" accept="image/*" capture="environment"
                  multiple onChange={handlePhotoCapture} style={{ display: 'none' }} />
              </div>
              {photos.length > 0 && (
                <div style={{ marginTop: 8 }}>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {photos.map((p, i) => (
                      <div key={i} style={{ width: 60, height: 60, borderRadius: 8, background: 'var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.75rem' }}>📄 {i + 1}</div>
                    ))}
                  </div>
                  <button className="btn btn-primary" onClick={submitPhotos} disabled={loading} style={{ marginTop: 8 }}>
                    {loading ? (
                      <><div className="spinner" style={{ width: 18, height: 18, borderWidth: 2 }} /> विश्लेषण हो रहा (Analysing)...</>
                    ) : `🔍 ${photos.length} फ़ोटो का विश्लेषण करें (Analyse)`}
                  </button>
                </div>
              )}
            </div>
          )}

          {/* ORF */}
          {channel === 'orf' && (
            <div className="card">
              <h3 style={{ marginBottom: 4 }}>🎤 पठन प्रवाह (Reading Fluency / ORF)</h3>
              <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: 12 }}>
                Stopwatch: count correct words read in 1 minute
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <input type="number" placeholder="Roll No." value={orfEntry.roll_number}
                  onChange={e => setOrfEntry(o => ({ ...o, roll_number: e.target.value }))}
                  style={{ padding: 10, borderRadius: 8, border: '1px solid var(--border)', fontSize: '1rem', fontFamily: 'inherit' }} />
                <input type="number" placeholder="CWPM (सही शब्द/मिनट — Correct Words Per Minute)" value={orfEntry.cwpm}
                  onChange={e => setOrfEntry(o => ({ ...o, cwpm: e.target.value }))}
                  style={{ padding: 10, borderRadius: 8, border: '1px solid var(--border)', fontSize: '1rem', fontFamily: 'inherit' }} />
                <input type="number" placeholder="गलतियाँ (Errors)" value={orfEntry.error_count}
                  onChange={e => setOrfEntry(o => ({ ...o, error_count: e.target.value }))}
                  style={{ padding: 10, borderRadius: 8, border: '1px solid var(--border)', fontSize: '1rem', fontFamily: 'inherit' }} />
              </div>
              <button className="btn btn-primary" onClick={submitORF}
                disabled={loading || !orfEntry.roll_number || !orfEntry.cwpm} style={{ marginTop: 10 }}>
                {loading ? 'दर्ज हो रहा...' : '🎤 ORF दर्ज करें (Record ORF)'}
              </button>
            </div>
          )}

          {!channel && (
            <div className="empty-state">
              <p>ऊपर से साक्ष्य चैनल चुनें (Select evidence channel above)</p>
            </div>
          )}

          <button className="btn btn-secondary" onClick={() => setStep(3)} style={{ marginTop: 12 }}>
            विश्लेषण देखें (View Analysis) →
          </button>
        </>
      )}

      {/* STEP 3: AI Analysis */}
      {step === 3 && (
        <>
          <h2 style={{ marginBottom: 12 }}>🔍 AI विश्लेषण (AI Analysis)</h2>

          {analysisResult ? (
            <>
              <div className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span>विश्लेषित बच्चे (Children analysed)</span>
                  <strong>{analysisResult.children_analysed}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span>समूह शुद्धता (Group accuracy)</span>
                  <strong>{Math.round(analysisResult.group_accuracy * 100)}%</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>AI सुझाव (AI recommendation)</span>
                  <strong style={{ color: analysisResult.ai_recommendation === 'advance' ? 'var(--proficient)' : 'var(--beginner)' }}>
                    {analysisResult.ai_recommendation === 'advance' ? '▲ आगे बढ़ें (Advance)' : '🔄 दोहराएँ (Re-teach)'}
                  </strong>
                </div>
              </div>

              {analysisResult.discrepancy && (
                <div className="card" style={{ borderLeft: '4px solid var(--beginner)', background: 'var(--beginner-bg)' }}>
                  <h3 style={{ color: 'var(--beginner)', marginBottom: 4 }}>⚠️ विसंगति (Discrepancy)</h3>
                  <p style={{ fontSize: '0.875rem' }}>{analysisResult.discrepancy.reason}</p>
                </div>
              )}

              {analysisResult.misconceptions_detected?.length > 0 && (
                <div className="card">
                  <h3 style={{ marginBottom: 8 }}>पाई गई गलतियाँ (Misconceptions Detected)</h3>
                  {analysisResult.misconceptions_detected.map(m => (
                    <div key={m.id} style={{ padding: '6px 0', borderBottom: '1px solid var(--border)', fontSize: '0.875rem' }}>
                      <strong>{m.id}</strong> — {m.total_occurrences} बार (occurrences)
                    </div>
                  ))}
                </div>
              )}

              {analysisResult.per_child?.map(c => (
                <div key={c.roll_number} className="card" style={{ padding: 10 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <strong>Roll {c.roll_number}</strong>
                    <span className={`badge badge-${c.status === 'achieved' ? 'proficient' : c.status === 'partially_achieved' ? 'progressor' : 'beginner'}`}>
                      {c.status === 'achieved' ? 'A' : c.status === 'partially_achieved' ? 'PA' : 'NA'}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    शुद्धता (Accuracy): {Math.round(c.accuracy * 100)}%
                    {c.misconceptions?.length > 0 && ` · गलती (Error): ${c.misconceptions.join(', ')}`}
                  </div>
                </div>
              ))}
            </>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">🔍</div>
              <p>फ़ोटो विश्लेषण के बाद परिणाम यहाँ दिखेंगे</p>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-light)', marginTop: 4 }}>Results will appear after photo analysis</p>
            </div>
          )}

          <button className="btn btn-secondary" onClick={() => { setStep(1); setDecisions({}); setPhotos([]); setAnalysisResult(null); setChannel(null); }}
            style={{ marginTop: 16, marginBottom: 80 }}>
            ← नई समीक्षा शुरू करें (Start new review)
          </button>
        </>
      )}
    </div>
  );
}
