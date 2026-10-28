/**
 * Ankur Saathi — API Service
 * Centralized backend calls. In dev, Vite proxies /api to localhost:8000.
 */

import { NetworkError, markNetworkFailed } from './network';
import { clearPrivateCaches } from './offlineCache';

const BASE = '/api';
// LAB PHONE TEST ONLY: the app was built or served with VITE_MOCK_SIGNAL=1 (see request() below). Outside Vite (the tests' own bundles) there is no import.meta.env: off.
const MOCK_SIGNAL = typeof import.meta.env !== 'undefined' && import.meta.env.VITE_MOCK_SIGNAL === '1';
const TOKEN_KEY = 'ankur_token';

export const getToken = () => { try { return localStorage.getItem(TOKEN_KEY); } catch { return null; } };
export const setToken = (t) => {
  const before = getToken();
  try { if (t) localStorage.setItem(TOKEN_KEY, t); else localStorage.removeItem(TOKEN_KEY); } catch { /* storage unavailable */ }
  if (before !== (t || null)) clearPrivateCaches();       // signing in or out: the offline copies of the last person's plan and worksheets go (see offlineCache.js)
};

// Every call carries the session token. A 401 means the session has ended (sign in again); a 403 "pin_change_required"
// means the school leader reset the password (or it is a first sign-in) and the teacher must choose a new one before anything else.
export async function authFetch(url, options = {}) {
  const headers = { ...(options.headers || {}) };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  let res;
  try { res = await fetch(url, { ...options, headers }); } catch { markNetworkFailed(); throw new NetworkError(); }      // no connection: say so plainly instead of the browser's "Failed to fetch"
  // (an answer does NOT clear a failure: the service worker may have answered from its saved copy; only a probe does, see network.js)
  if (res.status === 401 && token) window.dispatchEvent(new Event('ankur-auth-ended'));
  if (res.status === 403) {
    const body = await res.clone().json().catch(() => ({}));
    if (body && body.detail && body.detail.code === 'pin_change_required') window.dispatchEvent(new Event('ankur-pin-change'));
  }
  return res;
}

// The server's reason, whether `detail` is a plain string or {message, code}
const detailText = (err, fallback) => {
  const d = err && err.detail;
  if (!d) return fallback;
  if (typeof d === 'string') return d;
  return d.message || fallback;
};

