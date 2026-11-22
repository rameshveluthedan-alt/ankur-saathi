/**
 * When the phone prepares its offline plans (docs/drafts/OFFLINE_ASSEMBLER_PLAN.md, decision 3): at sign-in and when the Plan screen opens,
 * only while online, at most once a day unless what they are prepared from changed (offlinePlans.refreshIfNeeded decides), and at once on the
 * "download now" tap. It never blocks the screen: it runs in the background and the status line listens for UPDATED_EVENT.
 */
import * as api from '../services/api';
import { isOnline } from '../services/network';
import { localToday } from '../services/today';
import { appStore, requestPersistence } from './store';
import { refreshIfNeeded, clearOfflinePlans, DOMAINS } from './offlinePlans';

// called through the module (not named imports), so a screen test that stubs the API with only the calls it uses still builds; a missing call
// only makes the background preparation fail quietly, as with no connection
const API = {
  getGroupProposal: (...a) => api.getGroupProposal(...a), getGroups: (...a) => api.getGroups(...a),
  getLadder: (...a) => api.getLadder(...a), prepareOfflinePlans: (...a) => api.prepareOfflinePlans(...a),
};
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
