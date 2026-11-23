import React, { useState } from 'react';
import Bi from './Bi';
import { GROUP_LABELS } from '../tiers';

/**
 * A worksheet shown IN THE APP, for a plan made with no connection (docs/drafts/OFFLINE_ASSEMBLER_PLAN.md, decision 7): the server's printable
 * page is not on the phone, so the teacher reads the sheet here and copies it onto the board (the app's "no printer" way). Everything the sheet
 * has: the instructions, a passage, the problems (answers hidden until asked for), a writing task and its checklist, a task to watch.
 */
const LOOK_FOR_ROWS = [
  { key: 'achieved', labelHi: '✓ हासिल', labelEn: '✓ Achieved' },
  { key: 'partial', labelHi: '~ आंशिक', labelEn: '~ Partly' },
  { key: 'not_yet', labelHi: '✗ अभी नहीं', labelEn: '✗ Not yet' },
];

export default function WorksheetInApp({ ws, level, onClose }) {
  const [answers, setAnswers] = useState(false);
  if (!ws) return null;
  const label = GROUP_LABELS[level] || { hi: level, en: level };
  const problems = Array.isArray(ws.problems) ? ws.problems : [];
  const core = Number(ws.required_count) || null;
  const lf = ws.observe && ws.observe.look_for && typeof ws.observe.look_for === 'object' ? ws.observe.look_for : {};
  // what the teacher looks for: one line per result (A / PA / NA), in the app's two languages like the rest of the screen
  const lookFor = LOOK_FOR_ROWS.filter((r) => lf[`${r.key}_hi`] || lf[`${r.key}_en`]).map((r) => ({ ...r, hi: lf[`${r.key}_hi`] || lf[`${r.key}_en`], en: lf[`${r.key}_en`] || lf[`${r.key}_hi`] }));
  return (
    <div data-testid={`worksheet-inapp-${level}`} className="card" style={{ padding: 12, marginTop: 8, border: '2px solid var(--green-light)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <b style={{ flex: 1 }}>📝 <Bi hi={`वर्कशीट: ${label.hi}`} en={`Worksheet: ${label.en}`} inline /></b>
        <button type="button" className="btn btn-secondary btn-small" data-testid="worksheet-inapp-close" onClick={onClose} style={{ minHeight: 44 }}>
          ✕ <Bi hi="बंद करें" en="Close" inline />
        </button>
      </div>
      <p className="hint-line" style={{ marginTop: 0 }}>
        <Bi hi="बिना इंटरनेट के बनी योजना: बोर्ड पर उतारें। छापने वाला पेज इंटरनेट मिलने के बाद खुलेगा।" en="A plan made with no internet: copy this onto the board. The printable page opens once the plan is sent." inline />
      </p>
      {ws.instructions_hi && <p style={{ margin: '4px 0' }}>{ws.instructions_hi}</p>}
      {ws.passage_block && (ws.passage_block.text || ws.passage_block.title) && (
        <div data-testid="worksheet-inapp-passage" style={{ background: 'var(--surface)', borderRadius: 8, padding: 8, margin: '6px 0' }}>
          {ws.passage_block.title && <b>{ws.passage_block.title}</b>}
          <div style={{ whiteSpace: 'pre-wrap' }}>{ws.passage_block.text}</div>
        </div>
      )}
      {ws.writing_task && ws.writing_task.topic_hi && (
        <p style={{ margin: '4px 0' }}>✍️ <b><Bi hi="लेखन" en="Writing" inline />:</b> {ws.writing_task.topic_hi}</p>
      )}
      {Array.isArray(ws.checklist) && ws.checklist.length > 0 && (
        <ul style={{ margin: '4px 0', paddingLeft: 20 }}>{ws.checklist.map((c, i) => <li key={i}>☐ {c && (c.item_hi || c.item_en || '')}</li>)}</ul>
      )}
      {ws.observe && ws.observe.task_hi && (
        <div style={{ margin: '6px 0' }}>
          👀 <b><Bi hi="देखने का काम" en="Task to watch" inline />:</b> {ws.observe.task_hi}
          {lookFor.length > 0 && <ul style={{ margin: '4px 0', paddingLeft: 20 }}>{lookFor.map((r) => <li key={r.key} data-testid={`look-for-${r.key}`}><b><Bi hi={r.labelHi} en={r.labelEn} inline /></b>: <Bi hi={String(r.hi)} en={String(r.en)} inline /></li>)}</ul>}
        </div>
      )}
      {problems.length > 0 && (
        <ol style={{ margin: '6px 0', paddingLeft: 24 }} data-testid="worksheet-inapp-problems">
          {problems.map((p, i) => (
            <li key={i} style={{ marginBottom: 4, color: core && Number(p.number || i + 1) > core ? 'var(--text-secondary)' : undefined }}>
              {p.problem_hi || p.word_problem_text || ''}
              {answers && p.answer !== undefined && p.answer !== null && String(p.answer) !== '' && (
                <span data-testid="worksheet-inapp-answer" style={{ color: 'var(--green-dark)', marginLeft: 6 }}>→ {String(p.answer)}</span>
              )}
            </li>
          ))}
        </ol>
      )}
      {core && problems.length > core && (
        <p className="hint-line"><Bi hi={`पहले ${core} सवाल सबके लिए; बाकी जल्दी पूरा करने वालों के लिए।`} en={`The first ${core} for everyone; the rest for those who finish early.`} inline /></p>
      )}
      {problems.length > 0 && (
        <button type="button" className="btn btn-secondary btn-small" data-testid="worksheet-inapp-answers" onClick={() => setAnswers((a) => !a)} style={{ minHeight: 44 }}>
          {answers ? <Bi hi="उत्तर छिपाएँ" en="Hide answers" inline /> : <Bi hi="उत्तर दिखाएँ (शिक्षक के लिए)" en="Show answers (for the teacher)" inline />}
        </button>
      )}
    </div>
  );
}
