// Vaishnavi's review of the new Hindi (29 Oct, docs/HINDI_REVIEW_29OCT_REVIEWED_291026.csv): each change she asked for, pinned here by its row number, so a
// later edit cannot quietly undo it. The screens' own tests check the same lines in place; this one reads the sources. No browser, no server.
//
//     cd pwa
//     node tests/hindi_review_29oct.test.mjs
import fs from 'node:fs'; import path from 'node:path'; import { fileURLToPath } from 'node:url';
const here = path.dirname(fileURLToPath(import.meta.url)); const src = path.join(here, '..', 'src');
const read = (f) => fs.readFileSync(path.join(src, f), 'utf8');
const ways = read('services/reviewWays.js'), review = read('screens/ReviewScreen.jsx'), ticks = read('screens/TickSheet.jsx'), how = read('components/HowItWorks.jsx');
const plan = read('screens/PlanScreen.jsx'), today = read('components/ProgressToday.jsx'), summary = read('screens/ClassSummary.jsx'), mentor = read('screens/MentorReport.jsx');
const service = fs.readFileSync(path.join(here, '..', '..', 'backend', 'app', 'services', 'progress_service.py'), 'utf8');
let n = 0; const check = (label, ok) => { n += 1; console.log(`  ${ok ? 'OK  ' : 'FAIL'} ${label}`); if (!ok) process.exitCode = 1; };

check('#39 the meanings of A / PA / NA (the Review and the tick sheet\'s key, one line)', ways.includes("'A = बिना मदद के करके दिखाया · PA = मदद से या आंशिक रूप से सही · NA = अभी नहीं'") && ticks.includes("CHANNELS.find((c) => c.id === 'observed').how[1].hi") && !/आधा सही/.test(ways));
check('#52 reading aloud, who does what: "सही पढ़े गए शब्द … दर्ज करते हैं"', ways.includes("'बच्चा एक मिनट पढ़ता है; आप सही पढ़े गए शब्द और गलतियाँ दर्ज करते हैं।'"));
check('#54 reading aloud, why an unseen text: "पढ़ने की रफ़्तार सही पता चलेगी"', ways.includes('इसलिए पढ़ने की रफ़्तार सही पता चलेगी।') && !ways.includes('रफ़्तार सही दिखेगी'));
check('#64 the step badges in the back buttons are followed by a colon (both)', review.includes('<span className="step-count">1/3</span>: <Bi hi="पहला अनुमान बदलें"') && review.includes('<span className="step-count">2/3</span>: <Bi hi="बच्चों का काम"'));
check('#68 "… में से … बच्चों का आकलन" (Review step 3, and the Progress screen\'s today card)', review.includes('में से {ev.assessed} बच्चों का आकलन') && today.includes('में से {g.assessed} बच्चों का आकलन'));
check('#71 the suggestion says its rule: of those checked, a third or more; at least 4 checked', review.includes('सुझाव: 🔄 दोहराएँ (जाँचे गए बच्चों में से एक-तिहाई या ज़्यादा से गलती हुई; कम से कम 4 बच्चों की जाँच)'));
check('#88 the tick sheet\'s column: "रोल नंबर" (both tables)', ticks.includes('<th>{L.mark} रोल नंबर</th>'));
check('#99 "जाँची-परखी सामग्री" ("अंकुर साथी कैसे काम करता है?"; the Plan screen\'s coverage note that also used it was removed on 30 Oct)', how.includes('AI जाँची-परखी सामग्री') && !how.includes('जाँची हुई') && !plan.includes('जाँची हुई सामग्री'));
check('#167 the class summary\'s reasons: "❓ पक्का नहीं: यही कौशल फिर", "कई बच्चों से गलती हुई: यही फिर"', summary.includes("not_sure: '❓ पक्का नहीं: यही कौशल फिर'") && summary.includes("recommended: 'कई बच्चों से गलती हुई: यही फिर'"));
check('#136 the mentor report\'s strength: one line naming each part that is not zero (reviews, skills, plans)', /parts = \[x for x in \(p\["review_days"\] and .*दिन समीक्षा पूरी हुई.*बच्चों ने .*कौशल हासिल किए.*दिन योजना बनी/s.test(service));
check('#142 the evidence point needs at least 3 groups taught, printed with the rules', /"evidence_min": 3/.test(service) && /p\["groups_taught"\] >= R\["evidence_min"\]/.test(service) && mentor.includes('(कम से कम {R.evidence_min} समूह)'));
check('#10, #133 the names stay: "टिक शीट", "मेंटर रिपोर्ट"', ticks.includes("'टिक शीट'") && mentor.includes("'मेंटर रिपोर्ट'"));


console.log('\nthe footnotes (29 Oct, wording reviewed by Vaishnavi)');
const fmt = read('services/printFormat.js'), confirm = read('components/ReviewConfirm.jsx'), progress = read('screens/ProgressScreen.jsx'), print = read('screens/PlanPrint.jsx'), key = read('components/AbbrKey.jsx');
check('the key to A / PA / NA is ONE line (services/reviewWays.js ABBR), used by the observing steps and the AbbrKey line', /export const ABBR = \{ hi: 'A = बिना मदद के करके दिखाया · PA = मदद से या आंशिक रूप से सही · NA = अभी नहीं'/.test(ways) && /^\s+ABBR,$/m.test(ways) && key.includes('<Bi hi={ABBR.hi} en={ABBR.en} inline />'));
check('...shown wherever the letters stand alone: Review step 2 (observing) and step 3, the saved box, Class progress, the printed plan, the class summary',
  review.includes('<AbbrKey testid="abbr-observe" />') && review.includes('<AbbrKey testid="abbr-final" />') && confirm.includes('<AbbrKey testid="abbr-saved" />')
  && progress.includes('<AbbrKey testid="abbr-progress" />') && print.includes('{observing && <Line testid="print-abbr" className="print-footer">{ABBR.hi}</Line>}') && summary.includes('data-testid="class-key">{ABBR.hi} · {CODE_NOTE}'));
check('the skill codes, in her wording: "N2.3.2 जैसे कोड कौशल-सीढ़ी में दिए गए कौशलों की पहचान करते हैं।" (the class summary and the mentor report)',
  fmt.includes("export const CODE_NOTE = 'N2.3.2 जैसे कोड कौशल-सीढ़ी में दिए गए कौशलों की पहचान करते हैं।';") && mentor.includes('data-testid="mentor-key">{MARKS_NOTE} · {CODE_NOTE}'));
check('the group marks where they stand alone (the mentor report\'s groups line): "● शुरुआती · ▲ प्रगतिशील · ■ दक्ष"', fmt.includes("export const MARKS_NOTE = '● शुरुआती · ▲ प्रगतिशील · ■ दक्ष';"));
check('"CWPM" is never shown to the teacher: "सही शब्द/मिनट" instead (the saved box and the "पढ़ चुके" list)', !/\} CWPM|CWPM` :/.test(confirm + review) && confirm.includes('{r.cwpm} सही शब्द/मिनट') && review.includes('${rec.cwpm} सही शब्द/मिनट'));

console.log(process.exitCode ? `\nFAILED (${n} checks)` : `\nAll ${n} checks passed.`);
