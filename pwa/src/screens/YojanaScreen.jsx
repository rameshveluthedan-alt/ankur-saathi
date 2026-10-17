import React, { useState, useEffect } from 'react';
import { useAuth } from '../App';
import { getCachedPlan } from '../services/api';

const GROUP_LABELS = {
  beginner: { hi: 'शुरुआती', en: 'Beginner', emoji: '🟠', css: 'beginner' },
  progressor: { hi: 'प्रगतिशील', en: 'Progressor', emoji: '🟡', css: 'progressor' },
  proficient: { hi: 'दक्ष', en: 'Proficient', emoji: '🟢', css: 'proficient' },
};

// Generated text may contain line breaks (lists) and stray markdown markers.
// Keep the line breaks, wrap long strings, and drop ** / __ since we do not render markdown.
const ML = { whiteSpace: 'pre-line', overflowWrap: 'anywhere' };
const fmt = (s) => String(s ?? '').replace(/\*\*|__/g, '');
// the screen already shows the group's name, so drop a repeated leading label such as "शुरुआती:"
const stripGroup = (t) => fmt(t).replace(/^\s*(शुरुआती|प्रगतिशील|दक्ष)(\s*\([^)]*\))?\s*[:：]\s*/, '');

export default function YojanaScreen() {
  const { currentPlan, setCurrentPlan, teacher, selectedDomain } = useAuth();
  const [expandedBlock, setExpandedBlock] = useState(null);
  const [showWhyPanel, setShowWhyPanel] = useState(false);
  const [loadingStored, setLoadingStored] = useState(false);

  // After a page reload the plan is no longer in memory: load today's stored plan
  // from the backend instead of making the teacher regenerate it.
  useEffect(() => {
    if (currentPlan) return;
    const today = new Date().toISOString().split('T')[0];
    setLoadingStored(true);
    getCachedPlan(teacher.teacher_id, today, selectedDomain)
      .then(setCurrentPlan)
      .catch(() => {})   // no stored plan for today: the empty state below is shown
      .finally(() => setLoadingStored(false));
  }, []);

  if (!currentPlan && loadingStored) {
    return (
      <div className="screen">
        <div className="loading"><div className="spinner" /><span>योजना लोड हो रही है (Loading plan)...</span></div>
      </div>
    );
  }

  if (!currentPlan) {
    return (
      <div className="screen">
        <div className="empty-state">
          <div className="empty-icon">📋</div>
          <h2>कोई योजना नहीं (No plan yet)</h2>
          <p style={{ marginTop: 8, color: 'var(--text-secondary)' }}>
            पहले "योजना" टैब से लक्ष्य चुनें और दैनिक योजना बनाएँ।
          </p>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-light)', marginTop: 4 }}>
            Select a Lakshya from the Plan tab first, then generate the daily plan.
          </p>
        </div>
      </div>
    );
  }

  const plan = currentPlan.plan || {};
  const groups = currentPlan.groups || [];
  const anchor = plan.anchor || {};
  const rotation = plan.rotation_schedule || {};
  const blocks = rotation.blocks || [];
  const explainability = currentPlan.explainability || plan.explainability || {};

  return (
    <div className="screen">
      <div className="screen-header">
        <h1>📋 दैनिक योजना <span style={{fontSize:'0.75rem',color:'var(--text-secondary)',fontWeight:400}}>Daily Plan</span></h1>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          {currentPlan.plan_date} · {currentPlan.selected_competency_id}
        </span>
      </div>

      {/* Groups summary */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        {groups.map(g => (
          <div key={g.label} className="card" style={{ flex: 1, padding: 10, textAlign: 'center' }}>
            <span className={`badge badge-${g.label}`}>{GROUP_LABELS[g.label]?.hi}</span>
            <div style={{ fontSize: '0.55rem', color: 'var(--text-light)' }}>{GROUP_LABELS[g.label]?.en}</div>
            <div style={{ fontWeight: 700, fontSize: '1.125rem', margin: '4px 0' }}>{g.count}</div>
            <div style={{ fontSize: '0.6875rem', color: 'var(--text-secondary)' }}>{g.target_competency_name_hi}</div>
          </div>
        ))}
      </div>

      {/* Preparation before class (DIY TLMs etc.) */}
      {Array.isArray(plan.prep_hi) && plan.prep_hi.length > 0 && (
        <div className="card" style={{ borderLeft: '4px solid var(--progressor)' }}>
          <h3>🧰 कक्षा से पहले तैयारी (Before class)</h3>
          <ul style={{ paddingLeft: 18, marginTop: 6, fontSize: '0.875rem' }}>
            {plan.prep_hi.map((t, i) => <li key={i} style={{ marginBottom: 4, ...ML }}>{fmt(t)}</li>)}
          </ul>
        </div>
      )}

      {/* Anchor Activity */}
      {anchor.narration_hi && (
        <div className="card" style={{ borderLeft: '4px solid var(--channel-written)' }}>
          <div className="card-header">
            <h3>🎯 एंकर गतिविधि (Anchor Activity)</h3>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>10 मि.</span>
          </div>
          <p style={{ fontSize: '0.9375rem', marginBottom: 8, ...ML }}>{fmt(anchor.narration_hi)}</p>
          {anchor.opening_question_hi && (
            <div className="talking-point" style={ML}>
              <div className="talking-point-label">शुरुआती सवाल (Opening Question)</div>
              {fmt(anchor.opening_question_hi)}
            </div>
          )}
          {['beginner', 'progressor', 'proficient'].map(level => {
            const key = `${level}_participation_hi`;
            if (!anchor[key]) return null;
            return (
              <div key={level} style={{ fontSize: '0.8125rem', margin: '4px 0', padding: '4px 8px', borderRadius: 4, background: `var(--${level}-bg)`, ...ML }}>
                <strong>{GROUP_LABELS[level]?.emoji} {GROUP_LABELS[level]?.hi} ({GROUP_LABELS[level]?.en}):</strong> {stripGroup(anchor[key])}
              </div>
            );
          })}
        </div>
      )}

      {/* Rotation Timeline */}
      <h2 style={{ margin: '16px 0 8px' }}>⏱️ रोटेशन शेड्यूल (Rotation Schedule)</h2>
      {blocks.length > 0 ? (
        blocks.map((block, i) => (
          <div key={i}
            className={`timeline-block ${block.type === 'teach' ? 'teach' : block.type === 'anchor' ? 'anchor' : 'transition'}`}
            onClick={() => setExpandedBlock(expandedBlock === i ? null : i)}
          >
            <div className="timeline-dot" style={{ background: block.type === 'teach' ? `var(--${block.teach_group || 'green-dark'})` : 'var(--border)' }} />
            {block.time_start && (
              <div style={{ fontSize: '0.6875rem', color: 'var(--text-secondary)', marginBottom: 2 }}>{block.time_start}</div>
            )}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <strong style={{ fontSize: '0.875rem' }}>
                {block.type === 'teach' && `👩‍🏫 ${GROUP_LABELS[block.teach_group]?.hi || block.teach_group} पढ़ाएँ (Teach ${GROUP_LABELS[block.teach_group]?.en || ''})`}
                {block.type === 'anchor' && '🎯 एंकर (Anchor)'}
                {block.type === 'setup' && '📢 सेटअप (Setup)'}
                {block.type === 'reteach' && '🔄 पुनः शिक्षण (Re-teach)'}
                {block.type === 'transition' && '↔️ संक्रमण (Transition)'}
              </strong>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{block.duration_minutes} मि.</span>
            </div>

            {block.type === 'teach' && block.other_groups_hi && (
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 4, ...ML }}>
                बाकी समूह (Other groups): {fmt(block.other_groups_hi)}
              </div>
            )}
            {block.script_hi && (
              <div style={{ fontSize: '0.8125rem', fontStyle: 'italic', marginTop: 4, ...ML }}>“{fmt(block.script_hi)}”</div>
            )}

            {expandedBlock === i && block.talking_points && (
              <div style={{ marginTop: 8 }}>
                {block.talking_points.i_do_hi && (
                  <div className="talking-point" style={ML}>
                    <div className="talking-point-label">मैं करूँगा (I Do)</div>
                    {fmt(block.talking_points.i_do_hi)}
                  </div>
                )}
                {block.talking_points.we_do_hi && (
                  <div className="talking-point" style={ML}>
                    <div className="talking-point-label">हम करेंगे (We Do)</div>
                    {fmt(block.talking_points.we_do_hi)}
                  </div>
                )}
                {block.talking_points.you_do_hi && (
                  <div className="talking-point" style={ML}>
                    <div className="talking-point-label">तुम करोगे (You Do)</div>
                    {fmt(block.talking_points.you_do_hi)}
                  </div>
                )}
              </div>
            )}
            {expandedBlock !== i && block.talking_points && (
              <div style={{ fontSize: '0.75rem', color: 'var(--text-light)', marginTop: 4 }}>
                ▸ बात के मुद्दे देखें (Tap for talking points)
              </div>
            )}
          </div>
        ))
      ) : (
        <div className="card" style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
          <p>रोटेशन शेड्यूल योजना बनने के बाद यहाँ दिखेगा।</p>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-light)', marginTop: 4 }}>
            Rotation schedule will appear after plan generation.
          </p>
        </div>
      )}

      {/* Worksheets: each opens the printable A4 sheet for this plan and level */}
      <h2 style={{ margin: '16px 0 8px' }}>📝 वर्कशीट (Worksheets)</h2>
      <div style={{ display: 'flex', gap: 8 }}>
        {['beginner', 'progressor', 'proficient'].map(level => {
          const label = GROUP_LABELS[level];
          const sheet = plan.worksheets?.[level];
          const available = Array.isArray(sheet?.problems) && sheet.problems.length > 0;
          const href = `/api/worksheet/${teacher.teacher_id}/${currentPlan.plan_date}/${currentPlan.domain_id}/${level}`;
          const style = { flex: 1, flexDirection: 'column', gap: 2, padding: '10px 4px', fontSize: '0.8125rem', textDecoration: 'none', textAlign: 'center' };
          const inner = (
            <>
              <span style={{ fontSize: '1.25rem' }}>{label?.emoji}</span>
              <strong>{label?.hi}</strong>
              <span style={{ fontSize: '0.6rem', opacity: 0.7 }}>{label?.en}</span>
              {available && sheet.required_count && sheet.required_count < sheet.problems.length && (
                <span style={{ fontSize: '0.6rem', opacity: 0.8 }}>पहले {sheet.required_count} सवाल</span>
              )}
            </>
          );
          return available ? (
            <a key={level} href={href} target="_blank" rel="noopener noreferrer" className="btn btn-secondary" style={style}>{inner}</a>
          ) : (
            <span key={level} className="btn" style={{ ...style, opacity: 0.45, border: '2px dashed var(--border)', color: 'var(--text-secondary)' }}>
              {inner}<span style={{ fontSize: '0.6rem' }}>उपलब्ध नहीं (not available)</span>
            </span>
          );
        })}
      </div>
      <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 6 }}>
        खुलने पर प्रिंट करें, या बोर्ड पर उतारें। (Opens the sheet: print it, or copy it to the board.)
      </p>

      {/* Why this plan? */}
      <div style={{ marginTop: 16, marginBottom: 80 }}>
        <button onClick={() => setShowWhyPanel(!showWhyPanel)}
          style={{ background: 'none', border: 'none', color: 'var(--green-dark)', fontSize: '0.875rem', cursor: 'pointer', fontFamily: 'inherit', fontWeight: 600 }}>
          {showWhyPanel ? '▾' : '▸'} यह योजना क्यों? (Why this plan?)
        </button>
        {showWhyPanel && (
          <div className="card" style={{ marginTop: 8, fontSize: '0.8125rem', background: 'var(--green-bg)' }}>
            {Array.isArray(explainability.items) ? explainability.items.map((item, i) => (
              <div key={i} style={{ marginBottom: 10 }}>
                <strong>{fmt(item.title_hi)} <span style={{ fontWeight: 400, color: 'var(--text-light)' }}>({fmt(item.title_en)})</span></strong>
                <div style={ML}>{fmt(item.body_hi)}</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', ...ML }}>{fmt(item.body_en)}</div>
              </div>
            )) : Object.entries(explainability).filter(([key]) => !key.startsWith('teacher_decision_')).map(([key, val]) => (
              <div key={key} style={{ marginBottom: 6 }}>
                <strong>{key}:</strong> {typeof val === 'string' ? val : JSON.stringify(val)}
              </div>
            ))}
            {Object.keys(explainability).length === 0 && (
              <p style={{ color: 'var(--text-secondary)' }}>व्याख्या डेटा उपलब्ध नहीं (Explainability data not available).</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
