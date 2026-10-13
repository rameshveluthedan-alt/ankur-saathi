# Ankur Saathi (अंकुर साथी) — Build Stage

AI-powered daily differentiated instruction for every FLN classroom.  
**Challenge #1: Classroom Complexity** | AI for Foundational Learning Hackathon 2026

---

## Project Structure

```
ankur-saathi/
│
├── db/
│   ├── schema/
│   │   ├── 01_l1_schema.sql          # Layer 1: Structured Curriculum KB (Postgres)
│   │   └── 02_l2_schema.sql          # Layer 2: Curated Content Bank (pgvector)
│   │
│   ├── seeds/
│   │   ├── numeracy/
│   │   │   ├── 01_competencies.sql    # 53 competencies, Balvatika → Grade 3
│   │   │   ├── 02_prerequisites.sql   # 68 prerequisite links (DAG) + 37 learning outcomes
│   │   │   └── 03_misconceptions.sql  # 34 misconceptions with diagnostic indicators
│   │   │
│   │   ├── literacy/
│   │   │   ├── 01_competencies.sql    # 48 competencies, Balvatika → Grade 3
│   │   │   ├── 02_prerequisites.sql   # 74 prerequisite links (DAG) + 29 learning outcomes
│   │   │   └── 03_misconceptions.sql  # 21 misconceptions (matra, conjunct, fluency, comprehension)
│   │   │
│   │   ├── curriculum/
│   │   │   ├── 00_header.sql          # MP state entry + plan header
│   │   │   ├── 01_numeracy.sql        # 96 weeks: Grade 1-3 numeracy
│   │   │   └── 02_literacy.sql        # 75 weeks: Grade 1-3 R1 literacy
│   │   │
│   │   ├── content/                   # Layer 2 seed content
│   │   │   ├── 01_anchors_tlm.sql     # 14 anchor activities + 12 TLM references
│   │   │   ├── 02_interventions.sql   # 15 intervention templates (61% misconception coverage)
│   │   │   └── 03_passages.sql        # 9 graded Hindi reading passages
│   │   │
│   │   └── classroom/
│   │       └── 01_profile.sql         # Test classroom: 1 teacher, 30 children, B/P/P positions
│   │
│   └── setup.sh                       # One-command database setup (schema + all seeds)
│
├── prompts/
│   ├── templates/
│   │   ├── dainik_yojana_system.md    # System prompt: design principles + role
│   │   └── dainik_yojana_user.md      # User prompt template with {{placeholders}}
│   │
│   ├── examples/
│   │   └── n2_3_2_dainik_yojana.md    # Concrete prompt for N2.3.2 (2-digit addition with carry)
│   │
│   ├── orchestrate.py                 # Main orchestration: L1+L2 queries → prompt assembly → Claude API
│   ├── baseline_assessment.py         # Baseline diagnostic generator + placement + grouping algorithms
│   └── vision_analysis.py             # Claude Vision worksheet analysis + feedback loop + level changes
│
├── scripts/
│   └── populate_embeddings.py         # One-time script to populate pgvector L2 embeddings
│
└── docs/
    └── (proposal PDF, deck, handoff prompt — reference only)
```

## Quick Start

```bash
# 1. Database setup (requires PostgreSQL 14+)
chmod +x db/setup.sh
./db/setup.sh postgresql://user:pass@localhost/ankur_saathi

# 2. Populate L2 embeddings (requires embedding API key)
export EMBEDDING_API_KEY=sk-...
python scripts/populate_embeddings.py

# 3. Start backend (Week 2)
# uvicorn app:app --reload
```

## Week 1 Deliverables — Summary

### Layer 1: Structured Curriculum KB
| Entity | Numeracy | Literacy | Total |
|--------|----------|----------|-------|
| Competencies | 53 | 48 | **101** |
| Prerequisite links | 68 | 74 | **142** |
| Learning outcomes | 37 | 29 | **66** |
| Misconceptions | 34 | 21 | **55** |
| Curriculum weeks | 96 | 75 | **171** |

### Layer 2: Curated Content Bank
| Content Type | Count | Coverage |
|-------------|-------|----------|
| Anchor activities | 14 | 8 numeracy + 6 literacy |
| Reading passages | 9 | 3 per grade level (Grade 1-3) |
| Intervention templates | 15 | 34/55 misconceptions (61%) |
| TLM references | 12 | With DIY instructions |

### Orchestration Prompts
| Prompt | Purpose |
|--------|---------|
| Dainik Yojana | Generates complete daily plan (anchor + 3 worksheets + rotation + management) |
| Baseline Assessment | Generates diagnostic items, computes placement, clusters groups |
| Vision Analysis | Extracts answers from photos, diagnoses misconceptions, detects level changes |

### Test Classroom
- 30 children across Grades 1-3 (10 + 12 + 8)
- Separate B/P/P positions per domain (numeracy vs literacy)
- Cross-domain grouping validated: children in different groups per subject

## Architecture

```
Teacher's phone (PWA)
        │
        ▼
   FastAPI backend
        │
   ┌────┴────┐
   ▼         ▼
L1 (Postgres)  L2 (pgvector)
 Deterministic   Semantic
   lookup        retrieval
   │              │
   └──────┬───────┘
          ▼
    Claude API
   (constrained by
    L1 + L2 context)
          │
          ▼
   Dainik Yojana → PWA
```

## Key Design Decisions

1. **Three-layer knowledge architecture**: L1 (structured, deterministic) + L2 (semantic retrieval) + L3 (Claude generation constrained by L1+L2). Claude never generates from training data alone.

2. **Per-subject grouping**: A child can be Beginner in numeracy and Proficient in literacy. Groups are per-domain, not per-child.

3. **Roll-number anonymisation**: Names exist only in IndexedDB on teacher's device. Server and Claude see only roll numbers.

4. **AI proposes, teacher decides**: Teacher records Advance/Re-teach BEFORE seeing AI analysis. AI confirms or flags discrepancies.

5. **Misconception taxonomy, not hallucination**: Claude Vision diagnoses against the L1 taxonomy only. No invented error categories.

## Team

- **Vaishnavi** — Education Domain Lead (L1 curation, misconception validation)
- **Ramesh** — AI & Engineering Lead (orchestration, Claude integration)
- **Arjun** — Data & Architecture Lead (backend, DB, infrastructure)
