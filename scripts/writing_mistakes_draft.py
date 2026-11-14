#!/usr/bin/env python3
"""
DRAFT common mistakes for the three writing skills that have none in the knowledge base (L2.7.1 dictation, L2.7.2 connected sentences,
L3.7.1 paragraph). AI-proposed 13 Nov 2026; Vaishnavi confirmed all nine without changes on 14 Nov 2026 (docs/WRITING_MISTAKES_REVIEWED_141126.csv),
and the rows are now in db/seeds/literacy/03_misconceptions.sql. This script is kept to show where they came from.

    python scripts/writing_mistakes_draft.py            writes docs/drafts/WRITING_MISTAKES_FOR_REVIEW.csv (open in Excel or Google Sheets)
                                                        and docs/drafts/writing_mistakes_draft.sql (the rows, in the seed format, to load AFTER her review)

Why they matter: with no recorded mistakes, a writing plan's checks for understanding cannot target a known mistake, no worksheet item can be marked
as revealing one, and the photo analysis has nothing to name (docs/drafts/PLAN_REVIEW_L2.7.2.md, finding 5). The L2.7.2 three come from the curated
list in docs/CURATED_SKILLS.md (missing joining words, sentence boundary, repetition).
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# id, skill, name_en, name_hi, error_pattern, diagnostic_indicator (how it shows on the sheet), example_correct, example_incorrect,
# intervention_strategy, intervention ids, severity, frequency
MISTAKES = [
    ("L2.7.1-M1", "L2.7.1",
     "Confuses short and long vowel matras (ि/ी, ु/ू)",
     "छोटी-बड़ी मात्रा में भ्रम (ि/ी, ु/ू)",
     "Writes the short matra for the long one or the reverse, in words the child can read correctly",
     "The same pair is wrong in two or more dictated words; the consonants are right",
     "दीदी, पूजा", "दिदी, पुजा",
     "Say the word slowly and stretch the long vowel ('दी...दी'); the children show a short or long arm movement before writing. Minimal pairs on the board: दिन/दीन, कुल/कूल.",
     ["INT-LIT-002"], "critical", "very_common"),
    ("L2.7.1-M2", "L2.7.1",
     "Leaves out the nasal sign or a matra (ं, ँ, े/ै)",
     "अनुस्वार, चंद्रबिंदु या मात्रा छोड़ देना (ं, ँ, े/ै)",
     "Drops the anusvara or chandrabindu, or writes े for ै, so the word changes or loses its plural",
     "Missing ं/ँ or े↔ै in two or more words; often in है/हैं, में/मैं",
     "बच्चे खेलते हैं। मैं घर में हूँ।", "बच्चे खेलते है। में घर मै हू।",
     "Read the sentence back aloud from the child's own writing, word by word: the child hears the missing sound. Keep a small chart of है/हैं, में/मैं on the wall.",
     ["INT-LIT-002"], "moderate", "very_common"),
    ("L2.7.1-M3", "L2.7.1",
     "Joins or splits words (word boundaries)",
     "शब्दों को जोड़कर या तोड़कर लिखना",
     "Writes two words as one, or breaks one word into parts, because the sentence was heard as one stream",
     "No space between words that belong apart, or a space inside a word, in two or more places",
     "हम घर गए।", "हमघर गए। / ह म घरगए।",
     "Dictate slowly and clap once for each word; the children count the claps and then the words they wrote. A finger space between words.",
     [], "moderate", "common"),
    ("L2.7.2-M1", "L2.7.2",
     "Writes separate sentences with no joining words",
     "वाक्य अलग-अलग लिखना, जोड़ने वाले शब्द नहीं",
     "Each sentence stands alone; and, then, because are never used, so the writing reads as a list",
     "Three or more sentences on the topic, none joined by और / फिर / क्योंकि / लेकिन",
     "मेरी बहन का नाम सीमा है। वह स्कूल जाती है और रोज़ पढ़ती है।", "मेरी बहन सीमा है। वह स्कूल जाती है। वह पढ़ती है।",
     "Model joining two of the child's own sentences with और and with फिर; then the child joins one more pair from their writing.",
     [], "critical", "very_common"),
    ("L2.7.2-M2", "L2.7.2",
     "Does not mark where a sentence ends",
     "वाक्य कहाँ खत्म होता है, यह नहीं दिखाना",
     "Runs sentences together without the पूर्ण विराम (।), or puts it in the middle of a sentence",
     "Two or more full stops missing or misplaced on the sheet",
     "आज मेला है। हम मेले में जाएँगे।", "आज मेला है हम मेले में जाएँगे",
     "The child reads their writing aloud and stops where the voice stops: that is where । goes. Practise on two sentences written together on the board.",
     [], "moderate", "very_common"),
    ("L2.7.2-M3", "L2.7.2",
     "Repeats the same sentence start or idea",
     "एक ही शुरुआत या बात दोहराना",
     "Starts every sentence the same way, or says the same thing twice, so the writing does not move on",
     "Three or more sentences begin with the same words, or two sentences say the same thing",
     "मेरा गाँव छोटा है। वहाँ एक तालाब है। गाँव के लोग मेहनती हैं।", "मेरा गाँव छोटा है। मेरा गाँव अच्छा है। मेरा गाँव सुंदर है।",
     "Ask 'और क्या बताओगे?' after each sentence; list 3 different things about the topic before writing (what, where, who).",
     [], "minor", "common"),
    ("L3.7.1-M1", "L3.7.1",
     "Drifts away from the topic",
     "विषय से भटक जाना",
     "Begins on the topic but later sentences are about something else",
     "One or more sentences not about the given topic",
     "विषय 'मेरा त्योहार': सभी वाक्य दिवाली के बारे में", "विषय 'मेरा त्योहार': दो वाक्य दिवाली पर, फिर मेरे दोस्त और क्रिकेट पर",
     "Before writing, the child says the topic in one sentence; after writing, they tick each sentence that is about it and cross the one that is not.",
     [], "critical", "common"),
    ("L3.7.1-M2", "L3.7.1",
     "No order: no beginning, middle and end",
     "क्रम नहीं: शुरुआत, बीच और अंत नहीं",
     "Ideas are in a random order; no opening sentence that names the topic and no closing sentence",
     "The first sentence does not introduce the topic, or the paragraph stops without an ending; sequence words (पहले, फिर, अंत में) are missing",
     "पहले हमने घर सजाया। फिर पूजा की। अंत में सबने मिठाई खाई।", "सबने मिठाई खाई। हमने घर सजाया। पूजा हुई।",
     "Plan on three lines first: शुरुआत, बीच, अंत. Model with sequence words; the child numbers their sentences in order before copying them out.",
     [], "moderate", "common"),
    ("L3.7.1-M3", "L3.7.1",
     "Writes too little: a sentence or two, not a paragraph",
     "बहुत कम लिखना: एक-दो वाक्य, अनुच्छेद नहीं",
     "Stops after one or two sentences although the task asks for 5-7",
     "Fewer than 5 sentences on a task that asks for 5-7",
     "5-7 वाक्य", "मुझे दिवाली पसंद है। हम दीये जलाते हैं।",
     "Give question prompts on the board (कब? कहाँ? कौन? क्या करते हैं? कैसा लगता है?); the child writes one sentence for each.",
     [], "minor", "common"),
]

HEADER = ["#", "Skill", "ID", "Mistake (Hindi)", "Mistake (English)", "What the child does", "How it shows on the sheet", "Right example", "Wrong example",
          "What the teacher does", "Severity (draft)", "How common (draft)", "Vaishnavi: OK / change", "Vaishnavi: comment"]


def q(s: str) -> str:
    return "'" + str(s).replace("'", "''") + "'"


def main():
    out = ROOT / "docs" / "drafts"
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "WRITING_MISTAKES_FOR_REVIEW.csv", "w", encoding="utf-8-sig", newline="") as f:      # utf-8-sig: Excel opens the Hindi correctly
        w = csv.writer(f)
        w.writerow(HEADER)
        for n, m in enumerate(MISTAKES, 1):
            mid, skill, en, hi, pattern, shows, right, wrong, todo, _ints, sev, freq = m
            w.writerow([n, skill, mid, hi, en, pattern, shows, right, wrong, todo, sev, freq, "", ""])
    rows = []
    order = {}
    for m in MISTAKES:
        mid, skill, en, hi, pattern, shows, right, wrong, todo, ints, sev, freq = m
        order[skill] = order.get(skill, 0) + 1
        arr = "ARRAY[" + ", ".join(q(i) for i in ints) + "]" if ints else "ARRAY[]::text[]"
        rows.append(f"({q(mid)}, {q(skill)},\n {q(en)},\n {q(hi)},\n {q(pattern)},\n {q(shows)},\n {q(right)},\n {q(wrong)},\n {q(todo)},\n {arr}, {q(sev)}, {q(freq)}, {order[skill]})")
    sql = ("-- AI-proposed 13 Nov 2026; confirmed by Vaishnavi on 14 Nov 2026 without changes (docs/WRITING_MISTAKES_REVIEWED_141126.csv).\n"
           "-- These rows are now in db/seeds/literacy/03_misconceptions.sql; this file loads them into an existing database (ON CONFLICT DO NOTHING).\n"
           "INSERT INTO misconceptions (id, competency_id, name_en, name_hi, error_pattern, diagnostic_indicator, example_correct, example_incorrect, "
           "intervention_strategy, intervention_template_ids, severity, frequency, sort_order) VALUES\n\n" + ",\n\n".join(rows) + "\nON CONFLICT (id) DO NOTHING;\n")
    (out / "writing_mistakes_draft.sql").write_text(sql, encoding="utf-8")
    print(f"{len(MISTAKES)} draft mistakes: docs/drafts/WRITING_MISTAKES_FOR_REVIEW.csv and docs/drafts/writing_mistakes_draft.sql")


if __name__ == "__main__":
    main()
