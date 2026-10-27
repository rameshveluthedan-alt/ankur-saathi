// Reading aloud: the DAILY label is about pace ("रफ़्तार …"), never "reader". The "reader" words (grade-level / developing / early reader) are kept for the
// periodic round (Phase 3) and are not shown anywhere today: the server's classification is an internal code, and EVERY screen turns it into words here,
// so a teacher never sees two different labels for the same result.
//
// The server returns the A/PA/NA code from the skill's own CWPM thresholds (achieved | partially_achieved | not_achieved); the band names
// (grade_level | developing | early_reader) mean the same three bands and are accepted too, so a later rename on the server changes nothing on screen.
export const PACE_LABEL = {
  grade_level: { hi: 'रफ़्तार कक्षा-स्तर पर', en: 'Pace at grade level' },
  developing: { hi: 'रफ़्तार विकसित हो रही', en: 'Pace developing' },
  early_reader: { hi: 'रफ़्तार धीमी', en: 'Pace slow' },
};
const BAND_OF = {
  grade_level: 'grade_level', achieved: 'grade_level',
  developing: 'developing', partially_achieved: 'developing',
  early_reader: 'early_reader', not_achieved: 'early_reader',
};
export const paceLabel = (classification) => PACE_LABEL[BAND_OF[classification]] || null;

// The reading skills scored by words per minute (the others, such as pauses and expression, are judged by listening and keep the A/PA/NA line)
export const FLUENCY_SKILLS = ['L1.5.1', 'L2.5.1', 'L3.5.1'];
export const isFluencySkill = (skillId) => FLUENCY_SKILLS.includes(skillId);

// many errors for the words read: a quarter or more of the correct words (the errors part only turns amber; the pace label stays what it is)
export const manyErrors = (correct, errors) => Number(errors) > 0 && Number(errors) >= Number(correct) / 4;
