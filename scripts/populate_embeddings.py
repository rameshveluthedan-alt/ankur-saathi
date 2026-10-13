"""
Ankur Saathi — L2 Embeddings Pipeline
One-time script to populate pgvector embedding columns in L2 tables.

Run once after seeding L2 content, and again whenever new content is added.
Uses text-embedding-3-small (1536 dimensions) via the Anthropic-compatible
endpoint, or any OpenAI-compatible embedding API.

Usage:
    python populate_embeddings.py --db-url postgresql://user:pass@host/ankur_saathi
    
    # Or with environment variables:
    DATABASE_URL=postgresql://... EMBEDDING_API_KEY=sk-... python populate_embeddings.py
"""

import asyncio
import json
import os
import sys
from typing import Optional

try:
    import asyncpg
    import httpx
except ImportError:
    print("Install dependencies: pip install asyncpg httpx")
    sys.exit(1)


# ============================================================================
# CONFIGURATION
# ============================================================================

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
EMBEDDING_API_URL = os.getenv("EMBEDDING_API_URL", "https://api.openai.com/v1/embeddings")
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres@localhost/ankur_saathi")
BATCH_SIZE = 20  # Embed this many texts per API call


# ============================================================================
# EMBEDDING FUNCTION
# ============================================================================

async def get_embeddings(texts: list[str], client: httpx.AsyncClient) -> list[list[float]]:
    """Call the embedding API for a batch of texts."""
    
    response = await client.post(
        EMBEDDING_API_URL,
        headers={
            "Authorization": f"Bearer {EMBEDDING_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": EMBEDDING_MODEL,
            "input": texts,
            "dimensions": EMBEDDING_DIMENSIONS
        },
        timeout=60.0
    )
    response.raise_for_status()
    data = response.json()
    
    # Sort by index to maintain order
    sorted_embeddings = sorted(data['data'], key=lambda x: x['index'])
    return [e['embedding'] for e in sorted_embeddings]


# ============================================================================
# TABLE-SPECIFIC EMBEDDING TEXT BUILDERS
# ============================================================================

def anchor_embedding_text(row: dict) -> str:
    """Build the text to embed for an anchor activity."""
    return (
        f"{row['title_en']} {row['title_hi']} "
        f"{row['description_en']} "
        f"Theme: {row['theme']} "
        f"Grades: {', '.join(row['grade_range'])} "
        f"Competencies: {', '.join(row['primary_competency_ids'])} "
        f"{row['template_body'][:500]}"  # Truncate body to keep embedding focused
    )


def passage_embedding_text(row: dict) -> str:
    """Build the text to embed for a reading passage."""
    return (
        f"{row['title_hi']} "
        f"Grade: {row['target_grade']} Difficulty: {row['difficulty']} "
        f"Theme: {row.get('theme', '')} Genre: {row.get('genre', '')} "
        f"Features: {', '.join(row['decoding_features'])} "
        f"{row['passage_hi'][:300]}"  # First 300 chars of passage
    )


def intervention_embedding_text(row: dict) -> str:
    """Build the text to embed for an intervention template."""
    steps_text = " ".join(
        s.get('instruction_en', s.get('instruction_hi', ''))[:100]
        for s in (row['steps'] if isinstance(row['steps'], list) else json.loads(row['steps']))
    )
    return (
        f"{row['title_en']} {row['title_hi']} "
        f"{row['description_en']} "
        f"Misconceptions: {', '.join(row['misconception_ids'])} "
        f"Level: {row['target_level']} Modality: {row['modality']} "
        f"{steps_text}"
    )


def tlm_embedding_text(row: dict) -> str:
    """Build the text to embed for a TLM reference."""
    return (
        f"{row['name_en']} {row['name_hi']} "
        f"{row['description_en']} "
        f"Domains: {', '.join(row['domain_ids'])} "
        f"Availability: {row['availability']} "
        f"{row.get('diy_instructions', '') or ''}"
    )


# ============================================================================
# MAIN PIPELINE
# ============================================================================

async def populate_table_embeddings(
    db: asyncpg.Connection,
    client: httpx.AsyncClient,
    table: str,
    text_builder: callable,
    id_column: str = 'id'
):
    """Populate embeddings for one table."""
    
    # Fetch all rows that need embeddings
    rows = await db.fetch(f"""
        SELECT * FROM {table} 
        WHERE embedding IS NULL AND is_active = TRUE
    """)
    
    if not rows:
        print(f"  {table}: no rows need embeddings (all populated or none exist)")
        return
    
    print(f"  {table}: {len(rows)} rows to embed")
    
    # Process in batches
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        texts = [text_builder(dict(r)) for r in batch]
        ids = [r[id_column] for r in batch]
        
        try:
            embeddings = await get_embeddings(texts, client)
        except Exception as e:
            print(f"    ERROR embedding batch {i//BATCH_SIZE + 1}: {e}")
            continue
        
        # Update each row
        for row_id, embedding in zip(ids, embeddings):
            embedding_str = f"[{','.join(str(x) for x in embedding)}]"
            await db.execute(f"""
                UPDATE {table} SET embedding = $1::vector WHERE {id_column} = $2
            """, embedding_str, row_id)
        
        print(f"    Batch {i//BATCH_SIZE + 1}/{(len(rows)-1)//BATCH_SIZE + 1}: {len(batch)} rows embedded")
    
    print(f"  {table}: done")


async def main():
    """Run the full embedding pipeline."""
    
    if not EMBEDDING_API_KEY:
        print("ERROR: Set EMBEDDING_API_KEY environment variable")
        print("  export EMBEDDING_API_KEY=sk-...")
        sys.exit(1)
    
    print(f"Connecting to {DATABASE_URL}...")
    db = await asyncpg.connect(DATABASE_URL)
    
    # Check if pgvector is available
    try:
        await db.execute("SELECT '[1,2,3]'::vector")
    except Exception:
        print("ERROR: pgvector extension not installed. Run: CREATE EXTENSION vector;")
        await db.close()
        sys.exit(1)
    
    print(f"Using model: {EMBEDDING_MODEL} ({EMBEDDING_DIMENSIONS} dimensions)")
    print(f"API endpoint: {EMBEDDING_API_URL}")
    print()
    
    async with httpx.AsyncClient() as client:
        tables = [
            ("anchor_activities", anchor_embedding_text),
            ("reading_passages", passage_embedding_text),
            ("intervention_templates", intervention_embedding_text),
            ("tlm_references", tlm_embedding_text),
        ]
        
        for table, text_builder in tables:
            await populate_table_embeddings(db, client, table, text_builder)
    
    # Rebuild IVFFlat index after bulk insert
    print("\nRebuilding vector indexes...")
    for table in ["anchor_activities", "reading_passages", "intervention_templates", "tlm_references"]:
        try:
            await db.execute(f"""
                DROP INDEX IF EXISTS idx_{table.split('_')[0]}_embedding;
                CREATE INDEX idx_{table.split('_')[0]}_embedding 
                ON {table} USING ivfflat(embedding vector_cosine_ops)
                WITH (lists = 10);
            """)
            print(f"  {table}: index rebuilt")
        except Exception as e:
            print(f"  {table}: index skipped ({e})")
    
    await db.close()
    print("\nDone. All L2 embeddings populated.")


if __name__ == "__main__":
    asyncio.run(main())
