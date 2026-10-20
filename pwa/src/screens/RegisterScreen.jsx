import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { previewRegister, commitRegister, REGISTER_TEMPLATE_URL } from '../services/api';

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
        <h1>👥 कक्षा रजिस्टर <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 400 }}>Class register</span></h1>
        <button type="button" className="btn btn-secondary btn-small" onClick={() => navigate('/')}>← वापस (Back)</button>
      </div>

      <div className="card">
        <p style={{ fontSize: '0.875rem', marginBottom: 8 }}>
          अपनी कक्षा के बच्चों की सूची अपलोड करें: कक्षा और रोल नंबर, और चाहें तो हर विषय का शुरुआती स्तर। <b>नाम वैकल्पिक हैं:</b> वे सिर्फ़ आपको दिखेंगे, AI को कभी नहीं भेजे जाएँगे।
        </p>
        <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: 10 }}>
          Upload your class list: grade and roll number, and optionally the name and each child's starting level per subject. Names stay in this app, visible only to you: they are never sent to the AI and never go into the officer report. CSV is best; Excel works too if the server has it.
        </p>
        <a href={REGISTER_TEMPLATE_URL} className="btn btn-secondary" style={{ display: 'block', textAlign: 'center', marginBottom: 8, textDecoration: 'none' }} data-testid="template-link">
          ⬇ टेम्पलेट डाउनलोड करें (Download template)
        </a>
        <label className="btn btn-primary" style={{ display: 'block', textAlign: 'center' }}>
          📂 फ़ाइल चुनें (Choose file)
          <input type="file" accept=".csv,.xlsx,.txt" onChange={choose} style={{ display: 'none' }} data-testid="register-file" />
        </label>
        <p style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: 8 }}>
          अभी आपकी कक्षा में {teacher.total_children || 0} बच्चे हैं (Children in your class now).
        </p>
      </div>

      {loading && <div className="card" style={{ textAlign: 'center' }}><div className="spinner" style={{ margin: '0 auto' }} /> पढ़ रहे हैं (Reading)...</div>}
      {error && <div className="card" style={{ borderLeft: '4px solid var(--beginner)', background: 'var(--beginner-bg)', fontSize: '0.875rem' }} data-testid="register-error">⚠️ {error}</div>}

      {preview && (
        <div className="card" data-testid="register-preview">
          <h3 style={{ marginBottom: 6 }}>पूर्वावलोकन (Preview) · अभी कुछ दर्ज नहीं हुआ (nothing saved yet)</h3>
          <div style={{ fontSize: '0.875rem', lineHeight: 1.6 }}>
            ✅ <b>{preview.counts.new}</b> नए बच्चे जुड़ेंगे (new children) {gradeSummary && <span style={{ color: 'var(--text-secondary)' }}>· {gradeSummary}</span>}<br />
            ↺ <b>{preview.counts.exists}</b> पहले से हैं, छोड़े जाएँगे (already enrolled, skipped)<br />
            {preview.counts.error > 0 && <span>⚠️ <b>{preview.counts.error}</b> पंक्तियों में गलती है, जुड़ेंगी नहीं (lines with problems, not added)</span>}
          </div>
          {preview.names_to_save > 0 && preview.names_available && <p style={{ fontSize: '0.75rem', color: 'var(--proficient)', marginTop: 8 }} data-testid="names-note">🔒 {preview.names_to_save} नाम सहेजे जाएँगे: सिर्फ़ आपको दिखेंगे, AI को कभी नहीं भेजे जाएँगे (names kept private, never sent to the AI)</p>}
          {preview.warnings.map((w, i) => <p key={i} style={{ fontSize: '0.75rem', color: '#8A5A00', background: '#FFF4D6', borderRadius: 8, padding: '6px 10px', marginTop: 8 }}>{w}</p>)}
          {bad.length > 0 && (
            <div style={{ marginTop: 8, fontSize: '0.8125rem' }} data-testid="register-problems">
              {bad.map(r => <div key={r.row} style={{ padding: '3px 0', borderBottom: '1px solid var(--border)' }}>पंक्ति (line) {r.row}: {r.errors.join('; ')}</div>)}
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
            ✓ {preview.counts.new} बच्चे जोड़ें (Confirm and enrol)
          </button>
        </div>
      )}

      {done && (
        <div className="card" style={{ borderLeft: '4px solid var(--proficient)' }} data-testid="register-done">
          <h3>✅ {done.added} बच्चे जुड़ गए (children enrolled)</h3>
          <p style={{ fontSize: '0.8125rem', margin: '6px 0' }}>कक्षा में कुल (Total in class): <b>{done.total_children}</b></p>
          {done.names_saved > 0 && <p style={{ fontSize: '0.8125rem' }}>🔒 {done.names_saved} नाम सहेजे गए (names saved, private)</p>}
          {done.numbering === 'composite' && <p style={{ fontSize: '0.8125rem', color: '#8A5A00' }}>कक्षा नंबर में कक्षा शामिल है: कक्षा 3 रोल 5 = 305। बच्चे वर्कशीट पर यही नंबर लिखेंगे। (Class numbers carry the grade; children write this number on worksheets.)</p>}
          <button type="button" className="btn btn-primary" onClick={() => navigate('/')} style={{ marginTop: 8 }}>योजना पर जाएँ (Go to Plan)</button>
        </div>
      )}
      <div style={{ height: 80 }} />
    </div>
  );
}
