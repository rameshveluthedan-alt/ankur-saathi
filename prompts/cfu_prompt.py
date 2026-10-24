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
Write 3 questions for each teach block, MOST IMPORTANT FIRST: the app uses the first 2 that pass its checks (two show-me questions per group is what a lesson has time for). This holds for EVERY skill, including the early counting, pattern and comparing skills: never leave a teach block without them. Each question is one object:
  {"kind": "compute|choose|spot_error|answer",
   "question_hi": "what the teacher asks, one or two short sentences",
   "expected_hi": "the right answer, short",
   "listen_for": [{"misconception_id": "<an ID listed for THIS group below>", "wrong_answer_hi": "the wrong answer itself, at most 12 words"}],
   "shows_hi": "what a right answer shows (only when the group's skill has no recorded mistakes; otherwise \\"\\")"}
Rules for the questions:
- kind: "compute" = a sum, difference or product to work out, written as "58 + 27" with no answer given; "choose" = the child picks one of the offered answers ("58 + 27: 75 or 85?", or "which is more, 5 or 3?");
  "spot_error" = a worked line with ONE deliberate mistake that the children must find ("47 + 25 = 612: right or wrong, and why?"); "answer" = everything else (a digit, a word, a mark, right or wrong, a place value, a pattern, a count).
  Use compute, spot_error or a sum-based choose ONLY when the question really contains a sum, difference or product written with digits. Anything else is "answer", or a plain "choose".
- How a child shows the answer: written or drawn on a slate or notebook page, shown on fingers, or a card or object held up. For readiness skills (counting, patterns, comparing quantities), where children cannot write yet,
  use fingers, objects, cards, pointing or drawing. The answer must be quick to show: a number, a word, a mark, "सही / गलत", a shape, or one of two options. Never a sentence.
- Do not repeat the show-me procedure (hide, wait for the signal, show together) inside a question: the screen says it once.
- Do NOT tell a story about a child ('एक बच्चे ने ... लिखा'): it adds reading and listening load for Class 1 and 2. Write what is ON THE BOARD, as the teacher would say it: 'बोर्ड पर देखो: 34 + 28 = 52 लिखा है। क्या यह सही है?'
- No PERSON at all may have 'done' something in a question: not 'एक बच्चे ने', not 'एक पाठक ने', not 'किसी ने'. Either the teacher does it ('मैं ... पढ़ता/पढ़ती हूँ') or it is already ON THE BOARD.
- expected_hi is the verdict and the right number, word or mark ONLY: no explanation. Explanations are where mistakes hide (one key told the teacher to write the digits in exactly the places its own question called wrong).
- Never describe a drawing or a table in words (rows, columns, which digit sits where): a Class 2 child cannot follow it, and it tends to give the answer away. Put the numbers on one board line: 'बोर्ड पर देखें: 43 + 25 = 68'.
- When the choice is between punctuation marks write it as '1) । 2) ?', never 'लगेगा या ?'. A sentence 'different from the topic' is a paragraph-structure question: not allowed.
- No object is ever handed out for a show-me (no pebbles, buttons or counters: they cause distraction and mess): children use their slate, their fingers, or what is drawn on the board. Objects belong to the I Do and the We Do.
- A paragraph or writing skill: ask about punctuation, what happened first or next, or a missing full stop. NEVER about the structure or purpose of a paragraph (an introduction, a conclusion, a sentence out of topic): too abstract for Class 2 and 3.
- A matra skill: use real-word pairs a teacher would use, such as दिन / दीन, कुल / कूल, कल / काल, सिल / सील, पुल / पूल.
- Plain spoken Hindi: 'इसके बाद' (not 'इसके तुरंत बाद'); to give an oral cue write 'मैं एक संख्या बोलूँगा/बोलूँगी: 14'; for marks on a slate 'अगले दो निशान'.
- Each question must be SELF-CONTAINED: write into it every letter, word, sentence, number or picture the children need. Never refer to a text, a paragraph, a picture or a passage that is not written in the question itself.
- A WRONG answer you put on the board (a spot_error) must never be a number the lesson shows as a RIGHT answer: children remember the lesson's numbers and may take the wrong line for right.
- listen_for.wrong_answer_hi is the EXACT wrong answer a child with that mistake would give for THIS question (the number, the word, the mark), worked out from the mistake's error pattern, and never a description such as 'a random answer'.
- Never give the answer away inside the question (for example by saying what the right form "should" be). Ask ONE thing per question: do not ask the children to write something AND answer a second question about it.
- Children answer with one letter, one matra, one short word, a number, a mark, a choice (1 or 2 on fingers, or on a card) or a quick drawing. NEVER ask them to copy a sentence, to write a sentence, or to write more than one short word.
  To show where to pause in a sentence, ask for the NUMBER of the word after which to pause.
