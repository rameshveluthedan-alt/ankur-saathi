#!/usr/bin/env python3
"""
Compute the skill and L2-content embeddings OFFLINE, with an open-weights model, and write them to ONE file.

    python scripts\\embed_content.py --env-file backend\\.env                      BAAI/bge-m3, 1024 dimensions (MIT licence), about 150 short texts
    python scripts\\embed_content.py --env-file backend\\.env --dry-run            only the texts and the counts: no model needed
    python scripts\\embed_content.py --env-file backend\\.env --only competencies,anchor_activities

NEEDS, in the environment you run it from (NEVER in backend\\requirements.txt: the cloud container must not carry PyTorch):  pip install sentence-transformers asyncpg
The model (about 2.3 GB) is downloaded once into your Hugging Face cache. Runs on a laptop CPU in a few minutes. Nothing is sent to any service: the texts are read from your database, the vectors
are computed on your machine.

WRITES db/seeds/content/embeddings.json (about 1.5 MB): each vector with a FINGERPRINT of the text it was made from, plus the model name and revision. COMMIT it. The running app never loads a model:
scripts/load_embeddings.py puts the file into any database (the nightly job does it), and a vector made for an older text of a row is recognised as stale and not loaded.
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

DEFAULT_MODEL = "BAAI/bge-m3"
DIMS = 1024
OUT = ROOT / "db" / "seeds" / "content" / "embeddings.json"
FORMAT = 1


def make_sbert_encoder(model_name: str):
    """(encode, revision). encode(list of texts) -> list of unit-length vectors. The import is HERE so that --dry-run and the tests need no PyTorch."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        raise SystemExit("sentence-transformers is not installed in this environment.\n  pip install sentence-transformers asyncpg\n(do NOT add it to backend\\requirements.txt)")
    model = SentenceTransformer(model_name)
    revision = ""
    try:                                                    # the folder name of the cached snapshot IS the commit of the model files
        from huggingface_hub import snapshot_download
        revision = Path(snapshot_download(model_name, local_files_only=True)).name
    except Exception:
        pass

    def encode(texts):
        return [[float(x) for x in v] for v in model.encode(texts, batch_size=16, normalize_embeddings=True, show_progress_bar=False)]
    return encode, revision


def build_file(texts: dict, encode, model: str, revision: str, dims: int = DIMS, only=None, batch: int = 16) -> dict:
    """The embeddings file as a dict: {format, model, revision, dims, normalized, created, tables: {table: {id: {hash, vector}}}}. `encode` is any function texts -> vectors (the tests pass a stand-in)."""
    out = {"format": FORMAT, "model": model, "revision": revision, "dims": dims, "normalized": True, "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "tables": {}}
    for table in TABLES:
        if only and table not in only:
            continue
        items = list(texts.get(table, {}).items())
        out["tables"][table] = {}
        for i in range(0, len(items), batch):
            chunk = items[i:i + batch]
            vectors = encode([t for _, t in chunk])
            if len(vectors) != len(chunk):
                raise ValueError(f"{table}: asked for {len(chunk)} vectors, got {len(vectors)}")
            for (rid, text), v in zip(chunk, vectors):
                if len(v) != dims or not all(math.isfinite(x) for x in v):
                    raise ValueError(f"{table} {rid}: the vector has {len(v)} numbers (expected {dims}) or a value that is not a number")
                out["tables"][table][rid] = {"hash": fingerprint(text), "vector": [round(x, 5) for x in v]}
    return out


def write_file(data: dict, path: Path) -> str:
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def main():
    ap = argparse.ArgumentParser(description="Compute the L2 / skill embeddings offline with an open-weights model.", epilog=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--only", help="comma-separated tables (default: all five)")
    ap.add_argument("--dry-run", action="store_true", help="print the texts and the counts; compute nothing")
    ac.add_db_args(ap)
    args = ap.parse_args()
    only = set(args.only.split(",")) if args.only else None
    if only and not only <= set(TABLES):
        raise SystemExit(f"--only takes: {', '.join(TABLES)}")
    db = await ac.connect(args)
    try:
        texts = await load_texts(db)
    finally:
        await db.close()
    print("texts to embed: " + ", ".join(f"{t} {len(texts.get(t, {}))}" for t in TABLES if not only or t in only))
    if args.dry_run:
        for t in TABLES:
            for rid, text in list(texts.get(t, {}).items())[:1]:
                print(f"\n[{t} {rid}] ({len(text)} characters)\n  {text[:260]}")
        print("\n(--dry-run: nothing computed, nothing written)")
        return 0
    encode, revision = make_sbert_encoder(args.model)
    data = build_file(texts, encode, args.model, revision, DIMS, only)
    sha = write_file(data, Path(args.out))
    n = sum(len(v) for v in data["tables"].values())
    print(f"\n{n} vectors of {DIMS} numbers from {args.model} (revision {revision or 'unknown'}) written to {args.out} ({Path(args.out).stat().st_size / 1024:.0f} KB, sha256 {sha[:12]}).")
    print("Next: python scripts\\load_embeddings.py --check --env-file backend\\.env   then without --check to load it; commit the file.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
