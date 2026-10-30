"""
The "Teaching and Learning Resources" item of the plan's "Why this plan?" panel, built in CODE.

The AI used to write the item about the retrieved content, and its wording was hard to follow. Everything the item says is already
known to the code (the anchor and how well it matched, the re-teach template, the kits, each group's skill), so it is written from
those facts and never by the model. The same function serves a plan the AI wrote and a recorded sample plan.
"""
import re

ITEM_ID = "resources"
_CODE = re.compile(r"\b(?:ANC|INT|TLM)-[A-Z0-9-]+")
_DEVANAGARI = re.compile(r"[ऀ-ॿ]")
STICKS_ID = "TLM-001"
TEACHER_KIT_STICKS = 99          # orchestrate.STICK_TEACHER_KIT_TOTAL; passed in so this module stays free of imports


def _anchor_line(anchor, numeracy: bool):
    if anchor is None:
        return None
    today_hi = "आज की संख्याओं" if numeracy else "आज के कौशल"
    today_en = "today's numbers" if numeracy else "today's skill"
    t_hi, t_en = anchor.title_hi, anchor.title_en
    if anchor.match_quality == "exact":
        return (f"एंकर गतिविधि (पूरी कक्षा के लिए): «{t_hi}» इसी कौशल के लिए लिखी गई थी; इसे {today_hi} के हिसाब से ढाला गया।",
                f"Anchor activity (whole class): '{t_en}' was written for this very skill; it was adapted to {today_en}.")
    if anchor.match_quality == "semantic":
        return (f"एंकर गतिविधि (पूरी कक्षा के लिए): «{t_hi}» इस कौशल के लिए नहीं लिखी गई थी; अर्थ में सबसे पास होने से चुनी गई, और {today_hi} के हिसाब से ढाली गई।",
                f"Anchor activity (whole class): '{t_en}' was not written for this skill; it was chosen as the nearest in meaning, and adapted to {today_en}.")
    if anchor.match_quality in ("related", "topic_area"):
        return (f"एंकर गतिविधि (पूरी कक्षा के लिए): «{t_hi}» किसी जुड़े हुए कौशल के लिए लिखी गई थी, इसी कौशल के लिए नहीं; इसे {today_hi} के हिसाब से ढाला गया।",
                f"Anchor activity (whole class): '{t_en}' was written for a related skill, not this one; it was adapted to {today_en}.")
    return (f"एंकर गतिविधि (पूरी कक्षा के लिए): इस कौशल के लिए कोई मेल खाती गतिविधि नहीं थी; «{t_hi}» की सिर्फ़ कहानी का रूप लेकर नई गतिविधि बनाई गई।",
            f"Anchor activity (whole class): no activity matched this skill; a new one was made, keeping only the setting of '{t_en}'.")