- When the question needs something written or drawn on the board, say exactly what the teacher writes, including any deliberate mistake in it (for example: 'Write कमल on the board WITHOUT the line on top'). The children
  cannot see the board when they read your text: a word 'on the slate' or 'on the board' with no description of how it is written is not a question.
- When you show a pause as 'N (words before the pause / words after)', N is the number of words BEFORE the slash: count them. The same for 'how many words' and 'the third word': count carefully.
- The right answer (expected_hi) is ONLY the answer: a few words, with no working out and no correction of yourself in the middle of it.
- Do not ask children to write a word that is not a real word, or to rearrange a word. Ask them to choose between real written forms, or to write the one letter or matra.
- Beginner children answer with a finger choice (1 or 2) or one letter: a choice is better than writing, especially for letters and early Class 1 skills. Avoid making them write long words.
- Children are 6 to 9 years old: no percentages, no fractions and no calculations beyond the skill itself, even to explain fluency or accuracy.
- Every child must be able to answer from their own place at the same moment: never 'touch the letter on the board' or 'come to the board'.
- The three groups must not get questions of the same shape: the Beginners' questions are easier than the Progressors', and the Proficients' go further. Two questions in one block must not test the same thing in the same way.
- Aim each question at ONE recorded mistake of THAT group's own skill, taking the mistakes in the order listed (the first is the most important; one marked DETECTED comes first). A child who has the
  mistake must give a recognisable wrong answer: put it in listen_for with the mistake's ID and the exact wrong answer.
- Use ONLY the IDs listed for that group. Where a group's skill has no recorded mistakes, write questions that test the key idea of the skill, leave listen_for as [] and fill shows_hi.
- Every piece of arithmetic must be exactly right, including every worked line you write, except the one deliberate mistake in a spot_error (which must really be wrong).
- Use NEW numbers: no sum, difference or product in a question may repeat an example the group's lesson uses (its I Do, We Do or You Do). A skill with few possible examples (single-digit sums, multiplication tables)
  still has plenty: choose pairs the lesson does not show.
- A show-me question's right answer, and any wrong answer you list in listen_for, must not be a result the lesson has already written on the board (the results of its I Do, We Do and You Do): a child could copy it from there instead of working it out.
- At least one of a group's questions must make the child WORK OUT an answer (kind compute or choose). Two 'right or wrong?' questions (kind spot_error) whose lines are both WRONG are not enough: in a lesson about mistakes a child can simply guess 'wrong' twice. If you do write two 'right or wrong?' questions, at least one of the lines you show must be CORRECT (a fair decoy).
- The questions of ONE group must have DIFFERENT right answers: if one question's right answer is 84, no other question of that group has 84 (a child who knows one answer would know the other).
- For a comprehension or passage skill, QUOTE the sentence you ask about inside the question: the children are not looking at a page. Never leave a teach block without questions.
- Stay inside the group's own skill. If the skill is "without regrouping" or "without borrowing", no question may need a carry or a borrow.
- If the skill is oral (reading aloud, listening, speaking), still make a show-me that needs no speaking: children write the word they heard, mark the pauses with a slash on a sentence on the board,
  hold up a letter card, or write right or wrong.
- Respectful Hindi. No choral instructions. Do not name children.
- JSON: inside any text value NEVER use the double quote character ("). To quote a word, use single quotes (' ') instead: an unescaped double quote makes the whole reply invalid.
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


def render_topup(cfu_kb: dict, detected: dict, needs: dict) -> str:
    """The request for the questions a block is MISSING (the model skipped them, or too many were rejected). needs[group] = {"need": n, "existing": [question texts already valid],
    "avoid": ["6 x 4", ...] (the group's lesson examples), "why": [reasons earlier questions were rejected]}. Only the groups named are asked for."""
    out = [render_cfu_section({g: cfu_kb[g] for g in needs if g in cfu_kb}, detected), "\n### WHAT IS MISSING: write the questions below, for the groups named, and nothing else."]
    for g, n in needs.items():
        out.append(f"\nGROUP {g.upper()}: write exactly {n['need']} NEW questions.")
        if n.get("existing"):
            out.append("  Already written and valid (do NOT repeat or rephrase them):\n" + "\n".join(f"    - {x}" for x in n["existing"]))
        if n.get("taken"):
            out.append("  The right answers of the questions above are " + ", ".join(str(x) for x in n["taken"]) + ": every NEW question must have a DIFFERENT right answer.")
        if n.get("avoid"):
            out.append("  The group's lesson already uses these examples: do NOT use them: " + ", ".join(n["avoid"]))
        if n.get("why"):
            out.append("  Earlier attempts were rejected because:\n" + "\n".join(f"    - {w}" for w in n["why"]))
    keys = ", ".join(f'"{g}"' for g in needs)
    out.append(f"\nReply with JSON ONLY, no other text: an object with the keys {keys}, each a list of question objects as described above.")
    return "\n".join(out) + "\n"
