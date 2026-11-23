import React, { useEffect, useState } from 'react';
import Bi from './Bi';
import { appStore } from '../offline/store';
import { statusOf, UPDATED_EVENT } from '../offline/offlinePlans';
import { prepareOffline } from '../offline/prepareNow';
import { useOnline } from './OfflineBanner';

/**
 * The Plan screen's line about plans with no connection (docs/drafts/OFFLINE_ASSEMBLER_PLAN.md): one plain sentence for the teacher. Ready: a
 * plan can be made even with no internet (every skill is on the phone). Being downloaded (how far). Unfinished or missing: with a "download now"
 * tap while online. No date and no skill count: they answered questions the teacher does not ask (23 Nov).
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
  const download = online && (
    <button type="button" className="btn btn-secondary btn-small" data-testid="offline-download" style={{ minHeight: 44 }}
      onClick={() => prepareOffline(teacherId, [domain], { force: false })}>
      ⬇ <Bi hi="अभी डाउनलोड करें" en="Download now" inline />
    </button>
  );
  if (status.state === 'ready') {
    return <div data-testid="offline-ready" data-state="ready" style={box}>✓ <Bi hi="इंटरनेट न हो तब भी योजना बन जाएगी।" en="A plan can be made even without internet." inline /></div>;
  }
  if (status.state === 'preparing') {
    const pct = status.total ? Math.round((100 * status.done) / status.total) : 0;
    return (
      <div data-testid="offline-ready" data-state="preparing" style={box}>
        ⏳ <Bi hi={`बिना इंटरनेट की योजनाएँ फ़ोन पर आ रही हैं (${pct}%)…`} en={`Bringing plans for use with no internet to the phone (${pct}%)…`} inline />
      </div>
    );
  }
  if (status.state === 'partial') {
    return (
      <div data-testid="offline-ready" data-state="partial" style={box}>
        <Bi hi="बिना इंटरनेट की योजनाएँ पूरी नहीं आईं; जो आ गईं, वे बन जाएँगी।" en="Not all plans for use with no internet have arrived; those that did can be made." inline />
        {download}
      </div>
    );
  }
  return (
    <div data-testid="offline-ready" data-state="missing" style={box}>
      <Bi hi="बिना इंटरनेट की योजना अभी तैयार नहीं।" en="Plans for use with no internet are not ready yet." inline />
      {download}
    </div>
  );
}
