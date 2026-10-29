import React, { useState } from 'react';
import { useAuth } from '../App';
import { changePin, setToken } from '../services/api';

// (The file and the API keep their old name, "pin": the secret is now called a PASSWORD: 6 to 12 letters or digits, and a 6-digit number is fine.)
const clean = (v) => v.replace(/[^A-Za-z0-9]/g, '').slice(0, 12);
const field = { width: '100%', padding: '12px 16px', fontSize: '1.125rem', border: '2px solid var(--border)', borderRadius: 10, fontFamily: 'inherit', marginBottom: 10 };
const lab = { fontSize: '0.8125rem', color: 'var(--text-secondary)', display: 'block', marginBottom: 4 };

// Choose a new password. Used on the Profile page, and as the ONLY screen after a school leader's reset or a first sign-in (forced).
export function PinChangeForm({ forced = false, onDone }) {
  const { teacher, setTeacher } = useAuth();
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [again, setAgain] = useState('');
  const [show, setShow] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const type = show ? 'text' : 'password';

  const submit = async () => {
    if (next !== again) { setError('नए पासवर्ड एक जैसे नहीं हैं (The new passwords do not match).'); return; }
    setLoading(true); setError('');
    try {
      const res = await changePin(current, next);
      setToken(res.token);
      const { token, join_code, ...profile } = res;
      setTeacher({ ...teacher, ...profile });
      setCurrent(''); setNext(''); setAgain('');
      if (onDone) onDone();
    } catch (e) { setError(e.message || 'पासवर्ड नहीं बदला जा सका (Could not change the password)'); }
    setLoading(false);
  };

  return (
    <div data-testid="pin-form">
      <label style={lab}>{forced ? 'अस्थायी पासवर्ड जो स्कूल लीडर ने दिया (The temporary password from your school leader)' : 'वर्तमान पासवर्ड (Current password)'}</label>
      <input type={type} value={current} onChange={e => setCurrent(clean(e.target.value))} data-testid="pin-current" style={field} autoComplete="current-password" autoCapitalize="none" autoCorrect="off" spellCheck={false} />
      <label style={lab}>नया पासवर्ड, 6 से 12 अक्षर या अंक (New password, 6 to 12 letters or digits)</label>
      <input type={type} value={next} onChange={e => setNext(clean(e.target.value))} data-testid="pin-new" style={field} autoComplete="new-password" autoCapitalize="none" autoCorrect="off" spellCheck={false} />
      <label style={lab}>नया पासवर्ड दोबारा (Repeat the new password)</label>
      <input type={type} value={again} onChange={e => setAgain(clean(e.target.value))} data-testid="pin-new-again" style={field} autoComplete="new-password" autoCapitalize="none" autoCorrect="off" spellCheck={false} />
      <button type="button" onClick={() => setShow(v => !v)} data-testid="pin-toggle" aria-pressed={show}
        style={{ background: 'none', border: 'none', color: 'var(--green-dark)', fontSize: '0.8125rem', textDecoration: 'underline', minHeight: 44, marginBottom: 4 }}>{show ? 'छिपाएँ (Hide)' : 'दिखाएँ (Show)'}</button>
      {error && <p data-testid="pin-error" role="alert" style={{ color: 'var(--beginner)', fontSize: '0.8125rem', marginBottom: 8 }}>{error}</p>}
      <button className="btn btn-primary" onClick={submit} disabled={loading || current.length < 4 || next.length < 6} data-testid="pin-save">
        {loading ? 'सहेज रहे हैं...' : 'नया पासवर्ड सहेजें (Save new password)'}
      </button>
    </div>
  );
}

export default function ChangePinScreen({ forced = false }) {
  const { logout } = useAuth();
  return (
    <div className="screen" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', minHeight: '100dvh' }}>
      <div className="card" data-testid="forced-pin-change">
        <h2>🔑 नया पासवर्ड चुनें (Choose a new password)</h2>
        <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', margin: '6px 0 12px' }}>
          यह आपका पहला लॉगिन है, या आपके स्कूल लीडर ने पासवर्ड रीसेट किया है। जारी रखने से पहले अपना पासवर्ड चुनें। (This is your first sign-in, or your school leader reset your password. Choose your own before you continue.)
        </p>
        <PinChangeForm forced={forced} />
        <button type="button" onClick={logout} style={{ display: 'block', margin: '12px auto 0', background: 'none', border: 'none', color: 'var(--text-secondary)', textDecoration: 'underline', fontSize: '0.8125rem', minHeight: 44 }}>
          लॉग आउट (Log out)
        </button>
      </div>
    </div>
  );
}
