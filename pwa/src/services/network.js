/**
 * What the app knows about the network.
 *
 * Three signals, because each lies in a different way:
 *   1. the browser's online/offline flag: wrong on a phone that shows data bars but gets nothing through ("lie-fi"), the usual situation in a school with a weak signal;
 *   2. a failed request: only a moment, and the service worker answers many requests from its saved copies, so most requests SUCCEED even when the server cannot be reached;
 *   3. a PROBE: a tiny request (/health) that no cache ever answers, so it is the one thing that tells the truth about the server.
 * So the app is "online" when the browser says so AND the last probe or real request did not fail. A page request that succeeds does NOT clear a failure (it may have come from a saved copy):
 * only a probe that gets an answer, or the browser saying "online" followed by a probe that gets an answer, does. While offline the app probes every 15 seconds to notice when it is back.
 */
export const OFFLINE_MESSAGE =
  'इंटरनेट नहीं है या बहुत धीमा है। यह काम इंटरनेट से होता है; जो पहले खोला था वही दिखता है। ' +
  '(No internet, or it is too slow. This needs the internet; what you opened before is still shown.)';

// What a failed request throws, so a screen shows a sentence a teacher can act on and not the browser's "Failed to fetch"
export class NetworkError extends Error {
  constructor() {
    super(OFFLINE_MESSAGE);
    this.name = 'NetworkError';
    this.offline = true;
    this.code = 'offline';
  }
}

export const RECOVERY_MS = 15000;
export const PROBE_PATH = '/health';

let failed = false;
let timer = null;
const listeners = new Set();
const notify = () => listeners.forEach(fn => { try { fn(); } catch { /* a listener must never break a request */ } });
const browserOffline = () => typeof navigator !== 'undefined' && navigator.onLine === false;

export const isOnline = () => !failed && !browserOffline();
export const subscribe = (fn) => { listeners.add(fn); return () => listeners.delete(fn); };

function startRecovery() {
  if (!timer && typeof setInterval === 'function') {
    timer = setInterval(() => { if (!browserOffline()) probe(); }, RECOVERY_MS);        // the browser says offline: wait for its 'online' event instead
    if (timer && typeof timer.unref === 'function') timer.unref();                        // in Node (the tests) a timer must never keep the process alive; in a browser setInterval returns a number
  }
}
function stopRecovery() {
  if (timer) { clearInterval(timer); timer = null; }
}

export function markNetworkFailed() {
  const changed = !failed;
  failed = true;
  startRecovery();
  if (changed) notify();
}

export function markNetworkOk() {
  stopRecovery();
  if (failed) { failed = false; notify(); }
}

// Ask the server a tiny question that is never answered from a cache. Any answer, even an error page, means it can be reached.
export async function probe(fetchFn = (typeof fetch === 'function' ? fetch : null)) {
  if (!fetchFn) return true;
  try {
    await fetchFn(PROBE_PATH, { cache: 'no-store' });
    markNetworkOk();
    return true;
  } catch {
    markNetworkFailed();
    return false;
  }
}

if (typeof window !== 'undefined' && window.addEventListener) {
  window.addEventListener('online', () => { notify(); probe(); });            // the browser's flag just changed: the screens look again at once; then the server must answer before a remembered failure is cleared
  window.addEventListener('offline', notify);
}
if (typeof document !== 'undefined' && document.addEventListener) {
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible' && failed) probe(); });      // the teacher returns to the app: check again at once
}
