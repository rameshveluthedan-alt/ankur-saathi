import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { fetchAuthedPage, downloadAuthed } from '../services/api';
import { friendlyError } from '../services/errors';
import { notify } from '../services/notify';
import Bi from '../components/Bi';

// The two CSV reports of the Class progress screen, shown as a table INSIDE the app first, with ⬇ Download under it. Before (12 Nov), the buttons only
// downloaded a file: on a desktop nothing visible happened, and the hackathon evaluators could not get the report to work.
export const REPORTS = {
  class: { path: (id) => `/progress/export/class/${id}`, file: 'class_report.csv', hi: 'कक्षा रिपोर्ट, नामों के साथ', en: 'Class report, with names' },
  officer: { path: (id) => `/progress/export/${id}`, file: 'officer_report.csv', hi: 'अधिकारी डेटा, सिर्फ़ रोल नंबर', en: 'Officer data, roll numbers only' },
};

// A small CSV reader: commas, quoted fields with commas, doubled quotes and line breaks inside quotes. PURE: tested in tests/report_view.test.mjs.
export function parseCsv(text) {
  const rows = [];
  let row = [], field = '', quoted = false;
  const s = String(text || '').replace(/^﻿/, '');
  for (let i = 0; i < s.length; i += 1) {
    const c = s[i];
    if (quoted) {
      if (c === '"' && s[i + 1] === '"') { field += '"'; i += 1; } else if (c === '"') quoted = false; else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ',') { row.push(field); field = ''; }
    else if (c === '\n' || c === '\r') {
      if (c === '\r' && s[i + 1] === '\n') i += 1;
      row.push(field); field = '';
      if (row.some((f) => f !== '')) rows.push(row);
      row = [];
    } else field += c;
  }
  row.push(field);
  if (row.some((f) => f !== '')) rows.push(row);
  return rows;
}

export default function ReportView() {
  const { teacher } = useAuth();
  const { state } = useLocation();
  const navigate = useNavigate();
  const kind = state && REPORTS[state.kind] ? state.kind : 'class';
  const R = REPORTS[kind];
  const [rows, setRows] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => {
    let cancelled = false;
    setRows(null); setError(null);
    fetchAuthedPage(R.path(teacher.teacher_id)).then((t) => { if (!cancelled) setRows(parseCsv(t)); })
      .catch((e) => { if (!cancelled) setError(friendlyError(e, { hi: 'रिपोर्ट नहीं खुल सकी', en: 'The report could not be opened' })); });
    return () => { cancelled = true; };
  }, [kind, teacher.teacher_id]);
  const download = () => downloadAuthed(R.path(teacher.teacher_id), R.file)
    .then(() => notify(`⬇ ${R.file}`, 'info'))
    .catch((e) => notify(friendlyError(e, { hi: 'फ़ाइल डाउनलोड नहीं हो सकी', en: 'The file could not be downloaded' }), 'error'));

  return (
    <div className="screen report-view" data-testid="report-view" data-kind={kind}>
      <div className="screen-header">
        <button type="button" className="btn btn-secondary btn-small" data-testid="report-back" onClick={() => navigate('/progress')}>← <Bi hi="वापस" en="Back" inline /></button>
        <h1 style={{ fontSize: '1rem' }}>📄 <Bi hi={R.hi} en={R.en} inline /></h1>
      </div>
      {!rows && !error && <div className="loading"><div className="spinner" /><span><Bi hi="खुल रही है…" en="Opening" inline /></span></div>}
      {error && <p className="note note-error" role="alert" data-testid="report-error">{error}</p>}
      {rows && rows.length <= 1 && <p className="note note-info" data-testid="report-empty"><Bi hi="अभी इस रिपोर्ट में कोई पंक्ति नहीं है।" en="This report has no rows yet." /></p>}
      {rows && rows.length > 1 && (
        <div className="report-scroll">
          <table className="report-table" data-testid="report-table">
            <thead><tr>{rows[0].map((h, i) => <th key={i}>{h}</th>)}</tr></thead>
            <tbody>{rows.slice(1).map((r, i) => <tr key={i}>{rows[0].map((_, j) => <td key={j}>{r[j] ?? ''}</td>)}</tr>)}</tbody>
          </table>
        </div>
      )}
      {rows && (
        <button type="button" className="btn btn-primary" data-testid="report-download" onClick={download} style={{ marginTop: 12, marginBottom: 80, flexDirection: 'column', gap: 0 }}>
          <Bi hi={`⬇ CSV फ़ाइल डाउनलोड करें (${R.file})`} en={`Download the CSV file (${R.file})`} />
        </button>
      )}
    </div>
  );
}
