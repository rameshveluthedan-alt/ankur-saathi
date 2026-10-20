/**
 * Ankur Saathi — API Service
 * Centralized backend calls. In dev, Vite proxies /api to localhost:8000.
 */

const BASE = '/api';
const TOKEN_KEY = 'ankur_token';

export const getToken = () => { try { return localStorage.getItem(TOKEN_KEY); } catch { return null; } };
export const setToken = (t) => { try { if (t) localStorage.setItem(TOKEN_KEY, t); else localStorage.removeItem(TOKEN_KEY); } catch { /* storage unavailable */ } };

// Every call carries the session token. A 401 means the session has ended (sign in again); a 403 "pin_change_required"
// means an admin reset the PIN and the teacher must choose a new one before anything else.
export async function authFetch(url, options = {}) {
  const headers = { ...(options.headers || {}) };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(url, { ...options, headers });
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
  return res.json();
}

// ── Auth ──
export const login = (phoneHash, pin) =>
  request('/auth/login', { method: 'POST', body: JSON.stringify({ phone_hash: phoneHash, pin }) });

// A new teacher registers with a school code, the grades taught and a PIN. A new school code makes them the school admin;
// an existing school needs its join code.
export const registerTeacher = (phoneHash, pin, schoolCode, joinCode, grades) =>
  request('/auth/register', { method: 'POST', body: JSON.stringify({ phone_hash: phoneHash, pin, school_code: schoolCode, join_code: joinCode || null, enrolled_grades: grades }) });

export const changePin = (currentPin, newPin) =>
  request('/auth/change-pin', { method: 'POST', body: JSON.stringify({ current_pin: currentPin, new_pin: newPin }) });

export const getMe = () => request('/auth/me');

// The school admin: accounts only, never a child's data
export const adminSchool = () => request('/admin/school');
export const adminTeachers = () => request('/admin/teachers');
export const adminResetPin = (id) => request(`/admin/teachers/${id}/reset-pin`, { method: 'POST' });
export const adminUnlock = (id) => request(`/admin/teachers/${id}/unlock`, { method: 'POST' });
export const adminRotateJoinCode = () => request('/admin/school/join-code', { method: 'POST' });

// A plain link cannot carry the token, so printed pages and downloads are fetched with it and then opened.
export async function openAuthedPage(path) {
  const w = window.open('', '_blank');                       // opened first, so a phone's pop-up blocker allows it
  const res = await authFetch(`${BASE}${path}`);
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

export const generatePlan = (teacherId, competencyId, domainId, planDate) =>
  request(`/plan/generate?teacher_id=${teacherId}`, {
    method: 'POST',
    body: JSON.stringify({ competency_id: competencyId, domain_id: domainId, plan_date: planDate }),
  });

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
export const getProgressDashboard = (teacherId) =>
  request(`/progress/dashboard/${teacherId}`);

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
