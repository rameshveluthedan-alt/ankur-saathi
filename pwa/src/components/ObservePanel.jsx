import React from 'react';
import Bi from './Bi';

/**
 * An observed skill's task (14 Nov: half the skills are checked by watching the children): what the children do, with what, and what A / PA / NA look like
 * for THIS task. From the plan's worksheets[level].observe (backend/app/services/writing_sheets.py). Shown inside the group's You Do and on the in-class
 * recording page, above the A / PA / NA buttons. Materials in the user's order: the class kit first, else everyday objects; the worksheet is the back-up.
 * Nothing here is ever printed on the child's sheet.
 */
export function observeOf(plan, level) {
  const ws = plan && plan.worksheets && plan.worksheets[level];
  const o = ws && ws.sheet_kind === 'observed' && ws.observe;
  return o && (o.task_hi || o.look_for) ? o : null;
}

const list = (a) => (Array.isArray(a) ? a.filter((x) => typeof x === 'string' && x.trim()) : []);

export default function ObservePanel({ observe, testid = 'observe-panel', compact = false }) {
  if (!observe) return null;
  const kit = list(observe.kit_materials_hi);
  const local = list(observe.local_materials_hi);
  const lf = observe.look_for || {};
  const rows = [
    ['A', lf.achieved_hi, lf.achieved_en, 'var(--green-dark)'],
    ['PA', lf.partial_hi, lf.partial_en, 'var(--info)'],
    ['NA', lf.not_yet_hi, lf.not_yet_en, 'var(--text)'],
  ].filter((r) => r[1]);
  return (
    <div className="observe-panel" data-testid={testid}>
      {observe.task_hi && !compact && (
        <div data-testid={`${testid}-task`}><b>👀 <Bi hi="काम" en="Task" inline />:</b> <Bi hi={observe.task_hi} en={observe.task_en || ''} inline /></div>
      )}
      {(kit.length > 0 || local.length > 0) && !compact && (
        <div data-testid={`${testid}-materials`} style={{ marginTop: 2 }}>
          <b>🧺 <Bi hi="सामग्री" en="Materials" inline />:</b>{' '}
          {kit.length > 0 && <span data-testid={`${testid}-kit`}>{kit.join(', ')}</span>}
          {kit.length > 0 && local.length > 0 && <> · <Bi hi="या" en="or" inline /> </>}
          {local.length > 0 && <span data-testid={`${testid}-local`}>{local.join(', ')}</span>}
          <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
            <Bi hi="कुछ भी न हो तो वर्कशीट (बोर्ड पर बनाकर) से काम करवाएँ।" en="With no objects at all, use the worksheet (drawn on the board)." inline />
          </div>
        </div>
      )}
      {rows.length > 0 && (
        <div data-testid={`${testid}-look-for`} style={{ marginTop: 4 }}>
          <b><Bi hi="क्या देखें" en="What to look for" inline />:</b>
          {rows.map(([code, hi, en, color]) => (
            <div key={code} data-testid={`${testid}-${code}`} style={{ display: 'flex', gap: 6, marginTop: 2 }}>
              <span className="badge badge-result" style={{ color, minWidth: 30, textAlign: 'center' }}>{code}</span>
              <span><Bi hi={hi} en={en || ''} inline /></span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
