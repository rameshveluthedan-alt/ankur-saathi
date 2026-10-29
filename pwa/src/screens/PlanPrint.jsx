import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../App';
import { getCachedPlan } from '../services/api';
import SignalPanel, { hasSignalPanel } from '../components/SignalPanel';
import { reteachSummary } from '../services/reteachInfo';
import { GROUP_LABELS, GROUP_ORDER } from '../tiers';
import { isFluencySkill } from '../services/pace';
import { localToday } from '../services/today';
import { planMinutes } from '../services/planMinutes';
import { hasObservation } from '../services/reviewWays';
import { hiDate, classLine } from '../services/printFormat';

/**
 * The printed plan: ONE A4 page the teacher carries when she teaches without her phone (browser Print or "Save as PDF"). Hindi only, the same for every teacher:
 * it depends on no screen setting ("सिर्फ़ हिंदी", "छोटी स्क्रीन"). No talking points, no understanding-check method, no worksheet content, and never a child's name
 * (roll numbers only). Every line has a fixed allowance (data-lines, held by the print-line-1 / print-line-2 classes: longer text is cut with "…"), so the page
 * stays within its line budget (PRINT_LINE_BUDGET); the signal panel is the screen's own component, in its compact form.
 */
export const PRINT_LINE_BUDGET = 36;

const fmt = (s) => String(s ?? '').replace(/\*\*|__/g, '').replace(/\s+/g, ' ').trim();
export { hiDate, classLine };        // shared with the tick sheet and the mentor report (services/printFormat.js)

// One printed line (or two): the allowance is both declared (data-lines, counted by the test) and enforced (the class cuts longer text with "…")
function Line({ n = 1, testid, className = '', children }) {
  return <div className={`print-line-${n} ${className}`.trim()} data-lines={n} data-testid={testid}>{children}</div>;
}

function Block({ block, groups }) {
  const L = GROUP_LABELS[block.teach_group] || { hi: block.teach_group, mark: '' };
  const skill = (groups.find((g) => g.label === block.teach_group) || {}).target_competency_id;
  const rt = reteachSummary(block);
  const firstMistake = rt.mistakes[0];
  const cfu = Array.isArray(block.cfu) && block.cfu.length ? block.cfu[0] : null;
  return (
    <section className={`print-block tier-${block.teach_group}`} data-testid={`print-block-${block.teach_group}`}>
      <Line testid="print-block-head" className="print-block-head">
        {L.mark} {L.hi} पढ़ाएँ{skill ? ` — ${skill}` : ''} · {block.duration_minutes} मि.
      </Line>
      {rt.isReteach && (
        <Line testid="print-reteach">
          🔄 पुनः शिक्षण{rt.rolls.length ? `: रोल ${rt.rolls.join(', ')}` : ''}{firstMistake ? ` · ${fmt(firstMistake.name_hi || firstMistake.misconception_id)}` : ''}
        </Line>
      )}
      {fmt(block.script_hi) && <Line n={2} testid="print-script">“{fmt(block.script_hi)}”</Line>}
      {hasSignalPanel(block.signal) && <div data-lines={2} data-testid="print-signal"><SignalPanel signal={block.signal} compact /></div>}
      {cfu && fmt(cfu.question_hi) && <Line testid="print-cfu"><b>समझ की जाँच:</b> {fmt(cfu.question_hi)}</Line>}
      {fmt(block.other_groups_hi) && <Line testid="print-others"><b>बाकी:</b> {fmt(block.other_groups_hi)}</Line>}
    </section>
  );
}

// "वर्कशीट: ● शुरुआती 3 मुख्य + 2 · ▲ प्रगतिशील लेखन कार्य · ■ दक्ष: वर्कशीट देखें": one line for the whole page
export function worksheetLine(plan, teachBlocks) {
  const parts = GROUP_ORDER.filter((g) => teachBlocks.some((b) => b.teach_group === g)).map((g) => {
    const L = GROUP_LABELS[g];
    const s = (teachBlocks.find((b) => b.teach_group === g) || {}).signal || {};
    const sheet = (plan.worksheets || {})[g];
    const hasSheet = !!(sheet && Array.isArray(sheet.problems) && sheet.problems.length);
    if (s.shape === 'maths_questions' && s.maths_questions && Array.isArray(s.maths_questions.core) && s.maths_questions.core.length) {
      const extra = s.maths_questions.extra_count > 0 ? ` + ${s.maths_questions.extra_count}` : '';
      return `${L.mark} ${L.hi} ${s.maths_questions.core.length} मुख्य${extra}`;
    }
    if (s.shape === 'writing_prompt' && s.writing_prompt && fmt(s.writing_prompt.prompt)) return `${L.mark} ${L.hi} लेखन कार्य`;
    return `${L.mark} ${L.hi}: ${hasSheet ? 'वर्कशीट देखें' : 'वर्कशीट नहीं'}`;
  });
  return `वर्कशीट: ${parts.join(' · ')}`;
}

