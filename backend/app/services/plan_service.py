"""
Ankur Saathi — Plan Service
Business logic for competency tree, curriculum week, and Dainik Yojana generation.
Wraps the orchestrate.py pipeline with proper error handling and DB access.
"""

import json
import random
import re
import time
from collections import Counter
from datetime import date
from typing import Optional

import anthropic

from app.core.config import get_settings
from app.core.database import get_db
from app.services import ai_budget
from app.services.sampling import sample_for_group
from app.services.cfu import clean_plan_cfu, strip_cfu, MIN_ITEMS, right_answer as _cfu_right_answer, _avoid_for as _cfu_lesson_ops
from app.services.model_json import parse_model_json, ModelJSONError
from app.services import group_skills as _group_skills
from app.services.resources_item import build_resources_item, put_resources_item
from app.services.hindi_numbers import find_number_word_errors, find_numeric_overlaps, repair_place_value

# Import the orchestration module (copied from prompts/ into services/ or added to path)
import copy
from dataclasses import asdict
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'prompts'))
import hindi_style
from orchestrate import choose_reteach_group, pick_priority_group
from orchestrate import (
    OrchestrationContext, Competency, GroupInfo, Prerequisite,
    Misconception, AnchorTemplate, InterventionTemplate, TLMRef,
    build_system_prompt, build_user_prompt,
    fetch_competency, fetch_prerequisite_chain, fetch_misconceptions,
    fetch_anchor_activity, fetch_intervention, fetch_tlms, fetch_tlms_for_competencies,
    STICK_PAIR_KIT_TOTAL, STICK_TEACHER_KIT_TOTAL,
)
from baseline_assessment import compute_groups


# Claude Sonnet 5.5 runs adaptive thinking by default, and thinking tokens share
# max_tokens with the answer. At default effort, plan generation used all 16,000
# tokens on thinking and never wrote the plan. "between_tools" turns off up-front
# thinking (documented for Sonnet 5.5; "disabled" returns a 400 on this model).
# Sent via extra_body because the pinned SDK (0.34.0) predates this parameter.
# To test thinking later, try:
#   {"thinking": {"type": "adaptive"}, "output_config": {"effort": "medium"}}
CLAUDE_THINKING_BODY = {"thinking": {"type": "between_tools"}}


_STICK_WORDS = ("छड़ी", "छड़ियों", "छड़ियाँ")
_SUM_RE = re.compile(r"(\d{1,3})\s*\+\s*(\d{1,3})")
_STATED_SUM_RE = re.compile(r"(\d{1,3})\s*\+\s*(\d{1,3})\s*=\s*(\d{1,3})")
_TALK_KEYS = ("i_do_hi", "we_do_hi", "you_do_hi")


def _teach_blocks(plan: dict) -> list:
    return [b for b in ((plan.get("rotation_schedule") or {}).get("blocks") or []) if b.get("type") == "teach"]


def _stick_cap(group: str, key: str) -> int:
    """What children (Beginner We Do / You Do) build must fit a pair kit; the teacher's demo fits the teacher kit."""
    return STICK_PAIR_KIT_TOTAL if (group == "beginner" and key != "i_do_hi") else STICK_TEACHER_KIT_TOTAL


def _uses_sticks(plan: dict) -> bool:
    return any(any(w in ((b.get("talking_points") or {}).get(k) or "") for w in _STICK_WORDS)
               for b in _teach_blocks(plan) for k in _TALK_KEYS)


def find_stick_overflows(plan: dict) -> list[dict]:
    """Talking points that build an example with sticks which is bigger than the kit holds."""
    out = []
    for b in _teach_blocks(plan):
        group, tp = b.get("teach_group"), b.get("talking_points") or {}
        if group not in ("beginner", "progressor"):
            continue            # Proficients use no sticks (policy), so their sums are never stick examples
        for key in _TALK_KEYS:
            text = tp.get(key) or ""
            if not any(w in text for w in _STICK_WORDS):
                continue
            totals = [int(a) + int(c) for a, c in _SUM_RE.findall(text)]
            cap = _stick_cap(group, key)
            if totals and max(totals) > cap:
                out.append({"group": group, "key": key, "text": text, "largest": max(totals), "cap": cap})
    return out


def _pairs_in(text: str) -> set:
    return {tuple(sorted((int(a), int(c)))) for a, c in _SUM_RE.findall(text or "")}


def _max_digits(text: str) -> int:
    return max((len(str(n)) for a, c in _SUM_RE.findall(text or "") for n in (int(a), int(c))), default=0)


def _fix_is_acceptable(group: str, key: str, old: str, new: str, avoid: set) -> tuple[bool, str]:
    """A rewritten talking point is used only if it passes checks that do not depend on the model."""
    if not isinstance(new, str) or not new.strip():
        return False, "empty"
    if not any(w in new for w in _STICK_WORDS):
        return False, "no longer mentions the sticks"
    if not 0.5 * len(old) <= len(new) <= 2.0 * len(old):
        return False, "length changed too much"
    for a, c, r in _STATED_SUM_RE.findall(new):
        if int(a) + int(c) != int(r):
            return False, f"stated sum is wrong ({a} + {c} = {r})"
    if _max_digits(new) < _max_digits(old):
        return False, "the rewrite uses smaller numbers than the original (fewer digits)"
    cap = _stick_cap(group, key)
    pairs = _pairs_in(new)
    if any(a + c > cap for a, c in pairs):
        return False, f"an example still totals more than {cap}"
    if group == "beginner" and any((a % 10 + c % 10) >= 10 for a, c in pairs):
        return False, "a Beginner example needs a carry"
    # only the examples the rewrite INTRODUCES count: one that was already in the text is not the rewrite's doing. (It used to count: the model's first
    # worksheet often copies an example from the We Do, the worksheet is repaired only AFTER this step, and the fix was refused because of the unchanged
    # example, so a 67-stick sum stayed in a lesson whose kit holds 49.)
    if (pairs - _pairs_in(old)) & avoid:
        return False, "uses an example that is already used elsewhere in the lesson"
    return True, "ok"


_PLAIN_ADD_RE = re.compile(r"^\s*(\d{1,3})\s*\+\s*(\d{1,3})\s*(=\s*[_\s]*\??)?\s*$")


def _plain_addition(problem: dict):
    """(a, b, suffix) if the problem is a plain 'a + b' (optionally '= ___'); None for word problems and others."""
    m = _PLAIN_ADD_RE.match(str(problem.get("problem_hi") or ""))
    return (int(m.group(1)), int(m.group(2)), (m.group(3) or "").strip()) if m else None


def _taught_pairs(plan: dict) -> dict:
    """The a + b examples the teacher solves in each group's block (a worksheet problem must not repeat them)."""
    taught = {"beginner": set(), "progressor": set(), "proficient": set()}
    for b in _teach_blocks(plan):
        if b.get("teach_group") in taught:
            for text in (b.get("talking_points") or {}).values():
                taught[b["teach_group"]] |= _pairs_in(str(text))
    return taught


