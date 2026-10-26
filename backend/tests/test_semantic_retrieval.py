"""
Semantic retrieval for the L2 anchors (the proposal's pgvector design), as built: the curated ladder first, the semantic tier only where the ladder has nothing, a switch (default OFF), the vectors computed OFFLINE
and loaded from one file, and the running app calling no embedding service.

    cd backend && python tests/test_semantic_retrieval.py --env-file .env

The checks that need a database WITH pgvector run inside a transaction that is rolled back; against a database without it (the setup script turns the columns into text there) they are SKIPPED with a notice.
The vectors here are a stand-in (hashed words, 1024 numbers): they test the MACHINERY. Whether real BAAI/bge-m3 vectors give good choices is what scripts/eval_semantic.py is for.
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import asyncio
import hashlib
import json
import math
import os
import random
import re
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("AUTH_MODE", "off")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "prompts"), str(ROOT / "backend"), str(HERE)]
import _scratch
import embedding_texts as et
import embed_content as ec
import load_embeddings as le
import eval_semantic as ev
import orchestrate as o

failures = []
skipped = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


def stand_in(texts, dims=1024):
    """A deterministic stand-in for the model: hashed words, unit length. Texts that share words get similar vectors."""
    out = []
    for t in texts:
        v = [0.0] * dims
        for w in re.findall(r"\w+", t.lower()):
            h = int(hashlib.md5(w.encode()).hexdigest(), 16)
            v[h % dims] += 1.0 if (h >> 20) % 2 else -1.0
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        out.append([x / n for x in v])
    return out


async def main():
    print("the texts and their fingerprints")
    check("a fingerprint ignores white space and changes with the words", et.fingerprint("a  b\n c") == et.fingerprint("a b c") and et.fingerprint("a b c") != et.fingerprint("a b d") and len(et.fingerprint("x")) == 16)
    t = et.anchor_text({"title_en": "At the market", "title_hi": "बाज़ार में", "description_en": "Buying fruit", "theme": "market", "setting": "classroom", "primary_competency_ids": ["N1"], "secondary_competency_ids": ["N2", "NX"], "template_body": "x" * 900})
    check("an anchor's text carries its own content: title, description, theme, setting and at most 400 characters of the story", "At the market." in t and "Buying fruit" in t and "Theme: market." in t and "Setting: classroom." in t and t.count("x") == 400, t[:200])
    check("...and NEVER the skills it was written for (neither names nor codes): otherwise the recovery test would be circular", "Skills it practises" not in t and "N1" not in t and "N2" not in t and "NX" not in t)
    check("so the text of an anchor is the same whichever skills it is linked to (the vector depends on content only)", et.anchor_text({"title_en": "A", "primary_competency_ids": ["N1"]}) == et.anchor_text({"title_en": "A", "primary_competency_ids": ["N9", "N8"]}))
    check("a skill's text carries its name in both languages, its description, topic area and grade; missing fields do not break it", "Topic area: Money." in et.competency_text({"name_en": "Counts money", "name_hi": "पैसे गिनना", "description_en": "Counts coins", "grade_level": "grade_2"}, "Money") and et.competency_text({}, "") != "None")
    check("passages, interventions and teaching materials tolerate empty fields and JSON text", all(isinstance(f({}), str) for f in (et.passage_text, et.intervention_text, et.tlm_text)) and "do this" in et.intervention_text({"steps": json.dumps([{"instruction_en": "do this"}])}))

    print("\nthe embeddings file")
    texts = {"competencies": {"N1": "Adds two numbers", "N2": "Counts money"}, "anchor_activities": {"A1": "At the market. Buying fruit"}}
    data = ec.build_file(texts, stand_in, "stand-in", "rev0", 1024)
    check("each text becomes one vector of 1024 numbers, with the fingerprint of the text it was made from", set(data["tables"]) == set(et.TABLES) and len(data["tables"]["competencies"]["N1"]["vector"]) == 1024 and data["tables"]["competencies"]["N1"]["hash"] == et.fingerprint("Adds two numbers") and data["tables"]["reading_passages"] == {})
    check("the file says which model, revision and size made it, and the vectors are rounded (5 decimals)", data["model"] == "stand-in" and data["revision"] == "rev0" and data["dims"] == 1024 and data["normalized"] is True and all(abs(x * 1e5 - round(x * 1e5)) < 1e-6 for x in data["tables"]["competencies"]["N1"]["vector"][:50]))
    check("--only builds just the named tables", list(k for k, v in ec.build_file(texts, stand_in, "m", "r", 1024, only={"competencies"})["tables"].items() if v) == ["competencies"])
    try:
        ec.build_file(texts, lambda ts: [[0.0] * 10 for _ in ts], "m", "r", 1024)
        wrong = False
    except ValueError as e:
        wrong = "expected 1024" in str(e)
    check("a model that returns the wrong size is refused with a clear message (not written to a file)", wrong)
    try:
        ec.build_file(texts, lambda ts: [[float("nan")] * 1024 for _ in ts], "m", "r", 1024)
        nan = False
    except ValueError:
        nan = True
    check("a vector with a value that is not a number is refused", nan)
    tmp = Path(tempfile.mkdtemp()) / "e.json"
    sha = ec.write_file(data, tmp)
    check("the file round-trips through the loader's validator, with no problems", le.validate_file(json.loads(tmp.read_text(encoding="utf-8"))) == [] and len(sha) == 64)
    bad = json.loads(tmp.read_text(encoding="utf-8"))
    bad["tables"]["competencies"]["N1"]["vector"] = bad["tables"]["competencies"]["N1"]["vector"][:5]
    check("the validator catches: a wrong-size vector, a missing key, an unknown table, a wrong format, a non-object", any("5 numbers" in p for p in le.validate_file(bad)) and any("'tables'" in p for p in le.validate_file({"format": 1, "model": "m", "dims": 3}))
          and any("not one of" in p for p in le.validate_file({"format": 1, "model": "m", "dims": 3, "tables": {"users": {}}})) and any("format 2" in p for p in le.validate_file({"format": 2, "model": "m", "dims": 3, "tables": {}})) and le.validate_file([]) == ["the file is not a JSON object"])
    full = {"competencies": {f"C{i}": f"skill number {i} adds things" for i in range(101)}, "anchor_activities": {f"A{i}": f"anchor {i} market" for i in range(14)}, "reading_passages": {f"P{i}": f"passage {i}" for i in range(9)},
            "intervention_templates": {f"I{i}": f"fix {i}" for i in range(15)}, "tlm_references": {f"T{i}": f"tool {i}" for i in range(12)}}
    rng = random.Random(1)

    def dense(texts_):                                  # DENSE unit vectors, like a real model's (the stand-in is sparse and would understate the size)
        out = []
        for _ in texts_:
            v = [rng.gauss(0, 1) for _ in range(1024)]
            n = math.sqrt(sum(x * x for x in v))
            out.append([x / n for x in v])
        return out
    big = len(json.dumps(ec.build_file(full, dense, "m", "r", 1024), separators=(",", ":")))
    check(f"the whole file for 151 texts with DENSE vectors, like a real model's, is small enough to commit ({big / 1e6:.2f} MB)", 1_000_000 < big < 2_000_000, big)

    print("\nthe evidence script (pure functions)")
    check("cosine: identical 1, orthogonal 0, opposite -1, a zero vector 0", abs(ev.cosine([1, 0], [1, 0]) - 1) < 1e-9 and abs(ev.cosine([1, 0], [0, 1])) < 1e-9 and abs(ev.cosine([1, 0], [-1, 0]) + 1) < 1e-9 and ev.cosine([0, 0], [1, 0]) == 0.0)
    ranked = ev.rank_anchors([1, 0], [{"id": "B", "vec": [1, 0]}, {"id": "A", "vec": [1, 0]}, {"id": "C", "vec": [0, 1]}])
    check("ranking: the nearest first, and a tie goes to the LOWER id (the same rule as the SQL)", [a["id"] for a in ranked] == ["A", "B", "C"])
    check("the random baseline is right: 1 curated of 8, first = 1/8; top 3 = 3/8; of 2 anchors the top 3 always contains it", abs(ev.random_baseline(8, 1, 1) - 1 / 8) < 1e-12 and abs(ev.random_baseline(8, 1, 3) - 3 / 8) < 1e-12 and ev.random_baseline(2, 1, 3) == 1.0 and ev.random_baseline(5, 5, 1) == 1.0)
    anchors = [{"id": f"A{i}", "domain": "d", "grades": ["g"], "vec": [1.0 if j == i else 0.0 for j in range(4)]} for i in range(4)]
    skills_good = [{"id": f"S{i}", "domain": "d", "grade": "g", "vec": [1.0 if j == i else 0.0 for j in range(4)], "exact_ids": {f"A{i}"}} for i in range(4)]
    skills_bad = [{"id": f"S{i}", "domain": "d", "grade": "g", "vec": [1.0 if j == (i + 1) % 4 else 0.0 for j in range(4)], "exact_ids": {f"A{i}"}} for i in range(4)]
    g, b = ev.recovery(skills_good, anchors), ev.recovery(skills_bad, anchors)
    check("recovery: when the meaning matches the curation, the curated anchor is ranked first every time; when it does not, never", g["hit1"] == 1.0 and g["mrr"] == 1.0 and b["hit1"] == 0.0 and abs(g["random_hit1"] - 0.25) < 1e-9, (g, b))
    check("recovery ignores skills with no curated anchor, and anchors of another domain or grade", ev.recovery([{"id": "X", "domain": "d", "grade": "g", "vec": [1, 0, 0, 0], "exact_ids": set()}], anchors)["tested"] == 0 and ev.recovery([{"id": "X", "domain": "other", "grade": "g", "vec": [1, 0, 0, 0], "exact_ids": {"A0"}}], anchors)["tested"] == 0)

    print("\nthe switch and the nightly job")
    for v, want in (("on", True), ("ON", True), ("1", True), ("true", True), ("yes", True), ("off", False), ("", False), ("0", False), ("no", False), ("maybe", False)):
        os.environ["SEMANTIC_RETRIEVAL"] = v
        if o.semantic_enabled() != want:
            check(f"SEMANTIC_RETRIEVAL={v!r} means {want}", False)
            break
    else:
        check("on / ON / 1 / true / yes switch it on; off, empty, 0, no and anything else leave it off", True)
    del os.environ["SEMANTIC_RETRIEVAL"]
    check("with the variable not set at all it is OFF (the default of the frozen version until the gate says otherwise)", o.semantic_enabled() is False)
    nr = (ROOT / "scripts" / "nightly_reset.py").read_text(encoding="utf-8")
    check("the nightly job loads the embeddings as a step that cannot stop the demo reset", 'load_embeddings.py")], env_args, fatal=False' in nr)
    check("no trace of the old design is left in the retrieval (no query_embedding parameter, no embedding API in the config)", "query_embedding" not in (ROOT / "prompts" / "orchestrate.py").read_text(encoding="utf-8") and "embedding_api" not in (ROOT / "backend" / "app" / "core" / "config.py").read_text(encoding="utf-8"))
    check("the old OpenAI script is only a pointer now (it exits with a message and calls nothing)", "api.openai.com" not in (ROOT / "scripts" / "populate_embeddings.py").read_text(encoding="utf-8") and "REPLACED" in (ROOT / "scripts" / "populate_embeddings.py").read_text(encoding="utf-8"))

    db = await _scratch.connect()
    tr = db.transaction()
    await tr.start()
    try:
        await le.ensure_schema(db)
        ready, why = await le.vectors_ready(db)
        if not ready:
            print(f"\n  SKIPPED the database checks: {why}")
            skipped.append(why)
        else:
            print("\nthe loader, against the real schema and the real rows (inside a transaction that is rolled back)")
            ok_dims = await db.fetchval("SELECT format_type(a.atttypid, a.atttypmod) FROM pg_attribute a WHERE a.attrelid = 'competencies'::regclass AND a.attname = 'embedding'")
            check("the migration is idempotent and the skills table has a vector(1024) column", ok_dims == "vector(1024)" and (await le.ensure_schema(db)) is None, ok_dims)
            real = await et.load_texts(db)
            total = sum(len(v) for v in real.values())
            check(f"the texts are read from the database: {total} active rows ({', '.join(f'{k} {len(v)}' for k, v in real.items())})", real and len(real["competencies"]) == 101 and len(real["anchor_activities"]) >= 14, {k: len(v) for k, v in real.items()})
            data = ec.build_file(real, stand_in, "stand-in", "rev0", 1024)
            before = await db.fetchval("SELECT count(*) FROM competencies WHERE embedding IS NOT NULL")
            dry = await le.apply(db, data, "sha", dry_run=True)
            after = await db.fetchval("SELECT count(*) FROM competencies WHERE embedding IS NOT NULL")
            check("--check changes nothing, and says how many would load", before == after and dry["competencies"]["loaded"] == 101 and all(s["stale"] == 0 for s in dry.values()), dry)
            summary = await le.apply(db, data, "sha-1")
            check(f"loading puts ALL {total} vectors in, none stale or missing", sum(s["loaded"] for s in summary.values()) == total and all(s["stale"] == 0 and s["missing_row"] == 0 and s["without_vector"] == 0 for s in summary.values()), summary)
            meta = await db.fetchrow("SELECT model, revision, dims, file_sha256, counts FROM embedding_meta WHERE id = 1")
            check("the database remembers which model, revision and file the vectors came from", meta and meta["model"] == "stand-in" and meta["revision"] == "rev0" and meta["dims"] == 1024 and meta["file_sha256"] == "sha-1" and json.loads(meta["counts"])["competencies"]["loaded"] == 101)
            check("loading again changes nothing (idempotent)", sum(s["loaded"] for s in (await le.apply(db, data, "sha-1")).values()) == total)
            check("the report reads clearly, one line per table", len(le.report(summary)) == 5 and "101 of 101 loaded" in le.report(summary)[0])

            print("\nthe evidence script reads the file as well as the database")
            fv, fstale = await ev.vectors_from_file(db, data)
            fs, fa, _, _ = await ev.load(db, fv)
            ds, da, _, _ = await ev.load(db)
            rec_file, rec_db = ev.recovery(fs, fa), ev.recovery(ds, da)
            check("from the FILE (no pgvector needed) it tests the same 48 skills and gets exactly the same recovery numbers as from the database", fstale == 0 and rec_file["tested"] == rec_db["tested"] == 48 and rec_file["hit1"] == rec_db["hit1"] and rec_file["hit3"] == rec_db["hit3"] and abs(rec_file["mrr"] - rec_db["mrr"]) < 1e-9, (rec_file["hit1"], rec_db["hit1"]))
            stale_data = json.loads(json.dumps(data))
            some = next(iter(stale_data["tables"]["competencies"]))
            stale_data["tables"]["competencies"][some]["hash"] = "0" * 16
            fv2, fstale2 = await ev.vectors_from_file(db, stale_data)
            check("a vector in the file made for an older text is left out of the evidence, and counted", fstale2 == 1 and some not in fv2["competencies"])

            print("\nthe retrieval, for all 101 skills")
            comps = await db.fetch("SELECT c.id, c.grade_level, s.domain_id FROM competencies c JOIN subdomains s ON s.id = c.subdomain_id ORDER BY c.id")
            os.environ["SEMANTIC_RETRIEVAL"] = "off"
            base = {c["id"]: await o.fetch_anchor_activity(db, c["domain_id"], c["grade_level"], c["id"]) for c in comps}
            tiers = {}
            for a in base.values():
                tiers[a.match_quality] = tiers.get(a.match_quality, 0) + 1
            check("SWITCH OFF: the curated ladder is exactly what it was (48 exact, 29 related, 10 topic area, 14 loose of 101 skills)", tiers == {"exact": 48, "related": 29, "topic_area": 10, "loose": 14}, tiers)
            os.environ["SEMANTIC_RETRIEVAL"] = "on"
            on = {c["id"]: await o.fetch_anchor_activity(db, c["domain_id"], c["grade_level"], c["id"]) for c in comps}
            curated = [c for c in comps if base[c["id"]].match_quality in ("exact", "related")]
            check(f"SWITCH ON: the {len(curated)} skills the curated tiers serve get EXACTLY the same anchor as before (77% of skills: no change at all)", all((on[c["id"]].id, on[c["id"]].match_quality) == (base[c["id"]].id, base[c["id"]].match_quality) for c in curated))
            weak = [c for c in comps if base[c["id"]].match_quality in ("topic_area", "loose")]
            check(f"SWITCH ON: the {len(weak)} weakly served skills now get a 'semantic' anchor", all(on[c["id"]].match_quality == "semantic" for c in weak), [(c["id"], on[c["id"]].match_quality) for c in weak if on[c["id"]].match_quality != "semantic"])
            skills, anchors, _, _ = await ev.load(db)
            by_skill = {s["id"]: s for s in skills}
            bad = []
            for c in weak:
                s = by_skill[c["id"]]
                pool = [a for a in anchors if a["domain"] == s["domain"] and s["grade"] in a["grades"]]
                best = ev.rank_anchors(s["vec"], pool)[0]
                got = on[c["id"]]
                sim_got = next(a["sim"] for a in ev.rank_anchors(s["vec"], pool) if a["id"] == got.id)
                if got.id != best["id"] and abs(sim_got - best["sim"]) > 1e-5:
                    bad.append((c["id"], got.id, best["id"]))
            check("the semantic choice is the NEAREST anchor, checked against an independent cosine calculation in Python", not bad, bad[:3])
            check("the similarity it reports is the cosine similarity (within 1e-4)", all(abs(on[c["id"]].similarity - ev.cosine(by_skill[c["id"]]["vec"], next(a["vec"] for a in anchors if a["id"] == on[c["id"]].id))) < 1e-4 for c in weak))
            rows = {r["id"]: r for r in await db.fetch("SELECT id, domain_id, grade_range, is_active FROM anchor_activities")}
            check("it NEVER returns an anchor of another domain, another grade or an inactive one", all(rows[on[c["id"]].id]["domain_id"] == c["domain_id"] and c["grade_level"] in rows[on[c["id"]].id]["grade_range"] and rows[on[c["id"]].id]["is_active"] for c in weak))
            again = {c["id"]: await o.fetch_anchor_activity(db, c["domain_id"], c["grade_level"], c["id"]) for c in comps}
            check("the same inputs give the same answer (deterministic)", all((again[k].id, again[k].match_quality) == (on[k].id, on[k].match_quality) for k in on))

            print("\nwhen something is missing or wrong, the ladder simply continues")
            w0 = weak[0]
            await db.execute("UPDATE competencies SET embedding = NULL WHERE id = $1", w0["id"])
            fb = await o.fetch_anchor_activity(db, w0["domain_id"], w0["grade_level"], w0["id"])
            check("a skill without a vector falls back to the topic-area / loose answer it had before", (fb.id, fb.match_quality) == (base[w0["id"]].id, base[w0["id"]].match_quality))
            await db.execute("UPDATE competencies SET embedding = $1::vector WHERE id = $2", "[" + ",".join(repr(x) for x in by_skill[w0["id"]]["vec"]) + "]", w0["id"])
            real_sql = o._SEMANTIC_SQL
            o._SEMANTIC_SQL = "SELECT nothing FROM nowhere"
            try:
                broken = await o.fetch_anchor_activity(db, w0["domain_id"], w0["grade_level"], w0["id"])
                alive = await db.fetchval("SELECT 1")
            finally:
                o._SEMANTIC_SQL = real_sql
            check("an ERROR inside the semantic query does not raise, falls back, and does NOT poison the transaction the caller is in", (broken.id, broken.match_quality) == (base[w0["id"]].id, base[w0["id"]].match_quality) and alive == 1)
            real_ready = o._vectors_ready

            async def never(db_):
                return False
            o._vectors_ready = never
            try:
                nr_ = await o.fetch_anchor_activity(db, w0["domain_id"], w0["grade_level"], w0["id"])
            finally:
                o._vectors_ready = real_ready
            check("with no pgvector (the columns are text) it falls back too", (nr_.id, nr_.match_quality) == (base[w0["id"]].id, base[w0["id"]].match_quality))
            await db.execute("UPDATE anchor_activities SET embedding = (SELECT embedding FROM competencies WHERE id = $1)", w0["id"])
            tie = await o.fetch_anchor_activity(db, w0["domain_id"], w0["grade_level"], w0["id"])
            eligible = sorted(r["id"] for r in rows.values() if r["domain_id"] == w0["domain_id"] and w0["grade_level"] in r["grade_range"] and r["is_active"])
            check("when every anchor is exactly as near as every other, the LOWEST id wins (a stable demo)", tie.id == eligible[0] and tie.match_quality == "semantic", (tie.id, eligible[:3]))
            await db.execute("UPDATE anchor_activities SET embedding = NULL")
            gone = {c["id"]: await o.fetch_anchor_activity(db, c["domain_id"], c["grade_level"], c["id"]) for c in comps}
            check("with NO anchor vectors at all, all 101 skills get exactly the answer they had before", all((gone[k].id, gone[k].match_quality) == (base[k].id, base[k].match_quality) for k in base))
            x = next(iter(real["anchor_activities"]))
            await db.execute("UPDATE anchor_activities SET description_en = coalesce(description_en, '') || ' (edited after the vectors were made)' WHERE id = $1", x)
            stale = await le.apply(db, data, "sha-2")
            check("a vector made for an OLDER text of a row is recognised as stale and NOT loaded (the row stays without one)", stale["anchor_activities"]["stale"] == 1 and stale["anchor_activities"]["without_vector"] == 1 and stale["anchor_activities"]["loaded"] == len(real["anchor_activities"]) - 1, stale["anchor_activities"])

            print("\nthe prompt")
            sem_anchor = next(a for a in on.values() if a.match_quality == "semantic")
            section = o._anchor_prompt_section(SimpleNamespace(anchor=sem_anchor, selected_competency=SimpleNamespace(id="N2.3.2")))
            check("the model is told the anchor was chosen by closeness of meaning, to keep the setting and rewrite every group's task, and to say so in explainability", all(w in section for w in ("Match quality: SEMANTIC", "NEAREST IN MEANING", "rewrite each group's task", "semantic match")), section[:200])
            word = {"exact": "Match quality: EXACT", "related": "Match quality: RELATED", "topic_area": "Match quality: TOPIC-AREA", "loose": "Match quality: LOOSE"}
            one_per_tier = {}
            for k, a in base.items():
                one_per_tier.setdefault(a.match_quality, k)
            check("the four older tiers are described exactly as before (one anchor of each tier checked)", set(one_per_tier) == set(word) and all(word[q] in o._anchor_prompt_section(SimpleNamespace(anchor=base[k], selected_competency=SimpleNamespace(id=k))) for q, k in one_per_tier.items()), one_per_tier)
    finally:
        await tr.rollback()
        await db.close()
    if failures:
        print(f"\nFAILED ({len(failures)})")
        sys.exit(1)
    if skipped:
        print("\nOK so far, BUT the database checks (the retrieval for all 101 skills, the fallbacks, the loader) were SKIPPED: this database has no pgvector. Run this test against a database that has it.")
    else:
        print("\nOK: the curated ladder is unchanged, the semantic tier fills only the weak part and falls back on any problem, the vectors come from one file, and the running app calls no embedding service")


if __name__ == "__main__":
    asyncio.run(main())