async function request(path, options = {}) {
  const res = await authFetch(`${BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const e = new Error(detailText(err, `API error ${res.status}`));
    e.status = res.status;
    e.code = err && err.detail && err.detail.code;
    e.detail = err && err.detail;
    throw e;
  }
  const data = await res.json();
  // LAB PHONE TEST ONLY (VITE_MOCK_SIGNAL=1): a mock signal panel on plans the server has not given one yet (services/devMockSignal.js). Off in a normal build.
  if (MOCK_SIGNAL) {
    const { isPlanPath, withMockSignal } = await import('./devMockSignal');
    if (isPlanPath(path)) return withMockSignal(data);
  }
  return data;
}

// ── Auth ──
// Employee code (six letters or digits) and password. (The field of the request is still called "pin".) Accounts are made by the school leader: there is no registration call any more.
export const login = (employeeCode, password) =>
  request('/auth/login', { method: 'POST', body: JSON.stringify({ employee_code: employeeCode, pin: password }) });

export const changePin = (currentPin, newPin) =>
  request('/auth/change-pin', { method: 'POST', body: JSON.stringify({ current_pin: currentPin, new_pin: newPin }) });

export const getMe = () => request('/auth/me');

// The school leader: accounts only, never a child's data
export const adminSchool = () => request('/admin/school');
export const adminTeachers = () => request('/admin/teachers');
export const adminResetPin = (id) => request(`/admin/teachers/${id}/reset-pin`, { method: 'POST' });
export const adminUnlock = (id) => request(`/admin/teachers/${id}/unlock`, { method: 'POST' });
export const adminRecordConsent = (version) => request('/admin/school/consent', { method: 'POST', body: JSON.stringify({ version }) });

// A plain link cannot carry the token, so printed pages and downloads are fetched with it and then opened.
export async function openAuthedPage(path) {
  const w = window.open('', '_blank');                       // opened first, so a phone's pop-up blocker allows it
  let res;
  try { res = await authFetch(`${BASE}${path}`); } catch (e) { if (w) w.close(); throw e; }       // no network: do not leave a blank tab behind
  if (!res.ok) { if (w) w.close(); const err = await res.json().catch(() => ({})); throw new Error(detailText(err, 'Could not open the page')); }
  const url = URL.createObjectURL(new Blob([await res.text()], { type: 'text/html' }));
  if (w) w.location.href = url; else window.open(url);
}
export async function downloadAuthed(path, filename) {
  const res = await authFetch(`${BASE}${path}`);
  if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(detailText(err, 'Could not download the file')); }
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement('a');
  a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 4000);
}
export const worksheetPath = (teacherId, planDate, domainId, level) => `/worksheet/${teacherId}/${planDate}/${domainId}/${level}`;

// Right after a plan appears, make its offline copy, one request at a time and quietly: first the STORED plan (the address the app reopens it from after a reload: a plan just generated came
// straight from the server's reply, so that address had never been asked for), then each level's worksheet. The service worker keeps every answer (vite.config.js), so the teacher can
// reopen the plan and print the worksheets later with no network. A failure stops it silently: this only prepares a copy.
export async function prepareOfflineCopy(teacherId, planDate, domainId, levels) {
  const paths = [`/plan/${teacherId}/${planDate}/${domainId}`, ...(levels || []).map(level => worksheetPath(teacherId, planDate, domainId, level))];
  for (const p of paths) {
    try { await authFetch(`${BASE}${p}`); } catch { return; }
  }
}

// The names the teacher entered: shown on her own screens only (never sent to the AI)
export const getNames = async (teacherId) => {
  const res = await authFetch(`${BASE}/children/names/${teacherId}`);
  return res.ok ? ((await res.json()).names || {}) : {};
};
// Her own class report WITH names (the officer report has roll numbers only)
export const downloadClassReport = (teacherId) => downloadAuthed(`/progress/export/class/${teacherId}`, 'class_report.csv');
export const downloadOfficerReport = (teacherId) => downloadAuthed(`/progress/export/${teacherId}`, 'officer_report.csv');

// ── Class register (bulk enrolment) ──
export const REGISTER_TEMPLATE_URL = `${BASE}/register/template`;
export const previewRegister = async (teacherId, file) => {
  const fd = new FormData();
  fd.append('teacher_id', teacherId);
  fd.append('file', file);
  const res = await authFetch(`${BASE}/register/preview`, { method: 'POST', body: fd });
  if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(detailText(err, 'Could not read the file')); }
  return res.json();
};
export const commitRegister = async (teacherId, filename, rows) => {
  const res = await authFetch(`${BASE}/register/commit`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ teacher_id: teacherId, filename, rows }) });
  if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(detailText(err, 'Could not enrol the children')); }
  return res.json();
};

// ── Plan ──
export const getCompetencies = (domainId) =>
  request(`/plan/competencies/${domainId}`);

export const getCurriculumWeek = (gradeLevel, domainId, weekNumber) =>
  request(`/plan/curriculum-week?grade_level=${gradeLevel}&domain_id=${domainId}&week_number=${weekNumber}`);

export const getGroups = (teacherId, domainId) =>
  request(`/plan/groups/${teacherId}/${domainId}`);

// options: { groupSkills: {beginner, proficient}, reteachGroups: [...], sessionMinutes: 45 | 60 | 90 }. Omitted: the plan derives each group's skill from competencyId, decides about a re-teach
// itself (the old way), and uses the teacher's stored teaching time (90 unless changed).
export const generatePlan = (teacherId, competencyId, domainId, planDate, options = {}) =>
  request(`/plan/generate?teacher_id=${teacherId}`, {
    method: 'POST',
    body: JSON.stringify({
      competency_id: competencyId, domain_id: domainId, plan_date: planDate,
      ...(options.groupSkills ? { group_skills: options.groupSkills } : {}),
      ...(options.reteachGroups ? { reteach_groups: options.reteachGroups } : {}),
      ...(options.sessionMinutes ? { session_minutes: options.sessionMinutes } : {}),
    }),
  });

// What each group's skill could be on planDate, from the teacher's decisions at the last review
export const getGroupProposal = (teacherId, domainId, planDate) =>
  request(`/plan/proposal/${teacherId}/${domainId}?plan_date=${planDate}`);

// The skills the plan derives for the three groups when this skill is selected
export const getLadder = (competencyId) => request(`/plan/ladder/${competencyId}`);

export const getCachedPlan = (teacherId, planDate, domainId) =>
  request(`/plan/${teacherId}/${planDate}/${domainId}`);

// ── Review ──
export const recordDecisions = (teacherId, planDate, domainId, decisions) =>
  request(`/review/decisions?teacher_id=${teacherId}`, {
    method: 'POST',
    body: JSON.stringify({ plan_date: planDate, domain_id: domainId, decisions }),
  });

export const recordObserved = (teacherId, sessionDate, items) =>
  request(`/review/observed?teacher_id=${teacherId}`, {
    method: 'POST',
    body: JSON.stringify({ session_date: sessionDate, items }),
  });

export const recordORF = (teacherId, entry) =>
  request(`/review/orf?teacher_id=${teacherId}`, {
    method: 'POST',
    body: JSON.stringify(entry),
  });

// The photo analyses already done today (one per worksheet level), so a teacher can reopen one after pressing Back
export const getSavedAnalyses = async (teacherId, date, domainId) => {
  const res = await authFetch(`${BASE}/review/analyses/${teacherId}/${date}/${domainId}`);
  if (!res.ok) return [];
  return (await res.json()).analyses || [];
};

// Who in the group has been analysed today and who is still to do (so nobody is photographed twice)
// Which way of capturing evidence (photo, observed, oral reading) each group's skill needs today
export const getReviewChannels = async (teacherId, date, domainId) => {
  const res = await authFetch(`${BASE}/review/channels/${teacherId}/${date}/${domainId}`);
  return res.ok ? res.json() : null;
};

export const getReviewCoverage = async (teacherId, date, domainId, level, opts = {}) => {
  const q = new URLSearchParams();
  if (opts.absent && opts.absent.length) q.set('absent', opts.absent.join(','));   // sampled children who are away today
  if (opts.sampleSize) q.set('sample_size', opts.sampleSize);
  if (opts.channel) q.set('channel', opts.channel);                                  // photo | observed | orf
  const res = await authFetch(`${BASE}/review/coverage/${teacherId}/${date}/${domainId}/${level}${q.toString() ? '?' + q.toString() : ''}`);
  return res.ok ? res.json() : null;
};

export const analysePhotos = async (teacherId, formData) => {
  const res = await authFetch(`${BASE}/review/analyse-photos`, {
    method: 'POST',
    body: formData, // multipart — no Content-Type header (browser sets boundary)
  });
  if (!res.ok) {
    // show the server's reason (for example: no plan generated for today) instead of a generic message
    const err = await res.json().catch(() => ({}));
    throw new Error(detailText(err, 'Photo analysis failed'));
  }
  return res.json();
};

// ── Progress ──
// on: the phone's own date (services/today.js), so "today" on the Progress screen is the same day the Review saved under.
// The answer also carries today[subject].by_level (each group's counts and decision today) and numeracy_today / literacy_today on each child.
export const getProgressDashboard = (teacherId, on) =>
  request(`/progress/dashboard/${teacherId}${on ? `?on=${on}` : ''}`);

// ── Baseline ──
export const generateBaseline = (domainId, gradeLevels) =>
  request('/baseline/generate', {
    method: 'POST',
    body: JSON.stringify({ domain_id: domainId, grade_levels: gradeLevels }),
  });

export const submitBaseline = (teacherId, domainId, results) =>
  request(`/baseline/submit?teacher_id=${teacherId}`, {
    method: 'POST',
    body: JSON.stringify({ domain_id: domainId, results }),
  });
