#!/usr/bin/env python3
"""
The TLM inventory template (14 Nov 2026): what teaching-learning materials classrooms actually have, so a plan can name a real kit item for an
observed skill's hands-on task, and an everyday substitute (leaves, pebbles, buttons...) when the kit lacks it.

    python scripts/tlm_inventory_template.py      writes docs/drafts/TLM_INVENTORY_TEMPLATE.csv (open in Excel or Google Sheets; the Hindi stays intact)

Rows: the 12 TLMs in the knowledge base today (tlm_references, all AI-drafted and unreviewed: correct them), then common kit items marked
"suggested" (keep a row only if classrooms really have it, or delete it). Three columns are NEW and not yet in the database: the everyday
substitute, the quantity a class needs, and the kit the item comes from. Loading the filled sheet needs those columns added (a later step).
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

HEADER = ["ID", "Status", "Name (Hindi)", "Name (English)", "What it is / how it is used", "Subject (numeracy / literacy / both)",
          "Skills it supports (IDs, e.g. N0.1.1 N1.4.1)", "Availability (universal / common / uncommon / diy)", "Kit or source (e.g. NIPUN kit, school-made)",
          "Quantity a class needs (e.g. 1 per pair)", "Everyday substitute (leaves, pebbles, buttons...)", "How to make it (if DIY)", "Reviewed by", "Notes"]

# the 12 in the database (tlm_references), as they are today
EXISTING = [
    ("TLM-001", "बंडल की छड़ियाँ", "Bundling sticks", "numeracy", "N1.2.4 N2.2.2 N2.3.2 N2.3.4", "diy", "Collect thin sticks or straws and bundle groups of 10 with rubber bands.", "तीलियाँ, झाड़ू की सींकें, स्ट्रॉ"),
    ("TLM-002", "संख्या चार्ट 1-100", "Number chart 1-100", "numeracy", "N1.2.1 N1.2.3 N2.2.4", "common", "", ""),
    ("TLM-003", "वर्णमाला चार्ट", "Letter chart (varnamala)", "literacy", "L0.3.1 L1.3.1", "common", "", ""),
    ("TLM-004", "मात्रा चार्ट", "Matra chart", "literacy", "L1.3.2 L1.3.3 L1.7.2", "common", "Draw on chart paper: each row shows the vowel, its matra form and an example word.", ""),
    ("TLM-005", "स्थानीय मान पॉकेट चार्ट", "Place value pocket chart", "numeracy", "N1.2.4 N2.2.2 N3.2.2", "uncommon", "Make from cardboard: 3 columns labelled H|T|O with slits for sticks.", "तीन डिब्बे या कटोरियाँ (सैकड़ा, दहाई, इकाई)"),
    ("TLM-006", "खिलौने के सिक्के और नोट", "Coins and notes (play money)", "numeracy", "N2.4.3", "diy", "Print or draw denominations on card.", "असली सिक्के, बोतल के ढक्कन पर लिखी कीमत"),
    ("TLM-007", "फ्लैश कार्ड (संख्या)", "Flash cards (numbers)", "numeracy", "N0.2.3 N1.2.3 N3.3.3", "diy", "Cut card into playing-card size; numeral on the front.", "पुराने कैलेंडर या डिब्बे के गत्ते पर लिखे अंक"),
    ("TLM-008", "फ्लैश कार्ड (अक्षर/शब्द)", "Flash cards (letters/words)", "literacy", "L0.3.1 L1.3.1 L1.4.1 L2.4.2", "diy", "One letter or word per card, in large print.", "गत्ते के टुकड़े, स्लेट पर लिखे शब्द"),
    ("TLM-009", "30 सेमी पट्टी", "Ruler (30 cm)", "numeracy", "N3.4.1", "common", "", "धागा, पट्टी, कागज़ की पट्टी"),
    ("TLM-010", "श्यामपट्ट/श्वेतपट्ट", "Blackboard/whiteboard", "both", "", "universal", "", ""),
    ("TLM-011", "दस-फ्रेम कार्ड", "Ten-frame cards", "numeracy", "N1.3.1 N0.2.2", "diy", "Draw a 2x5 grid on card; children place counters.", "ज़मीन पर चॉक से बना 2x5 खाना, कंकड़"),
    ("TLM-012", "कहानी चित्र कार्ड", "Story picture cards", "literacy", "L0.1.3 L1.6.2", "diy", "Draw or print 4-6 scenes from a familiar story on separate cards.", ""),
]

# common classroom kit items, especially for the hands-on tasks of observed skills (sorting, comparing, measuring, reading cards aloud)
SUGGESTED = [
    ("गिनती के दाने/काउंटर", "Counters (seeds, beads)", "Counting, adding, grouping.", "numeracy", "N0.2.1 N0.2.2 N1.3.1", "common", "दाने, कंकड़, इमली के बीज, बटन"),
    ("आकृति कट-आउट (गोल, त्रिभुज, चौकोर; बड़े-छोटे, अलग रंग)", "Shape cut-outs (attribute blocks)", "Sorting by colour, shape or size; patterns.", "numeracy", "N0.1.1 N0.1.2 N0.1.3", "uncommon", "पत्तियाँ, बटन, बोतल के ढक्कन (रंग और आकार अलग)"),
    ("रंगीन ब्लॉक / क्यूब", "Coloured blocks / cubes", "Sorting, patterns, building towers to compare heights.", "numeracy", "N0.1.1 N0.1.2 N1.4.1", "uncommon", "माचिस की डिब्बियाँ, लकड़ी के गुटके"),
    ("मोती की माला (संख्या रेखा)", "Bead string (number line)", "Counting on, skip counting.", "numeracy", "N1.2.1 N1.3.1", "uncommon", "धागे में पिरोए 20 बटन या मोती"),
    ("तराज़ू (साधारण)", "Simple balance", "Comparing weights (heavier/lighter).", "numeracy", "N1.4.2", "uncommon", "हैंगर के दोनों ओर बँधी थैलियाँ"),
    ("नापने की पट्टियाँ / रिबन", "Measuring strips / ribbons", "Comparing and ordering lengths.", "numeracy", "N1.4.1 N2.4.1", "diy", "धागा, पत्तियाँ, तीलियाँ, हाथ-पैर से नाप"),
    ("घड़ी का मॉडल", "Clock model", "Reading time.", "numeracy", "N2.4.2", "uncommon", "कागज़ की थाली पर बनी घड़ी"),
    ("पासा", "Dice", "Number games, counting on.", "numeracy", "N0.2.3 N1.3.1", "common", "गत्ते का बना पासा"),
    ("चित्र-शब्द कार्ड", "Picture-word cards", "Reading words aloud, matching word to picture.", "literacy", "L1.4.1 L1.4.2 L2.4.1", "diy", "स्लेट या गत्ते पर बने शब्द"),
    ("वाक्य पट्टियाँ", "Sentence strips", "Reading sentences aloud, ordering sentences.", "literacy", "L2.4.2 L2.6.2", "diy", "कागज़ की पट्टियाँ"),
    ("बड़ी किताब (बिग बुक)", "Big book", "Shared reading, talking about a story.", "literacy", "L1.6.1 L1.6.2 L2.6.2", "uncommon", "चार्ट पेपर पर लिखी कहानी"),
    ("कठपुतली", "Puppets", "Retelling stories, speaking.", "literacy", "L0.1.3 L1.6.2", "diy", "मोज़े या कागज़ की थैली से बनी कठपुतली"),
    ("रेत की ट्रे", "Sand tray", "Tracing letters and numbers with a finger.", "both", "L0.7.1 L0.7.2", "diy", "ज़मीन पर रेत या मिट्टी"),
]


def main():
    out = ROOT / "docs" / "drafts" / "TLM_INVENTORY_TEMPLATE.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for tid, hi, en, subj, skills, avail, diy, sub in EXISTING:
            w.writerow([tid, "in the database (AI-drafted): correct it", hi, en, "", subj, skills, avail, "", "", sub, diy, "", ""])
        for k, (hi, en, what, subj, skills, avail, sub) in enumerate(SUGGESTED, 13):
            w.writerow([f"TLM-{k:03d}", "suggested: keep only if classrooms have it", hi, en, what, subj, skills, avail, "", "", sub, "", "", ""])
        for k in range(13 + len(SUGGESTED), 13 + len(SUGGESTED) + 5):
            w.writerow([f"TLM-{k:03d}", "new: add what your classrooms have", "", "", "", "", "", "", "", "", "", "", "", ""])
    print(f"{len(EXISTING)} existing + {len(SUGGESTED)} suggested rows + 5 empty rows: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
