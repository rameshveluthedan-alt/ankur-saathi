/**
 * Plans with no connection (docs/drafts/OFFLINE_ASSEMBLER_PLAN.md, revised 23 Nov): the server prepares, through its own pipeline and with no AI,
 * a plan for EVERY skill of the subject at 45 / 60 / 90 minutes (the derived group skills, moving on), so with no network the teacher can plan any
 * day's skill as online. One prepared copy serves any day (only the anchor setting and the independent activities rotate by date; the photo sample
 * is worked out at upload). Plus, refreshed daily, the suggested skill's own choice as the Plan screen makes it (a suggested re-teach, the
 * suggested group skills), worked out with the screen's OWN logic (initialRows, buildGenerateOptions).
 *
 * For low-end phones: the plans come in small batches (BATCH), each saved before the next is asked for, so the phone never holds more than about
 * a megabyte, and an interrupted download continues where it stopped; the full set is downloaded again only when the library changes or after
 * REFRESH_DAYS, never just because the groups changed (the groups used are the phone's latest, put in when a plan is used).
 */
import { initialRows, buildGenerateOptions } from '../services/groupSkills';

export const MINUTES = [45, 60, 90];
export const DOMAINS = ['numeracy', 'r1_literacy'];
export const UPDATED_EVENT = 'ankur-offline-updated';
export const BATCH = 25;               // plans per request: about 1 MB of text on a low-end phone, then saved
export const REFRESH_DAYS = 7;         // the full set again at most weekly unless the library changed

/** One choice's key: the subject, the length, the Progressors' skill, the other groups' chosen skills and the re-taught groups (no date). */
export function planKey({ domain, minutes, competencyId, groupSkills, reteachGroups }) {
  const gs = Object.entries(groupSkills || {}).filter(([, v]) => v).sort(([a], [b]) => a.localeCompare(b)).map(([k, v]) => `${k}=${v}`).join(',');
  const rt = [...(reteachGroups || [])].sort().join('+');
  return [domain, Number(minutes), competencyId, gs, rt].join('|');
}
const plainKey = (domain, minutes, competencyId) => planKey({ domain, minutes, competencyId });

/** The next n school days from `today` (YYYY-MM-DD, the phone's own date: services/today.js), today included, Sundays left out. Only counts
 * calendar days forward from that date (a UTC midnight is used as a plain calendar, never to find out what today is). */
export function schoolDays(today, n = 2) {
  const out = [];
  const d = new Date(`${today}T00:00:00Z`);
  const two = (x) => String(x).padStart(2, '0');
  while (out.length < n) {
    if (d.getUTCDay() !== 0) out.push(`${d.getUTCFullYear()}-${two(d.getUTCMonth() + 1)}-${two(d.getUTCDate())}`);
    d.setUTCDate(d.getUTCDate() + 1);
  }
  return out;
}

/** The skill the app suggests (the "⭐ सुझाया गया" card's): what the last review points to for the Progressors, else the skill they were last
 * taught, else the previous plan's own skill. */
export function suggestedSkill(proposal) {
  const p = proposal && proposal.has_history ? (proposal.groups || {}).progressor : null;
  return (p && p.proposed && p.proposed.id) || (p && p.previous_target && p.previous_target.id) || (proposal && proposal.has_history && proposal.previous_selected) || null;
}

/** The suggested skill's own choices as the Plan screen makes them (its suggested group skills and re-teach, and moving on), when they differ
 * from the plain one every skill has. [] when nothing is suggested. */
export async function suggestedChoices({ proposal, groups, getLadder }) {
  const skill = suggestedSkill(proposal);
  if (!skill) return [];
  const ladder = await Promise.resolve().then(() => getLadder(skill)).catch(() => null);
  if (!ladder) return [];
  const init = initialRows({ ladder, proposal, selectedId: skill });
  const opts = buildGenerateOptions({ rows: init.rows, reteach: init.reteach, groups, ready: true });
  const out = [{ competencyId: skill, groupSkills: opts.groupSkills, reteachGroups: opts.reteachGroups || [] }];
  if ((opts.reteachGroups || []).length) out.push({ competencyId: skill, groupSkills: opts.groupSkills, reteachGroups: [] });
  return out.filter((c) => c.groupSkills || c.reteachGroups.length);          // the plain choice is in the full set already
}

