import { useEffect, useState } from 'react';
import { appStore } from './store';
import { UPDATED_EVENT } from './offlinePlans';

/** This subject's record of prepared plans (offlinePlans.refreshIfNeeded), kept up to date as the background preparation runs. null: none. */
export function useOfflineMeta(domain) {
  const [meta, setMeta] = useState(null);
  useEffect(() => {
    let alive = true;
    const read = async () => { try { const s = await appStore(); const m = await s.get('meta', domain); if (alive) setMeta(m || null); } catch { if (alive) setMeta(null); } };
    read();
    const on = (e) => { if (!e.detail || e.detail === domain) read(); };
    window.addEventListener(UPDATED_EVENT, on);
    return () => { alive = false; window.removeEventListener(UPDATED_EVENT, on); };
  }, [domain]);
  return meta;
}
