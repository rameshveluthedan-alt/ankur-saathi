import React from 'react';
import Bi from './Bi';

// The question size, and the writing prompt's: larger, because the teacher reads it aloud to the group
export const QUESTION_SIZE = '0.875rem';
export const PROMPT_SIZE = '1rem';

// The shapes shown this round, and whether a block's signal draws anything at all (an empty payload draws nothing): shared with the printed plan
export const hasSignalPanel = (signal) => {
  if (!signal) return false;
  if (signal.shape === 'maths_questions') return Array.isArray((signal.maths_questions || {}).core) && signal.maths_questions.core.some((q) => String(q ?? '').trim());
  if (signal.shape === 'writing_prompt') return !!String((signal.writing_prompt || {}).prompt ?? '').trim();
  return false;
};

/**
 * The "signal panel" inside a teach block on the plan screen, visible without a tap: what the children of the group will actually do. From the block's `signal`
 * (the server's plan): { shape, signal_curated, maths_questions: { core, extra_count }, writing_prompt: { prompt } }.
 * Two shapes this round: maths_questions (the three core questions, then a grey line naming the extras) and writing_prompt (one or two lines, cut at two).
 * Any other shape (passage_questions, word_list: later), null, or no signal at all (a plan made before this): no panel, the block looks as before.
 * signal_curated is deliberately NOT shown: a curated skill and an uncurated one look the same (see docs/CURATED_SKILLS.md).
 * compact (the printed plan, screens/PlanPrint.jsx): the same content in two lines, Hindi only: the title, then the three questions on one line (the extras are named in the
 * page's worksheet line), or the title and the prompt together, cut at two lines.
 */
export default function SignalPanel({ signal, compact = false }) {
  if (!signal) return null;
  if (signal.shape === 'maths_questions') {
    const m = signal.maths_questions || {};
    const core = Array.isArray(m.core) ? m.core.filter((q) => String(q ?? '').trim()) : [];
    if (!core.length) return null;
    const extra = Number.isInteger(m.extra_count) && m.extra_count > 0 ? m.extra_count : 0;
    if (compact) {
      return (
        <div className="signal-panel compact" data-testid="signal-panel" data-shape="maths_questions" data-compact="true">
          <div className="signal-title">तीन मुख्य प्रश्न:</div>
          <div className="print-line-1" data-testid="core-questions" style={{ fontSize: QUESTION_SIZE }}>
            {core.map((q, i) => <span key={i} data-testid="core-question" style={{ marginRight: 14 }}>{i + 1}. {q}</span>)}
          </div>
        </div>
      );
    }
    return (
      <div className="signal-panel" data-testid="signal-panel" data-shape="maths_questions">
        <div className="signal-title"><Bi hi="तीन मुख्य प्रश्न" en="The three core questions" inline /></div>
        <ol data-testid="core-questions" style={{ margin: '4px 0 0', paddingLeft: 22, fontSize: QUESTION_SIZE }}>
          {core.map((q, i) => <li key={i} data-testid="core-question">{q}</li>)}
        </ol>
        {extra > 0 && (
          <div data-testid="extra-line" data-extra={extra} style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 4 }}>
            <Bi hi={`→ ${extra} और प्रश्न (जो जल्दी ख़त्म करें उनके लिए)`} en={`${extra} more ${extra === 1 ? 'question' : 'questions'} (for early finishers)`} inline />
          </div>
        )}
      </div>
    );
  }
  if (signal.shape === 'writing_prompt') {
    const prompt = String((signal.writing_prompt || {}).prompt ?? '').trim();
    if (!prompt) return null;
    if (compact) {
      return (
        <div className="signal-panel compact" data-testid="signal-panel" data-shape="writing_prompt" data-compact="true">
          <div className="print-line-2" data-testid="writing-prompt" style={{ fontSize: PROMPT_SIZE }}><span className="signal-title">लेखन कार्य: </span>{prompt}</div>
        </div>
      );
    }
    return (
      <div className="signal-panel" data-testid="signal-panel" data-shape="writing_prompt">
        <div className="signal-title"><Bi hi="लेखन कार्य" en="Writing prompt" inline /></div>
        {/* one or two short lines; a longer one is cut at two with "…" (the whole prompt is on the worksheet) */}
        <div className="signal-prompt" data-testid="writing-prompt" title={prompt} style={{ fontSize: PROMPT_SIZE, marginTop: 4 }}>{prompt}</div>
      </div>
    );
  }
  return null;
}