/** The request's items: every choice at every length. plan_date: the day they are prepared on (one copy serves any day). */
export function itemsFor(domain, choices, date) {
  const items = [];
  for (const c of choices) {
    for (const minutes of MINUTES) {
      items.push({ key: planKey({ domain, minutes, ...c }), competency_id: c.competencyId, plan_date: date, session_minutes: minutes,
                   reteach_groups: c.reteachGroups || [], ...(c.groupSkills ? { group_skills: c.groupSkills } : {}) });
    }
  }
  return items;
}

/** A short fingerprint (the suggestions): the suggested part is prepared again when it changes. */
export function fingerprint(value) {
  const s = JSON.stringify(value || null);
  let h = 2166136261;
  for (let i = 0; i < s.length; i += 1) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return (h >>> 0).toString(16);
}

const DAY_MS = 86400000;
const inFlight = new Map();
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function fetchBatched({ api, teacherId, domain, items, store, kind, epoch, onBatch, batch, pause }) {
  let version = null; let ok = 0; let failed = 0;
  for (let i = 0; i < items.length; i += batch) {
    const res = await api.prepareOfflinePlans(teacherId, domain, items.slice(i, i + batch));
    version = (res && res.library_version) || version;
    const got = ((res && res.plans) || []).filter((p) => p.ok && p.result);
    failed += ((res && res.plans) || []).length - got.length;
    ok += got.length;
    if (got.length) await store.setMany('prepared', got.map((p) => [p.key, { key: p.key, domain, kind, epoch, result: p.result }]));
    if (onBatch) await onBatch(Math.min(i + batch, items.length), version);
    if (pause && i + batch < items.length) await sleep(pause);          // a breath between batches: the app stays usable on a slow phone
  }
  return { version, ok, failed };
}

/**
 * Prepare this subject's plans: the suggested choices when the day or the suggestions changed, and the full set when it is missing, unfinished,
 * older than REFRESH_DAYS, or the library changed (or on the "download now" tap: force). api: { getCompetencies, getGroupProposal, getGroups,
 * getLadder, prepareOfflinePlans }. Returns the subject's status record. Never throws: with no connection what was prepared stays usable.
 */
