// The printed pages' date and class lines (the printed plan, the tick sheet, the mentor report): Hindi only, the same for every teacher.
// footnotes for the printed reports (29 Oct, wording reviewed by Vaishnavi): what a skill code is, and the group marks where they stand alone
export const CODE_NOTE = 'N2.3.2 जैसे कोड कौशल-सीढ़ी में दिए गए कौशलों की पहचान करते हैं।';
export const MARKS_NOTE = '● शुरुआती · ▲ प्रगतिशील · ■ दक्ष';

const MONTHS = ['जन॰', 'फ़र॰', 'मार्च', 'अप्रैल', 'मई', 'जून', 'जुलाई', 'अग॰', 'सित॰', 'अक्टू॰', 'नव॰', 'दिस॰'];
export const hiDate = (iso) => { const [y, m, d] = String(iso || '').split('-').map(Number); return y && m && d ? `${d} ${MONTHS[m - 1]} ${y}` : String(iso || ''); };
const GRADE = { balvatika: 'बालवाटिका', grade_1: '1', grade_2: '2', grade_3: '3' };
export const classLine = (grades) => {
  const g = (grades || []).filter((x) => GRADE[x]);
  const nums = g.filter((x) => x !== 'balvatika').map((x) => GRADE[x]);
  return [g.includes('balvatika') ? 'बालवाटिका' : null, nums.length ? `कक्षा ${nums.join(', ')}` : null].filter(Boolean).join(', ');
};
