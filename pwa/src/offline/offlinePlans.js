/**
 * Plans with no connection, step 2 (docs/drafts/OFFLINE_ASSEMBLER_PLAN.md): WHICH plans the phone may need, preparing them through the server,
 * keeping them (store.js) and saying whether they are ready. The server builds every plan with its own pipeline (POST /api/offline/prepare),
 * so the phone only chooses: for each subject, the suggested skill (the one the last review points to for the Progressors), moving on and its
 * re-teach where the app suggests one, and the next AHEAD skills on its ladder, at 45 / 60 / 90 minutes, for the next DAYS school days.
 * Each choice is worked out with the Plan screen's OWN logic (initialRows, buildGenerateOptions), so the key of a prepared plan is the key the
 * screen will build when the teacher taps Generate offline.
 */
import { initialRows, buildGenerateOptions } from '../services/groupSkills';

export const MINUTES = [45, 60, 90];
export const AHEAD = 3;            // skills ahead on the ladder (decision 1)
export const DAYS = 3;             // school days prepared
export const DOMAINS = ['numeracy', 'r1_literacy'];
export const UPDATED_EVENT = 'ankur-offline-updated';

/** One choice's key: the subject, the day, the length, the Progressors' skill, the other groups' chosen skills and the re-taught groups. */
export function planKey({ domain, date, minutes, competencyId, groupSkills, reteachGroups }) {
  const gs = Object.entries(groupSkills || {}).filter(([, v]) => v).sort(([a], [b]) => a.localeCompare(b)).map(([k, v]) => `${k}=${v}`).join(',');
  const rt = [...(reteachGroups || [])].sort().join('+');
  return [domain, date, Number(minutes), competencyId, gs, rt].join('|');
}

/** The next n school days from `today` (YYYY-MM-DD, the phone's own date: services/today.js), today included, Sundays left out. Only counts
 * calendar days forward from that date (a UTC midnight is used as a plain calendar, never to find out what today is). */
export function schoolDays(today, n = DAYS) {
  const out = [];
  const d = new Date(`${today}T00:00:00Z`);
  const two = (x) => String(x).padStart(2, '0');
  while (out.length < n) {
    if (d.getUTCDay() !== 0) out.push(`${d.getUTCFullYear()}-${two(d.getUTCMonth() + 1)}-${two(d.getUTCDate())}`);
    d.setUTCDate(d.getUTCDate() + 1);
  }
  return out;
}

/** The skill the plans are prepared around: what the last review points to for the Progressors, else the skill they were last taught. */
export function suggestedSkill(proposal) {
  const p = proposal && proposal.has_history ? (proposal.groups || {}).progressor : null;
  return (p && p.proposed && p.proposed.id) || (p && p.previous_target && p.previous_target.id) || null;
}

/** { skills, choices: [{ competencyId, groupSkills, reteachGroups }] } — the screen's own defaults for each skill; the suggested skill also moving on. */
export async function likelyChoices({ proposal, groups, getLadder, inSubject = null }) {
  const base = suggestedSkill(proposal);
  if (!base) return { skills: [], choices: [] };
  const baseLadder = await getLadder(base);
  const above = ((baseLadder && baseLadder.options && baseLadder.options.proficient) || []).map((o) => o && o.id)
    .filter((id, i, all) => id && id !== base && all.indexOf(id) === i && (!inSubject || inSubject.has(id)));
  const skills = [base, ...above.slice(0, AHEAD)];
  const choices = [];
  for (const skill of skills) {
    const ladder = skill === base ? baseLadder : await getLadder(skill).catch(() => null);
    if (!ladder) continue;
    const init = initialRows({ ladder, proposal, selectedId: skill });
    const opts = buildGenerateOptions({ rows: init.rows, reteach: init.reteach, groups, ready: true });
    const reteachGroups = opts.reteachGroups || [];
    choices.push({ competencyId: skill, groupSkills: opts.groupSkills, reteachGroups });
    if (skill === base && reteachGroups.length) choices.push({ competencyId: skill, groupSkills: opts.groupSkills, reteachGroups: [] });     // and moving on
  }
  return { skills: skills.filter((s) => choices.some((c) => c.competencyId === s)), choices };
}

/** The request's items: every choice at every length on every day. */
export function itemsFor(domain, choices, dates) {
  const items = [];
  for (const date of dates) {
    for (const minutes of MINUTES) {
      for (const c of choices) {
        items.push({
          key: planKey({ domain, date, minutes, ...c }), competency_id: c.competencyId, plan_date: date, session_minutes: minutes,
          reteach_groups: c.reteachGroups || [], ...(c.groupSkills ? { group_skills: c.groupSkills } : {}),
        });
      }
    }
  }
  return items;
}

