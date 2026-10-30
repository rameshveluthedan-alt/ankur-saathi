"""
"Why this plan?" > "Teaching and Learning Resources": the item about the content used is built in CODE from the retrieved facts (anchor and its match,
re-teach template, kits, each group's skill, the state plan's note), not written by the AI. It replaces the AI's own item (the one that names ANC-/INT-/TLM-
codes) in the same place, for an AI plan and for a recorded sample plan alike. The AI is a fake: no paid call.

    cd backend && AUTH_MODE=off python tests/test_resources_item.py --env-file .env
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import asyncio
import contextlib
import copy
import io
import json
import os
import re
import sys
from datetime import date, timedelta
from types import SimpleNamespace as NS

os.environ.setdefault("AUTH_MODE", "off")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "prompts"))
import _scratch
import anthropic
from app.services import ai_budget, plan_service
from app.services.resources_item import build_resources_item, put_resources_item

TODAY = date.today()
failures = []
SAMPLE = json.load(open(os.path.join(HERE, "..", "..", "db", "seeds", "sample_plans", "N2.3.2.json"), encoding="utf-8"))


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


def comp(hi, en):
    return NS(name_hi=hi, name_en=en)


def ctx(**kw):
    base = dict(
        domain_id="numeracy",
        anchor=NS(id="ANC-N-001", title_hi="गाँव का बाज़ार", title_en="Village Market Story", match_quality="exact"),
        intervention=NS(id="INT-OP-005", title_hi="हासिल पुनःशिक्षण (बंडल से)", title_en="Carry-over Re-teaching with Bundling"),
        available_tlms=[NS(id="TLM-001", name_hi="बंडल की छड़ियाँ", name_en="Bundling sticks")],
        stick_policy={"beginner_children": 5, "pair_kits": 3},
        week_notes=None,
        beginner=NS(target_competency=comp("बिना हासिल वाला जोड़", "addition without carrying")),
        progressor=NS(target_competency=comp("हासिल वाला जोड़", "addition with carrying")),
        proficient=NS(target_competency=comp("3 अंकों का जोड़", "3-digit addition")),
    )
    base.update(kw)
    return NS(**base)


def lines(item, lang):
    return item["body_" + lang].split("\n")


def unit():
    print("the item's text, from the facts")
    it = build_resources_item(ctx(), 99)
    check("titled 'शिक्षण और सीखने की सामग्री' / 'Teaching and Learning Resources'", it["title_hi"] == "शिक्षण और सीखने की सामग्री" and it["title_en"] == "Teaching and Learning Resources")
    hi, en = lines(it, "hi"), lines(it, "en")
    check("an exact anchor: named, 'written for this very skill', adapted to today's numbers",
          hi[0] == "एंकर गतिविधि (पूरी कक्षा के लिए): «गाँव का बाज़ार» इसी कौशल के लिए लिखी गई थी; इसे आज की संख्याओं के हिसाब से ढाला गया।"
          and en[0] == "Anchor activity (whole class): 'Village Market Story' was written for this very skill; it was adapted to today's numbers.", hi[0])
    check("all three groups are named with their own skill", all(any(s in l for l in hi) for s in ("शुरुआती («बिना हासिल वाला जोड़»)", "प्रगतिशील («हासिल वाला जोड़»)", "दक्ष («3 अंकों का जोड़»)"))
          and all(any(s in l for l in en) for s in ("Beginners ('addition without carrying')", "Progressors ('addition with carrying')", "Proficients ('3-digit addition')")))
    check("Beginners: the stick pair kits; Proficients: no sticks", any("शुरुआती" in l and "जोड़ी-किट" in l for l in hi) and any("दक्ष" in l and "बिना छड़ियों के" in l for l in hi))
    check("Progressors: the re-teach template's steps are the I Do and We Do, then You Do on the worksheet",
          any("प्रगतिशील" in l and "«हासिल पुनःशिक्षण (बंडल से)» के चरण I Do और We Do" in l and "You Do" in l for l in hi)
          and any("Progressors" in l and "'Carry-over Re-teaching with Bundling'" in l and "You Do" in l for l in en))
    check("materials: the teacher kit (99 sticks) and the Beginners' pair kits (3)", any(l.startswith("सामग्री (तैयारी): बंडल की छड़ियाँ: शिक्षक के लिए 99 छड़ियों का किट और शुरुआती समूह के लिए 3 जोड़ी-किट") for l in hi)
          and any(l.startswith("Materials (to prepare): Bundling sticks: a teacher demo kit of 99 sticks and 3 pair kits for the Beginners") for l in en))
    check("the codes line ends the item: ANC-N-001 · INT-OP-005 · TLM-001", hi[-1] == "(कोड: ANC-N-001 · INT-OP-005 · TLM-001)" and en[-1] == "(Codes: ANC-N-001 · INT-OP-005 · TLM-001)")
    check("no state plan note, no line for it", not any("State plan note" in l for l in en))

    n = build_resources_item(ctx(stick_policy={"beginner_children": 0, "pair_kits": 0}), 99)
    check("sticks but no Beginner child: only the teacher kit is listed (no '0 pair kits')", "जोड़ी-किट" not in "\n".join(l for l in lines(n, "hi") if l.startswith("सामग्री")) and "0 pair kits" not in n["body_en"])

    print("\nthe state plan's note")
    en_note = build_resources_item(ctx(week_notes="Use concrete objects before symbols."), 99)
    check("an English note: in the English text only, as a line before the codes", lines(en_note, "en")[-2] == "State plan note: Use concrete objects before symbols." and "Use concrete objects" not in en_note["body_hi"])
    hi_note = build_resources_item(ctx(week_notes="ठोस वस्तुओं से शुरू करें।"), 99)
    check("a note already in Hindi is not copied into the English text", "State plan note" not in hi_note["body_en"] and "ठोस वस्तुओं" not in hi_note["body_en"])

    print("\nwhen the facts differ")
    for q, word_hi, word_en in (("related", "जुड़े हुए कौशल", "a related skill"), ("topic_area", "जुड़े हुए कौशल", "a related skill"),
                                ("semantic", "अर्थ में सबसे पास", "nearest in meaning"), ("loose", "कोई मेल खाती गतिविधि नहीं", "no activity matched")):
        a = NS(id="ANC-X", title_hi="कहानी", title_en="A story", match_quality=q)
        it = build_resources_item(ctx(anchor=a), 99)
        check(f"a {q} anchor is said to be {q}, never 'written for this very skill'", word_hi in lines(it, "hi")[0] and word_en in lines(it, "en")[0] and "इसी कौशल के लिए लिखी गई" not in lines(it, "hi")[0] and "very skill" not in lines(it, "en")[0], lines(it, "hi")[0])
    it = build_resources_item(ctx(anchor=None, intervention=None, stick_policy=None, available_tlms=[]), 99)
    check("no anchor, no template, no kit: no anchor line, no materials line, no empty codes line", not any("एंकर" in l or l.startswith("सामग्री") or "कोड" in l for l in lines(it, "hi")) and lines(it, "hi")[0] == "हर समूह के लिए:")
    check("...and no sticks claim for Proficients or Beginners", not any("छड़ि" in l for l in lines(it, "hi")))
    it = build_resources_item(ctx(domain_id="r1_literacy", stick_policy=None), 99)
    check("a literacy plan says 'today's skill', not 'today's numbers'", "आज के कौशल" in lines(it, "hi")[0] and "skill" in lines(it, "en")[0] and "संख्याओं" not in lines(it, "hi")[0])
    other = ctx(available_tlms=[NS(id="TLM-001", name_hi="बंडल की छड़ियाँ", name_en="Bundling sticks"), NS(id="TLM-007", name_hi="संख्या कार्ड", name_en="Number cards")])
    it = build_resources_item(other, 99)
    check("another kit the skill uses is listed in the materials and the codes", "संख्या कार्ड" in it["body_hi"] and "Number cards" in it["body_en"] and lines(it, "hi")[-1].endswith("TLM-001 · TLM-007)"), it["body_hi"])

    print("\nputting it in the plan")
    item = build_resources_item(ctx(), 99)
    plan = {"explainability": {"items": [{"title_hi": "समूह", "title_en": "Groups", "body_hi": "x", "body_en": "x"},
                                         {"title_hi": "सामग्री", "title_en": "Content", "body_hi": "ANC-N-001 का उपयोग", "body_en": "used ANC-N-001, INT-OP-005"},
                                         {"title_hi": "गलतियाँ", "title_en": "Mistakes", "body_hi": "M3", "body_en": "M3"}]}}
    note = put_resources_item(plan, item)
    its = plan["explainability"]["items"]
    check("the AI's item that names the codes is replaced IN PLACE (3 items still, ours second), the others are kept", len(its) == 3 and its[1]["id"] == "resources" and its[0]["title_en"] == "Groups" and its[2]["title_en"] == "Mistakes", [i["title_en"] for i in its])
    check("...and the note says so", "replaced 1" in note, note)
    put_resources_item(plan, item)
    check("done twice, still one resources item", sum(1 for i in plan["explainability"]["items"] if i.get("id") == "resources") == 1 and len(plan["explainability"]["items"]) == 3)
    bare = {}
    put_resources_item(bare, item)
    check("a plan with no explainability at all gets one with the item", bare["explainability"]["items"] == [item])
    odd = {"explainability": {"items": ["not a dict", {"title_en": "ok"}]}}
    put_resources_item(odd, item)
    check("odd entries in the AI's list do not break it", len(odd["explainability"]["items"]) == 3)


async def flow():
    print("\nthrough plan generation (the AI is a fake)")
    db = await _scratch.connect()
    levels = {1: "beginner", 2: "beginner", 3: "progressor", 4: "progressor", 5: "progressor", 6: "proficient", 7: "proficient"}
    teacher_id, school = await _scratch.make_class(db, {r: (lv, lv) for r, lv in levels.items()}, grade="grade_2")
    ai_text = copy.deepcopy(SAMPLE)
    ai_text["explainability"]["items"].insert(3, {"title_hi": "इस्तेमाल की गई सामग्री", "title_en": "Content used", "body_hi": "ANC-N-001 को INT-OP-005 के साथ", "body_en": "ANC-N-001 and INT-OP-005"})

    code = re.compile(r"\b(?:ANC|INT|TLM)-[A-Z0-9-]+")
    kept_titles = [i["title_en"] for i in ai_text["explainability"]["items"] if not code.search(json.dumps(i, ensure_ascii=False))]
    check("(the fixture: the recorded plan already has one item naming codes, and the extra one added here makes two: both are the 'content used' item)", len(kept_titles) == len(ai_text["explainability"]["items"]) - 2)

    class Fake:
        async def create(self, **kw):
            return NS(content=[NS(type="text", text=json.dumps(ai_text, ensure_ascii=False))], stop_reason="end_turn", usage=NS(input_tokens=6000, output_tokens=9000))
    real_client = anthropic.AsyncAnthropic
    anthropic.AsyncAnthropic = lambda **kw: NS(messages=Fake())
    try:
        async def stored(day):
            row = await db.fetchrow("SELECT plan_content, explainability FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2 AND domain_id = 'numeracy'", teacher_id, day)
            f = lambda v: json.loads(v) if isinstance(v, str) else v
            return f(row["plan_content"]), f(row["explainability"])
        with contextlib.redirect_stdout(io.StringIO()):
            await plan_service.generate_dainik_yojana(db, teacher_id, "N2.3.2", "numeracy", TODAY)
        pc, ex = await stored(TODAY)
        for label, e in (("the plan", pc["explainability"]), ("the explainability column", ex)):
            items = e["items"]
            res = [i for i in items if i.get("id") == "resources"]
            check(f"{label}: exactly one 'Teaching and Learning Resources' item, and the model's own content item is gone", len(res) == 1 and len(items) == len(kept_titles) + 1 and not any("Content used" == i.get("title_en") for i in items), [i.get("title_en") for i in items])
        res = [i for i in pc["explainability"]["items"] if i.get("id") == "resources"][0]
        check("it sits where the model's item was (4th)", pc["explainability"]["items"][3] is not None and pc["explainability"]["items"][3].get("id") == "resources")
        check("it is built from this class: 2 Beginners -> 1 pair kit, a 99-stick teacher kit, and the codes of what was retrieved",
              "99 छड़ियों का किट और शुरुआती समूह के लिए 1 जोड़ी-किट" in res["body_hi"] and "ANC-" in res["body_hi"].split("(कोड:")[-1] and "TLM-001" in res["body_hi"].split("(कोड:")[-1], res["body_hi"])
        check("...the other items the model wrote are untouched", [i["title_en"] for i in pc["explainability"]["items"] if i.get("id") != "resources"] == kept_titles)

        real_check = ai_budget.check
        async def cap(*a, **k):
            raise ai_budget.AICapReached("disabled")
        ai_budget.check = cap
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                res2 = await plan_service.generate_dainik_yojana(db, teacher_id, "N2.3.2", "numeracy", TODAY + timedelta(days=1))
        finally:
            ai_budget.check = real_check
        pc2, _ = await stored(TODAY + timedelta(days=1))
        its2 = pc2["explainability"]["items"]
        check("a recorded sample plan (AI limit reached) gets the same built item, exactly once", res2["served_from"] == "sample" and sum(1 for i in its2 if i.get("id") == "resources") == 1, res2["served_from"])
    finally:
        anthropic.AsyncAnthropic = real_client
        await _scratch.remove_class(db, teacher_id, school)
        await db.close()


if __name__ == "__main__":
    unit()
    asyncio.run(flow())
    print(f"\n{'ALL OK' if not failures else str(len(failures)) + ' FAILED'}")
    sys.exit(1 if failures else 0)
