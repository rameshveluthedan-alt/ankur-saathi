import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { backOrHome } from '../services/backHistory';
import { useAuth } from '../App';
import { previewRegister, commitRegister, downloadRegisterTemplate } from '../services/api';
import Bi from '../components/Bi';

const GRADE_HI = { balvatika: 'बालवाटिका', grade_1: 'कक्षा 1', grade_2: 'कक्षा 2', grade_3: 'कक्षा 3' };
const LEVEL_HI = { beginner: 'शुरुआती', progressor: 'प्रगतिशील', proficient: 'दक्ष' };

// Enrol a class from a register file: choose the file, see exactly what would happen, then confirm.
export default function RegisterScreen() {
  const { teacher, setTeacher, refreshNames } = useAuth();
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [done, setDone] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const choose = async (e) => {
    const f = e.target.files && e.target.files[0];
    e.target.value = '';
    if (!f) return;
    setFile(f); setPreview(null); setDone(null); setError(''); setLoading(true);
    try { setPreview(await previewRegister(teacher.teacher_id, f)); }
    catch (err) { setError(err.message); }
    setLoading(false);
  };

  const confirm = async () => {
    setLoading(true); setError('');
    try {
      const res = await commitRegister(teacher.teacher_id, file.name, preview.raw_rows);
      setDone(res); setPreview(null);
      setTeacher({ ...teacher, total_children: res.total_children, enrolled_grades: res.enrolled_grades });
      refreshNames();
    } catch (err) { setError(err.message); }
    setLoading(false);
  };

  const bad = preview ? preview.rows.filter(r => r.status === 'error') : [];
  const gradeSummary = preview ? Object.entries(preview.by_grade).map(([g, n]) => `${GRADE_HI[g] || g}: ${n}`).join(' · ') : '';

  return (
    <div className="screen">
      <div className="screen-header">
        <h1>👥 <Bi hi="कक्षा रजिस्टर" en="Class register" inline /></h1>
        {/* back to the screen the teacher came from (navigation F), the Plan screen if the app was opened here */}
        <button type="button" className="btn btn-secondary btn-small" data-testid="register-back" onClick={() => backOrHome(navigate)}>← <Bi hi="वापस" en="Back" inline /></button>
      </div>

      <div className="card">
        <p style={{ fontSize: '0.875rem', marginBottom: 8 }}>
          अपनी कक्षा के बच्चों की सूची अपलोड करें: कक्षा और रोल नंबर, और चाहें तो हर विषय का शुरुआती स्तर। <b>नाम वैकल्पिक हैं:</b> वे सिर्फ़ आपको दिखेंगे, AI को कभी नहीं भेजे जाएँगे।
        </p>
        <p className="en" lang="en" style={{ fontSize: '0.75rem', marginBottom: 10 }}>
          Upload your class list: grade and roll number, and optionally the name and each child's starting level per subject. Names stay in this app, visible only to you: they are never sent to the AI and never go into the officer report. CSV is best; Excel works too if the server has it.
        </p>
        <button type="button" className="btn btn-secondary" style={{ display: 'block', width: '100%', textAlign: 'center', marginBottom: 8 }} data-testid="template-link" onClick={() => downloadRegisterTemplate().catch((err) => setError(err.message))}>
          ⬇ <Bi hi="टेम्पलेट डाउनलोड करें" en="Download template" inline />
        </button>
        <label className="btn btn-primary" style={{ display: 'block', textAlign: 'center' }}>
          📂 <Bi hi="फ़ाइल चुनें" en="Choose file" inline />
          <input type="file" accept=".csv,.xlsx,.txt" onChange={choose} style={{ display: 'none' }} data-testid="register-file" />
        </label>
        <p style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: 8 }}>
          अभी आपकी कक्षा में {teacher.total_children || 0} बच्चे हैं।<span className="en en-inline" lang="en">Children in your class now.</span>
        </p>
      </div>

      {loading && <div className="card" style={{ textAlign: 'center' }}><div className="spinner" style={{ margin: '0 auto' }} /> <Bi hi="पढ़ रहे हैं..." en="Reading" inline /></div>}
      {error && <div className="card" style={{ borderLeft: '4px solid var(--beginner)', background: 'var(--beginner-bg)', fontSize: '0.875rem' }} data-testid="register-error">⚠️ {error}</div>}

      {preview && (
        <div className="card" data-testid="register-preview">
          <h3 style={{ marginBottom: 6 }}><Bi hi="पूर्वावलोकन · अभी कुछ दर्ज नहीं हुआ" en="Preview · nothing saved yet" /></h3>
          <div style={{ fontSize: '0.875rem', lineHeight: 1.6 }}>
            ✅ <b>{preview.counts.new}</b> नए बच्चे जुड़ेंगे<span className="en en-inline" lang="en">new children</span> {gradeSummary && <span style={{ color: 'var(--text-secondary)' }}>· {gradeSummary}</span>}<br />
            ↺ <b>{preview.counts.exists}</b> पहले से हैं, छोड़े जाएँगे<span className="en en-inline" lang="en">already enrolled, skipped</span><br />
            {preview.counts.error > 0 && <span>⚠️ <b>{preview.counts.error}</b> पंक्तियों में गलती है, जुड़ेंगी नहीं<span className="en en-inline" lang="en">lines with problems, not added</span></span>}
          </div>
          {preview.names_to_save > 0 && preview.names_available && <p style={{ fontSize: '0.75rem', color: 'var(--proficient)', marginTop: 8 }} data-testid="names-note">🔒 {preview.names_to_save} नाम सहेजे जाएँगे: सिर्फ़ आपको दिखेंगे, AI को कभी नहीं भेजे जाएँगे<span className="en en-inline" lang="en">names kept private, never sent to the AI</span></p>}
          {preview.warnings.map((w, i) => <p key={i} style={{ fontSize: '0.75rem', color: '#8A5A00', background: '#FFF4D6', borderRadius: 8, padding: '6px 10px', marginTop: 8 }}>{w}</p>)}
          {bad.length > 0 && (
            <div style={{ marginTop: 8, fontSize: '0.8125rem' }} data-testid="register-problems">
              {bad.map(r => <div key={r.row} style={{ padding: '3px 0', borderBottom: '1px solid var(--border)' }}>पंक्ति<span className="en en-inline" lang="en">line</span> {r.row}: {r.errors.join('; ')}</div>)}
            </div>
          )}
          <div style={{ marginTop: 10, maxHeight: 190, overflow: 'auto', fontSize: '0.75rem' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead><tr style={{ textAlign: 'left', color: 'var(--text-secondary)' }}><th>कक्षा</th><th>रोल</th><th>कक्षा नं.</th><th>नाम</th><th>गणित</th><th>हिंदी</th></tr></thead>
              <tbody>
                {preview.rows.filter(r => r.status === 'new').slice(0, 40).map(r => (
                  <tr key={r.row} style={{ borderTop: '1px solid var(--border)' }}>
                    <td>{GRADE_HI[r.grade]}</td><td>{r.school_roll}</td><td><b>{r.class_number}</b></td><td>{r.name}</td><td>{LEVEL_HI[r.numeracy_level]}</td><td>{LEVEL_HI[r.literacy_level]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button type="button" className="btn btn-primary" disabled={loading || preview.counts.new === 0} onClick={confirm} style={{ marginTop: 10 }} data-testid="register-confirm">
            ✓ {preview.counts.new} बच्चे जोड़ें<span className="en en-inline" lang="en">Confirm and enrol</span>
          </button>
        </div>
      )}

      {done && (
        <div className="card" style={{ borderLeft: '4px solid var(--proficient)' }} data-testid="register-done">
          <h3>✅ {done.added} बच्चे जुड़ गए<span className="en en-inline" lang="en">children enrolled</span></h3>
          <p style={{ fontSize: '0.8125rem', margin: '6px 0' }}>कक्षा में कुल<span className="en en-inline" lang="en">Total in class</span>: <b>{done.total_children}</b></p>
          {done.names_saved > 0 && <p style={{ fontSize: '0.8125rem' }}>🔒 {done.names_saved} नाम सहेजे गए<span className="en en-inline" lang="en">names saved, private</span></p>}
          {done.numbering === 'composite' && <p style={{ fontSize: '0.8125rem', color: '#8A5A00' }}><Bi hi="कक्षा नंबर में कक्षा शामिल है: कक्षा 3 रोल 5 = 305। बच्चे वर्कशीट पर यही नंबर लिखेंगे।" en="Class numbers carry the grade; children write this number on worksheets." /></p>}
          <button type="button" className="btn btn-primary" onClick={() => navigate('/')} style={{ marginTop: 8 }}><Bi hi="योजना पर जाएँ" en="Go to Plan" inline /></button>
        </div>
      )}
      <div style={{ height: 80 }} />
    </div>
  );
}
