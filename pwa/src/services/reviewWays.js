// The three ways of looking at the children's work (the Review's step 2), in one place, so the Review and the plan screen say the same thing.
// label: what the teacher does (the tab); who: who does what; why: what kind of skill needs this way; how: the steps, shown under "▸ कैसे करें?".
// Observing: ONE general instruction (OBSERVE), always true of the plan. The plan's own AI-written review prompts are not shown: on 29 Oct the N0.1.1
// prompt asked the teacher to watch for a task (sorting 10+ objects by a self-chosen rule) that the plan's You Do did not contain. They stay in the plan's
// data, to be shown again once the prompt guarantees they match the plan's activities (see docs/KNOWN_ISSUES.md).
// The meanings of A / PA / NA and the reading-aloud error rule: reviewed by Vaishnavi on 29 Oct (docs/HINDI_REVIEW_29OCT_REVIEWED_291026.csv).
// The key to the letters A / PA / NA (Vaishnavi, 29 Oct): the observing steps below, the tick sheet and every footnote use this one line
export const ABBR = { hi: 'A = बिना मदद के करके दिखाया · PA = मदद से या आंशिक रूप से सही · NA = अभी नहीं', en: 'A = did it without help · PA = with help, or partly correct · NA = not yet' };

export const CHANNELS = [
  { id: 'observed', icon: '✓', hi: 'देखकर दर्ज करें', en: 'Observe and record',
    who: { hi: 'आप हर बच्चे के लिए A / PA / NA चुनते हैं।', en: 'You choose A / PA / NA for each child.' },
    why: { hi: 'यह कौशल बच्चे करके या बोलकर दिखाते हैं (जैसे छाँटना, गिनना, बताना); इसे देखकर आँका जाता है, लिखकर नहीं।', en: 'Children show this skill by doing or saying (sorting, counting, telling); it is judged by watching, not on paper.' },
    how: [
      { hi: 'स्वतंत्र अभ्यास (तुम करोगे) के दौरान बच्चों को काम करते हुए देखें, फिर हर बच्चे के लिए A / PA / NA चुनें। ज़रूरत हो तो एक छोटा सवाल पूछें।', en: 'During independent practice (You Do), watch the children at work, then choose A / PA / NA for each child. Ask a short question if needed.' },
      ABBR,
      { hi: 'जो बच्चे दिखे, उन्हीं के लिए चुनें; बाकी बाद में।', en: 'Choose only for the children you saw; the others later.' },
    ] },
  { id: 'photo', icon: '📸', hi: 'वर्कशीट की फ़ोटो', en: 'Worksheet photo',
    who: { hi: 'आप वर्कशीट की फ़ोटो लेते हैं; AI हर बच्चे का काम पढ़ता है।', en: "You take a photo of the worksheets; the AI reads each child's work." },
    why: { hi: 'इस कौशल का काम बच्चे कागज़ पर करते हैं; वर्कशीट में हर बच्चे का काम और उसकी गलतियाँ दिखती हैं।', en: "Children do this skill on paper; the worksheet shows each child's work and mistakes." },
    how: [
      { hi: 'हर बच्चा वर्कशीट पर ऊपर अपना रोल नंबर लिखे।', en: 'Each child writes their roll number at the top of the sheet.' },
      { hi: 'वर्कशीट समतल रखें, अच्छी रोशनी में; पूरा पन्ना फ़्रेम में हो।', en: 'Lay the sheet flat, in good light, with the whole page in the frame.' },
      { hi: 'ऊपर सुझाए गए बच्चों (नमूना) की वर्कशीट लें; एक बार में 6 तक फ़ोटो।', en: 'Take the sheets of the suggested children (the sample); up to 6 photos at a time.' },
      { hi: 'फ़ोटो में बच्चे का नाम न हो।', en: "No child's name in the photo." },
    ] },
  { id: 'orf', icon: '⏱️', hi: 'पढ़कर सुनाना', en: 'Reading aloud',
    who: { hi: 'बच्चा एक मिनट पढ़ता है; आप सही पढ़े गए शब्द और गलतियाँ दर्ज करते हैं।', en: 'The child reads for a minute; you enter the words read correctly and the errors.' },
    why: { hi: 'यह पढ़ने की रफ़्तार का कौशल है; इसे बच्चे को पढ़ते हुए सुनकर ही जाँचा जा सकता है।', en: 'This is a reading-speed skill; it can only be checked by listening to the child read.' },
    how: [
      { hi: 'नीचे दिया पाठ बच्चे को पढ़ने दें; यह आज कक्षा में नहीं पढ़ा गया, इसलिए पढ़ने की रफ़्तार सही पता चलेगी।', en: "Let the child read the text below; it was not read in class today, so the reading pace shows truly." },
      { hi: 'एक मिनट का समय शुरू करें।', en: 'Start a one-minute timer.' },
      { hi: 'एक मिनट में सही पढ़े गए शब्द गिनें।', en: 'Count the words read correctly in that minute.' },
      { hi: 'गलती गिनें: गलत शब्द, छूटा शब्द, या जो शब्द आपको बताना पड़ा।', en: 'Count errors: a wrong word, a skipped word, or a word you had to give.' },
      { hi: 'दोनों संख्याएँ दर्ज करें।', en: 'Enter both numbers.' },
    ] },
];

export const channelOf = (id) => CHANNELS.find((c) => c.id === id) || null;

// A group checked by observation may still have a worksheet (practice): say so, so the teacher does not photograph it
export const PRACTICE_ONLY = { hi: 'इस कौशल की वर्कशीट अभ्यास के लिए है; जाँच बच्चों को करते हुए देखकर होती है, वर्कशीट की फ़ोटो से नहीं।', en: "This skill's worksheet is for practice; the check is by watching the children do it, not from a photo of the worksheet." };
export const hasWorksheet = (planReply, level) => {
  const ws = ((planReply && planReply.plan && planReply.plan.worksheets) || {})[level];
  return !!(ws && Array.isArray(ws.problems) && ws.problems.length);
};

export const OBSERVE = { hi: 'स्वतंत्र अभ्यास (तुम करोगे) के दौरान बच्चों को काम करते हुए देखें, फिर हर बच्चे के लिए A / PA / NA चुनें।',
                         en: 'During independent practice (You Do), watch the children at work, then choose A / PA / NA for each child.' };

/** Does the plan say anything is checked by observation today? (Only whether: the plan's own prompt text is not shown.) */
export function hasObservation(planReply) {
  const raw = ((planReply && planReply.plan && planReply.plan.review_prompts) || {}).observation_reminders_hi;
  return (Array.isArray(raw) ? raw : [raw]).map((t) => String(t || '').trim()).some((t) => t && !/कोई (केवल-)?अवलोकन वाली दक्षता नहीं/.test(t));
}