/** A short fingerprint of what the plans are prepared FROM (the suggestions and the groups): prepared again when it changes. */
export function fingerprint(value) {
  const s = JSON.stringify(value || null);
  let h = 2166136261;
  for (let i = 0; i < s.length; i += 1) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return (h >>> 0).toString(16);
}

const inFlight = new Map();

/**
 * Prepare this subject's plans if they are missing, from another day, or from other suggestions or groups. api: { getGroupProposal,
 * getGroups, getLadder, prepareOfflinePlans }. force: prepare again whatever (the "download now" tap). Returns the subject's status record.
 */
export function refreshIfNeeded({ teacherId, domain, today, api, store, force = false, inSubject = null, emit = defaultEmit }) {
  const k = `${teacherId}|${domain}`;
  if (inFlight.has(k)) return inFlight.get(k);
  const run = (async () => {
    const before = await store.get('meta', domain);
    try {
      const [proposal, groupData] = await Promise.all([api.getGroupProposal(teacherId, domain, today), api.getGroups(teacherId, domain)]);
      const groups = (groupData && groupData.groups) || [];
      const fp = fingerprint({ proposal, groups });
      if (!force && before && before.status === 'ready' && before.preparedFor === today && before.fingerprint === fp) return before;
      await store.set('meta', domain, { ...(before || {}), domain, preparing: true });
      emit(domain);
      const { skills, choices } = await likelyChoices({ proposal, groups, getLadder: api.getLadder, inSubject });
      if (!choices.length) {
        const meta = { domain, status: 'no_history', preparedFor: today, checkedAt: new Date().toISOString(), fingerprint: fp, count: 0 };
        await replacePrepared(store, domain, []);
        await store.set('meta', domain, meta);
        return meta;
      }
      const dates = schoolDays(today, DAYS);
      const res = await api.prepareOfflinePlans(teacherId, domain, itemsFor(domain, choices, dates));
      const ok = ((res && res.plans) || []).filter((p) => p.ok && p.result);
      await replacePrepared(store, domain, ok.map((p) => [p.key, { key: p.key, domain, result: p.result }]));
      const meta = {
        domain, status: ok.length ? 'ready' : 'failed', preparedFor: today, preparedAt: new Date().toISOString(), dates, skills,
        count: ok.length, failed: ((res && res.plans) || []).length - ok.length, libraryVersion: res && res.library_version, fingerprint: fp,
      };
      await store.set('meta', domain, meta);
      return meta;
    } catch (e) {
      // no connection or a server error: what was prepared before stays usable; the status says the refresh failed
      const meta = { ...(before || { domain, status: 'missing', count: 0 }), preparing: false, lastError: (e && (e.code || e.name)) || 'error', lastTriedAt: new Date().toISOString() };
      await store.set('meta', domain, meta);
      return meta;
    } finally {
      inFlight.delete(k);
      emit(domain);
    }
  })();
  inFlight.set(k, run);
  return run;
}

async function replacePrepared(store, domain, entries) {
  for (const key of await store.keys('prepared')) if (String(key).startsWith(`${domain}|`)) await store.del('prepared', key);
  if (entries.length) await store.setMany('prepared', entries);
}

function defaultEmit(domain) {
  try { window.dispatchEvent(new CustomEvent(UPDATED_EVENT, { detail: domain })); } catch { /* no window (tests) */ }
}

/**
 * What the Plan screen says about this subject: 'ready' (with the skills and the last day prepared), 'preparing', 'no_history' (no plan has been
 * made in this subject yet, so nothing can be suggested), or 'missing' (not prepared, or the refresh failed with nothing kept).
 */
export function statusOf(meta) {
  if (!meta) return { state: 'missing' };
  if (meta.preparing) return { state: 'preparing' };
  if (meta.status === 'ready' && meta.count > 0) return { state: 'ready', skills: meta.skills || [], until: (meta.dates || []).slice(-1)[0] || null, preparedFor: meta.preparedFor };
  if (meta.status === 'no_history') return { state: 'no_history' };
  return { state: 'missing', lastError: meta.lastError || null };
}

/** Everything prepared or waiting is the class's data: removed when the signed-in person changes (store.js). Step 4 asks first about unsent plans. */
export async function clearOfflinePlans(store) {
  await store.clear('prepared');
  await store.clear('meta');
}
