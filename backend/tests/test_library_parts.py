"""
The block library, step 2: independent activities, anchor settings and anchor tasks (their checks), the generator's general job path, and the
Message Batches path (submit, collect, a failed reply asked for again). The AI and the batch API are fakes: no paid call, no network.

    python backend/tests/test_library_parts.py --env-file backend/.env
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

import httpx

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = Path(HERE).parents[1]
import _scratch
sys.path.insert(0, str(ROOT / "scripts"))
import generate_library as gl
import library_batch as lb
from app.services import library_parts as lpp, plan_service

failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


IND = {"title_hi": "छड़ियों से जोड़", "source": "board", "materials_hi": ["छड़ियाँ"], "board_hi": "21 + 13, 32 + 14",
       "core_hi": "बोर्ड पर लिखे सवाल 21 + 13 और 32 + 14 कॉपी में हल करें।", "extras_hi": ["41 + 25 हल करें।", "52 + 33 हल करें।", "अपने सवाल के उत्तर साथी से मिलाएँ।"],
       "check_hi": "साथी की कॉपी देखें।"}
SET = {"title_hi": "गाँव का बाज़ार", "title_en": "The village market", "theme": "village market", "board_hi": "आम 12 रुपये, केला 5 रुपये",
       "narration_hi": "आज हम बाज़ार चलते हैं।", "opening_question_hi": "बाज़ार में क्या-क्या मिलता है?", "closing_question_hi": "आज हमने क्या खरीदा?", "materials_hi": []}


class Fake:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []
        self.messages = self

    async def create(self, **kw):
        self.calls.append(kw)
        r = self.replies.pop(0)
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=r if isinstance(r, str) else json.dumps(r, ensure_ascii=False))], stop_reason="end_turn",
                               usage=SimpleNamespace(input_tokens=4000, output_tokens=1000, cache_read_input_tokens=0, cache_creation_input_tokens=0))


async def main():
    db = await _scratch.connect()
    try:
        s231, _ = await gl.skill_facts(db, "N2.3.1")
        print("the number rules (the show-me check's own)")
        check("a carry in a 'without regrouping' skill is caught", any("needs a carry" in x for x in lpp.number_issues("सवाल: 27 + 15", s231)))
        check("a sum without a carry is fine", lpp.number_issues("21 + 13 और 32 + 14", s231) == [])
        s232, _ = await gl.skill_facts(db, "N2.3.2")
        check("a two-digit addition skill: a total over 99 is caught", any("over 99" in x for x in lpp.number_issues("79 + 21", s232)))

        print("\nindependent activities")
        p = copy.deepcopy(IND)
        check("a good activity passes", lpp.check_independent_piece(p, s231)["ok"])
        p = copy.deepcopy(IND)
        p["extras_hi"] = p["extras_hi"][:2]
        check("fewer than 3 extras: fatal", not lpp.check_independent_piece(p, s231)["ok"])
        p = copy.deepcopy(IND)
        p["extras_hi"][0] = "38 + 47 हल करें।"
        r = lpp.check_independent_piece(p, s231)
        check("a carry in a no-carry skill's activity: fatal", not r["ok"] and "needs a carry" in "; ".join(r["fatal"]), r["fatal"])
        p = copy.deepcopy(IND)
        p["core_hi"] = "कहें: 'मैं बोर्ड पर लिखूँगी।' फिर सवाल हल करें।"
        lpp.check_independent_piece(p, s231)
        check("the Hindi style: a gendered 'मैं' in quotes becomes 'हम'", "हम बोर्ड पर लिखेंगे" in p["core_hi"], p["core_hi"])

        print("\nanchor settings and tasks")
        check("a good setting passes", lpp.check_setting_piece(copy.deepcopy(SET))["ok"])
        bad = copy.deepcopy(SET)
        bad["board_hi"] = ""
        check("a setting without a board picture: fatal", not lpp.check_setting_piece(bad)["ok"])
        settings = {"numeracy__village_market": SET, "numeracy__school_garden": dict(SET, title_hi="बगीचा"), "numeracy__bus_journey": dict(SET, title_hi="बस")}
        tasks = {"tasks": [{"setting": "numeracy__village_market", "task_hi": "आम और केला: 12 + 5 कितने?", "answer_hi": "17"},
                           {"setting": "numeracy__school_garden", "task_hi": "21 + 14 पौधे", "answer_hi": "35"},
                           {"setting": "numeracy__bus_journey", "task_hi": "23 + 16 लोग", "answer_hi": "39"},
                           {"setting": "numeracy__nowhere", "task_hi": "x", "answer_hi": "y"}]}
        r = lpp.check_tasks_piece(tasks, s231, settings)
        check("three tasks in known settings pass; one in an unknown setting is dropped", r["ok"] and len(tasks["tasks"]) == 3 and any("unknown setting" in w for w in r["warnings"]), r)
        t2 = {"tasks": [dict(t) for t in tasks["tasks"][:2]] + [{"setting": "numeracy__bus_journey", "task_hi": "38 + 47 लोग", "answer_hi": "85"}]}
        r = lpp.check_tasks_piece(t2, s231, settings)
        check("a task breaking the skill's rule is dropped, and fewer than 3 is fatal", not r["ok"] and len(t2["tasks"]) == 2, r)

        print("\nthe generator's general path (normal calls), with a stand-in model")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            man = gl.load_manifest(root)
            fake = Fake(["{not json", copy.deepcopy(IND)])
            st = await gl.run_job(fake, "claude-opus-5-5", db, gl.independent_job(s231, 1), root, man, [0.0], 3.0, log=lambda *a: None)
            rec = json.loads((root / "independent" / "N2.3.1__1.json").read_text(encoding="utf-8"))
            check("an independent activity: retried once, then written with its record", st == "ok" and len(fake.calls) == 2 and rec["piece"] == "independent" and rec["mode"] == "variant 1")
            check("...its request is the app's cached rules + the activity prompt", "ONE INDEPENDENT-PRACTICE ACTIVITY" in fake.calls[0]["messages"][0]["content"] and fake.calls[0]["system"][0]["cache_control"])
            fake2 = Fake([copy.deepcopy(SET)])
            st2 = await gl.run_job(fake2, "claude-opus-5-5", db, gl.setting_job("numeracy", "village market"), root, man, [0.0], 3.0, log=lambda *a: None)
            check("an anchor setting is written under its subject and theme", st2 == "ok" and (root / "setting" / "numeracy__village_market.json").is_file())

            print("\nMessage Batches (a fake API: no network)")
            sent = {}

            def api(request: httpx.Request):
                if request.method == "POST":
                    sent["body"] = json.loads(request.content)
                    sent["headers"] = dict(request.headers)
                    return httpx.Response(200, json={"id": "msgbatch_test1", "processing_status": "in_progress"})
                if request.url.path.endswith("/msgbatch_test1"):
                    return httpx.Response(200, json={"id": "msgbatch_test1", "processing_status": sent.get("status", "in_progress"),
                                                     "results_url": "https://api.anthropic.com/v1/messages/batches/msgbatch_test1/results", "request_counts": {}})
                if request.url.path.endswith("/results"):
                    return httpx.Response(200, text="\n".join(json.dumps(x, ensure_ascii=False) for x in sent["results"]))
                return httpx.Response(404)

            http = httpx.AsyncClient(transport=httpx.MockTransport(api))
            jobs = [gl.independent_job(s231, 2), gl.independent_job(s232, 1), gl.independent_job(s232, 2)]
            bid = await lb.submit(jobs, root, man, "claude-opus-5-5", "sk-test", 40.0, http=http, log=lambda *a: None)
            reqs = sent["body"]["requests"]
            check("one batch for the 3 pieces, each with a safe custom id and the app's cached system rules",
                  bid == "msgbatch_test1" and len(reqs) == 3 and all(r["custom_id"].startswith("p") and "." not in r["custom_id"] for r in reqs)
                  and reqs[0]["params"]["system"][0]["cache_control"] == {"type": "ephemeral"} and reqs[0]["params"]["output_config"] == {"effort": "low"})
            check("the API version header and key are sent", sent["headers"].get("anthropic-version") == "2023-06-01" and sent["headers"].get("x-api-key") == "sk-test")
            man2 = gl.load_manifest(root)
            check("the batch is saved in the manifest with its map (so a new session can collect it)",
                  man2["batches"][-1]["id"] == "msgbatch_test1" and len(man2["batches"][-1]["map"]) == 3 and man2["batches"][-1]["status"] == "submitted")
            args = SimpleNamespace(redo=False, max_usd=40.0)
            await lb.collect(db, root, man2, args, plan_service, "sk-test", http=http, anthropic_client=Fake([]), log=lambda *a: None)
            check("not ended yet: nothing collected, the batch stays open", gl.load_manifest(root)["batches"][-1]["status"] == "submitted")
            ids = {r["params"]["messages"][0]["content"][:0] or r["custom_id"]: r for r in reqs}
            cid = [r["custom_id"] for r in reqs]
            usage = {"input_tokens": 4000, "output_tokens": 1000}
            badp = copy.deepcopy(IND)
            badp["extras_hi"] = ["x"]
            sent["status"] = "ended"
            sent["results"] = [
                {"custom_id": cid[0], "result": {"type": "succeeded", "message": {"content": [{"type": "text", "text": json.dumps(IND, ensure_ascii=False)}], "usage": usage}}},
                {"custom_id": cid[1], "result": {"type": "succeeded", "message": {"content": [{"type": "text", "text": json.dumps(badp, ensure_ascii=False)}], "usage": usage}}},
                {"custom_id": cid[2], "result": {"type": "errored", "error": {"type": "overloaded_error"}}}]
            retry = Fake([copy.deepcopy(IND), copy.deepcopy(IND)])
            man3 = gl.load_manifest(root)
            counts = await lb.collect(db, root, man3, args, plan_service, "sk-test", http=http, anthropic_client=retry, log=lambda *a: None)
            m4 = gl.load_manifest(root)
            check("collected: the good reply written at half price, the failed one and the errored one asked again by a normal call",
                  counts.get("ok") == 3 and len(retry.calls) == 2 and m4["batches"][-1]["status"] == "collected", (counts, len(retry.calls)))
            check("...the failed one's normal call carries the batch's rejection reasons", "AN EARLIER ATTEMPT WAS REJECTED" in retry.calls[0]["messages"][0]["content"])
            half = gl.cost_of("claude-opus-5-5", usage) * 0.5
            check("...and the batch piece's cost is the half price", abs(m4["pieces"]["N2.3.1__2"]["cost_usd"] - round(half, 4)) < 1e-6, m4["pieces"]["N2.3.1__2"]["cost_usd"])
            await http.aclose()
            man5 = gl.load_manifest(root)
            man5["pieces"]["x"] = {"kind": "teach", "status": "ok", "cost_usd": 39.9, "model": "claude-opus-5-5"}
            check("over the cap: the batch is not submitted", await lb.submit([gl.independent_job(s231, 1)], root, man5, "claude-opus-5-5", "sk-test", 40.0, http=httpx.AsyncClient(transport=httpx.MockTransport(api)), log=lambda *a: None) is None)
        await db.execute("DELETE FROM ai_usage WHERE kind = 'library' AND teacher_id IS NULL AND created_at > now() - interval '5 minutes' AND input_tokens = 4000 AND output_tokens = 1000")

        print("\nthe daily caps are for teachers: the library job does not use them up")
        from app.services import ai_budget

        class Rollback(Exception):
            pass
        try:
            async with db.transaction():
                await db.execute("INSERT INTO ai_usage (kind, model, input_tokens, output_tokens) VALUES ('library', 'claude-opus-5-5', 0, 3000000)")   # $30 at the meter's price
                try:
                    await ai_budget.check(db, None, "plan")
                    check("a $30 library job today: a teacher's call is still allowed", True)
                except ai_budget.AICapReached as e:
                    check("a $30 library job today: a teacher's call is still allowed", False, e.reason)
                await db.execute("INSERT INTO ai_usage (kind, model, input_tokens, output_tokens) VALUES ('plan', 'claude-sonnet-5-5', 0, 3000000)")    # $30 of plans
                try:
                    await ai_budget.check(db, None, "plan")
                    check("...but $30 of teachers' plans today reaches the daily cap", False)
                except ai_budget.AICapReached as e:
                    check("...but $30 of teachers' plans today reaches the daily cap", e.reason == "global_daily", e.reason)
                raise Rollback()
        except Rollback:
            pass
    finally:
        await db.close()


asyncio.run(main())
if failures:
    print(f"\nFAILED ({len(failures)})")
    sys.exit(1)
print("\nOK: independent activities, anchor settings and tasks are checked; the general path and the batch path make, check and record them")
