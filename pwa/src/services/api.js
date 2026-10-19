/**
 * Ankur Saathi — API Service
 * Centralized backend calls. In dev, Vite proxies /api to localhost:8000.
 */

const BASE = '/api';

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API error ${res.status}`);
  }
  return res.json();
}

// ── Auth ──
export const login = (phoneHash) =>
  request('/auth/login', { method: 'POST', body: JSON.stringify({ phone_hash: phoneHash }) });

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

export const analysePhotos = async (teacherId, formData) => {
  const res = await fetch(`${BASE}/review/analyse-photos`, {
    method: 'POST',
    body: formData, // multipart — no Content-Type header (browser sets boundary)
  });
  if (!res.ok) {
    // show the server's reason (for example: no plan generated for today) instead of a generic message
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Photo analysis failed');
  }
  return res.json();
};

// ── Progress ──
export const getProgressDashboard = (teacherId) =>
  request(`/progress/dashboard/${teacherId}`);

export const applyLevelChange = (teacherId, childId, domainId, newBpp) =>
  request(`/progress/level-change?teacher_id=${teacherId}&child_id=${childId}&domain_id=${domainId}&new_bpp=${newBpp}`, {
    method: 'POST',
  });

export const exportMLOCsv = (teacherId) =>
  `${BASE}/progress/export/${teacherId}`;

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
