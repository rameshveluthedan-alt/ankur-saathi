#!/usr/bin/env python3
"""
Load the embeddings file (db/seeds/content/embeddings.json) into a database. NO MODEL, NO PYTORCH, NO KEY: it only reads the file and writes vectors.

    python scripts\\load_embeddings.py --check --env-file backend\\.env       what would be loaded, what is stale, what is missing: changes nothing
    python scripts\\load_embeddings.py --env-file backend\\.env               migrate the columns (idempotent), then load
    python scripts\\load_embeddings.py --file other.json --env-file backend\\.env

The nightly job runs it too (a step that cannot stop the demo reset), so the cloud database gets its vectors and the column migration without any manual database work.
It is SAFE EVERYWHERE: a database without pgvector (the setup script turns the columns into text there) is reported and left alone; a missing file is reported and left alone. A vector is loaded only
if its fingerprint equals the fingerprint of the row's CURRENT text (a vector made for an older text is "stale" and skipped). Semantic retrieval is a SEPARATE switch: SEMANTIC_RETRIEVAL=on.
"""
import argparse
import asyncio
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(HERE)]
import anchor_common as ac                                  # noqa: E402
from embedding_texts import TABLES, fingerprint, load_texts  # noqa: E402

DEFAULT_FILE = ROOT / "db" / "seeds" / "content" / "embeddings.json"
MIGRATION = ROOT / "db" / "schema" / "12_embeddings_1024.sql"


def validate_file(data) -> list:
    """The problems of an embeddings file, in plain words (an empty list = fine)."""
    if not isinstance(data, dict):
        return ["the file is not a JSON object"]
    problems = []
    for key in ("format", "model", "dims", "tables"):
        if key not in data:
            problems.append(f"the key '{key}' is missing")
    if problems:
        return problems
    if data["format"] != 1:
        problems.append(f"format {data['format']} is not understood (this loader reads format 1)")
    dims = data["dims"]
    if not isinstance(dims, int) or dims <= 0:
        return problems + [f"dims must be a whole number, not {dims!r}"]
    if not isinstance(data["tables"], dict):
        return problems + ["'tables' must be an object"]
    for table, items in data["tables"].items():
        if table not in TABLES:
            problems.append(f"the table '{table}' is not one of: {', '.join(TABLES)}")
            continue
        for rid, rec in (items or {}).items():
            v = rec.get("vector") if isinstance(rec, dict) else None
            if not isinstance(rec, dict) or "hash" not in rec or not isinstance(v, list):
                problems.append(f"{table} {rid}: needs a 'hash' and a 'vector'")
            elif len(v) != dims:
                problems.append(f"{table} {rid}: the vector has {len(v)} numbers, the file says {dims}")
            elif not all(isinstance(x, (int, float)) and math.isfinite(x) for x in v):
                problems.append(f"{table} {rid}: the vector holds a value that is not a number")
            if len(problems) >= 12:
                return problems + ["... (more problems not listed)"]
    return problems


async def vectors_ready(db, dims: int = 1024) -> tuple:
    """(True, '') when all five embedding columns are vector(dims); otherwise (False, the reason). Never raises."""
    if not await db.fetchval("SELECT to_regtype('vector') IS NOT NULL"):
        return False, "pgvector is not available in this database (the embedding columns are text): semantic retrieval stays off"
    rows = await db.fetch("""SELECT c.relname, format_type(a.atttypid, a.atttypmod) AS t FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid
                             WHERE c.relname = ANY($1::text[]) AND c.relkind = 'r' AND a.attname = 'embedding' AND NOT a.attisdropped""", list(TABLES))
    have = {r["relname"]: r["t"] for r in rows}
    wrong = [f"{t} ({have.get(t, 'no embedding column')})" for t in TABLES if have.get(t) != f"vector({dims})"]
    return (False, f"these columns are not vector({dims}) yet: {', '.join(wrong)}") if wrong else (True, "")


async def ensure_schema(db):
    """Run migration 12 (idempotent; a no-op without pgvector)."""
    await db.execute(MIGRATION.read_text(encoding="utf-8"))


