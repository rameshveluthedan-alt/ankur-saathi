/**
 * When the phone prepares its offline plans (docs/drafts/OFFLINE_ASSEMBLER_PLAN.md, decision 3): at sign-in and when the Plan screen opens,
 * only while online, at most once a day unless what they are prepared from changed (offlinePlans.refreshIfNeeded decides), and at once on the
 * "download now" tap. It never blocks the screen: it runs in the background and the status line listens for UPDATED_EVENT.
 */
import * as api from '../services/api';
import { isOnline } from '../services/network';
import { localToday } from '../services/today';
import { appStore, requestPersistence } from './store';
import { refreshIfNeeded, clearOfflinePlans, DOMAINS, sendWaiting, waitingPlans, dropOthersPlans, clearOutbox } from './offlinePlans';
import { notify } from '../services/notify';
import { bi } from '../services/language';

// called through the module (not named imports), so a screen test that stubs the API with only the calls it uses still builds; a missing call
// only makes the background preparation fail quietly, as with no connection
const API = {
  getCompetencies: (...a) => api.getCompetencies(...a), getGroupProposal: (...a) => api.getGroupProposal(...a), getGroups: (...a) => api.getGroups(...a),
  getLadder: (...a) => api.getLadder(...a), prepareOfflinePlans: (...a) => api.prepareOfflinePlans(...a),
  uploadOfflinePlan: (...a) => api.uploadOfflinePlan(...a),
};
export const SENT_EVENT = 'ankur-offline-sent';
let askedPersistence = false;

/** Prepare (if needed) the offline plans of these subjects. Returns the subjects' status records; never throws. */
export async function prepareOffline(teacherId, domains = DOMAINS, { force = false } = {}) {
  if (!teacherId || !isOnline()) return [];
  if (!askedPersistence) { askedPersistence = true; requestPersistence(); }
  try {
    const store = await appStore();
    return await Promise.all(domains.map((domain) => refreshIfNeeded({ teacherId, domain, today: localToday(), api: API, store, force })));
  } catch {
    return [];
  }
}

/** Everything prepared is removed when the signed-in person changes (api.js setToken). */
export async function clearOffline() {
  try { await clearOfflinePlans(await appStore()); } catch { /* storage unavailable: nothing kept */ }
}

let sending = null;

/**
 * Send the plans made offline (step 4) while online: at opening, at sign-in and whenever the connection comes back. Tells the teacher what
 * happened and announces the results (SENT_EVENT) so the screen holding an offline plan can show the stored one. Never throws.
 */
export function sendOffline(teacherId) {
  if (!teacherId || !isOnline()) return Promise.resolve([]);
  if (sending) return sending;
  sending = (async () => {
    try {
      const store = await appStore();
      await dropOthersPlans(store, teacherId);
      const results = await sendWaiting({ teacherId, api: API, store });
      const sent = results.filter((r) => r.status === 'stored' || r.status === 'duplicate').length;
      const kept = results.filter((r) => r.status === 'kept_server').length;
      const refused = results.filter((r) => r.status === 'refused').length;
      if (sent) notify(bi(`बिना इंटरनेट के बनी ${sent} योजना सर्वर पर भेज दी गई। अब उसकी समीक्षा हो सकती है।`, `${sent} plan(s) made with no internet sent to the server. It can now be reviewed.`), 'success');
      if (kept) notify(bi('उस दिन की योजना पहले से सर्वर पर थी; वही रखी गई और फ़ोन वाली हटा दी गई।', "A plan for that day was already on the server; that one is kept and the phone's copy removed."), 'info');
      if (refused) notify(bi('बिना इंटरनेट की एक योजना सर्वर ने नहीं ली। वह फ़ोन पर रहेगी; ज़रूरत हो तो नई योजना बनाएँ।', "The server did not accept a plan made with no internet. It stays on the phone; make a new plan if needed."), 'error');
      if (results.length) { try { window.dispatchEvent(new CustomEvent(SENT_EVENT, { detail: results })); } catch { /* no window */ } }
      return results;
    } catch {
      return [];
    } finally {
      sending = null;
    }
  })();
  return sending;
}

/** How many plans made offline are not yet sent (sign-out asks first when there are any). */
export async function waitingCount(teacherId) {
  try { return (await waitingPlans(await appStore(), teacherId)).length; } catch { return 0; }
}

/** The teacher chose to sign out: the plans made offline go too (asked first by the Profile screen when any is unsent). */
export async function clearOfflineOutbox() {
  try { await clearOutbox(await appStore()); } catch { /* nothing kept */ }
}
