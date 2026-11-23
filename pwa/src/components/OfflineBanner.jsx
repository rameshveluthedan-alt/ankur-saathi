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
      <span className="hi">📴 इंटरनेट नहीं है। पहले खुली योजना और वर्कशीट दिखेंगी, और फ़ोन पर तैयार कौशलों की योजना बन सकती है; फ़ोटो भेजने और समीक्षा के लिए इंटरनेट चाहिए।</span>
      <div className="en" lang="en" style={{ fontSize: '0.6875rem', color: 'inherit', opacity: 0.85 }}>📴 Offline. Plans and worksheets you already opened are available, and plans for the skills prepared on this phone can be made; sending photos and the review need the internet.</div>
    </div>
  );
}
