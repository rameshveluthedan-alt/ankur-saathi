import React, { useState } from 'react';
import { useAuth } from '../App';
import { changePin, setToken } from '../services/api';

const digits = (v) => v.replace(/\D/g, '').slice(0, 6);
const field = { width: '100%', padding: '12px 16px', fontSize: '1.125rem', border: '2px solid var(--border)', borderRadius: 10, fontFamily: 'inherit', marginBottom: 10, letterSpacing: 8 };

// Choose a new PIN. Used on the account page, and as the ONLY screen after an admin reset (forced).
export function PinChangeForm({ forced = false, onDone }) {
  const { teacher, setTeacher } = useAuth();
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [again, setAgain] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    if (next !== again) { setError('नए पिन एक जैसे नहीं हैं (The new PINs do not match).'); return; }
    setLoading(true); setError('');
    try {
      const res = await changePin(current, next);
      setToken(res.token);
      const { token, join_code, ...profile } = res;
      setTeacher({ ...teacher, ...profile });
      setCurrent(''); setNext(''); setAgain('');
      if (onDone) onDone();
    } catch (e) { setError(e.message || 'पिन नहीं बदला जा सका (Could not change the PIN)'); }
    setLoading(false);
  };

  return (
    <div data-testid="pin-form">
      <label style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>{forced ? 'अस्थायी पिन जो एडमिन ने दिया (The temporary PIN from your admin)' : 'वर्तमान पिन (Current PIN)'}</label>
      <input type="password" inputMode="numeric" value={current} onChange={e => setCurrent(digits(e.target.value))} data-testid="pin-current" style={field} autoComplete="current-password" />
      <label style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>नया पिन, 4 से 6 अंक (New PIN, 4 to 6 digits)</label>
      <input type="password" inputMode="numeric" value={next} onChange={e => setNext(digits(e.target.value))} data-testid="pin-new" style={field} autoComplete="new-password" />
      <label style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>नया पिन दोबारा (Repeat the new PIN)</label>
      <input type="password" inputMode="numeric" value={again} onChange={e => setAgain(digits(e.target.value))} data-testid="pin-new-again" style={field} autoComplete="new-password" />
      {error && <p data-testid="pin-error" style={{ color: 'var(--beginner)', fontSize: '0.8125rem', marginBottom: 8 }}>{error}</p>}
      <button className="btn btn-primary" onClick={submit} disabled={loading || current.length < 4 || next.length < 4} data-testid="pin-save">
        {loading ? 'सहेज रहे हैं...' : 'नया पिन सहेजें (Save new PIN)'}
      </button>
    </div>
  );
}

export default function ChangePinScreen({ forced = false }) {
  const { logout } = useAuth();
  return (
    <div className="screen" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', minHeight: '100dvh' }}>
      <div className="card" data-testid="forced-pin-change">
        <h2>🔑 नया पिन चुनें (Choose a new PIN)</h2>
        <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', margin: '6px 0 12px' }}>
          आपके एडमिन ने आपका पिन रीसेट किया है। जारी रखने से पहले अपना पिन चुनें। (Your admin reset your PIN. Choose your own before you continue.)
        </p>
        <PinChangeForm forced={forced} />
        <button type="button" onClick={logout} style={{ display: 'block', margin: '12px auto 0', background: 'none', border: 'none', color: 'var(--text-secondary)', textDecoration: 'underline', fontSize: '0.75rem' }}>
          लॉग आउट (Log out)
        </button>
      </div>
    </div>
  );
}
