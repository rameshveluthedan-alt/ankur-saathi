"""
The block-library generator, step 1 (teach blocks): the checks a piece must pass (the app's own), the file and the manifest, the retry with
reasons, the cost cap, and resuming. The AI is a fake: no paid call. (docs/drafts/BLOCK_LIBRARY_PLAN.md)

    python backend/tests/test_library_generator.py --env-file backend/.env
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import asyncio
import copy
import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = Path(HERE).parents[1]
import _scratch
sys.path.insert(0, str(ROOT / "scripts"))
import generate_library as gl
from app.services import library_pieces as lp, plan_service

failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


# a real block and worksheet (the Progressors of a prompt-v2 test plan) as the model's reply
PLAN = json.load(open(ROOT / "docs" / "drafts" / "prompt_v2_runs" / "N2.3.2_90.plan.json", encoding="utf-8"))
BLOCK = next(b for b in PLAN["rotation_schedule"]["blocks"] if b.get("teach_group") == "progressor")
GOOD = {"talking_points": copy.deepcopy(BLOCK["talking_points"]), "cfu": copy.deepcopy(BLOCK.get("cfu") or []),
        "prep_hi": ["छड़ियों के बंडल"], "worksheet": copy.deepcopy(PLAN["worksheets"]["progressor"])}


def fresh():
    return copy.deepcopy(GOOD)


class Fake:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []
        self.messages = self

    async def create(self, **kw):
        self.calls.append(kw)
        r = self.replies.pop(0) if self.replies else fresh()
        text = r if isinstance(r, str) else json.dumps(r, ensure_ascii=False)
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)], stop_reason="end_turn",
                               usage=SimpleNamespace(input_tokens=5000, output_tokens=3000, cache_read_input_tokens=9000, cache_creation_input_tokens=0))


async def main():
    db = await _scratch.connect()
    try:
        skill, mistakes = await gl.skill_facts(db, "N2.3.2")
        print("the checks on one piece (the app's own)")
        r = lp.check_teach_piece(fresh(), skill, mistakes, "long", plan_service)
        check("a real Progressor block and sheet pass", r["ok"], r)
        p = fresh()
        plain = next(x for x in p["worksheet"]["problems"] if lp._PLAIN.match(str(x.get("problem_hi") or "")))
        plain["answer"] = "999"
        p["talking_points"]["i_do_hi"] += " कहें: 'मैं अब जोड़ूँगी।'"
        p["worksheet"]["problems"][0]["diagnostic_for_misconception"] = "N9.9.9-M1"
        r = lp.check_teach_piece(p, skill, mistakes, "long", plan_service)
        check("a wrong answer on a plain sum is computed again by code", plain["answer"] != "999" and any("answer key" in x for x in r["repairs"]), r["repairs"])
        check("a gendered 'मैं' in the teacher's quoted words becomes 'हम'", "हम अब जोड़ेंगे" in p["talking_points"]["i_do_hi"], p["talking_points"]["i_do_hi"][-60:])
        check("a mistake ID from another skill is cleared", p["worksheet"]["problems"][0].get("diagnostic_for_misconception") is None)
        p = fresh()
        p["talking_points"]["you_do_hi"] = ""
        r = lp.check_teach_piece(p, skill, mistakes, "long", plan_service)
        check("no You Do: fatal", not r["ok"] and any("you_do_hi" in f for f in r["fatal"]))
        p = fresh()
        p["cfu"] = []
        r = lp.check_teach_piece(p, skill, mistakes, "long", plan_service)
        check("no show-me questions: fatal (2 are needed)", not r["ok"] and any("show-me" in f for f in r["fatal"]))
        p = fresh()
        p["talking_points"]["we_do_hi"] = ""
        check("a short (7-minute) block needs no We Do", lp.check_teach_piece(p, skill, mistakes, "short", plan_service)["ok"])
        check("the answer-key code: only plain sums, never a word problem",
              lp.compute_answer_keys({"problems": [{"number": 1, "problem_hi": "23 + 14", "answer": "36"}, {"number": 2, "problem_hi": "राम के पास 3 आम हैं", "answer": "x"},
                                                   {"number": 3, "problem_hi": "45 − 12 = ___", "answer": "33"}, {"number": 4, "problem_hi": "6 × 7", "answer": "41"}]})
              == ["problem 1: answer '36' -> 37 (computed)", "problem 4: answer '41' -> 42 (computed)"])

        print("\ngenerating, with a stand-in model")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            man = gl.load_manifest(root)
            spent = [0.0]
            fake = Fake(["not json at all", fresh()])
            st = await gl.generate_one(fake, "claude-opus-5-5", db, skill, mistakes, "long", root, man, spent, 3.0, plan_service, log=lambda *a: None)
            f = root / "teach" / "N2.3.2__normal__long.json"
            rec = json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {}
            check("not JSON the first time: asked again once, then ok", st == "ok" and len(fake.calls) == 2, (st, len(fake.calls)))
            check("...the second request carries the reason", "AN EARLIER ATTEMPT WAS REJECTED" in fake.calls[1]["messages"][0]["content"])
            check("the request is the app's cached system rules + the piece prompt, with Opus's own thinking setting",
                  fake.calls[0]["system"][0].get("cache_control") == {"type": "ephemeral"} and "ONE TEACH BLOCK FOR A LIBRARY" in fake.calls[0]["messages"][0]["content"]
                  and fake.calls[0]["extra_body"] == {"output_config": {"effort": "low"}})
            check("one file, with the piece, its checks, the model, the prompt version, the cost and 'ai_drafted'",
                  rec.get("key") == "N2.3.2__normal__long" and rec["content"]["talking_points"] and rec["checks"]["ok"] and rec["model"] == "claude-opus-5-5"
                  and len(rec["prompt_version"]) == 12 and rec["cost_usd"] > 0 and rec["review_status"] == "ai_drafted", {k: rec.get(k) for k in ("key", "model", "cost_usd")})
            m2 = gl.load_manifest(root)
            check("the manifest says ok, with the cost of both calls", m2["pieces"]["N2.3.2__normal__long"]["status"] == "ok"
                  and abs(m2["pieces"]["N2.3.2__normal__long"]["cost_usd"] - 2 * gl.cost_of("claude-opus-5-5", fake.calls and SimpleNamespace(input_tokens=5000, output_tokens=3000, cache_read_input_tokens=9000, cache_creation_input_tokens=0))) < 1e-6)
            bad = fresh()
            bad["cfu"] = []
            fake2 = Fake([bad, copy.deepcopy(bad)])
            st2 = await gl.generate_one(fake2, "claude-opus-5-5", db, skill, mistakes, "short", root, man, spent, 3.0, plan_service, log=lambda *a: None)
            check("failing the checks twice: 'failed_checks', with the reasons, for a person", st2 == "failed_checks" and len(fake2.calls) == 2
                  and gl.load_manifest(root)["pieces"]["N2.3.2__normal__short"]["fatal"])
            fake3 = Fake([fresh()])
            st3 = await gl.generate_one(fake3, "claude-opus-5-5", db, skill, mistakes, "medium", root, man, [5.0], 3.0, plan_service, log=lambda *a: None)
            check("the cost cap reached: nothing is called, the run stops", st3 == "stopped" and not fake3.calls)
            man4 = gl.load_manifest(root)
            todo = [(s, l) for s in ["N2.3.2"] for l in ("short", "medium", "long") if man4["pieces"].get(lp.teach_key(s, l), {}).get("status") != "ok"]
            check("a new run skips what is done (resume): the failed and the missing pieces are left to make", todo == [("N2.3.2", "short"), ("N2.3.2", "medium")], todo)

            print("\nre-teach pieces (one per recorded mistake)")
            m1 = next(m for m in mistakes if m["id"].endswith("-M1"))
            fake5 = Fake([fresh()])
            st5 = await gl.generate_one(fake5, "claude-opus-5-5", db, skill, mistakes, "medium", root, man, [0.0], 3.0, plan_service, log=lambda *a: None, reteach=m1)
            f5 = root / "reteach" / f"{m1['id']}__medium.json"
            rec5 = json.loads(f5.read_text(encoding="utf-8")) if f5.is_file() else {}
            check("the prompt says it is a re-teach of that mistake, by the system's re-teach rules", f"RE-TEACH of ONE recorded mistake: {m1['id']}" in fake5.calls[0]["messages"][0]["content"])
            check("its own file and key, with the mistake as the mode", st5 == "ok" and rec5.get("key") == f"{m1['id']}__medium" and rec5.get("mode") == m1["id"] and rec5.get("piece") == "reteach", (st5, rec5.get("key")))
            check("the manifest records the mistake", gl.load_manifest(root)["pieces"][f"{m1['id']}__medium"]["mistake_id"] == m1["id"])
            p6 = fresh()
            for p in p6["worksheet"]["problems"]:
                p["diagnostic_for_misconception"] = None
            r6 = lp.check_teach_piece(p6, skill, mistakes, "medium", plan_service, reteach=m1)
            check("a re-teach whose core reveals another mistake is warned about (not rejected)", r6["ok"] and any(f"no core problem reveals {m1['id']}" in w for w in r6["warnings"]), r6["warnings"])
        n = await db.fetchval("SELECT count(*) FROM ai_usage WHERE kind = 'library' AND teacher_id IS NULL AND created_at > now() - interval '5 minutes'")
        check("every call was metered as 'library'", n >= 4, n)
        await db.execute("DELETE FROM ai_usage WHERE kind = 'library' AND teacher_id IS NULL AND created_at > now() - interval '5 minutes' AND input_tokens = 5000 AND output_tokens = 3000")
    finally:
        await db.close()


asyncio.run(main())
if failures:
    print(f"\nFAILED ({len(failures)})")
    sys.exit(1)
print("\nOK: a library piece passes the app's own checks, is written once with its record, and a stopped run continues where it left off")
