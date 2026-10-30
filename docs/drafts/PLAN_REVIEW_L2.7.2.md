# Two L2.7.2 plans reviewed (30 Oct, lab)

**Skill:** L2.7.2 "परिचित विषय पर 3-5 जुड़े वाक्य लिखता है" (writes 3-5 connected sentences on a familiar topic). The groups' skills in both plans: Beginners
**L2.7.1** (writes sentences with correct matras from dictation), Progressors **L2.7.2**, Proficients **L3.7.1** (writes a coherent 5-7 sentence paragraph).
All three are checked by a photo of the worksheet ("written"), and **none has a recorded mistake in the knowledge base**.

**The two plans:**
- **Recorded:** `db/seeds/sample_plans/L2.7.2.json`, the plan teachers see when the AI limit is reached (read and signed by Vaishnavi, 26 Oct).
- **New:** generated on main on 30 Oct with the current prompt (`scripts/batch_generate.py --only L2.7.2`, $0.12, 90 minutes), copied to the lab as
  `C:\dev\lab-handoff\L2.7.2_new.json` (not committed).

**How they were checked:** the lab's copy of the server's plan checks (`validate_plan_shape`, `find_text_overlaps` with 5 and with 4 words), the Hindi safety net
(`soften_plan`), the knowledge base (the three skills' modality and recorded mistakes), then a read of every lesson line, show-me question, worksheet problem
and review prompt. Nothing was changed.

## Results side by side

| | Recorded | New |
|---|---|---|
| Server checks | pass, 0 warnings | 2 warnings: Progressor and Proficient problem 6 repeat lesson wording |
| Lesson (I Do / We Do / You Do) | fits each skill; think-aloud, built together | the same |
| Show-me questions | fit writing (full stops, which sentence connects, where a sentence ends); 10 command forms, all made polite by the safety net | fit writing (the sentence that does not belong, the order of events, where a sentence ends); 5 command forms, all made polite; **"मैं बोलती हूँ" twice, not fixed** |
| Progressor sheet | 7 comprehension questions on "पानी बचाओ"; **no writing** | 5 comprehension or punctuation items + **1 writing task** (problem 6) |
| Proficient sheet | 7 comprehension questions on "दादी की बगिया"; **no writing** | 5 comprehension items + **1 writing task** (problem 6) |
| Beginner sheet (dictation) | 8 sentences, **each printed on the sheet** | 3 words + 5 sentences, **each printed on the sheet** (problems 1-3 print the very word to write) |
| Mistake-revealing problems | none | none |
| Lesson/worksheet overlap | "सीता फूल लाती है।" in the We Do and on the sheet (missed: 4 words) | the Progressor writing topic is the I Do's own model ("हमारा स्कूल") |
| Session length recorded | no (shown as 90) | 90 |

## Findings, most serious first

1. **The worksheets do not check the skill they are for.** Most of the Progressor and Proficient sheets are reading comprehension, so the photo after class
   measures comprehension and records it as evidence of a writing skill. The new plan adds one writing task to each sheet (better), but it is 1 problem in 6.
   **Cause (the prompt):** the literacy worksheet rule makes every Progressor and Proficient sheet a passage with questions, whatever the skill, and the code
   places the bank's comprehension questions first. The same in both runs: it is built in, not chance.
2. **A writing task cannot be marked against an answer key.** The new plan's writing answers are "कोई भी 3 जुड़े वाक्य, …", while the prompt says every problem
   needs ONE checkable answer and no open-ended item, and the photo analysis compares against the key. A writing skill needs a short checklist instead
   (for example: 3 sentences or more · on the topic · each ends with । · joined by a word such as और / फिर / क्योंकि), and the photo analysis has to use it.
3. **Dictation that is printed is copying.** Both plans print the dictated sentence on the child's sheet ("शिक्षक बोलेंगे: 'बैल खेत जोतता है।' पूरा वाक्य लिखें।");
   the new one even prints the word to write ("पहला शब्द सुनकर लिखें: कछुआ"). The new plan's You Do even says to copy problems 1-5 **from the board**
   ("वर्कशीट की समस्याएँ 1-5 बोर्ड से कॉपी करके पूरी करें"). Either way the check measures copying, not writing from hearing. A dictation sheet needs numbered blank lines, with the sentences only in the
   teacher's text, and never written on the board. ("शिक्षक कहानी सुनाएँगे" in the recorded plan, for one sentence, comes from a prompt rule meant for passage sheets.)
4. **The writing task reuses the teacher's model, and contradicts the You Do** (new plan): the Progressor I Do writes 3 sentences on "हमारा स्कूल"; the
   worksheet's problem 6 asks the children to write on "हमारा स्कूल" (they can copy the board); the You Do tells them to write on "मेरा पसंदीदा खेल". The Proficient
   warning, by contrast, is a **false positive**: its You Do only names the worksheet's own task ("मेरा त्योहार"), which is expected.
5. **No mistakes are recorded for the three writing skills.** So the show-me questions cannot target known mistakes and no problem can be marked as revealing
   one. `docs/CURATED_SKILLS.md` lists L2.7.2 as curated ("missing conjunctions; sentence boundary; repetition"), but those three are not in the knowledge base.
6. **"मैं बोलती हूँ"** (new plan, the Beginners' two show-me questions): the gender-neutral rule is in the prompt, but the safety net only fixes command forms, so
   this reaches the teacher. The safety net could also turn a first-person feminine-only verb into the neutral pair ("बोलता/बोलती हूँ").
7. **Smaller:** the new plan calls literacy questions "समस्याएँ" ("वर्कशीट की समस्याएँ 1-5"), a maths word; "एक वाक्य उठाकर लिखें जिसमें किसान का नाम आया हो" means the
   word "किसान", not a name.

**Correction to the first review (recorded plan):** it said 5 command forms were made polite; the right number is **10**. The first count missed a command
followed directly by "।", because the full stop is in the same Unicode block as the letters. The safety net fixes all 10 either way.

## What would fix them

- **Prompt (Ramesh):** a writing skill gets a writing sheet: the task, a short checklist as its answer, and short items that check its parts (joining two
  sentences, ending a sentence, putting sentences in order); comprehension stays for reading skills. A dictation sheet has numbered blank lines and the
  sentences only in the teacher's text, never on the board. A worksheet never uses a topic, sentence or example from the lesson, whatever its length. The
  writing task's topic must be the one the You Do names. (The writing-sheet shape is the open question in `PROMPT_DRAFT_3N_WORKSHEET.md`; this is the evidence.)
- **Photo analysis:** mark writing against the checklist, not an answer key.
- **Code:** the overlap check also compares whole short sentences (the 4-word "सीता फूल लाती है।" slipped through) and topics, and does not flag a You Do that names
  its own worksheet task; the safety net also neutralises first-person feminine-only verbs.
- **Content (Vaishnavi):** add the three L2.7.2 mistakes from the curated list (missing conjunctions, sentence boundary, repetition) to the knowledge base, and
  ones for L2.7.1 (matra errors in dictation) and L3.7.1 (paragraph coherence), so questions and sheets can target them.
- **The recorded plan:** re-record L2.7.2 once the prompt is fixed (it is what teachers see when the AI limit is reached), and have Vaishnavi sign it again.
