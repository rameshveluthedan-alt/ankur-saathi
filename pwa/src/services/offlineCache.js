/**
 * The service worker keeps a teacher's own plan and worksheets so they can be read and printed with no network (vite.config.js). Those pages hold her class's roll numbers,
 * so they must not outlive her sign-in on a shared phone: they are removed whenever the identity changes (signing out, being signed out, signing in).
 * The app itself and the list of skills (public reference data) stay, so the app still opens offline.
 */
import { appStore } from '../offline/store';
import { clearOfflinePlans } from '../offline/offlinePlans';

export const PRIVATE_CACHES = ['plan-cache', 'worksheet-cache'];

/** The plans prepared for use with no connection (IndexedDB, offline/store.js) hold the class's roll numbers too: removed with the caches. */
export async function clearOfflineStore(open = appStore) {
  try { await clearOfflinePlans(await open()); return true; } catch { return false; }
}

export async function clearPrivateCaches(store = (typeof caches !== 'undefined' ? caches : null)) {
  if (!store) return 0;
  let removed = 0;
  try {
    for (const name of PRIVATE_CACHES) if (await store.delete(name)) removed += 1;
  } catch { /* cache storage unavailable: nothing to remove */ }
  return removed;
}
