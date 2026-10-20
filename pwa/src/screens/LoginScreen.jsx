import React, { useState } from 'react';
import { useAuth } from '../App';
import { login, registerTeacher, setToken } from '../services/api';

// Published demo accounts (fictional data only). Shown for reviewers; set VITE_DEMO_HINT=false for a real school.
// If you change the demo PINs with scripts/auth_admin.py, change them here too.
const DEMO_HINT = import.meta.env.VITE_DEMO_HINT !== 'false';
const DEMO = [
  ['9876543210', '4826', 'डेमो शिक्षक: 30 बच्चों की कक्षा (Demo teacher)'],
  ['9876500000', '7351', 'डेमो स्कूल एडमिन (Demo school admin)'],
  ['9000000101', '4826', 'टेस्ट शिक्षक 1: अपनी कक्षा (Test teacher 1)'],
  ['9000000199', '3917', 'पिन बदलना: पिन बदलकर और रीसेट करके देखें (Change PIN)'],
];
const GRADE_CHOICES = [['balvatika', 'बालवाटिका'], ['grade_1', 'कक्षा 1'], ['grade_2', 'कक्षा 2'], ['grade_3', 'कक्षा 3']];
const digits = (v) => v.replace(/\D/g, '').slice(0, 6);
const field = { width: '100%', padding: '12px 16px', fontSize: '1.125rem', border: '2px solid var(--border)', borderRadius: 10, fontFamily: 'inherit', marginBottom: 12 };
const label = { fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: 6, display: 'block' };