export function refreshIfNeeded({ teacherId, domain, today, api, store, force = false, emit = defaultEmit, batch = BATCH, pause = 250, now = () => Date.now() }) {
  const k = `${teacherId}|${domain}`;
  if (inFlight.has(k)) return inFlight.get(k);
  const run = (async () => {
    let meta = (await store.get('meta', domain)) || { domain, status: 'missing', count: 0 };
    const save = async (m) => { meta = m; await store.set('meta', domain, m); emit(domain); };
    const countOf = async () => (await store.keys('prepared')).filter((key) => String(key).startsWith(`${domain}|`)).length;
    try {
      const [compData, first, groupData] = await Promise.all([api.getCompetencies(domain), api.getGroupProposal(teacherId, domain, today), api.getGroups(teacherId, domain)]);
      const skills = ((compData && compData.competencies) || []).map((c) => c.id).filter(Boolean);
      const groups = (groupData && groupData.groups) || [];
      let proposal = first;            // nothing suggested from the plans BEFORE today (the first plan is today's): the next school day's suggestions count it
      if (!suggestedSkill(first)) {
        const later = await Promise.resolve().then(() => api.getGroupProposal(teacherId, domain, schoolDays(today, 2)[1])).catch(() => null);
        if (suggestedSkill(later)) proposal = later;
      }
      meta = { ...meta, groups };       // the latest groups: put into a plan when it is used offline (makeOfflinePlan)
      let version = meta.libraryVersion || null;
      // 1. the suggested skill's own choices (a few plans), daily or when the suggestions change
      const fp = fingerprint(proposal);
      if (force || meta.suggestedFor !== today || meta.suggestedFp !== fp) {
        const choices = await suggestedChoices({ proposal, groups, getLadder: api.getLadder });
        const keep = new Set(itemsFor(domain, choices, today).map((i) => i.key));
        for (const key of await store.keys('prepared')) {
          const r = await store.get('prepared', key);
          if (r && r.domain === domain && r.kind === 'suggested' && !keep.has(key)) await store.del('prepared', key);
        }
        if (choices.length) {
          const got = await fetchBatched({ api, teacherId, domain, items: itemsFor(domain, choices, today), store, kind: 'suggested', batch, pause: 0 });
          version = got.version || version;
        }
        const defaults = {};
        if (choices.length) defaults[choices[0].competencyId] = { groupSkills: choices[0].groupSkills || null, reteachGroups: choices[0].reteachGroups || [] };
        await save({ ...meta, suggestedFor: today, suggestedFp: fp, defaults });
      }
      // 2. the full set: every skill at every length
      const stale = !meta.fullDoneAt || now() - Date.parse(meta.fullDoneAt) >= REFRESH_DAYS * DAY_MS;
      const libraryChanged = !!(version && meta.libraryVersion && version !== meta.libraryVersion);
      const unfinished = !!(meta.fullEpoch && !meta.fullDoneAt);
      const newSkills = skills.some((id) => !(meta.skills || []).includes(id));
      if (force || stale || libraryChanged || unfinished || newSkills) {
        const continuing = unfinished && !force && !libraryChanged;
        const epoch = continuing ? meta.fullEpoch : `${today}-${now().toString(36)}`;
        const all = itemsFor(domain, skills.map((id) => ({ competencyId: id })), today);
        const have = new Set();
        if (continuing) {
          for (const key of await store.keys('prepared')) { const r = await store.get('prepared', key); if (r && r.domain === domain && r.epoch === epoch) have.add(key); }
        }
        const todo = all.filter((i) => !have.has(i.key));
        await save({ ...meta, preparing: true, fullEpoch: epoch, fullDoneAt: null, total: all.length, done: have.size });
        const res = await fetchBatched({ api, teacherId, domain, items: todo, store, kind: 'plain', epoch, batch, pause,
          onBatch: async (n) => save({ ...meta, done: have.size + n }) });
        version = res.version || version;
        const current = new Set(all.map((i) => i.key));         // the plain plans of an older set, or of a skill no longer in the list, go
        for (const key of await store.keys('prepared')) {
          const r = await store.get('prepared', key);
          if (r && r.domain === domain && (!r.kind || (r.kind === 'plain' && (r.epoch !== epoch || !current.has(key))))) await store.del('prepared', key);       // !kind: kept by the first version (keys with a date)
        }
        meta = { ...meta, fullDoneAt: new Date(now()).toISOString(), libraryVersion: version, failed: res.failed };
      }
      const plainSkills = new Set();
      for (const key of await store.keys('prepared')) { const parts = String(key).split('|'); if (parts[0] === domain && parts[3] === '' && parts[4] === '') plainSkills.add(parts[2]); }
      const count = await countOf();
      await save({ ...meta, preparing: false, status: count ? (meta.fullDoneAt ? 'ready' : 'partial') : 'missing', count, skills: [...plainSkills],
                   libraryVersion: version || meta.libraryVersion || null, lastError: null });
      return meta;
    } catch (e) {
      // no connection or a server error: what was prepared stays usable; an unfinished set continues next time
      const plainSkills = new Set();
      for (const key of await store.keys('prepared')) { const parts = String(key).split('|'); if (parts[0] === domain && parts[3] === '' && parts[4] === '') plainSkills.add(parts[2]); }
      const kept = await countOf();
      await save({ ...meta, preparing: false, count: kept, skills: [...plainSkills], status: kept ? (meta.fullDoneAt ? 'ready' : 'partial') : 'missing',
                   lastError: (e && (e.code || e.name)) || 'error', lastTriedAt: new Date(now()).toISOString() });
      return meta;
    } finally {
      inFlight.delete(k);
    }
  })();
  inFlight.set(k, run);
  return run;
}

