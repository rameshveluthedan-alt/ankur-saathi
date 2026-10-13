import React, { useState } from 'react';
import { useAuth } from '../App';
import { login } from '../services/api';

export default function LoginScreen() {
  const { setTeacher } = useAuth();
  const [phone, setPhone] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async () => {
    if (!phone.trim()) return;
    setLoading(true);
    setError('');
    try {
      // In production: hash the phone number client-side before sending
      const phoneHash = 'hash_' + phone.trim();
      const data = await login(phoneHash);
      setTeacher(data);
    } catch (e) {
      setError('लॉगिन नहीं हो सका। कृपया सही फ़ोन नंबर डालें।');
    }
    setLoading(false);
  };

  return (
    <div className="screen" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', minHeight: '100dvh' }}>
      <div style={{ textAlign: 'center', marginBottom: 32 }}>
        <div style={{ fontSize: '3rem', marginBottom: 8 }}>🌱</div>
        <h1 style={{ fontSize: '1.75rem', color: 'var(--green-dark)' }}>अंकुर साथी</h1>
        <p style={{ color: 'var(--text-secondary)', marginTop: 4 }}>Ankur Saathi</p>
        <p style={{ color: 'var(--text-light)', fontSize: '0.875rem', marginTop: 8 }}>
          AI-powered daily companion for FLN classrooms
        </p>
      </div>

      <div className="card">
        <label style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: 8, display: 'block' }}>
          फ़ोन नंबर डालें
        </label>
        <input
          type="tel"
          value={phone}
          onChange={e => setPhone(e.target.value)}
          placeholder="9876543210"
          style={{
            width: '100%', padding: '12px 16px', fontSize: '1.125rem',
            border: '2px solid var(--border)', borderRadius: 10,
            fontFamily: 'inherit', marginBottom: 12,
          }}
          onKeyDown={e => e.key === 'Enter' && handleLogin()}
        />
        {error && <p style={{ color: 'var(--beginner)', fontSize: '0.875rem', marginBottom: 8 }}>{error}</p>}
        <button className="btn btn-primary" onClick={handleLogin} disabled={loading}>
          {loading ? 'लॉगिन हो रहा है...' : 'लॉगिन करें'}
        </button>
      </div>

      <p style={{ textAlign: 'center', fontSize: '0.75rem', color: 'var(--text-light)', marginTop: 16 }}>
        Demo: "9876543210" डालें
      </p>
    </div>
  );
}