async def apply(db, data: dict, sha: str = "", dry_run: bool = False) -> dict:
    """Load the vectors whose fingerprint matches the row's current text. Returns {table: {in_file, loaded, stale, missing_row, without_vector}} (and 'skipped': reason when nothing could be done)."""
    ready, why = await vectors_ready(db, data["dims"])
    if not ready:
        return {"skipped": why}
    texts = await load_texts(db)
    summary = {}
    async with db.transaction():
        for table in TABLES:
            items = data["tables"].get(table, {})
            s = {"in_file": len(items), "loaded": 0, "stale": 0, "missing_row": 0}
            for rid, rec in items.items():
                current = texts[table].get(rid)
                if current is None:
                    s["missing_row"] += 1
                elif fingerprint(current) != rec["hash"]:
                    s["stale"] += 1
                else:
                    if not dry_run:
                        await db.execute(f"UPDATE {table} SET embedding = $1::vector WHERE id = $2", "[" + ",".join(repr(float(x)) for x in rec["vector"]) + "]", rid)
                    s["loaded"] += 1
            s["without_vector"] = (len(texts[table]) - s["loaded"]) if dry_run else await db.fetchval(f"SELECT count(*) FROM {table} WHERE is_active = TRUE AND embedding IS NULL")
            summary[table] = s
        if not dry_run:
            await db.execute("""INSERT INTO embedding_meta (id, model, revision, dims, file_sha256, loaded_at, counts) VALUES (1, $1, $2, $3, $4, $5, $6::jsonb)
                                ON CONFLICT (id) DO UPDATE SET model = EXCLUDED.model, revision = EXCLUDED.revision, dims = EXCLUDED.dims, file_sha256 = EXCLUDED.file_sha256, loaded_at = EXCLUDED.loaded_at, counts = EXCLUDED.counts""",
                             data["model"], data.get("revision", ""), data["dims"], sha, datetime.now(timezone.utc), json.dumps(summary))
    return summary


def report(summary: dict, prefix: str = "") -> list:
    if "skipped" in summary:
        return [f"{prefix}SKIPPED: {summary['skipped']}"]
    lines = []
    for t in TABLES:
        s = summary[t]
        extra = "".join(f", {k.replace('_', ' ')} {s[k]}" for k in ("stale", "missing_row") if s[k]) + (f", {s['without_vector']} active row(s) still without a vector" if s["without_vector"] else "")
        lines.append(f"{prefix}{t:<24} {s['loaded']:>3} of {s['in_file']:>3} loaded{extra}")
    return lines


async def main():
    ap = argparse.ArgumentParser(description="Load the embeddings file into a database.", epilog=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", help=f"default {DEFAULT_FILE.relative_to(ROOT)}")
    ap.add_argument("--check", action="store_true", help="say what would be loaded; change nothing")
    ap.add_argument("--dry-run", action="store_true", help="the same as --check")
    ac.add_db_args(ap)
    args = ap.parse_args()
    path = Path(args.file) if args.file else DEFAULT_FILE
    if not path.exists():
        if args.file:
            print(f"File not found: {path}")
            return 2
        print(f"No embeddings file ({path.relative_to(ROOT)}): semantic retrieval stays off. Create it with scripts\\embed_content.py.")
        return 0
    raw = path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except ValueError as e:
        print(f"{path.name} is not valid JSON: {e}")
        return 1
    problems = validate_file(data)
    if problems:
        print(f"{path.name} cannot be used:")
        for p in problems:
            print("  -", p)
        return 1
    sha = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    print(f"{path.name}: {sum(len(v) for v in data['tables'].values())} vectors of {data['dims']} numbers from {data['model']} (revision {data.get('revision') or 'unknown'}, made {data.get('created', '?')}).")
    db = await ac.connect(args)
    try:
        check = args.check or args.dry_run
        if not check:
            await ensure_schema(db)
        summary = await apply(db, data, sha, dry_run=check)
    finally:
        await db.close()
    for line in report(summary, "  "):
        print(line)
    print("(--check: nothing was changed)" if check else ("Done." if "skipped" not in summary else "Nothing loaded."))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
