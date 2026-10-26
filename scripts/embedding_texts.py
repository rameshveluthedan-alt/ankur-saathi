"""
The texts that get embedded, and how a text is fingerprinted. Plain Python: NO model, NO PyTorch, so the nightly job can use it.
Used by scripts/embed_content.py (on a laptop, with the model) and scripts/load_embeddings.py (anywhere, without it): the loader recomputes each fingerprint from the DATABASE, so a vector
made for an OLDER text of a row is recognised as stale and not loaded.
"""
import hashlib
import json

TABLES = ("competencies", "anchor_activities", "reading_passages", "intervention_templates", "tlm_references")


def fingerprint(text: str) -> str:
    """A short, stable fingerprint of a text (whitespace-insensitive)."""
    return hashlib.sha256(" ".join((text or "").split()).encode("utf-8")).hexdigest()[:16]


def _list(x) -> list:
    if x is None:
        return []
    if isinstance(x, str):
        try:
            x = json.loads(x)
        except ValueError:
            return [x]
    return x if isinstance(x, list) else [x]


def _s(x) -> str:
    return "" if x is None else str(x)


def competency_text(row: dict, subdomain_name: str = "") -> str:
    """A skill: its name in both languages, what it is, its topic area and grade."""
    return " ".join(p for p in (
        _s(row.get("name_en")) + ".", _s(row.get("name_hi")) + ".", _s(row.get("description_en")),
        f"Topic area: {subdomain_name}." if subdomain_name else "", f"Grade: {_s(row.get('grade_level'))}.") if p.strip(" .") != "")


def anchor_text(row: dict) -> str:
    """An anchor activity, from its OWN CONTENT only: title, description, theme, setting and the start of the story.
    It deliberately does NOT name the skills the anchor was written for. If it did, the vector of an anchor would sit near the vector of its own curated skills just because their names are written in it,
    and scripts/eval_semantic.py's recovery test ("is the curated anchor ranked first?") would be CIRCULAR: it would flatter the method for the wrong reason. (Found when the first run of that test, on
    stand-in vectors, scored 85% against 25% for a random ranking.) What is evaluated is exactly what runs."""
    return " ".join(p for p in (
        _s(row.get("title_en")) + ".", _s(row.get("title_hi")) + ".", _s(row.get("description_en")), f"Theme: {_s(row.get('theme'))}.",
        f"Setting: {_s(row.get('setting'))}." if row.get("setting") else "", _s(row.get("template_body"))[:400]) if p.strip(" .") != "")


def passage_text(row: dict) -> str:
    return (f"{_s(row.get('title_hi'))} Grade: {_s(row.get('target_grade'))} Difficulty: {_s(row.get('difficulty'))} Theme: {_s(row.get('theme'))} Genre: {_s(row.get('genre'))} "
            f"Features: {', '.join(_s(x) for x in _list(row.get('decoding_features')))} {_s(row.get('passage_hi'))[:300]}")


def intervention_text(row: dict) -> str:
    steps = " ".join(_s((s or {}).get("instruction_en") or (s or {}).get("instruction_hi"))[:100] for s in _list(row.get("steps")) if isinstance(s, dict))
    return (f"{_s(row.get('title_en'))} {_s(row.get('title_hi'))} {_s(row.get('description_en'))} Misconceptions: {', '.join(_s(x) for x in _list(row.get('misconception_ids')))} "
            f"Level: {_s(row.get('target_level'))} Modality: {_s(row.get('modality'))} {steps}")


def tlm_text(row: dict) -> str:
    return (f"{_s(row.get('name_en'))} {_s(row.get('name_hi'))} {_s(row.get('description_en'))} Domains: {', '.join(_s(x) for x in _list(row.get('domain_ids')))} "
            f"Availability: {_s(row.get('availability'))} {_s(row.get('diy_instructions'))}")


async def load_texts(db) -> dict:
    """{table: {row id: text to embed}} for every ACTIVE row, read from the database. Needs only text columns (not the vector type)."""
    subs = {r["id"]: r["name_en"] for r in await db.fetch("SELECT id, name_en FROM subdomains")}
    comps = [dict(r) for r in await db.fetch("SELECT id, name_en, name_hi, description_en, grade_level, subdomain_id FROM competencies WHERE is_active = TRUE ORDER BY id")]
    out = {"competencies": {c["id"]: competency_text(c, subs.get(c["subdomain_id"], "")) for c in comps}}
    out["anchor_activities"] = {r["id"]: anchor_text(dict(r)) for r in await db.fetch("SELECT * FROM anchor_activities WHERE is_active = TRUE ORDER BY id")}
    out["reading_passages"] = {r["id"]: passage_text(dict(r)) for r in await db.fetch("SELECT * FROM reading_passages WHERE is_active = TRUE ORDER BY id")}
    out["intervention_templates"] = {r["id"]: intervention_text(dict(r)) for r in await db.fetch("SELECT * FROM intervention_templates WHERE is_active = TRUE ORDER BY id")}
    out["tlm_references"] = {r["id"]: tlm_text(dict(r)) for r in await db.fetch("SELECT * FROM tlm_references WHERE is_active = TRUE ORDER BY id")}
    return out
