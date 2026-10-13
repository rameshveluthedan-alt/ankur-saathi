# SYSTEM PROMPT

You are the Ankur Saathi orchestration engine. You generate a complete Dainik Yojana (daily teaching plan) for an Indian FLN classroom using a station rotation model.

Your role: Generate structured, differentiated teaching plans. Every competency, prerequisite, misconception, and assessment criterion you reference MUST come from the structured context provided. Do not invent curriculum content from training data.

Design principles:
1. AI proposes, teacher decides. Tone is supportive, never prescriptive.
2. Level-matched instruction. Beginners get prerequisite content. Progressors get target with scaffolding. Proficients get extensions.
3. Station rotation. Two groups work independently (on previously mastered content) while teacher teaches one group. No group does new content independently before teacher has taught it.
4. Noise-robust assessment. Use the competency's modality tag for assessment channel.
5. Hindi-first. All teacher-facing content in Hindi. English only for metadata.
6. Offline-friendly. Plan must work once cached.

Output format: Return a JSON object with the structure specified in the user prompt.

---

# USER PROMPT

Generate today's Dainik Yojana using ONLY the structured context below.

## CLASSROOM CONTEXT

**Teacher:** Teacher (MP-DEMO-001)
**Grades in room:** grade_1, grade_2, grade_3
**Total children:** 30
**Available teaching time:** 90 minutes
**Has printer:** नहीं (board-copy mode)
**Date:** 2026-10-14
**Week:** 10 (दो अंकों का जोड़: हासिल के साथ)

## TODAY'S LAKSHYA

**Domain:** गणित (numeracy)
**Competency:** N2.3.2 — हासिल के साथ दो अंकों की संख्याओं का जोड़
(Adds two 2-digit numbers with regrouping (carry-over))
**Grade level:** grade_2
**Assessment modality:** written

A/PA/NA Criteria:
```json
{
  "type": "computation",
  "achieved": {
    "min_accuracy": 0.8,
    "sessions_required": 2,
    "no_persistent_misconception": true
  },
  "partially_achieved": {
    "accuracy_range": [
      0.4,
      0.8
    ],
    "or_has_misconception": true
  },
  "not_achieved": {
    "max_accuracy": 0.4,
    "or_cannot_attempt": true
  }
}
```

Number range: {"min": 10, "max": 99}
Problem types: addition_2digit_with_carry

## THREE GROUPS

### शुरुआती (Beginner) — 8 children (Roll: [1, 4, 7, 12, 15, 18, 22, 25])
Working on PREREQUISITE: N2.3.1 — बिना हासिल के दो अंकों की संख्याओं का जोड़

### प्रगतिशील (Progressor) — 12 children (Roll: [2, 3, 5, 8, 9, 13, 16, 19, 20, 23, 26, 28])
Working on TODAY'S LAKSHYA with scaffolding: N2.3.2 — हासिल के साथ दो अंकों की संख्याओं का जोड़

### दक्ष (Proficient) — 10 children (Roll: [6, 10, 11, 14, 17, 21, 24, 27, 29, 30])
Working on EXTENSION: N2.3.5 — जोड़ और घटाव के शाब्दिक प्रश्न हल करता है (दो अंक)

## PREREQUISITE CHAIN (from L1)
- **N0.2.2** — 10 तक वस्तु गिनती (hard)
- **N0.2.4** — अंक 1-9 लिखना (hard)
- **N1.3.1** — एक अंक का जोड़ (hard)
- **N1.2.4** — स्थानीय मान: दहाई-इकाई (hard)
- **N2.3.1** — बिना हासिल दो अंकों का जोड़ (hard) ← शुरुआती समूह का लक्ष्य (BEGINNER TARGET)


## MISCONCEPTION TAXONOMY (from L1)

### N2.3.2-M1: हासिल भूलना
- **Error pattern:** Writes ones digit, does not carry tens digit
- **How to detect:** Answer is exactly 10 less than correct, consistent across 3+ problems
- **Example correct:** 34 + 28 = 62
- **Example incorrect:** 34 + 28 = 52
- **Severity:** critical | **Frequency:** very_common

### N2.3.2-M2: पूरा इकाई योग लिखना
- **Error pattern:** Writes 2-digit sum in ones column
- **How to detect:** Answer has extra digit: 34+28 -> 512
- **Example correct:** 34 + 28 = 62
- **Example incorrect:** 34 + 28 = 512
- **Severity:** critical | **Frequency:** common

### N2.3.2-M3: गलत अंक हासिल
- **Error pattern:** Carries ones digit instead of tens digit from sum
- **How to detect:** Tens column is 1 more than expected
- **Example correct:** 34 + 28 = 62
- **Example incorrect:** 34 + 28 = 72
- **Severity:** moderate | **Frequency:** uncommon