def _gen_addition(level: str, digits: int, rng, used_answers: set, avoid_pairs: set, cap=None, want_ones=None):
    """
    A plain addition of the kind this level practises, correct by construction:
      Beginner (2-digit): no carrying anywhere.   Progressor / Proficient (2-digit): exactly one carry, total stays 2-digit.
      3-digit: at least one carry, total stays 3-digit.
    The answer and the pair must be new; `cap` limits the total (sticks), `want_ones` fixes the ones-column sum.
    """
    lo, hi = (10, 89) if digits == 2 else (100, 899)
    carry_needed = not (level == "beginner" and digits == 2)
    for _ in range(800):
        a, b = rng.randint(lo, hi), rng.randint(lo, hi)
        if a == b or a % 10 == 0 or b % 10 == 0:
            continue                       # no doubles (23 + 23) and no round addends (23 + 10): too easy to teach anything
        ones = a % 10 + b % 10
        if digits == 2:
            tens = a // 10 + b // 10
            if carry_needed:
                if ones < 10 or tens + 1 > 9:
                    continue
            elif ones > 9 or tens > 9:
                continue
        else:
            if not (ones >= 10 or (a // 10) % 10 + (b // 10) % 10 >= 10) or a + b > 999:
                continue
        if want_ones is not None and ones != want_ones:
            continue
        if str(a + b) in used_answers or tuple(sorted((a, b))) in avoid_pairs:
            continue
        if cap is not None and a + b > cap:
            continue
        return a, b
    return None


def repair_worksheet_numbers(plan: dict) -> list[str]:
    """
    Replace plain-addition worksheet problems that (1) copy an example solved in the lesson, (2) repeat an answer
    among the problems every child must do, (3) are too big for the sticks the Beginners use on problems 1-2, or
    (4) on a Beginner or Progressor sheet add two two-digit numbers to a total of 100 or more (found on the second real block: 79 + 21 = 100).
    Replacements are generated in code (so the answer is right by construction), keep the layout fields, are
    deterministic, and avoid every answer and pair already on the sheet. Word problems are never touched.
    """
    log = []
    taught = _taught_pairs(plan)
    uses_sticks = _uses_sticks(plan)
    expl = " ".join(str(it.get(k) or "") for it in ((plan.get("explainability") or {}).get("items") or []) for k in ("body_hi", "body_en"))

    for level in ("beginner", "progressor", "proficient"):
        ws = (plan.get("worksheets") or {}).get(level) or {}
        problems = ws.get("problems") or []
        if not problems:
            continue
        rc = ws.get("required_count")
        rc_ok = isinstance(rc, int) and not isinstance(rc, bool) and 1 <= rc <= len(problems)
        replace = {}
        for i, pr in enumerate(problems):
            pa = _plain_addition(pr)
            if not pa:
                continue
            if tuple(sorted(pa[:2])) in taught[level]:
                replace[i] = "copies an example solved in the lesson"
            elif level == "beginner" and uses_sticks and i < 2 and pa[0] + pa[1] > STICK_PAIR_KIT_TOTAL:
                replace[i] = f"is solved with sticks but totals more than {STICK_PAIR_KIT_TOTAL}"
            elif level in ("beginner", "progressor") and max(pa[0], pa[1]) < 100 and pa[0] + pa[1] >= 100:
                replace[i] = f"its total is {pa[0] + pa[1]}: three-digit numbers are a later (the Proficients') skill"
        seen = {}
        for i, pr in enumerate(problems[:rc] if rc_ok else problems):
            ans = str(pr.get("answer", "")).strip()
            if ans:
                seen.setdefault(ans, []).append(i)
        for ans, idxs in seen.items():
            if len(idxs) < 2:
                continue
            keep = next((i for i in idxs if i not in replace and not _plain_addition(problems[i])), None)   # keep a word problem if there is one
            if keep is None:
                keep = next((i for i in idxs if i not in replace), idxs[0])
            for i in idxs:
                if i != keep and i not in replace and _plain_addition(problems[i]):
                    replace[i] = f"repeats the answer {ans}"
        if not replace:
            continue

        kept = [pr for j, pr in enumerate(problems) if j not in replace]
        used_answers = {str(pr.get("answer", "")).strip() for pr in kept}
        used_pairs = {tuple(sorted(_plain_addition(pr)[:2])) for pr in kept if _plain_addition(pr)}
        ones_used = [(_plain_addition(pr)[0] % 10 + _plain_addition(pr)[1] % 10) for pr in kept if _plain_addition(pr)]
        for i in sorted(replace):
            pr = problems[i]
            a0, b0, suffix = _plain_addition(pr)
            digits = 3 if max(a0, b0) >= 100 else 2
            cap = STICK_PAIR_KIT_TOTAL if (level == "beginner" and uses_sticks and i < 2) else None
            rng = random.Random(f"{level}:{pr.get('number')}:{a0}:{b0}")
            targets = [None]
            if digits == 2 and level != "beginner":          # vary the ones-column sums across the sheet
                targets = [t for t in (10, 15, 16, 17, 18, 13, 11, 14, 12) if t not in ones_used] + [None]
            res = None
            for t in targets:
                res = _gen_addition(level, digits, rng, used_answers, used_pairs | taught[level], cap, t)
                if res:
                    break
            if not res:
                log.append(f"{level} problem {pr.get('number')}: no replacement could be generated; kept as is")
                continue
            a, b = res
            old = str(pr.get("problem_hi"))
            pr["problem_hi"] = f"{a} + {b} {suffix}".strip()
            pr["answer"] = str(a + b)
            used_answers.add(str(a + b))
            used_pairs.add(tuple(sorted((a, b))))
            ones_used.append(a % 10 + b % 10)
            log.append(f"{level} problem {pr.get('number')}: {old.strip()} -> {pr['problem_hi']} ({replace[i]})")
            if re.search(rf"{a0}\s*\+\s*{b0}|{b0}\s*\+\s*{a0}", expl):
                log.append(f"NOTE: 'Why this plan?' mentions {a0} + {b0}, which was just replaced; check that panel")
    return log


def _assign_replacements(group: str, o: dict, avoid: set) -> dict:
    """For every oversized example in a text, pick the replacement IN CODE: right kind, fits the kit, not used elsewhere."""
    mapping = {}
    for m in _SUM_RE.finditer(o["text"]):
        a, b = int(m.group(1)), int(m.group(2))
        old = tuple(sorted((a, b)))
        if a + b <= o["cap"] or old in mapping:
            continue
        rng = random.Random(f"stick:{group}:{o['key']}:{a}:{b}")
        res = _gen_addition(group, 3 if max(a, b) >= 100 else 2, rng, set(), set(avoid) | {tuple(sorted(v)) for v in mapping.values()}, o["cap"])
        if res:
            mapping[old] = res
    return mapping


def _substitute_pairs(text: str, mapping: dict):
    """
    Swap the oversized examples for the assigned ones directly in the text. Returns None when that cannot be done
    safely: if the text spells out steps for another sum, or the old total appears elsewhere, we cannot tell what to change.
    """
    for a, c, r in _STATED_SUM_RE.findall(text):
        if tuple(sorted((int(a), int(c)))) not in mapping:
            return None
    out = text
    for (a, b), (c, d) in mapping.items():
        out = re.sub(rf"(?<!\d)(?:{a}\s*\+\s*{b}|{b}\s*\+\s*{a})\s*=\s*{a + b}(?!\d)", f"{c} + {d} = {c + d}", out)
        out = re.sub(rf"(?<!\d)(?:{a}\s*\+\s*{b}|{b}\s*\+\s*{a})(?!\d)", f"{c} + {d}", out)
        if re.search(rf"(?<!\d){a + b}(?!\d)", out):
            return None
    return out


# Which bank question types fit a skill (a skill not listed accepts any type).
_QTYPE_FOR_SKILL = {"L1.6.1": ("literal",), "L2.6.1": ("literal",), "L2.6.2": ("main_idea",), "L2.6.3": ("inferential",),
                    "L3.6.1": ("inferential",), "L3.6.2": ("cause_effect",), "L3.6.3": ("main_idea",), "L3.6.4": ("fact_opinion",)}
_PASSAGE_COLS = "p.id, p.title_hi, p.passage_hi, p.word_count, p.target_grade, p.license, p.attribution, p.comprehension_questions"


def _questions_for_skill(comp_id: str, raw) -> list:
    qs = json.loads(raw) if isinstance(raw, str) else (raw or [])
    types = _QTYPE_FOR_SKILL.get(comp_id)
    return [{"type": q.get("type"), "question_hi": q["question_hi"], "answer_hi": q.get("answer_hi", "")}
            for q in qs if q.get("question_hi") and (not types or q.get("type") in types)]


async def _pick_passage(db, comp_id: str, plan_date, exclude: set):
    """A passage that lists the competency wins; otherwise one of the competency's grade. Rotates by date, skips `exclude`."""
    rows = await db.fetch(f"""
        SELECT {_PASSAGE_COLS} FROM reading_passages p
        WHERE p.is_active AND (p.fluency_competency_id = $1 OR $1 = ANY(p.comprehension_competency_ids))
        ORDER BY p.id""", comp_id)
    match = "competency"
    if not [r for r in rows if r["id"] not in exclude]:
        rows = await db.fetch(f"""
            SELECT {_PASSAGE_COLS} FROM reading_passages p JOIN competencies c ON c.id = $1
            WHERE p.is_active AND p.target_grade = c.grade_level ORDER BY p.id""", comp_id)
        match = "grade"
    fresh = [r for r in rows if r["id"] not in exclude]
    if not fresh:
        return None, match
    return fresh[plan_date.toordinal() % len(fresh)], match


def _passage_dict(r, comp_id: str, match: str) -> dict:
    return {"id": r["id"], "title": r["title_hi"], "text": r["passage_hi"], "word_count": r["word_count"],
            "attribution": r["attribution"], "license": r["license"], "match": match,
            "questions": _questions_for_skill(comp_id, r["comprehension_questions"])}


async def retrieve_group_passages(db, domain_id: str, targets: dict, plan_date) -> dict:
    """
    Literacy plans: pick each group's worksheet passage from the content bank, deterministically.
    targets = {'progressor': competency_id, 'proficient': competency_id}. The choice rotates by date and two groups never share one.
    Each passage carries the bank's questions that fit the group's skill.
    """
    if domain_id != "r1_literacy":
        return {}
    out, used = {}, set()
    for level, comp_id in targets.items():
        r, match = await _pick_passage(db, comp_id, plan_date, used)
        if r is None:
            r, match = await _pick_passage(db, comp_id, plan_date, set())      # only one passage exists: allow sharing
        if r is None:
            continue
        used.add(r["id"])
        out[level] = _passage_dict(r, comp_id, match)
    return out


async def retrieve_independent_passages(db, domain_id: str, targets: dict, plan_date, exclude: set) -> dict:
    """
    Literacy plans: a text for each group's INDEPENDENT practice (a skill the group has already mastered),
    from the bank, never one of the day's worksheet passages. targets = {'progressor': prior skill, 'proficient': skill}.
    """
    if domain_id != "r1_literacy":
        return {}
    out, used = {}, set(exclude)
    for level, comp_id in targets.items():
        r, match = await _pick_passage(db, comp_id, plan_date, used)
        if r is None:
            continue
        used.add(r["id"])
        out[level] = _passage_dict(r, comp_id, match)
    return out


def _problem_from_bank(q: dict, number: int) -> dict:
    literal = q.get("type") == "literal"
    p = {"number": number, "problem_hi": q["question_hi"], "answer": q.get("answer_hi", ""), "row_type": "plain" if literal else None,
         "answer_type": "box" if literal else "lines", "show_letter_grid": False, "diagnostic_for_misconception": None, "from_bank": True}
    if not literal:
        p["answer_lines"] = 2
    return p


def apply_bank_questions(plan: dict, group_passages: dict) -> list[str]:
    """
    The bank's questions for the passage go FIRST, word for word, with the bank's answers. The model's own questions
    follow, and the sheet keeps its length and its required count (the model's last questions are dropped).
    """
    log = []
    for level, ps in (group_passages or {}).items():
        ws = (plan.get("worksheets") or {}).get(level)
        if not ws or not ps.get("questions") or not ws.get("problems"):
            continue
        have = {str(p.get("problem_hi", "")).strip() for p in ws["problems"]}
        new = [q for q in ps["questions"] if q["question_hi"].strip() not in have]
        if not new:
            continue
        n0 = len(ws["problems"])
        rc = ws.get("required_count")
        R = rc if isinstance(rc, int) and not isinstance(rc, bool) and 1 <= rc <= n0 else n0
        merged = [_problem_from_bank(q, 0) for q in new] + ws["problems"]
        # keep the sheet's length: trim from the end, never dropping a bank question or a diagnostic problem
        k = len(merged) - 1
        while len(merged) > n0 and k >= 0:
            if not merged[k].get("from_bank") and not merged[k].get("diagnostic_for_misconception"):
                merged.pop(k)
            k -= 1
        merged = merged[:n0]
        # the bank questions pushed everything down: a diagnostic problem must stay inside the required zone
        for idx in range(R, len(merged)):
            if merged[idx].get("diagnostic_for_misconception"):
                for jdx in range(R - 1, -1, -1):
                    if not merged[jdx].get("diagnostic_for_misconception") and not merged[jdx].get("from_bank"):
                        merged[idx], merged[jdx] = merged[jdx], merged[idx]
                        break
        for n, pr in enumerate(merged, start=1):
            pr["number"] = n
        ws["problems"] = merged
        log.append(f"{level}: {len(new)} question(s) from the bank placed first")
    return log


_GROUP_HI = {"beginner": "शुरुआती", "progressor": "प्रगतिशील", "proficient": "दक्ष"}


def inject_independent(plan: dict, independent: dict) -> list[str]:
    """Put the independent-practice texts in the plan and in the 'before class' list, so the teacher has them to copy."""
    log = []
    if not independent:
        return log
    plan["independent_passages"] = {lvl: {"id": ps["id"], "title": ps["title"], "text": ps["text"], "questions": ps["questions"][:3]}
                                    for lvl, ps in independent.items()}
    prep = plan.setdefault("prep_hi", [])
    for lvl, ps in independent.items():
        qs = ps["questions"][:3]
        line = (f"{_GROUP_HI.get(lvl, lvl)} समूह के स्वतंत्र अभ्यास के लिए बोर्ड/चार्ट पर पहले से लिखें: «{ps['title']}» ({ps['id']}): {ps['text']}"
                + (" सवाल: " + " ".join(f"{n}) {q['question_hi']}" for n, q in enumerate(qs, 1)) if qs else ""))
        if line not in prep:
            prep.append(line)
        log.append(f"{lvl}: independent practice on {ps['id']} ({ps['match']} match)")
    return log


_PUNCT = re.compile(r"[।?!,.:;\"'‘’“”()\[\]/–—\-]")


def _tokens(text) -> list:
    return _PUNCT.sub(" ", str(text or "")).split()


def _ngrams_ordered(tokens: list, n: int) -> list:
    return [tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def find_text_overlaps(plan: dict, n: int = 5) -> list[str]:
    """
    Literacy: a worksheet question that repeats wording from the group's own lesson or from the anchor lets a child copy.
    Wording that is quoted from the group's passage is expected and ignored.
    """
    issues = []
    anchor = plan.get("anchor") or {}
    blocks = {b.get("teach_group"): b for b in _teach_blocks(plan)}
    for level, ws in (plan.get("worksheets") or {}).items():
        b = blocks.get(level) or {}
        lesson = " ".join(str(v) for v in (b.get("talking_points") or {}).values())
        anchor_text = " ".join(str(anchor.get(k) or "") for k in ("narration_hi", "opening_question_hi", "closing_question_hi", f"{level}_participation_hi"))
        seen = set(_ngrams_ordered(_tokens(lesson + " " + anchor_text), n))
        quoted = set(_ngrams_ordered(_tokens((ws.get("passage_block") or {}).get("text")), n))
        for pr in ws.get("problems") or []:
            hits = [g for g in _ngrams_ordered(_tokens(pr.get("problem_hi")), n) if g in seen and g not in quoted]
            if hits:
                issues.append(f"worksheets.{level} problem {pr.get('number')} repeats wording from the lesson or anchor: \u00ab{' '.join(hits[0])}\u00bb")
    return issues


def inject_passages(plan: dict, group_passages: dict) -> list[str]:
    """The model may paraphrase or invent: the passage that is printed is the one from the content bank."""
    log = []
    for level, ps in (group_passages or {}).items():
        ws = (plan.get("worksheets") or {}).get(level)
        if ws is None:
            continue
        block = {"title": ps["title"], "text": ps["text"], "passage_id": ps["id"]}
        if ps.get("attribution"):
            block["attribution"] = ps["attribution"]
        changed = (ws.get("passage_block") or {}).get("text") != ps["text"]
        ws["passage_block"] = block
        log.append(f"{level}: passage {ps['id']} ({ps['match']} match)" + ("; the model's own text was replaced" if changed else ""))
    if group_passages:
        plan["passages_used"] = {lvl: ps["id"] for lvl, ps in group_passages.items()}
    return log


async def repair_stick_overflows(client, model: str, plan: dict) -> tuple[dict, list[str]]:
    """
    If a talking point builds an example with more sticks than the kit holds, ask the model to rewrite ONLY
    that text. The rewrite is accepted only if _fix_is_acceptable passes. Costs nothing when nothing overflows.
    """
    overflows = find_stick_overflows(plan)
    if not overflows:
        return plan, []

    avoid = {}
    for o in overflows:
        g = o["group"]
        pairs = set()
        for pr in ((plan.get("worksheets") or {}).get(g) or {}).get("problems") or []:
            pairs |= _pairs_in(str(pr.get("problem_hi") or ""))
        for b in _teach_blocks(plan):
            if b.get("teach_group") == g:
                for k, t in (b.get("talking_points") or {}).items():
                    if k != o["key"]:
                        pairs |= _pairs_in(t)
        avoid[(g, o["key"])] = pairs

    assigned = {(o["group"], o["key"]): _assign_replacements(o["group"], o, avoid[(o["group"], o["key"])]) for o in overflows}
    items = []
    for n, o in enumerate(overflows, 1):
        extra = ("The new example must be an addition WITHOUT carrying (the ones digits add to less than 10)."
                 if o["group"] == "beginner" else "Keep the same kind of problem as the original (with a carry if it had one).")
        mp = assigned[(o["group"], o["key"])]
        def _as_written(a, b, text=o["text"]):          # show the old pair in the order the text writes it
            return f"{b} + {a}" if re.search(rf"(?<!\d){b}\s*\+\s*{a}(?!\d)", text) and not re.search(rf"(?<!\d){a}\s*\+\s*{b}(?!\d)", text) else f"{a} + {b}"
        use = "; ".join(f"replace {_as_written(a, b)} with {c} + {d} (total {c + d})" for (a, b), (c, d) in mp.items()) or "choose a new example yourself"
        pairs = ", ".join(f"{a}+{b}" for a, b in sorted(avoid[(o["group"], o["key"])])) or "none"
        items.append(f"ITEM {n}: teach_group={o['group']} key={o['key']}\n"
                     f"Largest stick example now totals {o['largest']}, but the kit holds only {o['cap']} sticks. {extra}\n"
                     f"USE EXACTLY THESE NUMBERS: {use}\n"
                     f"Do not use these pairs, in either order (already used elsewhere in this lesson): {pairs}\n"
                     f"TEXT:\n{o['text']}")
    user = ("Each talking point below (Hindi, for a teacher) builds an example with sticks that is too big for the kit.\n"
            "Rewrite each text IN HINDI. Keep the same wording, steps and structure. Replace only the oversized example, "
            "and the numbers that depend on it, using exactly the numbers given for that item. Keep every other sentence unchanged. "
            "Any sum you write (a + b = c) must be arithmetically correct.\n"
            'Return JSON only: {"fixes":[{"teach_group":"...","key":"...","text":"..."}]}\n\n' + "\n\n".join(items))
    data, model_note = {}, ""
    try:
        await ai_budget.guard("plan_repair")                      # over the AI limit: skip the repair (the plan is still valid)
        response = await client.messages.create(
            model=model, max_tokens=2500,
            system="You make one small correction to a teacher's talking point in a Hindi lesson plan. Output JSON only.",
            messages=[{"role": "user", "content": user}],
            extra_body=CLAUDE_THINKING_BODY,
        )
        text = next((b.text for b in response.content if getattr(b, "type", None) == "text"), "")
        print(f"   Stick repair call: usage={response.usage}")
        await ai_budget.record_ctx("plan_repair", model, response.usage)
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            a_, b_ = text.find("{"), text.rfind("}")
            data = json.loads(text[a_:b_ + 1]) if a_ != -1 and b_ > a_ else {}
    except Exception as e:
        model_note = f"model call failed ({type(e).__name__})"

    log = []
    fixes = {(fx.get("teach_group"), fx.get("key")): fx.get("text") for fx in (data.get("fixes") or []) if isinstance(fx, dict)}
    for o in overflows:
        key = (o["group"], o["key"])
        new, how, why = None, "", model_note
        if key in fixes:
            ok, why = _fix_is_acceptable(key[0], key[1], o["text"], fixes[key], avoid[key])
            if ok:
                new, how = fixes[key].strip(), "rewritten by the model"
        if new is None and assigned[key]:                       # the model failed or was rejected: swap the example in code
            sub_text = _substitute_pairs(o["text"], assigned[key])
            if sub_text:
                ok2, why2 = _fix_is_acceptable(key[0], key[1], o["text"], sub_text, avoid[key])
                if ok2:
                    new, how = sub_text, f"example replaced in code ({why or 'no usable model rewrite'})"
                else:
                    why = why2
            else:
                why = (why + "; " if why else "") + "the text has other steps that depend on the example"
        if new is None:
            log.append(f"{key[0]}.{key[1]}: kept the original ({why})")
            continue
        for b in _teach_blocks(plan):
            if b.get("teach_group") == key[0]:
                b["talking_points"][key[1]] = new
        log.append(f"{key[0]}.{key[1]}: {how}; largest stick example {o['largest']} -> {max(a + c for a, c in _pairs_in(new))} (kit {o['cap']})")
    return plan, log


def validate_plan_shape(plan: dict, domain_id: str = None) -> list[str]:
    """
    Check Claude's plan against the shape the PWA, worksheet renderer and Vision
    analysis read. Returns human-readable problems (empty list = good).
    The plan is stored either way so generation cost is never lost.
    """
    issues = []
    levels = ("beginner", "progressor", "proficient")

    anchor = plan.get("anchor") or {}
    for k in ("narration_hi", "opening_question_hi", "closing_question_hi",
              "beginner_participation_hi", "progressor_participation_hi",
              "proficient_participation_hi"):
        if not anchor.get(k):
            issues.append(f"anchor.{k} missing")

    blocks = (plan.get("rotation_schedule") or {}).get("blocks") or []
    if not blocks:
        issues.append("rotation_schedule.blocks missing or empty")
    teach_groups = []
    for i, b in enumerate(blocks):
        if b.get("type") not in ("anchor", "setup", "reteach", "teach", "transition"):
            issues.append(f"blocks[{i}].type invalid: {b.get('type')!r}")
        if not b.get("duration_minutes"):
            issues.append(f"blocks[{i}].duration_minutes missing")
        if b.get("type") == "teach":
            teach_groups.append(b.get("teach_group"))
            tp = b.get("talking_points") or {}
            for k in ("i_do_hi", "we_do_hi", "you_do_hi"):
                if not tp.get(k):
                    issues.append(f"blocks[{i}].talking_points.{k} missing")
    if sorted(g for g in teach_groups if g) != sorted(levels):
        issues.append(f"teach blocks should cover each group once, got {teach_groups}")

    # examples the teacher solves in each group's block (a worksheet problem must not repeat them)
    taught = _taught_pairs(plan)

    for level in levels:
        problems = ((plan.get("worksheets") or {}).get(level) or {}).get("problems") or []
        if not problems:
            issues.append(f"worksheets.{level}.problems missing or empty")
            continue
        if len(problems) > 8:
            issues.append(f"worksheets.{level} has {len(problems)} problems (max 8 for one page)")
        ws = (plan.get("worksheets") or {}).get(level) or {}
        rc = ws.get("required_count")
        if not isinstance(rc, int) or isinstance(rc, bool) or not 1 <= rc <= len(problems):
            issues.append(f"worksheets.{level}.required_count missing or invalid: {rc!r}")
        else:
            if level == "beginner" and len(problems) > 5 and rc != 5:
                issues.append(f"worksheets.beginner has {len(problems)} problems but required_count is {rc} (should be 5)")
            if level == "progressor" and len(problems) > 6 and rc != 6:
                issues.append(f"worksheets.progressor has {len(problems)} problems but required_count is {rc} (should be 6)")
            for p in problems:
                n = p.get("number")
                if p.get("diagnostic_for_misconception") and isinstance(n, int) and n > rc:
                    issues.append(f"worksheets.{level} problem {n} reveals a misconception but is an extra (required_count {rc})")
        # repeated answers among the problems every child must do, and problems copied from the lesson
        rc_ok = isinstance(rc, int) and not isinstance(rc, bool) and 1 <= rc <= len(problems)
        seen = {}
        req = problems[:rc] if rc_ok else problems
        for p in req:
            ans = str(p.get("answer", "")).strip()
            if ans and _plain_addition(p):          # a repeated answer matters when a SUM is involved
                seen.setdefault(ans, []).append(p.get("number"))
        for p in req:                               # ...including a word problem that copies a sum's answer
            ans = str(p.get("answer", "")).strip()
            if ans in seen and not _plain_addition(p):
                seen[ans].append(p.get("number"))
        for ans, nums in seen.items():              # literacy answers and non-addition skills may legitimately repeat
            if len(nums) > 1:
                issues.append(f"worksheets.{level}: problems {nums} all have the answer {ans}")
        if level == "beginner" and _uses_sticks(plan):
            for p in problems[:2]:
                pa = _plain_addition(p)
                if pa and pa[0] + pa[1] > STICK_PAIR_KIT_TOTAL:
                    issues.append(f"worksheets.beginner problem {p.get('number')} totals {pa[0] + pa[1]} but the first two problems use sticks "
                                  f"and the pair kit holds {STICK_PAIR_KIT_TOTAL}")
        for p in problems:
            m = re.search(r"(\d{1,3})\s*\+\s*(\d{1,3})", str(p.get("problem_hi") or ""))
            if m and tuple(sorted((int(m.group(1)), int(m.group(2))))) in taught[level]:
                issues.append(f"worksheets.{level} problem {p.get('number')} repeats an example solved in the talking points")
        for p in problems:
            for k in ("number", "problem_hi", "answer"):
                if p.get(k) in (None, ""):
                    issues.append(f"worksheets.{level} problem {p.get('number', '?')}: {k} missing")

    # Stick examples must fit the kits: teacher demo kit, and the Beginner pair kit for what children build
    for o in find_stick_overflows(plan):
        issues.append(f"{o['group']} {o['key']}: a stick example totals {o['largest']} but the kit holds only {o['cap']} sticks")
    uses_sticks = _uses_sticks(plan)
    if uses_sticks and "छड़" not in " ".join(plan.get("prep_hi") or []):
        issues.append("sticks are used in the talking points but prep_hi does not mention them")

    items = (plan.get("explainability") or {}).get("items")
    if not isinstance(items, list) or not items:
        issues.append("explainability.items missing or empty")
    else:
        for i, it in enumerate(items):
            if not isinstance(it, dict):
                issues.append(f"explainability.items[{i}] is not an object")
                continue
            for k in ("title_hi", "title_en", "body_hi", "body_en"):
                if not it.get(k):
                    issues.append(f"explainability.items[{i}].{k} missing")

    if domain_id == "numeracy":
        issues += find_number_word_errors(plan) + find_numeric_overlaps(plan)
    if domain_id == "r1_literacy":
        issues += find_text_overlaps(plan)
        text = json.dumps({"o": [b.get("other_groups_hi") for b in blocks], "c": plan.get("classroom_management")}, ensure_ascii=False)
        for lvl, ip in (plan.get("independent_passages") or {}).items():
            if ip["title"] not in text:
                issues.append(f"the independent-practice passage \u00ab{ip['title']}\u00bb for {lvl} is not mentioned in what the other groups do")

    return issues



async def get_competency_tree(db, domain_id: str) -> list[dict]:
    """The full competency tree for the Plan screen's Lakshya selector, each skill with its coverage label."""
    order = """ORDER BY CASE c.grade_level WHEN 'balvatika' THEN 0 WHEN 'grade_1' THEN 1 WHEN 'grade_2' THEN 2 WHEN 'grade_3' THEN 3 END,
               s.sort_order, c.sort_order"""
    try:
        rows = await db.fetch(f"""
            SELECT c.id, c.name_en, c.name_hi, c.grade_level, c.assessment_modality, s.name_en AS subdomain_name,
                   COALESCE(cc.tier, 'untested') AS coverage_tier, cc.note AS coverage_note
            FROM competencies c JOIN subdomains s ON c.subdomain_id = s.id
            LEFT JOIN competency_coverage cc ON cc.competency_id = c.id
            WHERE s.domain_id = $1 AND c.is_active = TRUE {order}""", domain_id)
    except Exception as e:                      # a database that has not loaded the coverage table yet
        if e.__class__.__name__ != "UndefinedTableError":
            raise
        rows = await db.fetch(f"""
            SELECT c.id, c.name_en, c.name_hi, c.grade_level, c.assessment_modality, s.name_en AS subdomain_name,
                   'untested' AS coverage_tier, NULL AS coverage_note
            FROM competencies c JOIN subdomains s ON c.subdomain_id = s.id
            WHERE s.domain_id = $1 AND c.is_active = TRUE {order}""", domain_id)
    return [dict(r) for r in rows]


async def get_coverage(db, competency_id: str):
    """{'tier', 'note'} for one skill, or None if the coverage table is not there."""
    try:
        r = await db.fetchrow("SELECT tier, note FROM competency_coverage WHERE competency_id = $1", competency_id)
    except Exception as e:
        if e.__class__.__name__ != "UndefinedTableError":
            raise
        return None
    return {"tier": r["tier"], "note": r["note"]} if r else {"tier": "untested", "note": None}


async def get_curriculum_week_for_competency(db, state_id: str, domain_id: str, competency_id: str) -> Optional[dict]:
    """
    Find the week of the state plan that teaches the selected competency.
    Prefers the focus week (fewest competencies listed), then the earliest.
    Looking up by competency, not by calendar date, keeps the week topic and notes
    consistent with what the teacher actually selected.
    """
    row = await db.fetchrow("""
        SELECT cw.week_number, cw.topic_title_en, cw.topic_title_hi,
               cw.competency_ids, cw.notes
        FROM curriculum_weeks cw
        JOIN curriculum_plans cp ON cw.plan_id = cp.id
        WHERE cp.state_id = $1 AND cp.is_active = TRUE
          AND cw.domain_id = $2 AND $3 = ANY(cw.competency_ids)
        ORDER BY array_length(cw.competency_ids, 1), cw.week_number
        LIMIT 1
    """, state_id, domain_id, competency_id)
    return dict(row) if row else None


async def get_curriculum_week(db, state_id: str, grade_level: str, domain_id: str, week_number: int) -> Optional[dict]:
    """Get the curriculum week for the recommended Lakshya highlight."""
    row = await db.fetchrow("""
        SELECT cw.week_number, cw.topic_title_en, cw.topic_title_hi, 
               cw.competency_ids, cw.notes
        FROM curriculum_weeks cw
        JOIN curriculum_plans cp ON cw.plan_id = cp.id
        WHERE cp.state_id = $1 AND cp.is_active = TRUE
          AND cw.grade_level = $2 AND cw.domain_id = $3
          AND cw.week_number = $4
        LIMIT 1
    """, state_id, grade_level, domain_id, week_number)
    return dict(row) if row else None


FEEDBACK_LOOKBACK_DAYS = 7


async def previous_review_feedback(db, teacher_id: str, domain_id: str, plan_date):
    """
    The misconceptions found at the teacher's most recent review before plan_date, and the date of that review.

    It looks back up to a week, not only at the previous calendar day: a Friday review must still feed a Monday plan. It looks only
    at the same subject, so numeracy gaps never turn into a literacy re-teach. If the last review found no misconceptions the result
    is empty (the group got it). Returns ([], None) when there was no review in the last week.
    """
    feedback_date = await db.fetchval("""
        SELECT max(e.session_date) FROM assessment_evidence e
        JOIN competencies c ON c.id = e.competency_id JOIN subdomains s ON s.id = c.subdomain_id
        WHERE e.teacher_id = $1 AND s.domain_id = $2 AND e.session_date < $3::date AND e.session_date >= $3::date - $4::int
    """, teacher_id, domain_id, plan_date, FEEDBACK_LOOKBACK_DAYS)
    if not feedback_date:
        return [], None
    rows = await db.fetch("""
        SELECT DISTINCT unnest(e.detected_misconception_ids) AS misc_id FROM assessment_evidence e
        JOIN competencies c ON c.id = e.competency_id JOIN subdomains s ON s.id = c.subdomain_id
        WHERE e.teacher_id = $1 AND s.domain_id = $2 AND e.session_date = $3 AND e.detected_misconception_ids IS NOT NULL
    """, teacher_id, domain_id, feedback_date)
    return [r["misc_id"] for r in rows], feedback_date


def _criteria_type(comp) -> Optional[str]:
    """'computation' (a numeric rule: sums to check), 'observational', 'written_production' or 'fluency'; None when unknown (the checks are then strict)."""
    c = getattr(comp, "apna_criteria", None)
    if isinstance(c, str):
        try:
            c = json.loads(c)
        except Exception:
            c = None
    return c.get("type") if isinstance(c, dict) else None


def _cfu_criteria_type(comp, domain_id: str) -> Optional[str]:
    """How strictly the CFU checks treat a skill. 'computation' ONLY for a NUMERACY skill with a numeric rule (there are sums to verify). Every literacy skill is 'literacy': eight of them are typed
    'computation' in the knowledge base (punctuation, matras, comprehension) because they are scored with a numeric accuracy rule, but they contain no arithmetic, and a good question such as
    'which mark ends this sentence: । or ?' must not be dropped for lacking an operation."""
    return "literacy" if domain_id != "numeracy" else _criteria_type(comp)


async def topup_cfu(client, model: str, plan_json: dict, cfu_kb: dict, deficient: list, lines: list, detected: dict) -> dict:
    """The model sometimes skips the check-for-understanding questions altogether (4 of about 25 plans in the first real runs: N0.2.2, L3.6.1, N3.3.2, L1.5.1), and in a skill with few possible examples (single-digit sums,
    multiplication tables) most of a block is rejected for repeating the lesson. When a block ends with fewer than 2 valid questions, the model is asked ONCE for just the missing ones, told which mistakes to aim at,
    what is already written, which examples the lesson uses and why earlier ones were rejected. The new questions go through the SAME checks (clean_plan_cfu runs again). The call is checked against the AI limit before and
    metered after, like the repairs; if anything fails the plan simply keeps what it has. Returns how many questions were added per group."""
    from cfu_prompt import render_topup
    blocks = {b.get("teach_group"): b for b in (plan_json.get("rotation_schedule") or {}).get("blocks") or [] if b.get("type") == "teach"}
    sym = {"*": "×", "/": "÷", "-": "−", "+": "+"}
    needs = {}
    for g in deficient:
        b = blocks.get(g)
        if b is None or g not in cfu_kb:
            continue
        kept = [q["question_hi"] for q in (b.get("cfu") or []) if isinstance(q, dict) and q.get("question_hi")]
        lesson, _ = _cfu_lesson_ops(plan_json, g, b)
        taken = sorted({ra for ra in (_cfu_right_answer(q) for q in (b.get("cfu") or [])) if ra is not None})
        needs[g] = {"need": max(1, 3 - len(kept)), "existing": kept, "taken": taken, "avoid": sorted(f"{a} {sym.get(op, op)} {c}" for op, a, c in lesson),
                    "why": [re.sub(rf"^{g}[: ]+", "", l.split(" | ")[0])[:200] for l in lines if l.startswith((g + " ", g + ":"))][:4]}
    if not needs:
        return {}
    try:
        await ai_budget.guard("plan_repair")                      # over the AI limit: no top-up (the plan is still valid)
        response = await client.messages.create(
            model=model, max_tokens=4000,
            system="You write check-for-understanding questions for a Hindi classroom lesson plan. Output JSON only.",
            messages=[{"role": "user", "content": render_topup(cfu_kb, detected or {}, needs)}],
            extra_body=CLAUDE_THINKING_BODY,
        )
        text = next((b.text for b in response.content if getattr(b, "type", None) == "text"), "")
        print(f"   CFU top-up call for {', '.join(needs)}: usage={response.usage}")
        await ai_budget.record_ctx("plan_repair", model, response.usage)
        if "```json" in text:
            text = text.split("```json", 1)[1]
        text = text.split("```", 1)[0].strip()
        data, note = parse_model_json(text)
        if note:
            print(f"   CFU top-up JSON: {note}")
    except Exception as e:
        print(f"   CFU top-up skipped: {type(e).__name__}: {str(e)[:140]}")
        return {}
    added = {}
    for g in needs:
        items = data.get(g) if isinstance(data, dict) else None
        if isinstance(items, list):
            new = [x for x in items if isinstance(x, dict)]
            blocks[g]["cfu"] = list(blocks[g].get("cfu") or []) + new
            added[g] = len(new)
    return added


async def build_reteach_items(db, teacher_id: str, misc_ids: list, feedback_date, groups: list) -> list[dict]:
    """One item per mistake found at the last review: what it was, how many children made it, and WHICH GROUP they are in now (the re-teach is for
    that group). The group used to be written in as 'progressor' for every item, whoever the children were."""
    roll_group = {str(r): g["label"] for g in groups for r in g.get("roll_numbers", [])}
    items = []
    for mid in misc_ids:
        detail = await db.fetchrow("SELECT name_hi, competency_id FROM misconceptions WHERE id = $1", mid)
        if not detail:
            continue
        rolls = await db.fetch("""SELECT DISTINCT ch.roll_number FROM assessment_evidence e JOIN children ch ON ch.id = e.child_id
                                  WHERE e.teacher_id = $1 AND e.session_date = $2::date AND $3 = ANY(e.detected_misconception_ids)""", teacher_id, feedback_date, mid)
        by_group, rolls_by_group = {}, {}
        for r in rolls:
            g = roll_group.get(str(r["roll_number"]))
            if g:
                by_group[g] = by_group.get(g, 0) + 1
                rolls_by_group.setdefault(g, []).append(r["roll_number"])
        items.append({"misconception_id": mid, "competency_id": detail["competency_id"], "misconception_name_hi": detail["name_hi"], "affected_count": len(rolls),
                      "group": choose_reteach_group(by_group), "affected_by_group": by_group,
                      "rolls_by_group": {g: sorted(v) for g, v in rolls_by_group.items()}})        # roll numbers go to the plan, never to the AI
    return items


def stamp_reteach_block(blocks: list, reteach_items: list) -> bool:
    """Fill in, in code, what the model leaves out of the re-teach block: WHICH GROUP it is for, WHICH CHILDREN (roll numbers) made the mistake, and
    what the OTHER groups do during its 5 minutes (they start the independent work given for the next teach block, so the text is copied from it:
    otherwise nobody is told what two thirds of the class do). Returns whether a re-teach block was found."""
    group = pick_priority_group(reteach_items)[0]
    rolls = sorted({r for item in reteach_items for r in (item.get("rolls_by_group") or {}).get(group, [])})
    found = False
    for i, blk in enumerate(blocks):
        if blk.get("type") != "reteach":
            continue
        found = True
        blk["teach_group"] = group
        blk["affected_rolls"] = rolls
        if not blk.get("other_groups_hi"):
            nxt = next((b for b in blocks[i + 1:] if b.get("type") == "teach" and b.get("other_groups_hi")), None)
            if nxt:
                blk["other_groups_hi"] = nxt["other_groups_hi"]
    return found


def stamp_reteach_main(blocks: list, reteach_groups: list, reteach_items: list, group_skill_ids: dict) -> list:
    """The teacher chose to re-teach these groups: each one's MAIN teach block is marked as a re-teach (`reteach`: True), and the code fills in what the model must not be given: WHICH CHILDREN of that
    group made a mistake (roll numbers) and WHICH mistakes (their names and how many children). Only mistakes found in the skill the group is taught today count, in that group. The other groups' blocks
    are left alone. Returns the groups marked."""
    marked = []
    for blk in blocks:
        g = blk.get("teach_group")
        if blk.get("type") != "teach" or g not in (reteach_groups or []):
            continue
        skill, rolls, mistakes = (group_skill_ids or {}).get(g), set(), []
        for item in reteach_items or []:
            n = (item.get("affected_by_group") or {}).get(g, 0)
            if item.get("competency_id") == skill and n > 0:
                rolls |= set((item.get("rolls_by_group") or {}).get(g, []))
                mistakes.append({"misconception_id": item.get("misconception_id"), "name_hi": item.get("misconception_name_hi"), "children": n})
        blk["reteach"] = True
        blk["affected_rolls"] = sorted(rolls)
        blk["reteach_mistakes"] = mistakes
        marked.append(g)
    return marked


async def get_current_groups(db, teacher_id: str, domain_id: str) -> list[dict]:
    """
    The current Beginner / Progressor / Proficient groups for this teacher and subject.

    Built from each child's CURRENT level (child_lakshya_positions), so a level change the
    teacher accepts shows up in the very next plan. The teaching_groups table is only a
    fallback for databases that have no level records: nothing keeps it in step with level
    changes, so trusting it would leave children in their old group.
    """
    groups = await derive_groups_from_positions(db, teacher_id, domain_id)
    if groups:
        return groups
    return await _stored_groups(db, teacher_id, domain_id)


async def _stored_groups(db, teacher_id: str, domain_id: str) -> list[dict]:
    """Groups saved in the teaching_groups table (fallback only; see get_current_groups)."""
    rows = await db.fetch("""
        SELECT tg.group_label, tg.child_count, tg.target_competency_id,
               tg.priority_rank, tg.child_ids,
               c.name_hi as target_name_hi, c.name_en as target_name_en
        FROM teaching_groups tg
        JOIN competencies c ON tg.target_competency_id = c.id
        WHERE tg.teacher_id = $1 AND tg.domain_id = $2
          AND tg.effective_until IS NULL
        ORDER BY tg.priority_rank
    """, teacher_id, domain_id)
    
    result = []
    for r in rows:
        # Get roll numbers for children in this group
        child_rolls = await db.fetch("""
            SELECT roll_number FROM children 
            WHERE id = ANY($1::uuid[]) AND is_active = TRUE
            ORDER BY roll_number
        """, r['child_ids'])
        
        result.append({
            "label": r['group_label'],
            "count": r['child_count'],
            "roll_numbers": [cr['roll_number'] for cr in child_rolls],
            "target_competency_id": r['target_competency_id'],
            "target_competency_name_hi": r['target_name_hi'],
            "target_competency_name_en": r['target_name_en'],
            "priority_rank": r['priority_rank'],
        })
    
    return result


async def derive_groups_from_positions(db, teacher_id: str, domain_id: str) -> list[dict]:
    """
    Build the Beginner / Progressor / Proficient groups from each child's current level in
    this subject (child_lakshya_positions): the same data the Progress screen shows.
    Children with no level recorded for this subject are not placed in any group.
    The returned target competency is the one most children in the group are currently
    working on. It is for display only: plan generation derives each group's teaching
    target from the prerequisite graph.
    """
    rows = await db.fetch("""
        SELECT c.roll_number, clp.bpp_level, clp.current_competency_id
        FROM child_lakshya_positions clp
        JOIN children c ON clp.child_id = c.id
        WHERE c.teacher_id = $1 AND clp.domain_id = $2 AND c.is_active = TRUE
        ORDER BY c.roll_number
    """, teacher_id, domain_id)
    if not rows:
        return []

    by_level: dict[str, list] = {}
    for r in rows:
        by_level.setdefault(r['bpp_level'], []).append(r)

    comp_ids = list({r['current_competency_id'] for r in rows if r['current_competency_id']})
    names = {}
    if comp_ids:
        for n in await db.fetch("SELECT id, name_hi, name_en FROM competencies WHERE id = ANY($1::text[])", comp_ids):
            names[n['id']] = (n['name_hi'], n['name_en'])

    result = []
    for rank, label in enumerate(('beginner', 'progressor', 'proficient'), start=1):
        members = by_level.get(label)
        if not members:
            continue
        counts = Counter(m['current_competency_id'] for m in members if m['current_competency_id'])
        target = min(counts, key=lambda k: (-counts[k], k)) if counts else None   # most common; ties by id
        name_hi, name_en = names.get(target, ('', ''))
        result.append({
            "label": label,
            "count": len(members),
            "roll_numbers": [m['roll_number'] for m in members],
            "target_competency_id": target,
            "target_competency_name_hi": name_hi,
            "target_competency_name_en": name_en,
            "priority_rank": rank,
        })
    return result


SAMPLE_PLAN_MINUTES = 90        # the recorded sample plans (db/seeds/sample_plans) were made for 90-minute sessions; one that records its own session_minutes keeps it


async def generate_dainik_yojana(
    db, 
    teacher_id: str, 
    competency_id: str, 
    domain_id: str,
    plan_date: date,
    group_skills: Optional[dict] = None,
    reteach_groups: Optional[list] = None,
    session_minutes: Optional[int] = None,
) -> dict:
    """
    Full Dainik Yojana generation pipeline.
    group_skills: the skills a teacher chose for the Beginners and the Proficients ({'beginner': id, 'proficient': id}); the Progressors' skill is competency_id.
    Without it each group's skill is derived from competency_id, as before.
    reteach_groups: the groups the TEACHER chose to re-teach (an empty list: move on with every group). Their main teach block is a focused re-teach and there is no separate re-teach block.
    Omitted (None): the old way, a separate 5-minute block when yesterday's photos found mistakes.
    session_minutes: how long the teacher has today (45, 60 or 90, from the Plan screen's time picker). It is the plan's teaching time, so the rotation is laid out
    for it and the prompt says it. None: the teacher's stored teaching time (90 unless changed), as before.
    Returns the complete plan + metadata.
    """
    settings = get_settings()
    start_time = time.time()
    
    # ── L1 Queries ──
    selected = await fetch_competency(db, competency_id)
    misconceptions = await fetch_misconceptions(db, competency_id)
    
    # Beginner target: direct hard prerequisite
    beginner_target_id = await _group_skills.derived_beginner_id(db, competency_id)      # the same rule the screen's panel uses
    beginner_comp = await fetch_competency(db, beginner_target_id)
    
    # Proficient extension: next competency that depends on this one
    proficient_comp = await fetch_competency(db, await _group_skills.derived_proficient_id(db, competency_id))

    # A teacher's choice for a group replaces the derived skill (checked: it must exist and belong to this subject)
    allowed = await _group_skills.allowed_skills(db, teacher_id, domain_id, plan_date, competency_id) if group_skills else None
    overrides = await _group_skills.clean_group_skills(db, domain_id, competency_id, group_skills, allowed=allowed)     # a skill the group cannot sensibly take is refused here, before any paid call
    decided_groups = _group_skills.clean_reteach_groups(reteach_groups)       # None: not asked (the old way); a list, maybe empty: the teacher decided
    if overrides.get("beginner"):
        beginner_target_id = overrides["beginner"]
        beginner_comp = await fetch_competency(db, beginner_target_id)
    if overrides.get("proficient"):
        proficient_comp = await fetch_competency(db, overrides["proficient"])
    await _group_skills.check_reteach_same_skill(db, teacher_id, domain_id, plan_date, decided_groups,
                                                 {"beginner": beginner_target_id, "progressor": competency_id, "proficient": proficient_comp.id})
    
    prereq_chain = await fetch_prerequisite_chain(db, competency_id, beginner_target_id)

    # Check for understanding: the recorded mistakes of EACH group's own skill (only the selected skill's reached the prompt before)
    cfu_kb = None
    if getattr(settings, "cfu_enabled", True):
        cfu_kb = {}
        for _g, _comp in (("beginner", beginner_comp), ("progressor", selected), ("proficient", proficient_comp)):
            _ms = misconceptions if _comp.id == competency_id else await fetch_misconceptions(db, _comp.id)
            cfu_kb[_g] = {"competency_id": _comp.id, "name_hi": _comp.name_hi, "name_en": getattr(_comp, "name_en", ""), "criteria_type": _cfu_criteria_type(_comp, domain_id), "mistakes": [asdict(m) for m in _ms]}

    # What each group may safely practise on its own, and the new skill it is taught today
    safe_beginner = []
    if beginner_target_id != competency_id:
        for r in await db.fetch("""
            SELECT c.id, c.name_hi FROM competency_prerequisites cp
            JOIN competencies c ON c.id = cp.prerequisite_id
            WHERE cp.competency_id = $1 AND cp.prerequisite_type = 'hard'
            ORDER BY c.sort_order LIMIT 3""", beginner_target_id):
            safe_beginner.append((r['id'], r['name_hi']))
    group_skills = {
        "beginner": {"safe": safe_beginner, "new": (beginner_comp.id, beginner_comp.name_hi)},
        "progressor": {"safe": [(beginner_comp.id, beginner_comp.name_hi)] if beginner_target_id != competency_id else [],
                       "new": (selected.id, selected.name_hi)},
        "proficient": {"safe": [(selected.id, selected.name_hi)] if proficient_comp.id != selected.id else [],
                       "new": (proficient_comp.id, proficient_comp.name_hi)},
    }
    
    # ── Groups ──
    groups = await get_current_groups(db, teacher_id, domain_id)
    
    group_map = {g['label']: g for g in groups}
    beginner_g = group_map.get('beginner', {"count": 0, "roll_numbers": []})
    progressor_g = group_map.get('progressor', {"count": 0, "roll_numbers": []})
    proficient_g = group_map.get('proficient', {"count": 0, "roll_numbers": []})
    
    # ── Teacher + school context ──
    teacher = await db.fetchrow("""
        SELECT t.enrolled_grades, t.available_minutes, s.school_code, s.has_printer
        FROM teachers t JOIN schools s ON t.school_id = s.id
        WHERE t.id = $1
    """, teacher_id)
    
    total_children = beginner_g['count'] + progressor_g['count'] + proficient_g['count']
    
    # ── Curriculum week ──
    # Estimate current week number from date
    week_number = max(1, (plan_date.timetuple().tm_yday - 180) // 7 + 1)  # Approximate, July start
    week_info = await get_curriculum_week_for_competency(
        db, settings.default_state_id, domain_id, competency_id
    ) or await get_curriculum_week(
        db, settings.default_state_id, selected.grade_level, domain_id, week_number
    )
    
    # ── The last review's feedback (the most recent review within a week, in THIS subject) ──
    yesterday_misc_ids, feedback_date = await previous_review_feedback(db, teacher_id, domain_id, plan_date)
    
    reteach_competencies = await build_reteach_items(db, teacher_id, yesterday_misc_ids, feedback_date, groups) if yesterday_misc_ids else []
    
    # ── L2 Queries ──
    anchor = await fetch_anchor_activity(db, domain_id, selected.grade_level, competency_id)
    if yesterday_misc_ids and (decided_groups is None or decided_groups):      # the old way, or the teacher chose to re-teach: the template for yesterday's gaps
        intervention = await fetch_intervention(db, yesterday_misc_ids)
        intervention_mode = "reteach" if intervention else "none"
    else:
        # No gaps yet: use the template for today's own misconceptions as pre-teaching
        intervention = await fetch_intervention(db, [m.id for m in misconceptions])
        intervention_mode = "preteach" if intervention else "none"
    
    tlm_ids = []
    if intervention and intervention.tlm_ids:
        tlm_ids.extend(intervention.tlm_ids)
    intervention_tlms = await fetch_tlms(db, tlm_ids)
    competency_tlms = await fetch_tlms_for_competencies(
        db, [competency_id, beginner_target_id, proficient_comp.id]
    )
    available_tlms, seen_tlm_ids = [], set()
    for t in competency_tlms + intervention_tlms:   # de-duplicate, keep order
        if t.id not in seen_tlm_ids:
            seen_tlm_ids.add(t.id)
            available_tlms.append(t)

    # Bundling sticks (TLM-001): teacher demo kit + Beginner pair kits sized from the Beginner group
    stick_policy = None
    sticks_for_skill = await db.fetchval(
        "SELECT TRUE FROM tlm_references WHERE id = 'TLM-001' AND $1 = ANY(competency_ids)", competency_id)
    if sticks_for_skill and any(t.id == "TLM-001" for t in available_tlms):
        n_beg = beginner_g['count']
        stick_policy = {"beginner_children": n_beg, "pair_kits": (n_beg + 1) // 2 if n_beg else 0}
    
    # ── Assemble context ──
    ctx = OrchestrationContext(
        teacher_name="Teacher",
        school_code=teacher['school_code'] if teacher else 'DEMO',
        enrolled_grades=teacher['enrolled_grades'] if teacher else ['grade_1', 'grade_2', 'grade_3'],
        total_children=total_children or 30,
        available_minutes=session_minutes or (teacher['available_minutes'] if teacher else settings.default_teaching_minutes),
        has_printer=teacher['has_printer'] if teacher else False,
        plan_date=str(plan_date),
        week_number=week_info['week_number'] if week_info else week_number,
        week_topic_hi=week_info['topic_title_hi'] if week_info else selected.name_hi,
        selected_competency=selected,
        domain_id=domain_id,
        domain_name_hi='गणित' if domain_id == 'numeracy' else 'R1 साक्षरता (हिंदी)',
        beginner=GroupInfo(
            label='beginner', count=beginner_g['count'],
            roll_numbers=beginner_g['roll_numbers'],
            target_competency=beginner_comp,
        ),
        progressor=GroupInfo(
            label='progressor', count=progressor_g['count'],
            roll_numbers=progressor_g['roll_numbers'],
            target_competency=selected,
        ),
        proficient=GroupInfo(
            label='proficient', count=proficient_g['count'],
            roll_numbers=proficient_g['roll_numbers'],
            target_competency=proficient_comp,
        ),
        prerequisite_chain=prereq_chain,
        misconceptions=misconceptions,
        anchor=anchor,
        intervention=intervention,
        available_tlms=available_tlms,
        reteach_competencies=reteach_competencies,
        reteach_groups=decided_groups,
        group_skill_ids={"beginner": beginner_target_id, "progressor": competency_id, "proficient": proficient_comp.id},
        week_notes=(week_info or {}).get('notes'),
        intervention_mode=intervention_mode,
        group_skills=group_skills,
        stick_policy=stick_policy,
        cfu_kb=cfu_kb,
    )
    ctx.cfu_detected = {r["misconception_id"]: r["affected_count"] for r in reteach_competencies if r.get("misconception_id")}
    
    # ── Reading passages (literacy): chosen in code from the content bank ──
    group_passages = await retrieve_group_passages(
        db, domain_id, {"progressor": competency_id, "proficient": proficient_comp.id}, plan_date)
    ctx.group_passages = group_passages
    independent_passages = await retrieve_independent_passages(
        db, domain_id, {"progressor": beginner_target_id, "proficient": competency_id}, plan_date,
        {ps["id"] for ps in group_passages.values()})
    ctx.independent_passages = independent_passages

    # ── Call Claude, unless the AI limit is reached: then a recorded plan for the same skill goes through the SAME checks and repairs ──
    ai_budget.bind(db, teacher_id)
    served_from, recorded = "ai", None
    try:
        await ai_budget.check(db, teacher_id, "plan")
    except ai_budget.AICapReached:
        recorded = ai_budget.sample_plan_for(competency_id)
        if recorded is None:
            raise
        served_from = "sample"
    client = None
    if served_from == "sample":
        plan_json = copy.deepcopy(recorded)
        print("   AI limit reached: serving a recorded sample plan for this skill")
    else:
        system_prompt = build_system_prompt()
        user_prompt = build_user_prompt(ctx)
    
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    
        plan_json = None
        for attempt in (1, 2):
            if attempt == 2:                          # a second paid call is checked against the AI limit again, exactly like the first
                try:
                    await ai_budget.check(db, teacher_id, "plan")
                except ai_budget.AICapReached as cap:
                    raise ValueError("The model's reply was not valid JSON and the AI limit is reached, so it could not be asked again.") from cap
            response = await client.messages.create(
                model=settings.claude_model,
                max_tokens=settings.claude_max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                extra_body=CLAUDE_THINKING_BODY,
            )
            await ai_budget.record(db, teacher_id, "plan", settings.claude_model, response.usage)     # paid for, whatever happens to the reply next

            # Find the text block: content[0] may be a thinking block on some models,
            # so search for the block with type == "text" rather than assuming position.
            response_text = None
            for block in response.content:
                if getattr(block, "type", None) == "text":
                    response_text = block.text
                    break

            print(f"   Claude: stop_reason={response.stop_reason}, usage={response.usage}")

            if response_text is None:
                raise ValueError(
                    f"No text block found in Claude's response. "
                    f"Block types: {[getattr(b, 'type', '?') for b in response.content]}, "
                    f"stop_reason={response.stop_reason}. "
                    f"If stop_reason is 'max_tokens', thinking used the whole budget: "
                    f"raise CLAUDE_MAX_TOKENS in .env."
                )

            if response.stop_reason == "max_tokens":
                raise ValueError(
                    "Claude's response was cut off by max_tokens, so the plan JSON is incomplete. "
                    "Raise CLAUDE_MAX_TOKENS in .env."
                )

            # Strip markdown fences if Claude wraps in ```json
            if "```json" in response_text:
                response_text = response_text.split("```json", 1)[1]
            if "```" in response_text:
                response_text = response_text.split("```", 1)[0]
            response_text = response_text.strip()

            try:
                plan_json, note = parse_model_json(response_text)
                if note:
                    print(f"   Model JSON: {note}")
                break
            except ModelJSONError as e:
                print(f"   Model JSON problem (attempt {attempt} of 2): {e}")
                if attempt == 2:
                    raise
                print("   Asking the model again (this second call is checked and metered like the first)")

    for line in inject_passages(plan_json, group_passages):
        print(f"   Passage: {line}")
    for line in apply_bank_questions(plan_json, group_passages):
        print(f"   Bank questions: {line}")
    for line in inject_independent(plan_json, independent_passages):
        print(f"   Independent practice: {line}")

    # A talking point that builds an example bigger than the stick kit is rewritten once (only that text)
    try:                                         # the re-teach block: its group, its children and the other groups' work are set by the code, not left to the model
        if ctx.reteach_groups is not None:       # the teacher decided: the re-teach groups' MAIN blocks are marked, with their children and mistakes
            marked = stamp_reteach_main((plan_json.get("rotation_schedule") or {}).get("blocks", []), ctx.reteach_groups, ctx.reteach_competencies, ctx.group_skill_ids)
            plan_json["reteach_groups"] = ctx.reteach_groups
            print(f"   Re-teach as the main block: {', '.join(marked) or 'none (move on with every group)'}")
        elif ctx.reteach_competencies:
            stamp_reteach_block((plan_json.get("rotation_schedule") or {}).get("blocks", []), ctx.reteach_competencies)
    except Exception as e:
        print(f"   Re-teach group step skipped: {type(e).__name__}: {e}")
    try:                                         # the Hindi tone rules, as a safety net: whole-word swaps in what the teacher says and reads
        style = hindi_style.soften_plan(plan_json)
        if style:
            print(f"   Hindi style: {sum(style.values())} wording changes ({', '.join(f'{k} x{v}' for k, v in sorted(style.items()))})")
    except Exception as e:
        print(f"   Hindi style step skipped: {type(e).__name__}: {e}")
    try:
        if served_from == "ai":
            plan_json, repair_log = await repair_stick_overflows(client, settings.claude_model, plan_json)
            for line in repair_log:
                print(f"   Stick repair: {line}")
    except Exception as e:      # a failed repair must never break plan generation
        print(f"   Stick repair skipped: {type(e).__name__}: {e}")

    # Worksheet numbers (repeated answers, problems copied from the lesson) are repaired in code, not by the model
    try:
        for line in repair_worksheet_numbers(plan_json):
            print(f"   Worksheet repair: {line}")
    except Exception as e:      # never let a repair break plan generation
        print(f"   Worksheet repair skipped: {type(e).__name__}: {e}")

    # Place-value and number-reading worksheets: number words written from the digits, answers not printed in the question,
    # numbers the lesson already used replaced, and the flash-card list built from the cards the lesson shows
    try:
        if domain_id == "numeracy":
            for line in repair_place_value(plan_json):
                print(f"   Place-value repair: {line}")
    except Exception as e:      # never let a repair break plan generation
        print(f"   Place-value repair skipped: {type(e).__name__}: {e}")

    # Which children to photograph is chosen by code (systematic sampling, the same every time for the same group and day),
    # not by the model: the model's own pick was arbitrary and could not be reproduced
    try:
        plan_json.setdefault("review_prompts", {})["photo_sample_rolls"] = {
            "beginner": sample_for_group(ctx.beginner.roll_numbers, plan_date, "beginner", beginner_target_id)["rolls"],
            "progressor": sample_for_group(ctx.progressor.roll_numbers, plan_date, "progressor", competency_id)["rolls"],
            "proficient": sample_for_group(ctx.proficient.roll_numbers, plan_date, "proficient", proficient_comp.id)["rolls"],
        }
        plan_json["review_prompts"]["photo_sample_method"] = "systematic sampling, the start moves each day"
    except Exception as e:
        print(f"   Photo sample skipped: {type(e).__name__}: {e}")

    # Check for understanding: the model writes the questions, the CODE decides which a teacher may use (arithmetic, mistake IDs, no reuse, the skill's own rule)
    try:
        if getattr(settings, "cfu_enabled", True) and served_from == "ai" and ctx.cfu_kb:
            cfu_lines, cfu_stats = clean_plan_cfu(plan_json, ctx.cfu_kb)
            deficient = [g for g, st in cfu_stats.items() if st["kept"] < MIN_ITEMS]
            if deficient and os.environ.get("CFU_TOPUP", "1") != "0":         # CFU_TOPUP=0 switches the extra call off
                added = await topup_cfu(client, settings.claude_model, plan_json, ctx.cfu_kb, deficient, cfu_lines, ctx.cfu_detected)
                if added:
                    lines2, stats2 = clean_plan_cfu(plan_json, ctx.cfu_kb)       # the new questions are judged by the same checks
                    cfu_lines += [f"top-up: {l}" for l in lines2 if any(l.startswith((g + " ", g + ":")) for g in added)]
                    for g in added:
                        stats2[g]["written"] = cfu_stats[g]["written"] + added[g]
                        stats2[g]["topped_up"] = True
                        cfu_stats[g] = stats2[g]
            plan_json["cfu_stats"] = cfu_stats
            for line in cfu_lines:
                print(f"   CFU: {line}")
            print("   CFU kept: " + ", ".join(f"{g} {s['kept']}/{s['written']}" for g, s in cfu_stats.items()))
        else:
            strip_cfu(plan_json)        # switched off, or a recorded sample plan: no unchecked question may reach a teacher
    except Exception as e:              # a failed check must never break plan generation, and nothing unchecked is kept
        strip_cfu(plan_json)
        print(f"   CFU check skipped (questions removed): {type(e).__name__}: {e}")

    validation_warnings = validate_plan_shape(plan_json, domain_id)
    if decided_groups is not None and any(b.get("type") == "reteach" for b in (plan_json.get("rotation_schedule") or {}).get("blocks") or []):
        validation_warnings.append("a separate re-teach block was written, but the teacher decided the re-teach is the group's main block")
    plan_json["coverage"] = await get_coverage(db, competency_id)      # shown on the plan screen
    if validation_warnings:
        print(f"   PLAN SHAPE WARNINGS ({len(validation_warnings)}):")
        for w in validation_warnings[:15]:
            print(f"     - {w}")
    else:
        print("   Plan shape OK")
    
    generation_time_ms = int((time.time() - start_time) * 1000)
    
    plan_json["group_skills"] = {"beginner": beginner_target_id, "progressor": competency_id, "proficient": proficient_comp.id}
    plan_json["group_skills_source"] = {"beginner": "teacher" if "beginner" in overrides else "derived", "progressor": "selected",
                                        "proficient": "teacher" if "proficient" in overrides else "derived"}

    # The "Why this plan?" item about the content used is built from the retrieved facts, not written by the model
    try:
        print(f"   Resources item: {put_resources_item(plan_json, build_resources_item(ctx, STICK_TEACHER_KIT_TOTAL))}")
    except Exception as e:      # never let this break plan generation
        print(f"   Resources item skipped: {type(e).__name__}: {e}")

    # ── Store plan ──
    explainability = plan_json.get('explainability', {})
    groups_snapshot = {
        'beginner': {'count': ctx.beginner.count, 'rolls': ctx.beginner.roll_numbers, 'target': beginner_target_id},
        'progressor': {'count': ctx.progressor.count, 'rolls': ctx.progressor.roll_numbers, 'target': competency_id},
        'proficient': {'count': ctx.proficient.count, 'rolls': ctx.proficient.roll_numbers, 'target': proficient_comp.id},
    }
    
    plan_json["served_from"] = served_from          # 'ai', or 'sample' when the AI limit was reached: the screen says so
    # the plan's length, read by the plan screen's time chip: the time the teacher chose (not the AI's own total_minutes); a recorded sample plan keeps the length it was made for (90 for the six today)
    plan_json["session_minutes"] = ctx.available_minutes if served_from == "ai" else int(plan_json.get("session_minutes") or SAMPLE_PLAN_MINUTES)
    await db.execute("""
        INSERT INTO daily_plans (teacher_id, plan_date, domain_id, selected_competency_id,
                                 plan_content, explainability, groups_snapshot, 
                                 generation_time_ms, claude_model)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        ON CONFLICT (teacher_id, plan_date, domain_id) DO UPDATE SET
            plan_content = EXCLUDED.plan_content,
            explainability = EXCLUDED.explainability || COALESCE((SELECT jsonb_object_agg(e.key, e.value)
                                 FROM jsonb_each(COALESCE(daily_plans.explainability, '{}'::jsonb)) e
                                 WHERE starts_with(e.key, 'teacher_decision_') OR starts_with(e.key, 'teacher_first_') OR starts_with(e.key, 'teacher_final_')), '{}'::jsonb),
            groups_snapshot = EXCLUDED.groups_snapshot,
            generation_time_ms = EXCLUDED.generation_time_ms,
            selected_competency_id = EXCLUDED.selected_competency_id,
            claude_model = EXCLUDED.claude_model
    """,
        teacher_id, plan_date, domain_id, competency_id,
        json.dumps(plan_json, ensure_ascii=False),
        json.dumps(explainability, ensure_ascii=False),
        json.dumps(groups_snapshot, ensure_ascii=False),
        generation_time_ms, settings.claude_model if served_from == "ai" else "sample-replay",
    )
    
    return {
        "plan_date": str(plan_date),
        "domain_id": domain_id,
        "selected_competency_id": competency_id,
        "groups": [
            {"label": "beginner", "count": ctx.beginner.count, "roll_numbers": ctx.beginner.roll_numbers,
             "target_competency_id": beginner_target_id, "target_competency_name_hi": beginner_comp.name_hi},
            {"label": "progressor", "count": ctx.progressor.count, "roll_numbers": ctx.progressor.roll_numbers,
             "target_competency_id": competency_id, "target_competency_name_hi": selected.name_hi},
            {"label": "proficient", "count": ctx.proficient.count, "roll_numbers": ctx.proficient.roll_numbers,
             "target_competency_id": proficient_comp.id, "target_competency_name_hi": proficient_comp.name_hi},
        ],
        "plan": plan_json,
        "explainability": explainability,
        "generation_time_ms": generation_time_ms,
        "validation_warnings": validation_warnings,
        "served_from": served_from,
    }


async def plan_evidence(db, teacher_id: str, plan_date: date, snapshot: dict) -> dict:
    """
    What has already been recorded against a stored plan, for the Plan screen's "replace this plan?" warning: per group, how many of the
    children in the plan's snapshot (who were in the group when the plan was made, not their group today) have a result on that day on the
    group's own skill. Every channel counts (observed, reading aloud, photo: a photo result is written as soon as the AI has read the sheet).
    An older snapshot without roll numbers counts any of the teacher's children with a result on the group's skill: a missing list must never
    hide evidence. Returns {"has_evidence": bool, "evidence_by_group": {"beginner": n, "progressor": n, "proficient": n}} (zeros included).
    """
    groups = {k: v for k, v in (snapshot or {}).items() if k in ("beginner", "progressor", "proficient") and isinstance(v, dict) and v.get("target")}
    counts = {"beginner": 0, "progressor": 0, "proficient": 0}
    if groups:
        rows = await db.fetch("""
            WITH g AS (
                SELECT key AS tier, value->>'target' AS skill,
                       CASE WHEN jsonb_typeof(value->'rolls') = 'array'
                            THEN ARRAY(SELECT jsonb_array_elements_text(value->'rolls')::int) END AS rolls
                FROM jsonb_each($3::jsonb)
            )
            SELECT g.tier, COUNT(DISTINCT e.child_id) AS n
            FROM g
            JOIN assessment_evidence e ON e.teacher_id = $1::uuid AND e.session_date = $2 AND e.competency_id = g.skill
            JOIN children c ON c.id = e.child_id AND c.teacher_id = $1::uuid
            WHERE g.rolls IS NULL OR c.roll_number = ANY(g.rolls)
            GROUP BY g.tier
        """, teacher_id, plan_date, json.dumps(groups))
        for r in rows:
            counts[r["tier"]] = int(r["n"])
    return {"has_evidence": any(counts.values()), "evidence_by_group": counts}
