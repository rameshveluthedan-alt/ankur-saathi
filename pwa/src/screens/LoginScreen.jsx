import React, { useState } from 'react';
import { useAuth } from '../App';
import { login, setToken } from '../services/api';
import Bi from '../components/Bi';
import { bi } from '../services/language';

// Published demo accounts (fictional data only). Shown for reviewers; set VITE_DEMO_HINT=false for a real school.
// If you change the demo passwords with scripts/auth_admin.py, change them here too: pwa/tests/demo_accounts.test.mjs checks that this list and the access guide agree.
const DEMO_HINT = import.meta.env.VITE_DEMO_HINT !== 'false';
const ROLES = [
  { code: 'MPT101', password: '4826', icon: '👩‍🏫', hi: 'शिक्षक', en: 'Teacher', whatHi: '30 बच्चों की कक्षा: योजना, वर्कशीट, समीक्षा', whatEn: 'A 30-child class: plan, worksheets, review' },
  { code: 'MPA101', password: '7351', icon: '🏫', hi: 'स्कूल लीडर', en: 'School leader (head teacher)', whatHi: 'पढ़ाते भी हैं, और स्कूल के खाते सँभालते हैं', whatEn: 'Teaches too, and looks after the school’s accounts' },
];
const PRACTICE = { code: 'MPT199', password: '3917' };       // the practice account: its password can be changed and reset
const field = { width: '100%', padding: '12px 16px', fontSize: '1.125rem', border: '2px solid var(--border)', borderRadius: 10, fontFamily: 'inherit', marginBottom: 12 };
const label = { fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: 6, display: 'block' };
const clean = (v) => v.replace(/[^A-Za-z0-9]/g, '').toUpperCase().slice(0, 6);

