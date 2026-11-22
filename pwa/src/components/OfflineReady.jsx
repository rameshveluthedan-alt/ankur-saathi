import React, { useEffect, useState } from 'react';
import Bi from './Bi';
import { appStore } from '../offline/store';
import { statusOf, UPDATED_EVENT } from '../offline/offlinePlans';
import { prepareOffline } from '../offline/prepareNow';
import { useOnline } from './OfflineBanner';

/** "12 नवंबर" style day for the status line (no year: the buffer is a few days). */
function dayLabel(iso) {
  if (!iso) return '';
  const months = ['जनवरी', 'फ़रवरी', 'मार्च', 'अप्रैल', 'मई', 'जून', 'जुलाई', 'अगस्त', 'सितंबर', 'अक्टूबर', 'नवंबर', 'दिसंबर'];
  const monthsEn = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const [, m, d] = iso.split('-').map(Number);
  return { hi: `${d} ${months[m - 1]}`, en: `${d} ${monthsEn[m - 1]}` };
}

/**
 * The Plan screen's line about plans with no connection (docs/drafts/OFFLINE_ASSEMBLER_PLAN.md, decision 5): ready (until which day), being
 * prepared, not possible yet (no plan made in this subject), or not ready, with a "download now" tap while online.
 */
export default function OfflineReady({ teacherId, domain }) {
  const online = useOnline();
  const [status, setStatus] = useState({ state: 'missing' });
  useEffect(() => {
    let alive = true;
    const read = async () => { try { const s = await appStore(); const meta = await s.get('meta', domain); if (alive) setStatus(statusOf(meta)); } catch { /* none */ } };
    read();
    const on = (e) => { if (!e.detail || e.detail === domain) read(); };
    window.addEventListener(UPDATED_EVENT, on);
    return () => { alive = false; window.removeEventListener(UPDATED_EVENT, on); };
  }, [domain]);

  const box = { fontSize: '0.75rem', color: 'var(--text-secondary)', margin: '0 0 12px', display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' };
  if (status.state === 'ready') {
    const until = dayLabel(status.until);
    return (
      <div data-testid="offline-ready" data-state="ready" style={box}>
        <span>✓ <Bi hi={`ऑफ़लाइन योजना तैयार (${until.hi} तक, ${status.skills.length} कौशल)`} en={`Offline plans ready (until ${until.en}, ${status.skills.length} skills)`} inline /></span>
      </div>
    );
  }
  if (status.state === 'preparing') {
    return <div data-testid="offline-ready" data-state="preparing" style={box}>⏳ <Bi hi="बिना इंटरनेट की योजनाएँ तैयार हो रही हैं…" en="Preparing plans for use with no internet…" inline /></div>;
  }
  if (status.state === 'no_history') {
    return (
      <div data-testid="offline-ready" data-state="no_history" style={box}>
        <Bi hi="बिना इंटरनेट की योजना के लिए पहले इस विषय की एक योजना इंटरनेट के साथ बनाएँ।" en="For plans with no internet, first make one plan in this subject while online." inline />
      </div>
    );
  }
  return (
    <div data-testid="offline-ready" data-state="missing" style={box}>
      <Bi hi="बिना इंटरनेट की योजना अभी तैयार नहीं।" en="Plans for use with no internet are not ready yet." inline />
      {online && (
        <button type="button" className="btn btn-secondary btn-small" data-testid="offline-download" style={{ minHeight: 44 }}
          onClick={() => prepareOffline(teacherId, [domain], { force: true })}>
          ⬇ <Bi hi="अभी डाउनलोड करें" en="Download now" inline />
        </button>
      )}
    </div>
  );
}
