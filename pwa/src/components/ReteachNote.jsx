import React from 'react';
import { reteachSummary } from '../services/reteachInfo';

/**
 * The note on a re-teach block of the lesson plan.
 * Always: that it is a re-teach, which children made the mistake (their roll numbers: this is the teacher's own screen) and which mistakes.
 * When the block is opened: the pace for the block's length, and what the teachers asked for: the wrong way first and erased, a quiet visit to the children, the quarter rule.
 */
export default function ReteachNote({ block, expanded }) {
  const s = reteachSummary(block);
  if (!s.isReteach) return null;
  const small = { fontSize: '0.7rem', color: 'var(--text-secondary)' };
  return (
    <div data-testid="reteach-note" style={{ marginTop: 6, background: 'var(--green-bg)', borderRadius: 8, padding: '6px 8px', fontSize: '0.75rem' }}>
      <div><b>🔄 पुनः शिक्षण (Re-teach)</b>: पिछली जाँच की गलतियों पर, कौशल दोबारा समझाना</div>
      {s.rolls.length > 0 && (
        <div data-testid="reteach-children">👥 पिछली जाँच में गलती करने वाले बच्चे (Children who made the mistake at the last review): रोल {s.rolls.join(', ')}</div>
      )}
      {s.mistakes.length > 0 ? (
        <div data-testid="reteach-mistakes">गलतियाँ (Mistakes): {s.mistakes.map((m) => `${m.name_hi || m.misconception_id} (${m.children} बच्चे)`).join('; ')}</div>
      ) : (
        <div data-testid="reteach-no-mistake" style={small}>कोई खास गलती दर्ज नहीं हुई: इस कौशल की आम गलतियाँ दोबारा समझाई जाएँगी। (No specific mistake was recorded: the skill's usual mistakes are re-taught.)</div>
      )}
      {expanded && (
        <div style={{ marginTop: 4 }}>
          {s.pace && (
            <div data-testid="reteach-pace">
              ⏱ सुझाया समय ({s.pace.total} मि.): {s.pace.parts.map((p) => `${p.hi} ${p.min}`).join(' · ')}
              <span style={{ ...small, display: 'block' }}>(Suggested pace: {s.pace.parts.map((p) => `${p.en} ${p.min}`).join(' · ')} minutes)</span>
            </div>
          )}
          <ul data-testid="reteach-tips" style={{ margin: '4px 0 0', paddingLeft: 18, ...small }}>
            <li>पहले गलत तरीका दिखाएँ और समझाएँ, फिर सही तरीका। मैं करूँगा के अंत में गलत वाला मिटा दें, ताकि बोर्ड पर केवल सही रहे। (Show the wrong way first, then the right one, and erase the wrong one at the end of I Do.)</li>
            <li>तुम करोगे में सबसे पहले इन बच्चों के पास चुपचाप जाएँ, सामान्य चक्कर के भाग की तरह। नाम या रोल नंबर न बोलें। (In You Do visit these children first, quietly, as part of the normal round. Never call out names or roll numbers.)</li>
            <li>जाँच में समूह के एक-चौथाई से ज़्यादा बच्चे गलत हों, तो आगे बढ़ने से पहले वही कदम अभी दोबारा समझाएँ। (If more than a quarter are wrong in the show-me, re-teach that step at once.)</li>
          </ul>
        </div>
      )}
    </div>
  );
}
