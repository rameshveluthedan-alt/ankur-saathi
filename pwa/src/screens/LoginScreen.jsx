import React, { useState } from 'react';
import { useAuth } from '../App';
import { login, setToken } from '../services/api';
import Bi from '../components/Bi';
import HowItWorks from '../components/HowItWorks';
import { bi } from '../services/language';

// Published demo accounts (fictional data only). Shown for reviewers; set VITE_DEMO_HINT=false for a real school.
// If you change the demo passwords with scripts/auth_admin.py, change them here too: pwa/tests/demo_accounts.test.mjs checks that this list and the access guide agree.
const DEMO_HINT = import.meta.env.VITE_DEMO_HINT !== 'false';
// The cards follow the reviewer's rule of thumb (docs/DEMO_ACCESS.md): 5 minutes -> the shared demo teacher and its recorded story; 30 minutes -> a test teacher of one's own;
// a leader -> the school leader; the password flows -> the practice account.
const STORY = { code: 'MPT101', password: '4826' };          // shared by every reviewer; the nightly reset rewrites it to the story the deck tells (N2.3.2)
const TESTERS = [                                             // one each: their own class of 24, never reset, so reviewers do not overwrite each other
  { code: 'MPT102', password: '4826' },
  { code: 'MPT103', password: '4826' },
  { code: 'MPT104', password: '4826' },
  { code: 'MPT105', password: '4826' },
  { code: 'MPT106', password: '4826' },
];
const LEADER = { code: 'MPA101', password: '7351' };         // the head teacher: teaches too, and looks after the school's accounts
const PRACTICE = { code: 'MPT199', password: '3917' };       // the practice account: its password can be changed and reset
// One demo account as a tappable card: what it is for (title), a line or two about it, its code and password, and a "भरें ›" / "✓ भर गया" cue.
function DemoCard({ acct, code, fill, icon, title, lines, main }) {
  const chosen = code === acct.code;
  return (
    <button type="button" data-testid={`demo-${acct.code}`} onClick={() => fill(acct.code, acct.password)} aria-pressed={chosen}
      className={`demo-card ${main ? 'demo-card-main' : ''} ${chosen ? 'selected' : ''}`}
      style={{ display: 'flex', gap: 10, alignItems: 'center', width: '100%', textAlign: 'left', borderRadius: 10, padding: '10px 12px', marginBottom: 8, minHeight: 56, fontFamily: 'inherit' }}>
      <span aria-hidden="true" style={{ fontSize: '1.5rem' }}>{icon}</span>
      <span style={{ flex: 1, fontSize: '0.8125rem' }}>
        <b style={{ fontSize: main ? '0.9375rem' : '0.875rem' }}>{title}</b>
        {lines.map((l, i) => <span key={i} style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 2 }}>{l}</span>)}
        <span style={{ display: 'block', fontFamily: 'monospace', fontSize: '0.75rem', marginTop: 2 }}>कोड {acct.code} · पासवर्ड {acct.password}</span>
      </span>
      <span className="demo-card-go" data-testid={`demo-go-${acct.code}`}>
        {chosen ? <Bi hi="✓ भर गया" en="Filled" /> : <Bi hi="भरें ›" en="Tap to fill" />}
      </span>
    </button>
  );
}

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
        <p style={{ textAlign: 'center', fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 4 }}><Bi hi="आपका खाता आपके स्कूल लीडर द्वारा बनाया जाता है।" en="Your account is created by your school leader." /></p>
      </div>

      {DEMO_HINT && (
        <div className="card" data-testid="demo-hint" style={{ background: '#FFF8E1' }}>
          <div style={{ fontSize: '0.8125rem', fontWeight: 600, marginBottom: 2 }}><Bi hi="समीक्षकों के लिए: डेमो अकाउंट" en="For reviewers: demo accounts" inline /></div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: 8 }}><Bi hi="सिर्फ़ काल्पनिक डेटा। अपने समय के हिसाब से एक कार्ड चुनें, कोड और पासवर्ड भर जाएँगे; फिर लॉगिन दबाएँ।" en="Fictional data only. Pick a card by the time you have; it fills in the code and password, then press Login." /></div>

          {/* 1. Five minutes: the shared demo teacher and the recorded story (the biggest card, first). Each card is a button and looks like one: hover lift, a "भरें ›" cue, a tick once filled. */}
          <DemoCard acct={STORY} code={code} fill={fill} main icon="⏱"
            title={<Bi hi="5 मिनट: तैयार कहानी देखें" en="5 minutes: see the recorded story" />}
            lines={[
              <Bi key="w" hi="👩‍🏫 डेमो शिक्षक · 30 बच्चे · N2.3.2 की कहानी" en="Demo teacher · 30 children · the N2.3.2 story" />,
              <Bi key="s" hi="सबके लिए एक साझा कक्षा, हर रात फिर से सेट होती है" en="One class shared by everyone, reset every night" />,
            ]} />

          {/* 2. Thirty minutes: a test teacher of one's own. One card, five chips: each reviewer picks a different one. */}
          <div className="demo-group" data-testid="demo-testers">
            <div style={{ fontSize: '0.875rem' }}>
              <span aria-hidden="true">🧪 </span><b><Bi hi="30 मिनट: खुद आज़माएँ" en="30 minutes: try it yourself" /></b>
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 2 }}>
              <Bi hi="अपनी अलग कक्षा (24 बच्चे); आपका काम अगले दिन तक बना रहता है।" en="Your own class (24 children); your work stays until you change it." />
            </div>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, margin: '6px 0 4px' }}>
              <Bi hi="हर समीक्षक अलग कोड चुनें:" en="Each reviewer picks a different code:" inline />
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {TESTERS.map((t) => {
                const chosen = code === t.code;
                return (
                  <button key={t.code} type="button" data-testid={`demo-${t.code}`} onClick={() => fill(t.code, t.password)} aria-pressed={chosen}
                    className={`demo-chip ${chosen ? 'selected' : ''}`} style={{ minHeight: 44 }}>
                    {chosen ? '✓ ' : ''}{t.code}
                  </button>
                );
              })}
            </div>
            <div style={{ fontFamily: 'monospace', fontSize: '0.75rem', marginTop: 6 }}>
              पासवर्ड {TESTERS[0].password} · सबका एक<span className="en en-inline" lang="en">same for all</span>
            </div>
          </div>

          {/* 3. The school leader */}
          <DemoCard acct={LEADER} code={code} fill={fill} icon="🏫"
            title={<Bi hi="स्कूल लीडर: स्कूल के खाते सँभालें" en="School leader: manage the school's accounts" />}
            lines={[<Bi key="w" hi="पढ़ाते भी हैं; शिक्षकों के खाते देखते, अनलॉक करते और पासवर्ड रीसेट करते हैं।" en="Teaches too; views teachers' accounts, unlocks them and resets passwords." />]} />
          <button type="button" data-testid={`demo-${PRACTICE.code}`} onClick={() => fill(PRACTICE.code, PRACTICE.password)} aria-pressed={code === PRACTICE.code}
            className={`demo-link ${code === PRACTICE.code ? 'selected' : ''}`}
            style={{ display: 'block', width: '100%', textAlign: 'left', background: 'none', border: 'none', padding: '6px 2px', fontSize: '0.75rem', fontFamily: 'inherit', color: 'var(--green-dark)', minHeight: 44 }}>
            🔑 पासवर्ड बदलकर देखें<span className="en en-inline" lang="en">Try changing a password</span>: <span style={{ fontFamily: 'monospace' }}>कोड {PRACTICE.code} · पासवर्ड {PRACTICE.password}</span>
          </button>
        </div>
      )}

      {/* how the parts come together, for a teacher or an evaluator before signing in */}
      <HowItWorks />
    </div>
  );
}
