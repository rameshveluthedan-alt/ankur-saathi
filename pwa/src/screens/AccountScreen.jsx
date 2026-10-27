import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { adminSchool, adminTeachers, adminResetPin, adminUnlock, adminRecordConsent } from '../services/api';
import { CONSENT } from '../services/consent';
import { PinChangeForm } from './ChangePinScreen';
import { getHindiOnly, setHindiOnly } from '../services/language';
import Bi from '../components/Bi';

const GRADE_HI = { balvatika: 'बालवाटिका', grade_1: 'कक्षा 1', grade_2: 'कक्षा 2', grade_3: 'कक्षा 3' };

export default function AccountScreen() {
  const { teacher, logout } = useAuth();
  const navigate = useNavigate();
  const isAdmin = teacher.role === 'school_admin';
  const [showPin, setShowPin] = useState(false);
  const [pinDone, setPinDone] = useState(false);
  const [school, setSchool] = useState(null);
  const [teachers, setTeachers] = useState([]);
  const [temp, setTemp] = useState(null);            // a temporary password, shown once
  const [error, setError] = useState('');
  const [hindiOnly, setHindiOnlyState] = useState(getHindiOnly);
  const toggleHindiOnly = (on) => { setHindiOnly(on); setHindiOnlyState(on); };

  const load = () => {
    if (!isAdmin) return;
    adminSchool().then(setSchool).catch(e => setError(e.message));
    adminTeachers().then(d => setTeachers(d.teachers || [])).catch(e => setError(e.message));
  };
  useEffect(load, [isAdmin]);

  const reset = async (t) => {
    if (!window.confirm(`इस शिक्षक (${t.code}) का पासवर्ड रीसेट करें? (Reset the password for ${t.code}?)`)) return;
    setError(''); setTemp(null);
    try { const r = await adminResetPin(t.teacher_id); setTemp({ who: t.code, pin: r.temporary_pin }); load(); }
    catch (e) { setError(e.message); }
  };
  const unlock = async (t) => { setError(''); try { await adminUnlock(t.teacher_id); load(); } catch (e) { setError(e.message); } };
  const confirmConsent = async () => {
    if (!window.confirm(`${CONSENT.hi}\n\n${CONSENT.en}\n\nक्या यह सही है? (Is this correct?)`)) return;
    setError('');
    try { await adminRecordConsent(CONSENT.version); load(); } catch (e) { setError(e.message); }
  };

  return (
    <div className="screen">
      <div className="screen-header">
        <h1>👤 <Bi hi="प्रोफ़ाइल" en="Profile" inline /></h1>
        <button type="button" className="btn btn-secondary btn-small" onClick={() => navigate('/')}>← <Bi hi="वापस" en="Back" inline /></button>
      </div>

      <div className="card" data-testid="account-info">
        {teacher.employee_code && <div style={{ fontSize: '0.875rem' }}>आपका कोड (Your code): <b data-testid="my-code" style={{ letterSpacing: 2 }}>{teacher.employee_code}</b></div>}
        <div style={{ fontSize: '0.875rem', marginTop: 4 }}>स्कूल (School): <b>{teacher.school_code}</b></div>
        <div style={{ fontSize: '0.875rem', marginTop: 4 }}>भूमिका (Role): <b>{isAdmin ? 'स्कूल लीडर (School leader)' : 'शिक्षक (Teacher)'}</b></div>
        <div style={{ fontSize: '0.875rem', marginTop: 4 }}>कक्षाएँ (Grades): {(teacher.enrolled_grades || []).map(g => GRADE_HI[g] || g).join(', ')}</div>
        {teacher.is_demo && <div style={{ fontSize: '0.75rem', color: '#8A5A00', marginTop: 6 }}>डेमो अकाउंट: काल्पनिक डेटा (Demo account: fictional data)</div>}
      </div>

      <div className="card" data-testid="language-card">
        <h3 style={{ marginBottom: 6 }}>🔤 <Bi hi="भाषा" en="Language" inline /></h3>
        <label style={{ display: 'flex', alignItems: 'center', gap: 10, minHeight: 44, fontSize: '0.9375rem', cursor: 'pointer' }}>
          <input type="checkbox" checked={hindiOnly} onChange={(e) => toggleHindiOnly(e.target.checked)} data-testid="hindi-only" />
          <span>सिर्फ़ हिंदी दिखाएँ <span className="en en-inline" lang="en">Hindi only</span></span>
        </label>
        <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 2 }}>
          अंग्रेज़ी अनुवाद छिप जाएँगे; कौशल कोड और रोल नंबर दिखते रहेंगे। यह सेटिंग इसी फ़ोन पर रहती है।
          <span className="en" lang="en">Hides the English translations; skill codes and roll numbers stay. This setting stays on this phone.</span>
        </p>
      </div>

      <div className="card">
        <h3 style={{ marginBottom: 6 }}>🔑 पासवर्ड <span style={{ fontSize: '0.75rem', fontWeight: 400, color: 'var(--text-secondary)' }}>Password</span></h3>
        {teacher.pin_fixed ? (
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }} data-testid="pin-fixed-note">
            यह साझा डेमो अकाउंट है: इसका पासवर्ड बदला नहीं जा सकता। बदलकर देखने के लिए अभ्यास अकाउंट MPT199 से लॉगिन करें। (This is a shared demo account: its password cannot be changed. To try changing a password, sign in with the practice account MPT199.)
          </p>
        ) : pinDone ? (
          <p style={{ fontSize: '0.875rem', color: 'var(--proficient)' }} data-testid="pin-changed">✅ पासवर्ड बदल गया (Password changed)</p>
        ) : showPin ? (
          <PinChangeForm onDone={() => { setPinDone(true); setShowPin(false); }} />
        ) : (
          <button type="button" className="btn btn-secondary" onClick={() => setShowPin(true)} data-testid="open-pin-form"><Bi hi="पासवर्ड बदलें" en="Change password" inline /></button>
        )}
      </div>

      {isAdmin && (
        <div className="card" data-testid="admin-panel">
          <h3 style={{ marginBottom: 6 }}>🏫 स्कूल लीडर (School leader)</h3>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: 8 }}>आप अपने स्कूल के शिक्षकों के पासवर्ड रीसेट कर सकते हैं। आप किसी बच्चे का डेटा नहीं देखते। (You can reset your teachers’ passwords. You never see any child’s data.)</p>
          {school && (
            <div data-testid="consent-row" style={{ marginBottom: 10, fontSize: '0.8125rem' }}>
              {school.consent ? (
                <span data-testid="consent-recorded" style={{ color: 'var(--green-dark)' }}>
                  ✓ {school.consent.demo ? 'डेमो स्कूल: सभी बच्चे काल्पनिक हैं (Demonstration school: every child is fictional)' : `अभिभावकों की जानकारी और अनुमति की पुष्टि हो चुकी है (Consent confirmed) · ${new Date(school.consent.attested_at).toLocaleDateString('en-IN')}`}
                </span>
              ) : (
                <span data-testid="consent-missing">
                  <span style={{ color: '#8A5A00' }}>⚠ अभिभावकों की अनुमति की पुष्टि दर्ज नहीं है (Consent is not confirmed yet)</span>
                  <button type="button" onClick={confirmConsent} data-testid="consent-confirm" style={{ marginLeft: 8, background: 'none', border: 'none', color: 'var(--green-dark)', textDecoration: 'underline', fontSize: '0.8125rem' }}>पुष्टि करें (Confirm)</button>
                </span>
              )}
            </div>
          )}
          {temp && (
            <div data-testid="temp-pin" style={{ background: '#E4F4EA', border: '1px solid #BFE3CC', borderRadius: 10, padding: 10, marginBottom: 10 }}>
              <div style={{ fontSize: '0.8125rem' }}>शिक्षक {temp.who} का अस्थायी पासवर्ड, सिर्फ़ अभी दिख रहा है (Temporary password, shown once):</div>
              <div data-testid="temp-pin-value" style={{ fontSize: '2rem', fontWeight: 700, letterSpacing: 6, textAlign: 'center' }}>{temp.pin}</div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>शिक्षक को यह दें। इससे वे सिर्फ़ नया पासवर्ड चुन सकते हैं। (Give it to the teacher. It only lets them choose a new password.)</div>
            </div>
          )}
          {error && <p style={{ color: 'var(--beginner)', fontSize: '0.8125rem' }}>{error}</p>}
          {teachers.map(t => (
            <div key={t.teacher_id} data-testid="teacher-row" style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 0', borderTop: '1px solid var(--border)', fontSize: '0.8125rem' }}>
              <div style={{ flex: 1 }}>
                <b data-testid="teacher-code" style={{ letterSpacing: 1 }}>{t.code}</b> {t.is_you && '(आप / you)'}<br />
                <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                  {t.role === 'school_admin' ? 'स्कूल लीडर' : 'शिक्षक'} · {t.children} बच्चे
                  {t.locked && ' · 🔒 बंद (locked)'}{t.must_change_pin && ' · नया पासवर्ड बाकी'}{!t.has_pin && ' · पासवर्ड नहीं'}
                </span>
              </div>
              {t.locked && <button type="button" className="btn btn-secondary btn-small" data-testid={`unlock-${t.teacher_id}`} onClick={() => unlock(t)}>खोलें (Unlock)</button>}
              {!t.is_you && (t.pin_fixed
                ? <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>पासवर्ड स्थिर (fixed demo password)</span>
                : <button type="button" className="btn btn-secondary btn-small" data-testid={`reset-${t.teacher_id}`} onClick={() => reset(t)}>पासवर्ड रीसेट (Reset)</button>)}
            </div>
          ))}
        </div>
      )}

      <button type="button" className="btn btn-secondary" onClick={logout} data-testid="logout" style={{ marginTop: 8 }}><Bi hi="लॉग आउट" en="Log out" inline /></button>
      <div style={{ height: 80 }} />
    </div>
  );
}
