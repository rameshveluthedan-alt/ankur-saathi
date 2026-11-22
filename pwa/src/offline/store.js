/**
 * Storage on the phone for plans with no connection (docs/drafts/OFFLINE_ASSEMBLER_PLAN.md, decision 4): IndexedDB, not localStorage, whose
 * ~5 MB cap the prepared plans (about 4 MB) would nearly fill. Three stores, all PRIVATE (they hold the class's roll numbers), removed at sign-out:
 *   prepared   one record per prepared plan, under its key (offlinePlans.planKey)
 *   meta       per subject: when the plans were prepared, for which skills and days, the library's version, what they were prepared from
 *   outbox     plans made offline, waiting to be sent (step 4)
 * A plain key-value interface, so the tests (and a browser with no IndexedDB) use the same code on memory.
 */

export const DB_NAME = 'ankur-offline';
export const STORES = ['prepared', 'meta', 'outbox'];
const VERSION = 1;

/** The same interface on memory: for the tests, and for a browser without IndexedDB (then nothing survives a reload, and the status says not ready). */
export function memoryStore() {
  const data = Object.fromEntries(STORES.map((s) => [s, new Map()]));
  return {
    kind: 'memory',
    get: async (store, key) => (data[store].has(key) ? structuredCloneSafe(data[store].get(key)) : undefined),
    set: async (store, key, value) => { data[store].set(key, structuredCloneSafe(value)); },
    setMany: async (store, entries) => { for (const [k, v] of entries) data[store].set(k, structuredCloneSafe(v)); },
    del: async (store, key) => { data[store].delete(key); },
    keys: async (store) => [...data[store].keys()],
    all: async (store) => [...data[store].values()].map(structuredCloneSafe),
    clear: async (store) => { data[store].clear(); },
  };
}

function structuredCloneSafe(v) {
  return v === undefined ? v : JSON.parse(JSON.stringify(v));
}

function req(r) {
  return new Promise((resolve, reject) => { r.onsuccess = () => resolve(r.result); r.onerror = () => reject(r.error); });
}

/** The IndexedDB store, or the memory one when IndexedDB is missing or refuses (a private window in some browsers). */
export async function openStore(idb = (typeof indexedDB !== 'undefined' ? indexedDB : null)) {
  if (!idb) return memoryStore();
  let db;
  try {
    db = await new Promise((resolve, reject) => {
      const open = idb.open(DB_NAME, VERSION);
      open.onupgradeneeded = () => { for (const s of STORES) if (!open.result.objectStoreNames.contains(s)) open.result.createObjectStore(s); };
      open.onsuccess = () => resolve(open.result);
      open.onerror = () => reject(open.error);
      open.onblocked = () => reject(new Error('blocked'));
    });
  } catch {
    return memoryStore();
  }
  const tx = (store, mode) => db.transaction(store, mode).objectStore(store);
  const done = (t) => new Promise((resolve, reject) => { t.oncomplete = () => resolve(); t.onerror = () => reject(t.error); t.onabort = () => reject(t.error); });
  return {
    kind: 'indexeddb',
    get: (store, key) => req(tx(store, 'readonly').get(key)),
    set: async (store, key, value) => { const t = db.transaction(store, 'readwrite'); t.objectStore(store).put(value, key); await done(t); },
    setMany: async (store, entries) => { const t = db.transaction(store, 'readwrite'); const os = t.objectStore(store); for (const [k, v] of entries) os.put(v, k); await done(t); },
    del: async (store, key) => { const t = db.transaction(store, 'readwrite'); t.objectStore(store).delete(key); await done(t); },
    keys: (store) => req(tx(store, 'readonly').getAllKeys()),
    all: (store) => req(tx(store, 'readonly').getAll()),
    clear: async (store) => { const t = db.transaction(store, 'readwrite'); t.objectStore(store).clear(); await done(t); },
  };
}

let shared = null;
/** The app's one store (opened once). */
export function appStore() {
  if (!shared) shared = openStore();
  return shared;
}

/** Ask the browser to keep this app's data under storage pressure (decision 4). Most Android browsers grant it to an installed app. */
export async function requestPersistence(nav = (typeof navigator !== 'undefined' ? navigator : null)) {
  try {
    if (nav && nav.storage && nav.storage.persisted && await nav.storage.persisted()) return true;
    if (nav && nav.storage && nav.storage.persist) return !!(await nav.storage.persist());
  } catch { /* not supported */ }
  return false;
}