export default function LoginScreen() {
  const { setTeacher } = useAuth();
  const [registering, setRegistering] = useState(false);
  const [phone, setPhone] = useState('');
  const [pin, setPin] = useState('');
  const [pin2, setPin2] = useState('');
  const [schoolCode, setSchoolCode] = useState('');
  const [joinCode, setJoinCode] = useState('');
  const [grades, setGrades] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [welcome, setWelcome] = useState(null);       // a new school's join code, shown once to its admin
  const toggleGrade = (g) => setGrades(prev => prev.includes(g) ? prev.filter(x => x !== g) : [...prev, g]);

  const finish = (data) => {
    setToken(data.token);
    const { token, join_code, ...profile } = data;
    if (join_code) setWelcome({ code: join_code, profile }); else setTeacher(profile);
  };

  const handleLogin = async () => {
    if (!phone.trim() || pin.length < 4) { setError('फ़ोन नंबर और पिन डालें (Enter your phone number and PIN).'); return; }
    setLoading(true); setError('');
    try { finish(await login('hash_' + phone.trim(), pin)); }
    catch (e) { setError(e.message || 'लॉगिन नहीं हो सका (Could not sign in)'); }
    setLoading(false);
  };

  const handleRegister = async () => {
    if (!phone.trim() || !schoolCode.trim() || !grades.length) { setError('फ़ोन, स्कूल कोड और कम से कम एक कक्षा चुनें (Phone, school code and at least one grade).'); return; }
    if (pin.length < 4) { setError('पिन 4 से 6 अंकों का होना चाहिए (The PIN must be 4 to 6 digits).'); return; }
    if (pin !== pin2) { setError('दोनों पिन एक जैसे नहीं हैं (The two PINs do not match).'); return; }
    setLoading(true); setError('');
    try { finish(await registerTeacher('hash_' + phone.trim(), pin, schoolCode.trim(), joinCode.trim(), grades)); }
    catch (e) { setError(e.message || 'पंजीकरण नहीं हो सका (Registration failed)'); }
    setLoading(false);
  };

  if (welcome) {
    return (
      <div className="screen" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', minHeight: '100dvh' }}>
        <div className="card" data-testid="welcome">
          <h2>✅ स्कूल पंजीकृत हुआ (School registered)</h2>
          <p style={{ fontSize: '0.875rem', margin: '8px 0' }}>आप इस स्कूल के एडमिन हैं। दूसरे शिक्षकों को जुड़ने के लिए यह कोड दें:</p>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>You are this school's admin. Give other teachers this join code so they can register:</p>
          <div data-testid="join-code-shown" style={{ fontSize: '2rem', fontWeight: 700, letterSpacing: 6, textAlign: 'center', margin: '12px 0', color: 'var(--green-dark)' }}>{welcome.code}</div>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>इसे बाद में भी "प्रोफ़ाइल" पेज पर देख सकते हैं। (You can see it again on the Profile page.)</p>
          <button className="btn btn-primary" style={{ marginTop: 10 }} onClick={() => setTeacher(welcome.profile)}>आगे बढ़ें (Continue)</button>
        </div>
      </div>
    );
  }

  return (
    <div className="screen" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', minHeight: '100dvh' }}>
      <div style={{ textAlign: 'center', marginBottom: 24 }}>
        <div style={{ fontSize: '3rem', marginBottom: 8 }}>🌱</div>
        <h1 style={{ fontSize: '1.75rem', color: 'var(--green-dark)' }}>अंकुर साथी</h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: 4 }}>Ankur Saathi</p>
      </div>

      <div className="card">
        <label style={label}>फ़ोन नंबर (Phone number)</label>
        <input type="tel" value={phone} onChange={e => setPhone(e.target.value)} placeholder="9876543210" data-testid="phone" style={field} />
        {registering && (
          <div data-testid="register-fields">
            <label style={label}>स्कूल कोड (School code)</label>
            <input type="text" value={schoolCode} onChange={e => setSchoolCode(e.target.value)} placeholder="MP-1234" data-testid="school-code" style={field} />
            <label style={label}>जॉइन कोड, अगर आपका स्कूल पहले से जुड़ा है (Join code, if your school is already registered)</label>
            <input type="text" value={joinCode} onChange={e => setJoinCode(e.target.value.toUpperCase().slice(0, 8))} placeholder="ABC234" data-testid="join-code" style={{ ...field, letterSpacing: 3 }} />
            <label style={label}>आप किन कक्षाओं को पढ़ाते हैं? (Grades you teach)</label>
            <div style={{ display: 'flex', gap: 6, marginBottom: 12 }}>
              {GRADE_CHOICES.map(([g, hi]) => (
                <button key={g} type="button" data-testid={`grade-${g}`} onClick={() => toggleGrade(g)}
                  style={{ flex: 1, padding: '8px 2px', borderRadius: 8, border: '1px solid var(--border)', fontSize: '0.75rem', fontWeight: 600,
                           background: grades.includes(g) ? 'var(--green-dark)' : 'var(--surface)', color: grades.includes(g) ? 'white' : 'var(--text)' }}>{hi}</button>
              ))}
            </div>
          </div>
        )}
        <label style={label}>{registering ? 'अपना पिन चुनें, 4 से 6 अंक (Choose a PIN, 4 to 6 digits)' : 'पिन (PIN)'}</label>
        <input type="password" inputMode="numeric" pattern="[0-9]*" autoComplete={registering ? 'new-password' : 'current-password'} value={pin}
          onChange={e => setPin(digits(e.target.value))} placeholder="••••" data-testid="pin" style={{ ...field, letterSpacing: 8 }}
          onKeyDown={e => e.key === 'Enter' && !registering && handleLogin()} />
        {registering && (
          <>
            <label style={label}>पिन दोबारा (Repeat the PIN)</label>
            <input type="password" inputMode="numeric" pattern="[0-9]*" autoComplete="new-password" value={pin2} onChange={e => setPin2(digits(e.target.value))}
              placeholder="••••" data-testid="pin-confirm" style={{ ...field, letterSpacing: 8 }} />
          </>
        )}
        {error && <p data-testid="login-error" style={{ color: 'var(--beginner)', fontSize: '0.875rem', marginBottom: 8 }}>{error}</p>}
        {registering ? (
          <button className="btn btn-primary" onClick={handleRegister} disabled={loading} data-testid="register-submit">{loading ? 'पंजीकरण हो रहा है...' : 'पंजीकरण करें (Register)'}</button>
        ) : (
          <button className="btn btn-primary" onClick={handleLogin} disabled={loading} data-testid="login-submit">{loading ? 'लॉगिन हो रहा है (Logging in)...' : 'लॉगिन करें (Login)'}</button>
        )}
        <button type="button" onClick={() => { setRegistering(v => !v); setError(''); }} data-testid="toggle-register"
          style={{ display: 'block', margin: '12px auto 0', background: 'none', border: 'none', color: 'var(--green-dark)', textDecoration: 'underline', fontSize: '0.8125rem' }}>
          {registering ? 'पहले से पंजीकृत हैं? लॉगिन (Already registered? Log in)' : 'नए शिक्षक? पंजीकरण करें (New teacher? Register)'}
        </button>
        {!registering && <p style={{ textAlign: 'center', fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: 8 }}>पिन भूल गए? अपने स्कूल एडमिन से कहें। (Forgot your PIN? Ask your school admin.)</p>}
      </div>

      {DEMO_HINT && !registering && (
        <div className="card" data-testid="demo-hint" style={{ background: '#FFF8E1' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, marginBottom: 6 }}>समीक्षकों के लिए डेमो अकाउंट (Demo accounts for reviewers: fictional data only)</div>
          {DEMO.map(([ph, pn, what]) => (
            <button key={ph} type="button" data-testid={`demo-${ph}`} onClick={() => { setPhone(ph); setPin(pn); setError(''); }}
              style={{ display: 'block', width: '100%', textAlign: 'left', background: 'none', border: 'none', borderBottom: '1px solid #E8DDB5', padding: '5px 0', fontSize: '0.75rem', fontFamily: 'inherit' }}>
              <b>{ph}</b> · पिन {pn}<br /><span style={{ color: 'var(--text-secondary)' }}>{what}</span>
            </button>
          ))}
          <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', marginTop: 4 }}>किसी अकाउंट पर दबाएँ, फ़ोन और पिन भर जाएँगे। (Tap an account to fill in the phone and PIN.)</div>
        </div>
      )}
    </div>
  );
}
