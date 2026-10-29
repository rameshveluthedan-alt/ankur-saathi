// The printed pages' date and class lines (the printed plan, the tick sheet, the mentor report): Hindi only, the same for every teacher.
const MONTHS = ['जन॰', 'फ़र॰', 'मार्च', 'अप्रैल', 'मई', 'जून', 'जुलाई', 'अग॰', 'सित॰', 'अक्टू॰', 'नव॰', 'दिस॰'];
export const hiDate = (iso) => { const [y, m, d] = String(iso || '').split('-').map(Number); return y && m && d ? `${d} ${MONTHS[m - 1]} ${y}` : String(iso || ''); };
const GRADE = { balvatika: 'बालवाटिका', grade_1: '1', grade_2: '2', grade_3: '3' };
export const classLine = (grades) => {
  const g = (grades || []).filter((x) => GRADE[x]);
  const nums = g.filter((x) => x !== 'balvatika').map((x) => GRADE[x]);
  return [g.includes('balvatika') ? 'बालवाटिका' : null, nums.length ? `कक्षा ${nums.join(', ')}` : null].filter(Boolean).join(', ');
};