function defaultEmit(domain) {
  try { window.dispatchEvent(new CustomEvent(UPDATED_EVENT, { detail: domain })); } catch { /* no window (tests) */ }
}

/**
 * What the Plan screen says about this subject: 'ready' (every skill), 'preparing' (with how far), 'partial' (an interrupted download: the skills
 * already there can be planned), or 'missing'.
 */
export function statusOf(meta) {
  if (!meta) return { state: 'missing', skills: [] };
  if (meta.preparing) return { state: 'preparing', done: meta.done || 0, total: meta.total || 0, skills: meta.skills || [] };
  if (meta.status === 'ready' && meta.count > 0) return { state: 'ready', skills: meta.skills || [] };
  if (meta.status === 'partial' && meta.count > 0) return { state: 'partial', skills: meta.skills || [], total: meta.total || 0 };
  return { state: 'missing', skills: [], lastError: meta.lastError || null };
}

/**
 * The prepared plan for this choice: the exact choice if it was prepared; else, when the teacher did NOT change the groups' skills or the
 * re-teach ticks (allowPlain), the skill's plain plan (the derived group skills, moving on). null: not prepared (a changed group skill, a re-teach
 * the evidence did not suggest, a skill whose download has not come yet).
 */
export async function findPrepared(store, { domain, minutes, competencyId, groupSkills, reteachGroups, allowPlain = false }) {
  const hit = await store.get('prepared', planKey({ domain, minutes, competencyId, groupSkills, reteachGroups }));
  if (hit) return { record: hit };
  if (allowPlain) {
    const plain = await store.get('prepared', plainKey(domain, minutes, competencyId));
    if (plain) return { record: plain, plain: true };
  }
  return null;
}

/**
 * The choice to look up offline. The group panel loaded: the screen's own choice, and the plain plan is allowed only if the teacher changed nothing
 * in it. It could not load (usual with no connection): the suggested skill's own choice as prepared, else the plain one.
 */
export function offlineChoice({ meta, competencyId, panelReady, edited = false, options }) {
  if (panelReady) return { groupSkills: options.groupSkills, reteachGroups: options.reteachGroups || [], allowPlain: !edited };
  const d = meta && meta.defaults && meta.defaults[competencyId];
  return d ? { groupSkills: d.groupSkills || undefined, reteachGroups: d.reteachGroups || [], allowPlain: true } : { groupSkills: undefined, reteachGroups: [], allowPlain: true };
}

/** Did the teacher change anything in the group panel (a group's skill, a re-teach tick)? Then only that exact choice may be used. */
export function panelEdited(rows, reteach) {
  if (!rows) return false;
  return Object.entries(rows).some(([label, r]) => r && (r.skillId !== r.initialId || !!(reteach && reteach[label]) !== !!r.initialReteach));
}

