import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { backOrHome } from '../services/backHistory';
import { useAuth } from '../App';
import { adminSchool, adminTeachers, adminResetPin, adminUnlock, adminRecordConsent } from '../services/api';
import { CONSENT } from '../services/consent';
import { PinChangeForm } from './ChangePinScreen';
import { setLang, bi } from '../services/language';
import { useLang } from '../components/LangSwitch';
import { getFamiliarMode, setFamiliarMode } from '../services/preferences';
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
  const lang = useLang();          // हिंदी / English / both: the same setting as the हिं / EN pill at the top
  const confirmLogout = () => {
    if (window.confirm(bi('लॉग आउट करें? इस फ़ोन पर रखी योजनाएँ और वर्कशीट हट जाएँगी।', 'Log out? The plans and worksheets kept on this phone will be removed.'))) logout();
  };
  const [shorter, setShorter] = useState(getFamiliarMode);        // "छोटी स्क्रीन": the plan screen folds the one-line scripts and the anchor card
  const toggleShorter = (on) => { setFamiliarMode(on); setShorter(on); };

  const load = () => {
    if (!isAdmin) return;
    adminSchool().then(setSchool).catch(e => setError(e.message));
    adminTeachers().then(d => setTeachers(d.teachers || [])).catch(e => setError(e.message));
  };
  useEffect(load, [isAdmin]);

  const reset = async (t) => {
    if (!window.confirm(bi(`इस शिक्षक (${t.code}) का पासवर्ड रीसेट करें?`, `Reset the password for ${t.code}?`))) return;
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
        {/* back to the screen the teacher came from (navigation F), the Plan screen if the app was opened here */}
        <button type="button" className="btn btn-secondary btn-small" data-testid="account-back" onClick={() => backOrHome(navigate)}>← <Bi hi="वापस" en="Back" inline /></button>
      </div>

      <div className="card" data-testid="account-info">
        {teacher.employee_code && <div style={{ fontSize: '0.875rem' }}><Bi hi="आपका कोड" en="Your code" inline />: <b data-testid="my-code" style={{ letterSpacing: 2 }}>{teacher.employee_code}</b></div>}
        <div style={{ fontSize: '0.875rem', marginTop: 4 }}><Bi hi="स्कूल" en="School" inline />: <b>{teacher.school_code}</b></div>
        <div style={{ fontSize: '0.875rem', marginTop: 4 }}><Bi hi="भूमिका" en="Role" inline />: <b>{isAdmin ? <Bi hi="स्कूल लीडर" en="School leader" inline /> : <Bi hi="शिक्षक" en="Teacher" inline />}</b></div>
        <div style={{ fontSize: '0.875rem', marginTop: 4 }}><Bi hi="कक्षाएँ" en="Grades" inline />: {(teacher.enrolled_grades || []).map(g => GRADE_HI[g] || g).join(', ')}</div>
        {teacher.is_demo && <div style={{ fontSize: '0.75rem', color: 'var(--info)', marginTop: 6 }}><Bi hi="डेमो अकाउंट: काल्पनिक डेटा" en="Demo account: fictional data" inline /></div>}
        {/* at the top, not after the leader's list; signing out removes this phone's offline copies, so it asks first */}
        <button type="button" className="btn btn-secondary" data-testid="logout" onClick={confirmLogout} style={{ marginTop: 10, flexDirection: 'column', gap: 0 }}>
          <Bi hi="लॉग आउट" en="Log out" />
        </button>
      </div>

      <div className="card" data-testid="language-card">
        <h3 style={{ marginBottom: 6 }}>🔤 <Bi hi="भाषा" en="Language" inline /></h3>
        <div role="radiogroup" aria-label="भाषा / Language" data-testid="lang-options">
          {[['hi', 'hindi-only', 'हिंदी', 'Hindi'], ['en', 'lang-opt-en', 'अंग्रेज़ी', 'English'], ['both', 'lang-opt-both', 'दोनों', 'Both']].map(([id, testid, hi, en]) => (
            <label key={id} style={{ display: 'flex', alignItems: 'center', gap: 10, minHeight: 44, fontSize: '0.9375rem', cursor: 'pointer' }}>
              <input type="radio" name="app_language" value={id} checked={lang === id} onChange={() => setLang(id)} data-testid={testid} />
              <span><Bi hi={hi} en={en} inline /></span>
            </label>
          ))}
        </div>
        <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 2 }}>
          <Bi hi="ऊपर के हिं / EN बटन से भी बदलें। योजना की अपनी सामग्री हिंदी में रहती है; कौशल कोड और रोल नंबर हर भाषा में दिखते हैं। यह सेटिंग इसी फ़ोन पर रहती है।" en="Also switched with the हिं / EN button at the top. The plan's own content stays in Hindi; skill codes and roll numbers show in every language. This setting stays on this phone." />
        </p>
        <label style={{ display: 'flex', alignItems: 'center', gap: 10, minHeight: 44, fontSize: '0.9375rem', cursor: 'pointer', marginTop: 6 }}>
          <input type="checkbox" checked={shorter} onChange={(e) => toggleShorter(e.target.checked)} data-testid="shorter-screen" />
          <span><Bi hi="छोटी स्क्रीन" en="Shorter screen" inline /></span>
        </label>
        <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 2 }} data-testid="shorter-screen-hint">
          <Bi hi="योजना की स्क्रीन छोटी हो जाती है; एक टैप पर सब कुछ खुलता है।" en="The plan screen gets shorter; one tap opens everything." />
        </p>
      </div>

      <div className="card">
        <h3 style={{ marginBottom: 6 }}>🔑 <Bi hi="पासवर्ड" en="Password" inline /></h3>
        {teacher.pin_fixed ? (
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }} data-testid="pin-fixed-note">
            <Bi hi="यह साझा डेमो अकाउंट है: इसका पासवर्ड बदला नहीं जा सकता। बदलकर देखने के लिए अभ्यास अकाउंट MPT199 से लॉगिन करें।" en="This is a shared demo account: its password cannot be changed. To try changing a password, sign in with the practice account MPT199." />
          </p>
        ) : pinDone ? (
          <p style={{ fontSize: '0.875rem', color: 'var(--green-dark)' }} data-testid="pin-changed">✅ <Bi hi="पासवर्ड बदल गया" en="Password changed" inline /></p>
        ) : showPin ? (
          <PinChangeForm onDone={() => { setPinDone(true); setShowPin(false); }} />
        ) : (
          <button type="button" className="btn btn-secondary" onClick={() => setShowPin(true)} data-testid="open-pin-form"><Bi hi="पासवर्ड बदलें" en="Change password" inline /></button>
        )}
      </div>

      {isAdmin && (
        <div className="card" data-testid="admin-panel">
          <h3 style={{ marginBottom: 6 }}>🏫 <Bi hi="स्कूल लीडर" en="School leader" inline /></h3>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: 8 }}><Bi hi="आप अपने स्कूल के शिक्षकों के पासवर्ड रीसेट कर सकते हैं। आप किसी बच्चे का डेटा नहीं देखते।" en="You can reset your teachers’ passwords. You never see any child’s data." /></p>
          {school && (
            <div data-testid="consent-row" style={{ marginBottom: 10, fontSize: '0.8125rem' }}>
              {school.consent ? (
                <span data-testid="consent-recorded" style={{ color: 'var(--green-dark)' }}>
                  ✓ {school.consent.demo
                    ? <Bi hi="डेमो स्कूल: सभी बच्चे काल्पनिक हैं" en="Demonstration school: every child is fictional" inline />
                    : <><Bi hi="अभिभावकों की जानकारी और अनुमति की पुष्टि हो चुकी है" en="Consent confirmed" inline /> · {new Date(school.consent.attested_at).toLocaleDateString('en-IN')}</>}
                </span>
              ) : (
                <span data-testid="consent-missing">
                  <span style={{ color: 'var(--info)' }}>⚠ <Bi hi="अभिभावकों की अनुमति की पुष्टि दर्ज नहीं है" en="Consent is not confirmed yet" inline /></span>
                  <button type="button" onClick={confirmConsent} data-testid="consent-confirm" style={{ marginLeft: 8, background: 'none', border: 'none', color: 'var(--green-dark)', textDecoration: 'underline', fontSize: '0.8125rem', minHeight: 44, fontFamily: 'inherit' }}><Bi hi="पुष्टि करें" en="Confirm" inline /></button>
                </span>
              )}
            </div>
          )}
          {temp && (
            <div data-testid="temp-pin" style={{ background: '#E4F4EA', border: '1px solid #BFE3CC', borderRadius: 10, padding: 10, marginBottom: 10 }}>
              <div style={{ fontSize: '0.8125rem' }}><span className="hi">शिक्षक {temp.who} का अस्थायी पासवर्ड, सिर्फ़ अभी दिख रहा है</span><span className="en en-inline" lang="en">Temporary password for teacher {temp.who}, shown once</span>:</div>
              <div data-testid="temp-pin-value" style={{ fontSize: '2rem', fontWeight: 700, letterSpacing: 6, textAlign: 'center' }}>{temp.pin}</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}><Bi hi="शिक्षक को यह दें। इससे वे सिर्फ़ नया पासवर्ड चुन सकते हैं।" en="Give it to the teacher. It only lets them choose a new password." /></div>
            </div>
          )}
          {error && <p style={{ color: 'var(--danger)', fontSize: '0.8125rem' }}>{error}</p>}
          {teachers.map(t => (
            <div key={t.teacher_id} data-testid="teacher-row" style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 0', borderTop: '1px solid var(--border)', fontSize: '0.8125rem' }}>
              <div style={{ flex: 1 }}>
                <b data-testid="teacher-code" style={{ letterSpacing: 1 }}>{t.code}</b> {t.is_you && <>(<Bi hi="आप" en="you" inline />)</>}<br />
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  {t.role === 'school_admin' ? <Bi hi="स्कूल लीडर" en="School leader" inline /> : <Bi hi="शिक्षक" en="Teacher" inline />} · {t.children} <Bi hi="बच्चे" en="children" inline />
                  {t.locked && <> · 🔒 <Bi hi="बंद" en="locked" inline /></>}{t.must_change_pin && <> · <Bi hi="नया पासवर्ड बाकी" en="new password pending" inline /></>}{!t.has_pin && <> · <Bi hi="पासवर्ड नहीं" en="no password" inline /></>}
                </span>
              </div>
              {t.locked && <button type="button" className="btn btn-secondary btn-small" data-testid={`unlock-${t.teacher_id}`} onClick={() => unlock(t)}><Bi hi="खोलें" en="Unlock" inline /></button>}
              {!t.is_you && (t.pin_fixed
                ? <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}><Bi hi="पासवर्ड स्थिर" en="fixed demo password" /></span>
                : <button type="button" className="btn btn-secondary btn-small" data-testid={`reset-${t.teacher_id}`} onClick={() => reset(t)}><Bi hi="पासवर्ड रीसेट" en="Reset" inline /></button>)}
            </div>
          ))}
        </div>
      )}

      <div style={{ height: 80 }} />
    </div>
  );
}
