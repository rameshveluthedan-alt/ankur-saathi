"""
Check for understanding (CFU) in every lesson: what the model is told.

A CFU is a SHOW-ME: the teacher asks a question, every child writes the answer on a slate or a notebook page and hides it, and on one signal all hold it up at the same moment. The
teacher sees every answer, then asks two children to explain. There is no choral answering (the teacher could not tell who was right).

The questions are aimed at the recorded mistakes of EACH GROUP'S OWN skill (the knowledge base has them for 27 of the 101 skills). For the other skills the model writes questions
that test the key idea, and the plan says so. The code (backend/app/services/cfu.py) checks everything the model writes: the arithmetic, the mistake IDs, that no example is reused.
See docs/CFU.md.
"""

_FREQ = {"very_common": 0, "common": 1, "uncommon": 2, "rare": 3}
_SEV = {"critical": 0, "moderate": 1, "minor": 2}
MAX_MISTAKES_PER_GROUP = 4

GROUP_ORDER = ("beginner", "progressor", "proficient")
GROUP_HI = {"beginner": "शुरुआती", "progressor": "प्रगतिशील", "proficient": "दक्ष"}


def rank_mistakes(mistakes: list, detected: dict) -> list:
    """Most important first: detected at the last review, then the most common, then the most serious, then the order in the knowledge base."""
    def key(item):
        i, m = item
        return (0 if m.get("id") in detected else 1, _FREQ.get(m.get("frequency"), 4), _SEV.get(m.get("severity"), 3), i)
    return [m for _, m in sorted(enumerate(mistakes or []), key=key)]


CFU_RULES = """
## CHECK FOR UNDERSTANDING (CFU): add the key "cfu" to EVERY teach block (type "teach") and to no other block.
A CFU is a SHOW-ME: the teacher asks, every child writes the answer on a slate or a notebook page and hides it, and on one signal all children hold it up at the same moment. The teacher
scans the room, then asks two children to explain why. Never choral answering (the teacher could not tell who was right).
Each teach block gets 2 or 3 questions (4 at most, and only when a mistake below is marked as detected at the last review). Each question is one object:
  {"kind": "compute|choose|spot_error|answer",
   "question_hi": "what the teacher asks, one or two short sentences",
   "expected_hi": "the right answer, short",
   "listen_for": [{"misconception_id": "<an ID listed for THIS group below>", "wrong_answer_hi": "exactly what a child with that mistake writes or says"}],
   "shows_hi": "what a right answer shows (only when the group's skill has no recorded mistakes; otherwise \\"\\")"}
Rules for the questions:
- kind: "compute" = a sum, difference or product to work out, written as "58 + 27" with no answer given; "choose" = two answers are offered and the child picks one ("58 + 27: 75 or 85?");
  "spot_error" = a worked line with ONE deliberate mistake that the children must find ("47 + 25 = 612: right or wrong, and why?"); "answer" = any other short answer (a digit, a word, a mark, right or wrong, a place value).
- The answer must fit on a slate in a few seconds: a number, a word, a mark, "सही / गलत", or one of two options. Never a sentence.
- Aim each question at ONE recorded mistake of THAT group's own skill, taking the mistakes in the order listed (the first is the most important; one marked DETECTED comes first). A child who has the
  mistake must give a recognisable wrong answer: put it in listen_for with the mistake's ID and the exact wrong answer.
- Use ONLY the IDs listed for that group. Where a group's skill has no recorded mistakes, write questions that test the key idea of the skill, leave listen_for as [] and fill shows_hi.
- Every piece of arithmetic must be exactly right, including every worked line you write, except the one deliberate mistake in a spot_error (which must really be wrong).
- Use NEW numbers. No sum, difference or product in a question may repeat an example in a talking point or a worksheet problem of the same group.
- Stay inside the group's own skill. If the skill is "without regrouping" or "without borrowing", no question may need a carry or a borrow.
- If the skill is oral (reading aloud, listening, speaking), still make a show-me that needs no speaking: children write the word they heard, mark the pauses with a slash on a sentence on the board,
  hold up a letter card, or write right or wrong.
- Respectful Hindi. No choral instructions. Do not name children.
"""


def render_cfu_section(cfu_kb: dict, detected: dict = None) -> str:
    """The rules plus, for each group, the group's skill and its recorded mistakes (most important first). cfu_kb[group] = {competency_id, name_hi, name_en, mistakes: [dict]}."""
    if not cfu_kb:
        return ""
    detected = detected or {}
    out = [CFU_RULES, "### MISTAKES TO TARGET, PER GROUP (from L1; use only these IDs)"]
    for g in GROUP_ORDER:
        kb = cfu_kb.get(g)
        if not kb:
            continue
        out.append(f"\nGROUP {g.upper()} ({GROUP_HI[g]}): skill {kb['competency_id']}: {kb.get('name_en') or ''} / {kb.get('name_hi') or ''}")
        mistakes = rank_mistakes(kb.get("mistakes") or [], detected)[:MAX_MISTAKES_PER_GROUP]
        if not mistakes:
            out.append("  No mistakes are recorded for this skill: test its key idea, leave listen_for as [] and fill shows_hi.")
            continue
        for n, m in enumerate(mistakes, 1):
            flag = f"   DETECTED at the last review in {detected[m['id']]} child(ren): put this first." if m["id"] in detected else ""
            out.append(f"  {n}. {m['id']} [{m.get('severity')}, {m.get('frequency')}] {m.get('name_hi')}{flag}\n"
                       f"     pattern: {m.get('error_pattern')}\n     how to detect: {m.get('diagnostic_indicator')}\n"
                       f"     right: {m.get('example_correct') or '-'} | wrong: {m.get('example_incorrect') or '-'}")
    return "\n".join(out) + "\n"
