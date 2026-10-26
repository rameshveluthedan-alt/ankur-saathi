# L2 semantic retrieval (pgvector): how it works, how to run it, how to switch it on

**What it is.** The proposal promised semantic retrieval of the L2 content bank on pgvector. Today it covers the **anchor activities** (the whole-class opening story), where the curated ladder is weakest. **Curated first, semantic as the fallback:** for the 77% of skills with an exact or related anchor (48 + 29 of 101), nothing changes. For the 24% the ladder served only weakly (topic area 10, loose 14: "the most broadly applicable first"), the semantic tier chooses the anchor **nearest in meaning to the skill**.

**The running app calls no embedding service and needs no key for it.** The query is the skill's own **stored vector** (`competencies.embedding`), compared inside PostgreSQL with `<=>`. The vectors are computed once, **offline, on a laptop, with an open-weights model**: `BAAI/bge-m3` (MIT licence, 1024 dimensions, handles Hindi and English). Nothing leaves the machine.

## The pieces
| File | What it does |
|---|---|
| `scripts/embed_content.py` | **On a laptop** (needs `pip install sentence-transformers asyncpg`; **never** add it to `backend/requirements.txt`). Reads the texts from the database, computes the vectors, writes **one file**: `db/seeds/content/embeddings.json` (about 1.4 MB: 151 vectors, each with a fingerprint of its text, plus the model name and revision). Commit it. |
| `scripts/embedding_texts.py` | The texts that get embedded and the fingerprint. No model, no PyTorch. An anchor is embedded from its **own content only** (title, description, theme, setting, start of the story): it deliberately does NOT name the skills it was written for, otherwise the recovery test below would be circular. |
| `scripts/load_embeddings.py` | **Anywhere, no model, no key.** Runs migration 12 (idempotent), then loads each vector **only if its fingerprint equals the fingerprint of the row's current text** (a vector made for an older text is "stale" and skipped). `--check` changes nothing. Safe without pgvector or without the file: it says so and stops. **The nightly job runs it** (a step that cannot stop the demo reset), so the cloud database gets its vectors and the column migration with no manual database work. |
| `db/schema/12_embeddings_1024.sql` | The embedding columns become `vector(1024)` (4 content tables + `competencies`), ivfflat indexes dropped (at 9 to 101 rows an exact scan is instant and exactly right), a small `embedding_meta` table remembers which model, revision and file the vectors came from. A no-op where pgvector is missing. |
| `prompts/orchestrate.py` | `fetch_anchor_activity`: exact, related, **semantic** (if the switch is on), topic area, loose. Any problem (no pgvector, no vectors, an error) falls back to the ladder; an error cannot poison the caller's transaction (savepoint). Deterministic: ties go to the lower id. The prompt tells the model the match is SEMANTIC: keep the setting, rewrite every group's task. |
| `scripts/eval_semantic.py` | The evidence (below). `--file` reads the vectors from the file: **no pgvector needed on the laptop**. |
| `backend/tests/test_semantic_retrieval.py` | 48 checks. The database part runs against any database WITH pgvector (inside a rolled-back transaction) and is skipped, with a notice, without it. |

## Run it (once, then whenever the content changes)
```powershell
# 1. In an environment that has sentence-transformers and asyncpg (the model, 2.3 GB, is already in your Hugging Face cache)
python scripts\embed_content.py --env-file backend\.env --dry-run      # the texts and counts; no model needed
python scripts\embed_content.py --env-file backend\.env                # a few minutes on a laptop CPU -> db\seeds\content\embeddings.json
# 2. The evidence (no pgvector needed)
python scripts\eval_semantic.py --env-file backend\.env --file db\seeds\content\embeddings.json
# 3. Commit the file. The nightly job loads it into the cloud database.
```
To load it into a LOCAL database too, that database needs pgvector (the setup script turns the columns into text where it is missing): `python scripts\load_embeddings.py --check --env-file backend\.env`.

## The evidence, and the gate
1. **Recovery test.** For each of the 48 skills that HAVE a curated anchor, rank all anchors valid for its domain and grade by closeness of meaning. Is the curated one first? In the top 3? It is printed next to what a **random ranking would score** (first: 25%, top 3: 62%), so the number cannot flatter itself. (Because anchors are embedded from their content only, a good score is not an artefact of the skill's name being written in the anchor. The first version had exactly that leak: stand-in vectors scored 85% first against 25% random; without the leak the same stand-in scores 50%. The stand-in numbers mean nothing for the real model; they showed the leak.)
2. **Blind A/B for the domain lead.** For the skills the ladder serves weakly, today's pick and the semantic pick, in random order, unlabelled: `docs/semantic_ab_sheet.csv` (for her) and `docs/semantic_ab_key.csv` (the key: keep it back until she has answered).
3. **Determinism and speed**, on a database with pgvector (about 0.4 ms per skill).
**Gate (Thu 29 Oct, noon).** Switch it ON only if the recovery test is clearly above random, the reviewer prefers the semantic pick in about half or more of the differing skills, and no test fails. Otherwise it ships OFF and the README says "built and evaluated, not enabled in the frozen version".

## The switch
`SEMANTIC_RETRIEVAL=on|off`, **off by default**. In the cloud it lives in `deploy/cloudrun-env.yaml` (a redeploy REPLACES the service's variables with the generated file, so keep it there): put `SEMANTIC_RETRIEVAL: "on"` in `deploy\cloudrun-env.generated.yaml` and redeploy, or switch at once with no build: `gcloud run services update $SERVICE --region $REGION --update-env-vars SEMANTIC_RETRIEVAL=on` (and `=off` to roll back). Switching changes only the anchor chosen for the weakly served skills; nothing else.

## Honest limits
- The bank is small (14 anchors; 8 numeracy). The larger gain is **more anchors** (content work); this is the machinery and the evidence that scales when the bank grows.
- Only anchors use it today. Passages, intervention templates and teaching materials have vectors loaded for later (matching a recorded misconception to an intervention, a passage by theme and level) but nothing reads them yet.
- Nothing here is proven for the real model until `eval_semantic.py` has run on the real vectors and the reviewer has answered the sheet.