### N2.3.2-M4: बाएँ से दाएँ जोड़ना
- **Error pattern:** Adds tens column first, then ones, cannot carry back
- **How to detect:** Tens digit correct for no-carry but wrong with carry; may cross out
- **Example correct:** 34 + 28 = 62
- **Example incorrect:** 34 + 28 = 512
- **Severity:** moderate | **Frequency:** common


## YESTERDAY'S FEEDBACK
Yesterday's gaps require a 5-minute re-teaching segment:
- N2.3.2: हासिल भूलना (M1) (4 children)


## RETRIEVED CONTENT (from L2)

### Anchor Activity Template
**ANC-N-001** — गाँव का बाज़ार (Theme: market)
```
Story setup (teacher narrates):
"आज हम बाज़ार जाएंगे। {{story_character}} को अपनी माँ के लिए सामान खरीदना है।"

Whole-class moment: Teacher shows/draws market items on board with prices.

Differentiated participation:
- Beginners ({{beginner_task}}): "बाज़ार में कितनी चीज़ें हैं? गिनो!" — Count items. Practice {{beginner_competency_name}}.
- Progressors ({{progressor_task}}): "{{story_character}} ने {{item_1}} और {{item_2}} खरीदा। कुल कितने पैसे लगे?" — Add prices. Practice {{progressor_competency_name}}.
- Proficients ({{proficient_task}}): "{{story_character}} के पास {{total_amount}} रुपये हैं। खरीदने के बाद कितने बचे?" — Multi-step.

Closing: "सबसे महँगी चीज़ कौन सी थी? सबसे सस्ती?" 
```
Adapt this for today's competency and number range. Fill all {{placeholders}}.

### Intervention Template

**Template ID:** INT-OP-005 — हासिल पुनःशिक्षण (बंडल से)
**Targets:** N2.3.2-M1, N2.3.2-M2, N2.3.2-M3, N2.3.2-M4
**Steps:**
```json
[
  {
    "step": 1,
    "type": "demonstrate",
    "instruction_hi": "34 + 28 छड़ियों से बनाएँ। इकाई: 4+8=12। 10 का बंडल बनाएँ।",
    "duration_min": 4
  },
  {
    "step": 2,
    "type": "guided_practice",
    "instruction_hi": "3 सवाल छड़ियों और लिखित दोनों से।",
    "duration_min": 5
  },
  {
    "step": 3,
    "type": "check",
    "instruction_hi": "2 सवाल बिना छड़ियों के।",
    "duration_min": 3
  }
]
```
**Required TLM:** TLM-001


### Available TLMs
- TLM-001: बंडल की छड़ियाँ (diy) — DIY: 10 छड़ियों के बंडल रबर बैंड से बाँधें।
- TLM-005: स्थानीय मान पॉकेट चार्ट (uncommon) — DIY: गत्ते पर H|T|O स्तम्भ बनाएँ।


## GENERATE THE DAINIK YOJANA

### PART A: ANCHOR (10 min, whole class)
Adapt the anchor template. Hindi narration, differentiated participation, closing question.

### PART B: THREE WORKSHEETS
- शुरुआती: बिना हासिल के दो अंकों की संख्याओं का जोड़ — 8-10 problems with visual scaffolding
- प्रगतिशील: हासिल के साथ दो अंकों की संख्याओं का जोड़ — 8-10 problems, scaffolding faded, misconception-revealing problems for N2.3.2-M1, N2.3.2-M2, N2.3.2-M3
- दक्ष: जोड़ और घटाव के शाब्दिक प्रश्न हल करता है (दो अंक) — 8-10 extension problems + word problems
Include answer keys and misconception diagnostic maps.

### PART C: ROTATION SCHEDULE (90 min total)
- Anchor: 10 min
- Setup: 2 min
- Re-teach: 5 min
- Block 1: TEACH progressor (27 min) — Yesterday's analysis detected misconceptions in Progressor group.
- Block 2: TEACH beginner (21 min)
- Block 3: TEACH proficient (21 min)
- Transitions: 2 min each
Each block: I Do → We Do → You Do with Hindi talking points.

### PART D: CLASSROOM MANAGEMENT
Rotation chart, peer monitors, transition scripts (Hindi), independent station activities (on PREVIOUSLY MASTERED content only).

### PART E: REVIEW PROMPTS
- Photo sample: ALL of progressor, 3-4 each from other groups
- Observation: No observed-modality competencies today.


Return as a single JSON object with keys: anchor, worksheets, rotation_schedule, classroom_management, review_prompts, explainability.
