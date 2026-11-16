// The printed pages' date and class lines (the printed plan, the tick sheet, the mentor report): Hindi only, the same for every teacher.
// footnotes for the printed reports (29 Oct, wording reviewed by Vaishnavi): what a skill code is, and the group marks where they stand alone
export const CODE_NOTE = 'N2.3.2 जैसे कोड कौशल-सीढ़ी में दिए गए कौशलों की पहचान करते हैं।';
export const MARKS_NOTE = '● शुरुआती · ▲ प्रगतिशील · ■ दक्ष';

// the English versions, for the class summary and the mentor report when the teacher has chosen English (16 Nov)
export const CODE_NOTE_EN = 'Codes such as N2.3.2 identify the skills on the skill ladder.';
export const MARKS_NOTE_EN = '● Beginner · ▲ Progressor · ■ Proficient';
const MONTHS_EN = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
export const enDate = (iso) => { const [y, m, d] = String(iso || '').split('-').map(Number); return y && m && d ? `${d} ${MONTHS_EN[m - 1]} ${y}` : String(iso || ''); };
export const classLineEn = (grades) => {
  const g = grades || [];
  const nums = g.filter((x) => /^grade_\d$/.test(x)).map((x) => x.slice(6));
  return [g.includes('balvatika') ? 'Balvatika' : null, nums.length ? `Grade ${nums.join(', ')}` : null].filter(Boolean).join(', ');
};

const MONTHS = ['जन॰', 'फ़र॰', 'मार्च', 'अप्रैल', 'मई', 'जून', 'जुलाई', 'अग॰', 'सित॰', 'अक्टू॰', 'नव॰', 'दिस॰'];
export const hiDate = (iso) => { const [y, m, d] = String(iso || '').split('-').map(Number); return y && m && d ? `${d} ${MONTHS[m - 1]} ${y}` : String(iso || ''); };
const GRADE = { balvatika: 'बालवाटिका', grade_1: '1', grade_2: '2', grade_3: '3' };
export const classLine = (grades) => {
  const g = (grades || []).filter((x) => GRADE[x]);
  const nums = g.filter((x) => x !== 'balvatika').map((x) => GRADE[x]);
  return [g.includes('balvatika') ? 'बालवाटिका' : null, nums.length ? `कक्षा ${nums.join(', ')}` : null].filter(Boolean).join(', ');
};
