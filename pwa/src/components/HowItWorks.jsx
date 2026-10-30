import React from 'react';
import Bi from './Bi';

// How the parts come together, in the order a teacher meets them. Each step names what powers it, so an evaluator sees the whole loop in one place.
export const HOW_STEPS = [
  { icon: '👥', hi: 'कक्षा-रजिस्टर', en: 'Class register', part: { hi: 'CSV / Excel', en: 'CSV / Excel' },
    text: { hi: 'सब यहीं से शुरू होता है: आप अपनी कक्षा का रजिस्टर (CSV या Excel) डालते हैं, और बच्चों के स्तर से ऐप तीनों समूह बनाता है।',
            en: "Everything starts here: you upload your class register (CSV or Excel), and the app forms the three groups from the children's levels." } },
  { icon: '🎯', hi: 'योजना बनाएँ', en: 'Make plan', part: { hi: 'कौशल-सीढ़ी', en: 'skill ladder' },
    text: { hi: 'आप आज का कौशल और समय चुनते हैं। ऐप तीनों समूहों (● शुरुआती, ▲ प्रगतिशील, ■ दक्ष) के कौशल सुझाता है: 101 कौशलों की सीढ़ी और पिछली समीक्षा से।',
            en: "You choose today's skill and time. The app suggests each group's skill (● Beginner, ▲ Progressor, ■ Proficient) from a ladder of 101 skills and the last review." } },
  { icon: '📋', hi: 'आज की योजना', en: "Today's plan", part: { hi: 'AI + जाँच', en: 'AI + checks' },
    text: { hi: 'AI जाँची-परखी सामग्री (गतिविधियाँ, पाठ, आम गलतियाँ) से हर समूह का पाठ, समझ की जाँच और वर्कशीट लिखता है। ऐप हर योजना को नियमों पर जाँचता है।',
            en: "The AI writes each group's lesson, understanding check and worksheet from checked content (activities, passages, common mistakes). The app checks every plan against rules." } },
  { icon: '☑️', hi: 'समीक्षा', en: 'Review', part: { hi: 'फ़ोटो, अवलोकन, पढ़कर सुनाना', en: 'photo, observation, reading aloud' },
    text: { hi: 'तीन चरण: हर समूह का आपका पहला अनुमान; बच्चों का काम देखें (वर्कशीट की फ़ोटो जिसे AI पढ़ता है, अवलोकन, या पढ़कर सुनाना, जो कौशल के लिए ठीक हो); और आज की जाँच देखकर अंतिम निर्णय।',
            en: "Three steps: your first judgment for each group; the children's work (a worksheet photo read by the AI, observation, or reading aloud: whichever fits the skill); and a final decision with today's evidence in front of you." } },
  { icon: '📊', hi: 'कक्षा प्रगति', en: 'Class progress', part: { hi: 'आज के नतीजे', en: "today's results" },
    text: { hi: 'आज के नतीजे, आपके निर्णय, और जिन बच्चों पर एक नज़र डालनी है।', en: "Today's results, your decisions, and the children to look at." } },
];

/** "अंकुर साथी कैसे काम करता है?" (How Ankur Saathi works): a fold, closed by default, on the login screen only (Profile is for account tasks). */
export default function HowItWorks({ className = 'card fold' }) {
  return (
    <details className={className} data-testid="how-it-works" style={{ padding: '4px 12px' }}>
      <summary><span>ℹ️ <Bi hi="अंकुर साथी कैसे काम करता है?" en="How Ankur Saathi works" inline /></span></summary>
      <ol style={{ listStyle: 'none', padding: 0, margin: '4px 0 0' }}>
        {HOW_STEPS.map((s, i) => (
          <li key={s.en} data-testid="how-step" style={{ display: 'flex', gap: 8, padding: '6px 0', borderTop: i ? '1px dashed var(--border)' : 'none' }}>
            <span style={{ fontSize: '1.25rem', lineHeight: 1.2 }} aria-hidden="true">{s.icon}</span>
            <div style={{ fontSize: '0.8125rem' }}>
              <div style={{ fontWeight: 700 }}>
                {i + 1}. {s.hi}<span className="en en-inline" lang="en">{s.en}</span>
                <span style={{ fontWeight: 400, fontSize: '0.7rem', color: 'var(--text-secondary)', marginLeft: 6 }}>· {s.part.hi}<span className="en en-inline" lang="en">{s.part.en}</span></span>
              </div>
              <Bi hi={s.text.hi} en={s.text.en} />
            </div>
          </li>
        ))}
      </ol>
      <p data-testid="how-loop" style={{ fontSize: '0.8125rem', fontWeight: 600, margin: '6px 0 2px' }}>
        <Bi hi="↻ आपके निर्णय और आज के नतीजे कल की योजना का सुझाव बनाते हैं।" en="↻ Your decisions and today's results shape tomorrow's suggestion." />
      </p>
      <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: '2px 0 8px' }}>
        <Bi hi="🔒 बच्चों के नाम AI को कभी नहीं भेजे जाते।" en="🔒 Children's names never go to the AI." />
      </p>
    </details>
  );
}