/** A fresh id for a plan made offline, so a retry never stores it twice (decision 8). */
export function newClientId(rand = (typeof crypto !== 'undefined' && crypto.randomUUID ? () => crypto.randomUUID() : null)) {
  if (rand) return rand();
  return `off-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

/**
 * The plan the teacher uses offline: the prepared one, dated for the day it is used, marked as made offline, with the latest groups. The server
 * built it; nothing else in it is changed.
 */
export function makeOfflinePlan(result, { date, clientId, teacherId = null, groups = null, now = new Date() }) {
  const out = JSON.parse(JSON.stringify(result));
  // the class's groups as the phone last saw them (a prepared plan may be some days old): each group's children; its skill stays the plan's
  if (Array.isArray(groups) && Array.isArray(out.groups)) {
    for (const g of out.groups) {
      const latest = groups.find((x) => x && x.label === g.label);
      if (latest && Array.isArray(latest.roll_numbers)) { g.roll_numbers = latest.roll_numbers.slice(); g.count = latest.roll_numbers.length; }
      else if (latest && typeof latest.count === 'number') g.count = latest.count;
    }
  }
  out.plan_date = date;
  out.served_from = 'library_offline';
  if (out.plan) out.plan.served_from = 'library_offline';
  out.offline = { client_id: clientId, prepared_for: result.plan_date, made_at: now.toISOString(), sent: false, ...(teacherId ? { teacher_id: teacherId } : {}) };
  return out;
}

/** Offline plans wait in the outbox until sent (step 4): one per subject and day (a second one made offline the same day replaces the first). */
export const outboxKey = (domain, date) => `${domain}|${date}`;
export async function saveOfflinePlan(store, plan) {
  await store.set('outbox', outboxKey(plan.domain_id, plan.plan_date), plan);
}
export async function getOfflinePlan(store, domain, date) {
  return (await store.get('outbox', outboxKey(domain, date))) || null;
}
export async function waitingPlans(store, teacherId = null) {
  return (await store.all('outbox')).filter((p) => p && p.offline && !p.offline.sent && !p.offline.refused
    && (!teacherId || !p.offline.teacher_id || p.offline.teacher_id === teacherId));
}

/**
 * Send the plans made offline (step 4, decision 8), oldest first. Each result: 'stored' or 'duplicate' (on the server now: removed from the
 * phone), 'kept_server' (another plan was already stored for that day: the server's is kept, the phone's removed, the teacher is told),
 * 'refused' (the server could not take it: kept on the phone, never sent again), 'waiting' (no connection or a server error: tried again later;
 * the rest wait too). api: { uploadOfflinePlan }.
 */
export async function sendWaiting({ teacherId, api, store }) {
  const out = [];
  const waiting = (await waitingPlans(store, teacherId)).sort((a, b) => String(a.plan_date).localeCompare(String(b.plan_date)));
  for (const p of waiting) {
    const key = outboxKey(p.domain_id, p.plan_date);
    const body = { client_id: p.offline.client_id, plan_date: p.plan_date, domain_id: p.domain_id, competency_id: p.selected_competency_id,
                   prepared_for: p.offline.prepared_for || null, made_at: p.offline.made_at || null,
                   result: { plan: p.plan, groups: p.groups, explainability: p.explainability } };
    try {
      const r = await api.uploadOfflinePlan(teacherId, body);
      await store.del('outbox', key);
      out.push({ plan: p, status: (r && r.status) === 'duplicate' ? 'duplicate' : 'stored' });
    } catch (e) {
      if (e && e.code === 'plan_exists') {
        await store.del('outbox', key);
        out.push({ plan: p, status: 'kept_server' });
      } else if (e && e.status >= 400 && e.status < 500 && e.status !== 401 && e.status !== 403) {
        await store.set('outbox', key, { ...p, offline: { ...p.offline, refused: true } });
        out.push({ plan: p, status: 'refused' });
      } else {
        out.push({ plan: p, status: 'waiting' });
        break;                                    // no connection (or signed out): the rest wait for the next chance
      }
    }
  }
  return out;
}

/** Plans made offline by ANOTHER teacher on this phone are that teacher's class data: removed when someone else signs in. */
export async function dropOthersPlans(store, teacherId) {
  for (const p of await store.all('outbox')) if (p && p.offline && p.offline.teacher_id && p.offline.teacher_id !== teacherId) await store.del('outbox', outboxKey(p.domain_id, p.plan_date));
}

/** Signing out (after the teacher was asked, if any plan is waiting): the plans made offline go too. */
export async function clearOutbox(store) {
  await store.clear('outbox');
}

/** Everything prepared or waiting is the class's data: removed when the signed-in person changes (store.js). Step 4 asks first about unsent plans. */
export async function clearOfflinePlans(store) {
  await store.clear('prepared');
  await store.clear('meta');
}