def build_resources_item(ctx, teacher_kit_sticks: int = TEACHER_KIT_STICKS):
    """The item (title_hi, title_en, body_hi, body_en) from the facts in the OrchestrationContext."""
    numeracy = ctx.domain_id == "numeracy"
    hi, en = [], []
    a = _anchor_line(ctx.anchor, numeracy)
    if a:
        hi.append(a[0]); en.append(a[1])

    sticks = ctx.stick_policy
    itv = ctx.intervention
    beg, pro, prof = ctx.beginner.target_competency, ctx.progressor.target_competency, ctx.proficient.target_competency
    hi.append("हर समूह के लिए:"); en.append("For each group:")

    kits = (sticks or {}).get("pair_kits", 0)
    if sticks and kits:
        b_hi, b_en = "बंडल की छड़ियों के जोड़ी-किट से हाथ से सीखना।", "hands-on learning with the stick pair kits."
    else:
        b_hi, b_en = "अपने स्तर की वर्कशीट पर अभ्यास।", "practice on a worksheet at their own level."
    hi.append(f"• शुरुआती («{beg.name_hi}»): {b_hi}"); en.append(f"• Beginners ('{beg.name_en}'): {b_en}")

    if itv:
        p_hi = f"«{itv.title_hi}» के चरण I Do और We Do का आधार हैं; इसके बाद You Do में वर्कशीट पर स्वतंत्र अभ्यास होता है, ताकि अवधारणा स्पष्ट हो और गलतियाँ रुकें।"
        p_en = f"the steps of '{itv.title_en}' form the basis for I Do and We Do, followed by You Do (worksheet practice) to build conceptual clarity and prevent errors."
    else:
        p_hi = "I Do और We Do के बाद You Do में वर्कशीट पर स्वतंत्र अभ्यास होता है, ताकि अवधारणा स्पष्ट हो और गलतियाँ रुकें।"
        p_en = "I Do and We Do, followed by You Do (worksheet practice) to build conceptual clarity and prevent errors."
    hi.append(f"• प्रगतिशील («{pro.name_hi}»): {p_hi}"); en.append(f"• Progressors ('{pro.name_en}'): {p_en}")

    if sticks:
        d_hi, d_en = "बिना छड़ियों के, बोर्ड पर लिखित तरीके से अभ्यास।", "practice with the written method on the board, no sticks."
    else:
        d_hi, d_en = "बोर्ड पर और वर्कशीट पर लिखित अभ्यास।", "written practice on the board and the worksheet."
    hi.append(f"• दक्ष («{prof.name_hi}»): {d_hi}"); en.append(f"• Proficients ('{prof.name_en}'): {d_en}")

    others = [t for t in (ctx.available_tlms or []) if t.id != STICKS_ID]
    if sticks:
        m_hi = f"बंडल की छड़ियाँ: शिक्षक के लिए {teacher_kit_sticks} छड़ियों का किट" + (f" और शुरुआती समूह के लिए {kits} जोड़ी-किट।" if kits else "।")
        m_en = f"Bundling sticks: a teacher demo kit of {teacher_kit_sticks} sticks" + (f" and {kits} pair kits for the Beginners." if kits else ".")
        if others:
            m_hi = m_hi.rstrip("।") + "; " + ", ".join(t.name_hi for t in others) + "।"
            m_en = m_en.rstrip(".") + "; " + ", ".join(t.name_en for t in others) + "."
        hi.append(f"सामग्री (तैयारी): {m_hi}"); en.append(f"Materials (to prepare): {m_en}")
    elif others:
        hi.append("सामग्री (तैयारी): " + ", ".join(t.name_hi for t in others) + "।")
        en.append("Materials (to prepare): " + ", ".join(t.name_en for t in others) + ".")

    note = (ctx.week_notes or "").strip()
    if note and not _DEVANAGARI.search(note):          # the state plan's note is English in most weeks: shown in the English text only
        en.append(f"State plan note: {note}")

    codes = [x for x in (ctx.anchor.id if ctx.anchor else None, itv.id if itv else None) if x]
    codes += [t.id for t in ([t for t in (ctx.available_tlms or []) if t.id == STICKS_ID] if sticks else []) + others]
    if codes:
        line = " · ".join(codes)
        hi.append(f"(कोड: {line})"); en.append(f"(Codes: {line})")

    return {"id": ITEM_ID, "title_hi": "शिक्षण और सीखने की सामग्री", "title_en": "Teaching and Learning Resources",
            "body_hi": "\n".join(hi), "body_en": "\n".join(en)}


def put_resources_item(plan: dict, item: dict) -> str:
    """Replace the AI's own item about the retrieved content (it names ANC-/INT-/TLM- codes) with the built one, in the same place; else add it."""
    ex = plan.get("explainability")
    if not isinstance(ex, dict):
        ex = plan["explainability"] = {}
    items = ex.get("items")
    if not isinstance(items, list):
        items = ex["items"] = []
    kept, at = [], None
    for it in items:
        text = " ".join(str(it.get(k) or "") for k in ("title_hi", "title_en", "body_hi", "body_en")) if isinstance(it, dict) else ""
        if isinstance(it, dict) and (it.get("id") == ITEM_ID or _CODE.search(text)):
            if at is None:
                at = len(kept)
            continue
        kept.append(it)
    removed = len(items) - len(kept)
    kept.insert(len(kept) if at is None else at, item)
    ex["items"] = kept
    return f"built in code (replaced {removed} written by the model)" if removed else "built in code (added)"