export default function LoginScreen() {
  const { setTeacher } = useAuth();
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async () => {
    if (code.length !== 6 || !password) { setError(bi('कर्मचारी कोड (6 अक्षर या अंक) और पासवर्ड डालें।', 'Enter your 6-character employee code and your password.')); return; }
    setLoading(true); setError('');
    try {
      const data = await login(code, password);
      setToken(data.token);
      const { token, join_code, ...profile } = data;
      setTeacher(profile);
    } catch (e) { setError(e.message || bi('लॉगिन नहीं हो सका', 'Could not sign in')); }
    setLoading(false);
  };
  const fill = (c, p) => { setCode(c); setPassword(p); setError(''); };

  return (
    <div className="screen" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', minHeight: '100dvh' }}>
      <div style={{ textAlign: 'center', marginBottom: 24 }}>
        <div style={{ fontSize: '3rem', marginBottom: 8 }}>🌱</div>
        <h1 style={{ fontSize: '1.75rem', color: 'var(--green-dark)' }}>अंकुर साथी</h1>
        <p className="en" lang="en" style={{ fontSize: '1rem', marginTop: 4 }}>Ankur Saathi</p>
      </div>

      <div className="card">
        <label htmlFor="employee-code" style={label}><Bi hi="कर्मचारी कोड" en="Employee code" inline /></label>
        <input id="employee-code" type="text" value={code} onChange={e => setCode(clean(e.target.value))} placeholder="MPT101" data-testid="employee-code"
          autoCapitalize="characters" autoCorrect="off" spellCheck={false} autoComplete="username" maxLength={6} style={{ ...field, letterSpacing: 3, textTransform: 'uppercase' }} />
        <label htmlFor="password" style={label}><Bi hi="पासवर्ड" en="Password" inline /></label>
        <div style={{ position: 'relative' }}>
          <input id="password" type={show ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value.slice(0, 12))} placeholder="••••••" data-testid="password"
            autoComplete="current-password" autoCapitalize="none" autoCorrect="off" spellCheck={false} style={{ ...field, paddingRight: 96 }}
            onKeyDown={e => e.key === 'Enter' && handleLogin()} />
          <button type="button" onClick={() => setShow(v => !v)} data-testid="toggle-password" aria-pressed={show}
            style={{ position: 'absolute', right: 6, top: 6, height: 44, minWidth: 80, background: 'none', border: 'none', color: 'var(--green-dark)', fontSize: '0.8125rem', fontWeight: 600 }}>
            {show ? <Bi hi="छिपाएँ" en="Hide" inline /> : <Bi hi="दिखाएँ" en="Show" inline />}
          </button>
        </div>
        {error && <p data-testid="login-error" role="alert" style={{ color: 'var(--beginner)', fontSize: '0.875rem', marginBottom: 8 }}>{error}</p>}
        <button className="btn btn-primary" onClick={handleLogin} disabled={loading} data-testid="login-submit">{loading ? <Bi hi="लॉगिन हो रहा है..." en="Logging in" inline /> : <Bi hi="लॉगिन करें" en="Login" inline />}</button>
        <p style={{ textAlign: 'center', fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 10 }}><Bi hi="पासवर्ड भूल गए? अपने स्कूल लीडर से कहें।" en="Forgot your password? Ask your school leader." /></p>
        <p style={{ textAlign: 'center', fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 4 }}><Bi hi="खाता आपके स्कूल लीडर बनाते हैं।" en="Your school leader makes your account." /></p>
      </div>

      {DEMO_HINT && (
        <div className="card" data-testid="demo-hint" style={{ background: '#FFF8E1' }}>
          <div style={{ fontSize: '0.8125rem', fontWeight: 600, marginBottom: 2 }}><Bi hi="समीक्षकों के लिए: डेमो अकाउंट" en="For reviewers: demo accounts" inline /></div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: 8 }}><Bi hi="सिर्फ़ काल्पनिक डेटा। किसी कार्ड पर दबाएँ, कोड और पासवर्ड भर जाएँगे; फिर लॉगिन दबाएँ।" en="Fictional data only. Tap a card to fill in the code and password, then press Login." /></div>
          {/* each card is a button and looks like one: pointer and lift on hover, a "भरें ›" (fill) cue at the end, and a tick once its code is filled in */}
          {ROLES.map(r => {
            const chosen = code === r.code;
            return (
              <button key={r.code} type="button" data-testid={`demo-${r.code}`} onClick={() => fill(r.code, r.password)} aria-pressed={chosen}
                className={`demo-card ${chosen ? 'selected' : ''}`}
                style={{ display: 'flex', gap: 10, alignItems: 'center', width: '100%', textAlign: 'left', borderRadius: 10, padding: '10px 12px', marginBottom: 8, minHeight: 56, fontFamily: 'inherit' }}>
                <span aria-hidden="true" style={{ fontSize: '1.5rem' }}>{r.icon}</span>
                <span style={{ flex: 1, fontSize: '0.8125rem' }}>
                  <b>{r.hi}</b><span className="en en-inline" lang="en" style={{ fontSize: '0.75rem' }}>{r.en}</span><br />
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}><Bi hi={r.whatHi} en={r.whatEn} /></span><br />
                  <span style={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>कोड {r.code} · पासवर्ड {r.password}</span>
                </span>
                <span className="demo-card-go" data-testid={`demo-go-${r.code}`}>
                  {chosen ? <Bi hi="✓ भर गया" en="Filled" /> : <Bi hi="भरें ›" en="Tap to fill" />}
                </span>
              </button>
            );
          })}
          <button type="button" data-testid={`demo-${PRACTICE.code}`} onClick={() => fill(PRACTICE.code, PRACTICE.password)} aria-pressed={code === PRACTICE.code}
            className={`demo-link ${code === PRACTICE.code ? 'selected' : ''}`}
            style={{ display: 'block', width: '100%', textAlign: 'left', background: 'none', border: 'none', padding: '6px 2px', fontSize: '0.75rem', fontFamily: 'inherit', color: 'var(--green-dark)', minHeight: 44 }}>
            🔑 पासवर्ड बदलकर देखें<span className="en en-inline" lang="en">Try changing a password</span>: <span style={{ fontFamily: 'monospace' }}>कोड {PRACTICE.code} · पासवर्ड {PRACTICE.password}</span>
          </button>
        </div>
      )}
    </div>
  );
}
