import React, { useEffect, useState } from 'react';
import { isOnline, subscribe } from '../services/network';

// true while the phone can reach the server; screens use it to say WHY a button is off, not just switch it off
export function useOnline() {
  const [online, setOnline] = useState(isOnline());
  useEffect(() => { setOnline(isOnline()); return subscribe(() => setOnline(isOnline())); }, []);
  return online;
}

export const NEEDS_INTERNET = 'इंटरनेट चाहिए (needs the internet)';

export default function OfflineBanner() {
  const online = useOnline();
  if (online) return null;
  return (
    <div role="status" data-testid="offline-banner"
      style={{ background: '#E8EEF4', color: '#26405A', fontSize: '0.72rem', padding: '5px 10px', textAlign: 'center', borderBottom: '1px solid #C9D6E3' }}>
      📴 इंटरनेट नहीं है। पहले खुली योजना और वर्कशीट दिखेंगी; नई योजना बनाने और फ़ोटो भेजने के लिए इंटरनेट चाहिए।
      <div className="en" lang="en" style={{ fontSize: '0.6875rem', color: 'inherit', opacity: 0.85 }}>Offline. Plans and worksheets you already opened are available; making a new plan and sending photos need the internet.</div>
    </div>
  );
}
