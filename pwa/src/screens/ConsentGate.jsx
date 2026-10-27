import React, { useState } from 'react';
import { useAuth } from '../App';
import { adminRecordConsent } from '../services/api';
import { CONSENT } from '../services/consent';
import Bi from '../components/Bi';
import { bi } from '../services/language';

// Shown ONCE, to the SCHOOL LEADER, at the first sign-in of a school that has no confirmation on record (a demonstration school carries its own statement, so it never sees this).
// The school's teachers are never asked: the school confirms once, through its leader. The wording is kept with the date and the version (docs/PRIVACY.md, "Consent").
export default function ConsentGate() {
  const { teacher, setTeacher, logout } = useAuth();
  const [checked, setChecked] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const confirm = async () => {
    setLoading(true); setError('');
    try { await adminRecordConsent(CONSENT.version); setTeacher({ ...teacher, consent_needed: false }); }
    catch (e) { setError(e.message || bi('पुष्टि दर्ज नहीं हो सकी', 'Could not save the confirmation')); }
    setLoading(false);
  };

  return (
    <div className="screen" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', minHeight: '100dvh' }}>
      <div className="card" data-testid="consent-gate">
        <h2>🏫 <Bi hi="स्कूल की एक पुष्टि" en="One confirmation for your school" /></h2>
        <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', margin: '6px 0 10px' }}>
          <Bi hi="आप इस स्कूल के लीडर हैं। ऐप इस्तेमाल करने से पहले, पहली बार, यह पुष्टि चाहिए।" en="You are this school’s leader. We need this confirmation once, before the app is used." />
        </p>
        {/* the statement itself always shows BOTH languages, even with "Hindi only": the leader confirms its exact wording */}
        <div style={{ background: 'var(--green-bg)', border: '1px solid var(--green-light)', borderRadius: 8, padding: 10, marginBottom: 10 }}>
          <p lang="hi" data-testid="consent-hi" style={{ fontSize: '0.875rem', margin: '0 0 6px' }}>{CONSENT.hi}</p>
          <p lang="en" data-testid="consent-en" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: 0 }}>{CONSENT.en}</p>
        </div>
        <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.875rem', minHeight: 44 }}>
          <input type="checkbox" checked={checked} onChange={e => setChecked(e.target.checked)} data-testid="consent-check" style={{ width: 24, height: 24 }} />
          <span><Bi hi="हाँ, यह सही है" en="Yes, this is correct" inline /></span>
        </label>
        {error && <p data-testid="consent-error" role="alert" style={{ color: 'var(--beginner)', fontSize: '0.8125rem', margin: '6px 0' }}>{error}</p>}
        <button className="btn btn-primary" style={{ marginTop: 8 }} onClick={confirm} disabled={!checked || loading} data-testid="consent-continue">
          {loading ? 'दर्ज हो रहा है...' : <Bi hi="पुष्टि करें और आगे बढ़ें" en="Confirm and continue" inline />}
        </button>
        <button type="button" onClick={logout} style={{ display: 'block', margin: '12px auto 0', background: 'none', border: 'none', color: 'var(--text-secondary)', textDecoration: 'underline', fontSize: '0.8125rem', minHeight: 44 }}>
          <Bi hi="लॉग आउट" en="Log out" inline />
        </button>
      </div>
    </div>
  );
}
