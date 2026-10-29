// A failure in words a teacher can act on, instead of the server's raw (often English) text. PURE apart from bi() (the "Hindi only" setting).
// What went wrong (`action`, e.g. "योजना नहीं बन सकी") + why, in plain Hindi with its English, + what to do. A message the server already wrote for the teacher
// (in Hindi) is kept as it is; the offline message is already plain. The raw text goes to the console for whoever debugs it.
import { bi } from './language';

const HINDI = /[ऀ-ॿ]/;

export const WHY = {
  server: { hi: 'सर्वर अभी जवाब नहीं दे रहा। थोड़ी देर बाद फिर कोशिश करें।', en: "The server isn't answering right now. Try again in a little while." },
  notFound: { hi: 'ज़रूरी जानकारी नहीं मिली। पेज दोबारा खोलकर फिर कोशिश करें।', en: "Something needed wasn't found. Reopen the page and try again." },
  badInput: { hi: 'भेजी गई जानकारी में कुछ ठीक नहीं है। जाँचकर फिर कोशिश करें।', en: "Something in what was sent isn't right. Check it and try again." },
  signIn: { hi: 'कृपया फिर से लॉगिन करें।', en: 'Please sign in again.' },
};

/**
 * e: the error from services/api.js (status, code, message; NetworkError when offline). action: { hi, en }, what could not be done.
 * byStatus: optional plainer reasons for this action, e.g. { 404: { hi: 'यह रोल नंबर इस कक्षा में नहीं है।', en: '…' } }.
 */
export function friendlyError(e, action, byStatus = {}) {
  const what = bi(action.hi, action.en);
  if (e && (e.offline || e.name === 'NetworkError')) return e.message;                 // already plain: "इंटरनेट नहीं है…"
  const msg = String((e && e.message) || '');
  if (typeof console !== 'undefined' && msg) console.warn(`[${action.en}]`, e && e.status, msg);
  const status = e && e.status;
  if (byStatus[status]) return `${what}। ${bi(byStatus[status].hi, byStatus[status].en)}`;
  if (HINDI.test(msg)) return `${what}: ${msg}`;                                        // the server wrote it for the teacher
  if (status === 401 || status === 403) return `${what}। ${bi(WHY.signIn.hi, WHY.signIn.en)}`;
  if (status === 404) return `${what}। ${bi(WHY.notFound.hi, WHY.notFound.en)}`;
  if (status >= 400 && status < 500) return `${what}। ${bi(WHY.badInput.hi, WHY.badInput.en)}`;
  return `${what}। ${bi(WHY.server.hi, WHY.server.en)}`;                                // 5xx, or no answer we can read
}
