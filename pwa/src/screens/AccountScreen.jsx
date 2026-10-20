import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { adminSchool, adminTeachers, adminResetPin, adminUnlock, adminRotateJoinCode } from '../services/api';
import { PinChangeForm } from './ChangePinScreen';

const GRADE_HI = { balvatika: 'बालवाटिका', grade_1: 'कक्षा 1', grade_2: 'कक्षा 2', grade_3: 'कक्षा 3' };

export default function AccountScreen() {
  const { teacher, logout } = useAuth();
  const navigate = useNavigate();
  const isAdmin = teacher.role === 'school_admin';
  const [showPin, setShowPin] = useState(false);
  const [pinDone, setPinDone] = useState(false);
  const [school, setSchool] = useState(null);
  const [teachers, setTeachers] = useState([]);
  const [temp, setTemp] = useState(null);            // a temporary PIN, shown once
  const [error, setError] = useState('');

  const load = () => {
    if (!isAdmin) return;
    adminSchool().then(setSchool).catch(e => setError(e.message));
    adminTeachers().then(d => setTeachers(d.teachers || [])).catch(e => setError(e.message));
  };
  useEffect(load, [isAdmin]);

  const reset = async (t) => {
    if (!window.confirm(`इस शिक्षक (${t.phone_end}) का पिन रीसेट करें? (Reset the PIN for ${t.phone_end}?)`)) return;
    setError(''); setTemp(null);
    try { const r = await adminResetPin(t.teacher_id); setTemp({ who: t.phone_end, pin: r.temporary_pin }); load(); }
    catch (e) { setError(e.message); }
  };
  const unlock = async (t) => { setError(''); try { await adminUnlock(t.teacher_id); load(); } catch (e) { setError(e.message); } };
  const rotate = async () => {
    if (!window.confirm('नया जॉइन कोड बनाएँ? पुराना कोड बंद हो जाएगा। (Make a new join code? The old one stops working.)')) return;
    try { setSchool({ ...school, ...(await adminRotateJoinCode()) }); } catch (e) { setError(e.message); }
  };

  return (
    <div className="screen">
      <div className="screen-header">
        <h1>👤 प्रोफ़ाइल <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 400 }}>Profile</span></h1>
        <button type="button" className="btn btn-secondary btn-small" onClick={() => navigate('/')}>← वापस (Back)</button>
      </div>

      <div className="card" data-testid="account-info">
        <div style={{ fontSize: '0.875rem' }}>स्कूल (School): <b>{teacher.school_code}</b></div>
        <div style={{ fontSize: '0.875rem', marginTop: 4 }}>भूमिका (Role): <b>{isAdmin ? 'स्कूल एडमिन (School admin)' : 'शिक्षक (Teacher)'}</b></div>
        <div style={{ fontSize: '0.875rem', marginTop: 4 }}>कक्षाएँ (Grades): {(teacher.enrolled_grades || []).map(g => GRADE_HI[g] || g).join(', ')}</div>
        {teacher.is_demo && <div style={{ fontSize: '0.75rem', color: '#8A5A00', marginTop: 6 }}>डेमो अकाउंट: काल्पनिक डेटा (Demo account: fictional data)</div>}
      </div>

      <div className="card">
        <h3 style={{ marginBottom: 6 }}>🔑 पिन <span style={{ fontSize: '0.75rem', fontWeight: 400, color: 'var(--text-secondary)' }}>PIN</span></h3>
        {teacher.pin_fixed ? (
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }} data-testid="pin-fixed-note">
            यह साझा डेमो अकाउंट है: इसका पिन बदला नहीं जा सकता। पिन बदलकर देखने के लिए "पिन बदलना" अकाउंट से लॉगिन करें। (This is a shared demo account: its PIN cannot be changed. To try changing a PIN, sign in with the "Change PIN" account.)
          </p>
        ) : pinDone ? (
          <p style={{ fontSize: '0.875rem', color: 'var(--proficient)' }} data-testid="pin-changed">✅ पिन बदल गया (PIN changed)</p>
        ) : showPin ? (
          <PinChangeForm onDone={() => { setPinDone(true); setShowPin(false); }} />
        ) : (
          <button type="button" className="btn btn-secondary" onClick={() => setShowPin(true)} data-testid="open-pin-form">पिन बदलें (Change PIN)</button>
        )}
      </div>

      {isAdmin && (
        <div className="card" data-testid="admin-panel">
          <h3 style={{ marginBottom: 6 }}>🏫 स्कूल एडमिन (School admin)</h3>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: 8 }}>आप शिक्षकों के पिन रीसेट कर सकते हैं। आप किसी बच्चे का डेटा नहीं देखते। (You can reset PINs. You never see any child's data.)</p>
          {school && (
            <div style={{ marginBottom: 10 }}>
              <span style={{ fontSize: '0.8125rem' }}>जॉइन कोड (Join code): </span>
              <b data-testid="join-code-value" style={{ fontSize: '1.25rem', letterSpacing: 4 }}>{school.join_code || '—'}</b>
              <button type="button" onClick={rotate} style={{ marginLeft: 8, background: 'none', border: 'none', color: 'var(--green-dark)', textDecoration: 'underline', fontSize: '0.75rem' }} data-testid="rotate-join">नया कोड (New code)</button>
            </div>
          )}
          {temp && (
            <div data-testid="temp-pin" style={{ background: '#E4F4EA', border: '1px solid #BFE3CC', borderRadius: 10, padding: 10, marginBottom: 10 }}>
              <div style={{ fontSize: '0.8125rem' }}>शिक्षक {temp.who} का अस्थायी पिन, सिर्फ़ अभी दिख रहा है (Temporary PIN, shown once):</div>
              <div data-testid="temp-pin-value" style={{ fontSize: '2rem', fontWeight: 700, letterSpacing: 6, textAlign: 'center' }}>{temp.pin}</div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>शिक्षक को यह दें। इससे वे सिर्फ़ नया पिन चुन सकते हैं। (Give it to the teacher. It only lets them choose a new PIN.)</div>
            </div>
          )}
          {error && <p style={{ color: 'var(--beginner)', fontSize: '0.8125rem' }}>{error}</p>}
          {teachers.map(t => (
            <div key={t.teacher_id} data-testid="teacher-row" style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 0', borderTop: '1px solid var(--border)', fontSize: '0.8125rem' }}>
              <div style={{ flex: 1 }}>
                <b>{t.phone_end}</b> {t.is_you && '(आप / you)'}<br />
                <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                  {t.role === 'school_admin' ? 'एडमिन' : 'शिक्षक'} · {t.children} बच्चे
                  {t.locked && ' · 🔒 बंद (locked)'}{t.must_change_pin && ' · नया पिन बाकी'}{!t.has_pin && ' · पिन नहीं'}
                </span>
              </div>
              {t.locked && <button type="button" className="btn btn-secondary btn-small" data-testid={`unlock-${t.teacher_id}`} onClick={() => unlock(t)}>खोलें (Unlock)</button>}
              {!t.is_you && (t.pin_fixed
                ? <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>पिन स्थिर (fixed demo PIN)</span>
                : <button type="button" className="btn btn-secondary btn-small" data-testid={`reset-${t.teacher_id}`} onClick={() => reset(t)}>पिन रीसेट (Reset)</button>)}
            </div>
          ))}
        </div>
      )}

      <button type="button" className="btn btn-secondary" onClick={logout} data-testid="logout" style={{ marginTop: 8 }}>लॉग आउट (Log out)</button>
      <div style={{ height: 80 }} />
    </div>
  );
}