export default function PlanPrint() {
  const { currentPlan, setCurrentPlan, teacher, selectedDomain } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(!currentPlan);

  // opened directly or reloaded: the plan is not in memory, so load today's stored plan (as the plan screen does)
  useEffect(() => {
    if (currentPlan) return;
    getCachedPlan(teacher.teacher_id, localToday(), selectedDomain).then(setCurrentPlan).catch(() => {}).finally(() => setLoading(false));
  }, []);
  // while this page is open, printing shows this page alone (no banner, no bottom bar): see "body.print-plan" in index.css
  useEffect(() => { document.body.classList.add('print-plan'); return () => document.body.classList.remove('print-plan'); }, []);

  const bar = (
    <div className="no-print" style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
      <button type="button" className="btn btn-secondary btn-small" data-testid="print-back" onClick={() => navigate('/yojana')}>← वापस</button>
      {currentPlan && <button type="button" className="btn btn-primary btn-small" data-testid="print-now" onClick={() => window.print()}>🖨️ प्रिंट करें</button>}
    </div>
  );
  if (!currentPlan) {
    return <div className="screen">{bar}{loading ? <div className="loading"><div className="spinner" /></div> : <p data-testid="print-no-plan">कोई योजना नहीं</p>}</div>;
  }

  const plan = currentPlan.plan || {};
  const groups = currentPlan.groups || [];
  const blocks = (plan.rotation_schedule && plan.rotation_schedule.blocks) || [];
  const teachBlocks = blocks.filter((b) => b && b.type === 'teach' && GROUP_LABELS[b.teach_group]);
  const anchorBlock = blocks.find((b) => b && b.type === 'anchor');
  const anchor = plan.anchor || {};
  const anchorTitle = fmt(anchor.title_hi) || fmt(anchor.narration_hi);
  const length = planMinutes(currentPlan);        // the recorded length; for an older plan its blocks added up, so "लगभग"
  const observing = hasObservation(currentPlan);        // the general instruction, not the plan's own AI-written prompt (see services/reviewWays.js)
  const reading = groups.some((g) => isFluencySkill(g.target_competency_id));
  const code = teacher.employee_code || teacher.school_code || '';

  return (
    <div className="screen plan-print" data-testid="plan-print">
      {bar}
      <header>
        <Line testid="print-head" className="print-title">{[code, classLine(teacher.enrolled_grades), hiDate(currentPlan.plan_date), currentPlan.selected_competency_id].filter(Boolean).join(' · ')}</Line>
        {length && <Line testid="print-time">योजना समय: {length.recorded ? '' : 'लगभग '}{length.minutes} मिनट</Line>}
      </header>
      <hr />
      {anchorTitle && <Line testid="print-anchor">🎯 <b>एंकर गतिविधि:</b> {anchorTitle}{anchorBlock && anchorBlock.duration_minutes ? ` · ${anchorBlock.duration_minutes} मि.` : ''}</Line>}
      {teachBlocks.map((b, i) => <Block key={i} block={b} groups={groups} />)}
      <hr />
      <div data-testid="print-review">
        {observing && <Line testid="print-review-obs"><b>अवलोकन:</b> स्वतंत्र अभ्यास के दौरान देखकर हर बच्चे के लिए A / PA / NA</Line>}
        <Line testid="print-review-photo"><b>फ़ोटो:</b> समीक्षा स्क्रीन पर चुने जाएँगे</Line>
        {reading && <Line testid="print-review-reading"><b>पढ़कर सुनाना:</b> समीक्षा स्क्रीन पर</Line>}
      </div>
      <Line testid="print-worksheets">{worksheetLine(plan, teachBlocks)}</Line>
      <hr />
      <Line testid="print-footer" className="print-footer">🌱 अंकुर साथी · {currentPlan.plan_date} · योजना {currentPlan.selected_competency_id}</Line>
    </div>
  );
}
