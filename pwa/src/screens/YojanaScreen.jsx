import React, { useState } from 'react';
import { useAuth } from '../App';

const GROUP_LABELS = {
  beginner: { hi: 'शुरुआती', emoji: '🟠', css: 'beginner' },
  progressor: { hi: 'प्रगतिशील', emoji: '🟡', css: 'progressor' },
  proficient: { hi: 'दक्ष', emoji: '🟢', css: 'proficient' },
};

export default function YojanaScreen() {
  const { currentPlan } = useAuth();
  const [expandedBlock, setExpandedBlock] = useState(null);
  const [showWhyPanel, setShowWhyPanel] = useState(false);

  if (!currentPlan) {
    return (
      <div className="screen">
        <div className="empty-state">
          <div className="empty-icon">📋</div>
          <h2>कोई योजना नहीं</h2>
          <p style={{ marginTop: 8, color: 'var(--text-secondary)' }}>
            पहले "योजना" टैब से लक्ष्य चुनें और दैनिक योजना बनाएँ।
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
  const management = plan.classroom_management || {};
  const explainability = currentPlan.explainability || plan.explainability || {};

  return (
    <div className="screen">
      {/* Header */}
      <div className="screen-header">
        <h1>📋 दैनिक योजना</h1>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
          {currentPlan.plan_date} · {currentPlan.selected_competency_id}
        </span>
      </div>

      {/* Groups summary */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        {groups.map(g => (
          <div key={g.label} className="card" style={{ flex: 1, padding: 10, textAlign: 'center' }}>
            <span className={`badge badge-${g.label}`}>{GROUP_LABELS[g.label]?.hi}</span>
            <div style={{ fontWeight: 700, fontSize: '1.125rem', margin: '4px 0' }}>{g.count}</div>
            <div style={{ fontSize: '0.6875rem', color: 'var(--text-secondary)' }}>{g.target_competency_name_hi}</div>
          </div>
        ))}
      </div>

      {/* Anchor Activity */}
      {anchor.narration_hi && (
        <div className="card" style={{ borderLeft: '4px solid var(--channel-written)' }}>
          <div className="card-header">
            <h3>🎯 एंकर गतिविधि</h3>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>10 मि.</span>
          </div>
          <p style={{ fontSize: '0.9375rem', marginBottom: 8 }}>{anchor.narration_hi}</p>
          {anchor.opening_question_hi && (
            <div className="talking-point">
              <div className="talking-point-label">शुरुआती सवाल</div>
              {anchor.opening_question_hi}
            </div>
          )}
          {['beginner', 'progressor', 'proficient'].map(level => {
            const key = `${level}_participation_hi`;
            if (!anchor[key]) return null;
            return (
              <div key={level} style={{ fontSize: '0.8125rem', margin: '4px 0', padding: '4px 8px', borderRadius: 4, background: `var(--${level}-bg)` }}>
                <strong>{GROUP_LABELS[level]?.emoji} {GROUP_LABELS[level]?.hi}:</strong> {anchor[key]}
              </div>
            );
          })}
        </div>
      )}

      {/* Rotation Timeline */}
      <h2 style={{ margin: '16px 0 8px' }}>⏱️ रोटेशन शेड्यूल</h2>
      {blocks.length > 0 ? (
        blocks.map((block, i) => (
          <div key={i}
            className={`timeline-block ${block.type === 'teach' ? 'teach' : block.type === 'anchor' ? 'anchor' : 'transition'}`}
            data-time={block.time_start || ''}
            onClick={() => setExpandedBlock(expandedBlock === i ? null : i)}
          >
            <div className="timeline-dot" style={{ background: block.type === 'teach' ? `var(--${block.teach_group || 'green-dark'})` : 'var(--border)' }} />
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <strong style={{ fontSize: '0.875rem' }}>
                {block.type === 'teach' && `👩‍🏫 ${GROUP_LABELS[block.teach_group]?.hi || block.teach_group} पढ़ाएँ`}
                {block.type === 'anchor' && '🎯 एंकर गतिविधि'}
                {block.type === 'setup' && '📢 सेटअप'}
                {block.type === 'reteach' && '🔄 पुनः शिक्षण'}
                {block.type === 'transition' && '↔️ संक्रमण'}
              </strong>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{block.duration_minutes} मि.</span>
            </div>

            {/* Talking points (expanded) */}
            {expandedBlock === i && block.talking_points && (
              <div style={{ marginTop: 8 }}>
                {block.talking_points.i_do_hi && (
                  <div className="talking-point">
                    <div className="talking-point-label">मैं करूँगा (I Do)</div>
                    {block.talking_points.i_do_hi}
                  </div>
                )}
                {block.talking_points.we_do_hi && (
                  <div className="talking-point">
                    <div className="talking-point-label">हम करेंगे (We Do)</div>
                    {block.talking_points.we_do_hi}
                  </div>
                )}
                {block.talking_points.you_do_hi && (
                  <div className="talking-point">
                    <div className="talking-point-label">तुम करोगे (You Do)</div>
                    {block.talking_points.you_do_hi}
                  </div>
                )}
              </div>
            )}
            {expandedBlock !== i && block.talking_points && (
              <div style={{ fontSize: '0.75rem', color: 'var(--text-light)', marginTop: 4 }}>
                ▸ बात के मुद्दे देखने के लिए टैप करें
              </div>
            )}
          </div>
        ))
      ) : (
        <div className="card" style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
          <p>रोटेशन शेड्यूल योजना बनने के बाद यहाँ दिखेगा।</p>
          <p style={{ fontSize: '0.8125rem', marginTop: 8 }}>
            {rotation.total_minutes ? `कुल समय: ${rotation.total_minutes} मिनट` : ''}
          </p>
        </div>
      )}

      {/* Worksheets download */}
      <h2 style={{ margin: '16px 0 8px' }}>📝 वर्कशीट</h2>
      <div style={{ display: 'flex', gap: 8 }}>
        {['beginner', 'progressor', 'proficient'].map(level => (
          <button key={level} className="btn btn-secondary" style={{ flex: 1, padding: '10px 4px', fontSize: '0.8125rem' }}>
            {GROUP_LABELS[level]?.emoji}<br />
            {GROUP_LABELS[level]?.hi}
          </button>
        ))}
      </div>

      {/* Why this plan? */}
      <div style={{ marginTop: 16, marginBottom: 80 }}>
        <button
          onClick={() => setShowWhyPanel(!showWhyPanel)}
          style={{ background: 'none', border: 'none', color: 'var(--green-dark)', fontSize: '0.875rem', cursor: 'pointer', fontFamily: 'inherit', fontWeight: 600 }}
        >
          {showWhyPanel ? '▾' : '▸'} यह योजना क्यों? (Why this plan?)
        </button>
        {showWhyPanel && (
          <div className="card" style={{ marginTop: 8, fontSize: '0.8125rem', background: 'var(--green-bg)' }}>
            {Object.entries(explainability).map(([key, val]) => (
              <div key={key} style={{ marginBottom: 6 }}>
                <strong>{key}:</strong> {typeof val === 'string' ? val : JSON.stringify(val)}
              </div>
            ))}
            {Object.keys(explainability).length === 0 && (
              <p style={{ color: 'var(--text-secondary)' }}>व्याख्या डेटा उपलब्ध नहीं।</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
