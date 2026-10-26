// The three groups (B/P/P), named and marked the same way on every screen.
// mark: a shape as well as a colour (index.css draws the same shapes on .badge-*), so the groups never depend on colour alone.
export const GROUP_LABELS = {
  beginner: { hi: 'शुरुआती', en: 'Beginner', emoji: '🟠', mark: '●', css: 'beginner' },
  progressor: { hi: 'प्रगतिशील', en: 'Progressor', emoji: '🟡', mark: '▲', css: 'progressor' },
  proficient: { hi: 'दक्ष', en: 'Proficient', emoji: '🟢', mark: '■', css: 'proficient' },
};
export const GROUP_ORDER = ['beginner', 'progressor', 'proficient'];
