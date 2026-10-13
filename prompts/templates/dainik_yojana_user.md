# Dainik Yojana Generation — User Prompt Template
# Variables marked {{VAR}} are injected by the FastAPI orchestration pipeline.

Generate today's Dainik Yojana using the structured context below. Do NOT use knowledge outside this context for curriculum content.

---

## CLASSROOM CONTEXT

**Teacher:** {{teacher_name}} ({{school_code}})
**Grades in room:** {{enrolled_grades}}  <!-- e.g., "Grade 1, Grade 2, Grade 3" -->
**Total children:** {{total_children}}
**Available teaching time:** {{available_minutes}} minutes
**Has printer:** {{has_printer}}  <!-- true/false — affects worksheet vs board-copy -->
**Date:** {{plan_date}}
**Curriculum week:** {{week_number}} ({{week_topic_hi}})

---

## TODAY'S LAKSHYA SELECTION

**Domain:** {{domain_name_hi}} ({{domain_id}})
**Selected competency:** {{selected_competency_id}} — {{selected_competency_name_hi}}
**English:** {{selected_competency_name_en}}
**Grade level:** {{competency_grade_level}}
**Assessment modality:** {{assessment_modality}}

### A/PA/NA Criteria for this Lakshya
```json
{{apna_criteria_json}}
```

### Number/content range constraints
```json
{{number_range_json}}
```

---

## THREE GROUPS (from current Lakshya positions)

### Beginner Group
- **Children:** {{beginner_count}} (Roll numbers: {{beginner_roll_numbers}})
- **Working on (prerequisite):** {{beginner_competency_id}} — {{beginner_competency_name_hi}}
- **This means:** These children have NOT yet mastered the prerequisite for today's Lakshya. Their worksheet and teaching target this prerequisite, not today's main competency.

### Progressor Group
- **Children:** {{progressor_count}} (Roll numbers: {{progressor_roll_numbers}})
- **Working on (current with scaffolding):** {{selected_competency_id}} — {{selected_competency_name_hi}}
- **This means:** These children are learning today's Lakshya with visual scaffolding, structured practice, and guided support.

### Proficient Group
- **Children:** {{proficient_count}} (Roll numbers: {{proficient_roll_numbers}})
- **Working on (extension):** {{proficient_extension_competency_id}} — {{proficient_extension_name_hi}}
- **This means:** These children have demonstrated mastery of today's Lakshya. They get extension problems, word problems, or the next competency in the progression.

---

## PREREQUISITE CHAIN (from Layer 1)

The selected competency requires these prerequisites (in learning order):
{{#each prerequisite_chain}}
- **{{this.id}}** — {{this.name_hi}} ({{this.prerequisite_type}}) {{#if this.is_beginner_target}}← BEGINNER GROUP TARGET{{/if}}
{{/each}}

---

## MISCONCEPTION TAXONOMY (from Layer 1)

Known error patterns for today's competency. Use these for:
(a) Designing worksheet problems that REVEAL these errors
(b) Guiding Claude Vision analysis of completed work
(c) Generating the "What to watch for" section in talking points

{{#each misconceptions}}
### {{this.id}}: {{this.name_hi}}
- **Error pattern:** {{this.error_pattern}}
- **How to detect:** {{this.diagnostic_indicator}}
- **Example correct:** {{this.example_correct}}
- **Example incorrect:** {{this.example_incorrect}}
- **Severity:** {{this.severity}} | **Frequency:** {{this.frequency}}
{{/each}}

---

## YESTERDAY'S FEEDBACK (from previous session)

### Teacher's pre-AI judgment
- Beginner group: {{yesterday_beginner_decision}}  <!-- advance / reteach / not_sure / null -->
- Progressor group: {{yesterday_progressor_decision}}
- Proficient group: {{yesterday_proficient_decision}}

### AI analysis results
{{#if yesterday_analysis}}
- **Misconceptions detected:** {{yesterday_detected_misconceptions}}
- **Discrepancy flag:** {{yesterday_discrepancy}}  <!-- e.g., "Teacher said advance Group 2, but 3/4 worksheets showed carry errors" -->
- **Confirmed decision:** {{yesterday_confirmed_decision}}
{{else}}
No previous session data (first session or baseline just completed).
{{/if}}

### Re-teaching needed
{{#if reteach_competencies}}
Yesterday's gaps require re-teaching. Include a 5-minute re-teaching segment for:
{{#each reteach_competencies}}
- {{this.competency_id}}: {{this.misconception_name_hi}} ({{this.affected_count}} children)
{{/each}}
{{else}}
No re-teaching needed from yesterday.
{{/if}}

---

## RETRIEVED CONTENT (from Layer 2)

### Anchor Activity Template
**Template ID:** {{anchor_id}} — {{anchor_title_hi}}
**Theme:** {{anchor_theme}}
```
{{anchor_template_body}}
```
Adapt this template for today's specific competency and number range. Fill all {{placeholders}}.

### Intervention Template (if re-teaching needed)
{{#if intervention_template}}
**Template ID:** {{intervention_id}} — {{intervention_title_hi}}
**Targets misconception(s):** {{intervention_misconception_ids}}
**Steps:**
```json
{{intervention_steps_json}}
```
**Required TLM:** {{intervention_tlm}}
{{/if}}

### TLM Available
{{#each available_tlms}}
- {{this.id}}: {{this.name_hi}} ({{this.availability}}) {{#if this.diy_instructions}}— DIY: {{this.diy_instructions}}{{/if}}
{{/each}}

---

## GENERATE THE DAINIK YOJANA

Produce a complete plan in the following structure. All teacher-facing text in Hindi.

### PART A: ANCHOR ACTIVITY ({{anchor_duration}} minutes, whole class)

Adapt the retrieved anchor template for today's specific content. Fill all placeholders. Include:
1. **कहानी/गतिविधि** (Story/Activity setup) — 2-3 sentences the teacher narrates
2. **शुरुआती सवाल** (Opening question) — One question all children can attempt
3. **स्तर-अनुसार भागीदारी** (Level-differentiated participation):
   - शुरुआती (Beginner): What they do during the anchor — must connect to their prerequisite competency
   - प्रगतिशील (Progressor): What they do — connects to the target competency
   - दक्ष (Proficient): What they do — connects to the extension
4. **समापन** (Closing) — One whole-class reflection question

### PART B: THREE WORKSHEETS

Generate content for three one-page worksheets. For each:

**शुरुआती (Beginner) Worksheet — {{beginner_competency_name_hi}}**
- 8-10 problems targeting the PREREQUISITE competency
- Visual scaffolding (number line, place-value grid, picture support)
- First 2-3 problems are worked examples
- Progressive difficulty: start very easy, build up
- Clear response grid with roll number field at top
- Instructions in simple Hindi on the sheet itself
- Include at least 2 problems designed to REVEAL the most common misconception for this level

**प्रगतिशील (Progressor) Worksheet — {{selected_competency_name_hi}}**
- 8-10 problems targeting today's Lakshya WITH scaffolding
- Place-value grid / visual support for first 4 problems, then faded
- Mix of problem types from: {{problem_types}}
- Number range: {{number_range_json}}
- Include at least 2 problems designed to REVEAL these misconceptions: {{top_misconception_ids}}
- Word problem at the end (1-2 problems)

**दक्ष (Proficient) Worksheet — {{proficient_extension_name_hi}}**
- 8-10 problems at extension level
- Minimal scaffolding
- Include 2-3 word problems requiring the competency
- 1 challenge problem that stretches thinking
- Number range extended beyond standard: {{proficient_number_range}}

For each worksheet, also output:
- **Answer key** with expected correct answers
- **Misconception diagnostic map**: which problems detect which misconceptions

### PART C: ROTATION SCHEDULE

Generate a time-blocked rotation schedule for {{available_minutes}} minutes.

Structure:
1. **Anchor** (whole class) — {{anchor_duration}} min
2. **Setup moment** (2 min) — scripted instruction in Hindi directing all groups simultaneously
{{#if reteach_competencies}}
3. **Re-teach segment** (5 min) — for children with yesterday's gaps, before rotation begins
{{/if}}
4. **Rotation Block 1** — TEACH {{priority_group}} ({{priority_duration}} min)
   - Other groups: warm-up/review on PREVIOUSLY MASTERED content (not today's new topic)
5. **Rotation Block 2** — TEACH {{second_group}} ({{standard_duration}} min)
   - {{priority_group}}: now does today's worksheet (the "You Do" from Block 1)
6. **Rotation Block 3** — TEACH {{third_group}} ({{standard_duration}} min)
   - Transition script between each block (2 min each)

**Priority group logic:** The group with the most critical gaps from yesterday gets the FIRST and LONGEST teaching slot.
- Priority group: {{priority_group}} ({{priority_reason}})

For each TEACH block, generate:
**3 Talking Points (बात करने के मुद्दे):**
1. **मैं करूँगा (I Do):** Teacher demonstrates — scripted example in Hindi (2-3 min)
2. **हम करेंगे (We Do):** Guided practice — teacher and group solve together (3-4 min)  
3. **तुम करोगे (You Do):** "अब अपनी शीट पर करो" — transition to independent worksheet

### PART D: CLASSROOM MANAGEMENT

1. **दृश्य रोटेशन चार्ट (Visual Rotation Chart):**
   - Table showing: Group | Block 1 | Block 2 | Block 3
   - Use symbols: 👩‍🏫 = with teacher, 📝 = worksheet, 🔄 = warm-up/review

2. **सहकर्मी मॉनिटर (Peer Monitors):**
   - Assign 1 monitor per group (rotate daily from capable children)
   - Monitor's job: "अगर कोई अटका है तो मदद करो, शोर हो तो शांत कराओ"

3. **संक्रमण स्क्रिप्ट (Transition Scripts):**
   - Between each rotation block: exact Hindi words the teacher says
   - Example: "समूह 1, अपनी शीट बंद करो। समूह 2, मेरे पास आओ। समूह 3, अपनी जगह पर revision शुरू करो। राधा मॉनिटर है।"

4. **स्वतंत्र स्टेशन डिज़ाइन (Independent Station Design):**
   - Warm-up/review activities for groups NOT with the teacher
   - MUST be on previously mastered content (not today's new topic)
   - Self-explanatory with written instructions on the sheet
   - Include a visual example at the top so children can start without teacher help

### PART E: END-OF-DAY REVIEW PROMPTS

1. **नमूना चयन (Sample Selection):**
   - Which children to photograph worksheets for (system-selected rotating sample)
   - Priority group: ALL worksheets captured
   - Other groups: {{sample_count}} children each (selected to cover different roll numbers across the week)

2. **अवलोकन अनुस्मारक (Observation Reminders):**
   {{#if observed_competencies}}
   - During teaching, observe and tap A/PA/NA for these competencies (observed modality):
   {{#each observed_competencies}}
     - {{this.id}}: {{this.name_hi}} — for {{this.target_roll_numbers}}
   {{/each}}
   {{/if}}

3. **ORF अनुस्मारक (Reading Fluency Reminder):**
   {{#if orf_scheduled}}
   - Today's ORF assessment: Roll numbers {{orf_roll_numbers}} on passage {{orf_passage_id}}
   - Target CWPM: {{orf_target_cwpm}}
   {{/if}}

---

## OUTPUT FORMAT

Return the complete Dainik Yojana as a JSON object with this structure:

```json
{
  "plan_date": "{{plan_date}}",
  "domain": "{{domain_id}}",
  "selected_competency": "{{selected_competency_id}}",
  
  "anchor": {
    "template_id": "{{anchor_id}}",
    "narration_hi": "...",
    "opening_question_hi": "...",
    "beginner_participation_hi": "...",
    "progressor_participation_hi": "...",
    "proficient_participation_hi": "...",
    "closing_question_hi": "..."
  },
  
  "worksheets": {
    "beginner": {
      "target_competency": "...",
      "title_hi": "...",
      "instructions_hi": "...",
      "problems": [...],
      "answer_key": [...],
      "misconception_diagnostic_map": {...}
    },
    "progressor": { ... },
    "proficient": { ... }
  },
  
  "rotation_schedule": {
    "total_minutes": {{available_minutes}},
    "blocks": [
      {
        "time_start": "...",
        "duration_minutes": ...,
        "type": "anchor|setup|reteach|teach|transition",
        "teach_group": "...",
        "other_groups": {...},
        "talking_points": {
          "i_do_hi": "...",
          "we_do_hi": "...",
          "you_do_hi": "..."
        }
      }
    ],
    "transition_scripts_hi": [...]
  },
  
  "classroom_management": {
    "rotation_chart": {...},
    "peer_monitors": {...},
    "independent_activities": {...}
  },
  
  "review_prompts": {
    "photo_sample": {...},
    "observation_reminders": [...],
    "orf_schedule": {...}
  },
  
  "explainability": {
    "anchor_source": "{{anchor_id}} ({{anchor_title_en}})",
    "beginner_rationale": "Prerequisite {{beginner_competency_id}} because ...",
    "priority_group_rationale": "{{priority_reason}}",
    "reteach_rationale": "...",
    "misconceptions_to_watch": [...]
  }
}
```
