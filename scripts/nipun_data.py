"""
Proposed alignment of Ankur Saathi's 101 skills to the coded learning outcomes in NIPUN Bharat Annexure I
(Guidelines for Implementation, 2021). AI-PROPOSED: every row is for an educator to confirm.

Code families in the annexure:
  IL n.m / ILM n.m   Goal 3, involved learners: cognitive skills and mathematics (ILM = the mathematics rows of Classes 1-3)
  ECL1 n.m           Goal 2, effective communicators, first language (Hindi examples)
  HW n.m             Goal 1, health and wellbeing (motor skills, following instructions)
  n = level: 1 Preschool 1, 2 Preschool 2, 3 Preschool 3 (Balvatika), 4 Class 1, 5 Class 2, 6 Class 3

"says" is our own short paraphrase of the outcome, never the annexure's wording.
match: exact   same outcome as ours
       finer   ours is one piece of a broader NIPUN outcome (we split it)
       related close in topic, but wider/narrower or a different level
       none    no counterpart in the annexure's outcomes
"""

# skill_id: (codes, match, confidence, what NIPUN says, note from the team)
MAPPING = {
    # ── Numeracy: Balvatika ────────────────────────────────────────────────
    "N0.1.1": (["IL 3.5", "IL 2.5"], "related", "medium", "Classifies objects by up to three factors such as shape, colour and size; uses position words.", "Ours is simpler (one attribute); NIPUN reaches two factors at Preschool 2 and three at Balvatika."),
    "N0.2.1": (["IL 3.10", "ILM 4.10"], "related", "medium", "Counts forward and backward from a number: up to 9 in Balvatika, up to 20 in Class 1.", "Our target (1 to 20) is above NIPUN's Balvatika range."),
    "N0.5.1": (["IL 3.25"], "related", "medium", "Identifies 2-D shapes by tracing the faces of 3-D shapes.", ""),
    "N0.1.2": (["IL 2.27", "IL 3.27"], "exact", "medium", "Identifies the repeating unit of a simple pattern and extends it (Preschool 2); creates new patterns (Balvatika).", "NIPUN places extending a pattern at Preschool 2."),
    "N0.2.2": (["IL 3.9"], "exact", "high", "Counts up to 10 objects, with objects and with pictures.", ""),
    "N0.1.3": (["IL 2.13", "IL 3.13"], "exact", "medium", "Compares two numbers using more/less words: up to 5 at Preschool 2, up to 10 at Balvatika.", ""),
    "N0.2.3": (["IL 3.11"], "finer", "high", "Identifies numerals with their numbers and writes numerals up to 9.", "NIPUN has one outcome for recognising and writing; we split it into two skills."),
    "N0.2.4": (["IL 3.11"], "finer", "high", "Identifies numerals with their numbers and writes numerals up to 9.", "NIPUN has one outcome for recognising and writing; we split it into two skills."),
    # ── Numeracy: Grade 1 ──────────────────────────────────────────────────
    "N1.1.1": (["ILM 4.27"], "exact", "high", "Observes, extends and creates patterns of shapes, numbers and sounds.", ""),
    "N1.2.1": (["ILM 4.10", "ILM 5.10"], "related", "medium", "Counts forward and backward from a number: up to 20 in Class 1, up to 99 in Class 2.", "Our target (to 100) sits between NIPUN's Class 1 and Class 2."),
    "N1.3.1": (["ILM 4.14"], "exact", "high", "Builds addition facts up to 18 with concrete objects and uses them in daily life.", ""),
    "N1.4.1": (["IL 3.21", "IL 2.21"], "related", "medium", "Compares two objects by length (Preschool 2) and three objects as longest or shortest (Balvatika).", "NIPUN expects direct comparison before Class 1."),
    "N1.5.1": (["ILM 5.25"], "exact", "medium", "Identifies and describes basic 2-D shapes, including their sides and corners.", "NIPUN places this in Class 2; we teach it in Grade 1."),
    "N1.2.2": (["ILM 4.9"], "exact", "high", "Counts objects up to 20, with objects and with pictures.", ""),
    "N1.3.2": (["ILM 4.15"], "related", "medium", "Builds subtraction facts up to 9 with concrete objects and uses them in daily life.", "Our range (minuend up to 18) is wider than NIPUN's Class 1 statement."),
    "N1.4.2": (["IL 4.7", "IL 3.7"], "exact", "medium", "Describes a daily routine in order, using words such as morning, afternoon, evening, night.", ""),
    "N1.5.2": (["ILM 4.25"], "exact", "high", "Identifies and describes 3-D shapes by their features (cube, sphere, cylinder).", ""),
    "N1.2.3": (["ILM 4.11"], "exact", "high", "Identifies numerals with their numbers and writes numerals up to 99.", ""),
    "N1.3.3": (["ILM 4.14", "ILM 4.15", "ILM 5.19"], "related", "medium", "Applies addition and subtraction facts to daily-life problems; Class 2 adds choosing the operation.", ""),
    "N1.2.4": (["ILM 5.9", "ILM 4.11"], "related", "low", "Counts objects up to 100 in groups of tens (Class 2); numerals up to 99 (Class 1).", "NIPUN does not name place value until Classes 2 and 3."),
    "N1.2.5": (["ILM 5.13", "ILM 4.13"], "exact", "medium", "Compares two-digit numbers and forms the greatest and smallest (Class 2); compares numbers up to 20 (Class 1).", "NIPUN places two-digit comparison in Class 2."),
    "N1.2.6": (["IL 5.6", "IL 6.6"], "related", "medium", "Applies ordering to numbers and measurements (Class 2); ascending and descending order (Class 3).", ""),
    # ── Numeracy: Grade 2 ──────────────────────────────────────────────────
    "N2.2.1": (["ILM 5.11"], "exact", "high", "Reads and writes number names and numerals up to 999.", ""),
    "N2.3.1": (["ILM 5.14"], "finer", "high", "Develops own strategies to add two numbers with a sum up to 99 and applies them to daily-life problems.", "NIPUN has one outcome; we split it into without and with regrouping."),
    "N2.4.1": (["ILM 4.21", "ILM 5.21"], "exact", "medium", "Measures short lengths with non-uniform units such as finger or hand span (Class 1), then uniform non-standard units (Class 2).", "NIPUN places hand-span measuring in Class 1."),
    "N2.5.1": ([], "none", "medium", "", "The annexure's Class 1 to 3 outcomes do not mention symmetry."),
    "N2.6.1": (["ILM 4.28", "ILM 5.28"], "related", "medium", "Collects, records and interprets simple information from visuals (Class 1); draws inferences from data (Class 2).", ""),
    "N2.2.2": (["ILM 5.12", "ILM 6.11"], "related", "low", "Uses zero in the place value system (Class 2); numbers up to 9999 using place value (Class 3).", ""),
    "N2.3.2": (["ILM 5.14"], "finer", "high", "Develops own strategies to add two numbers with a sum up to 99 and applies them to daily-life problems.", "NIPUN has one outcome; we split it into without and with regrouping."),
    "N2.4.2": (["ILM 5.29", "ILM 6.29"], "exact", "high", "Identifies days of the week and months on a calendar (Class 2); a particular date and its day (Class 3).", ""),
    "N2.2.3": (["ILM 6.13"], "exact", "medium", "Compares and forms the greatest and smallest three-digit numbers.", "NIPUN places this in Class 3; we teach it in Grade 2."),
    "N2.3.3": (["ILM 5.15"], "finer", "high", "Develops own strategies to subtract two numbers up to 99 and applies them to daily-life problems.", "NIPUN has one outcome; we split it into without and with borrowing."),
    "N2.4.3": (["ILM 5.20", "ILM 4.20"], "exact", "high", "Represents an amount using notes and coins: up to Rs 20 in Class 1, up to Rs 100 in Class 2.", ""),
    "N2.2.4": (["ILM 5.27", "ILM 5.9"], "related", "medium", "Generalises number patterns such as tables and the 1 to 100 grid; counts in groups of tens.", ""),
    "N2.3.4": (["ILM 5.15"], "finer", "high", "Develops own strategies to subtract two numbers up to 99 and applies them to daily-life problems.", "NIPUN has one outcome; we split it into without and with borrowing."),
    "N2.3.5": (["ILM 5.19"], "exact", "high", "Chooses addition or subtraction to solve problems in a familiar situation.", ""),
    "N2.3.6": (["ILM 5.17", "ILM 4.17"], "exact", "medium", "Repeated addition (Class 1); the idea of multiplication and the tables of 2, 3 and 4 (Class 2).", ""),
    # ── Numeracy: Grade 3 ──────────────────────────────────────────────────
    "N3.2.1": (["ILM 6.11"], "exact", "high", "Reads and writes number names and numerals up to 9999 using place value.", ""),
    "N3.3.1": (["ILM 6.14"], "exact", "high", "Appreciates the standard algorithm for addition with sums up to 999 and applies it to daily-life problems.", ""),
    "N3.4.1": (["ILM 6.21"], "exact", "high", "Estimates and measures length and distance in centimetres and metres and relates the units.", ""),
    "N3.5.1": ([], "none", "medium", "", "Angles are not named in the annexure's Class 1 to 3 outcomes."),
    "N3.6.1": (["ILM 6.28"], "related", "medium", "Records data with tally marks, represents it pictorially and draws conclusions.", "Bar graphs are not named."),
    "N3.2.2": (["ILM 6.11"], "finer", "medium", "Reads and writes numbers up to 9999 using place value.", "Place value is one part of this NIPUN outcome."),
    "N3.3.2": (["ILM 6.15"], "exact", "high", "Appreciates the standard algorithm for subtraction up to 999 and applies it to daily-life problems.", ""),
    "N3.4.2": (["IL 6.7"], "related", "low", "Sequences events by their duration in days, months and hours.", "Reading a clock is not named in the annexure."),
    "N3.5.2": ([], "none", "medium", "", "Perimeter is not named in the annexure's Class 1 to 3 outcomes."),
    "N3.6.2": (["ILM 6.28", "ILM 4.28"], "related", "medium", "Records data with tally marks and pictures; collects and records simple information (Class 1).", "Tables are not named."),
    "N3.2.3": (["ILM 6.13", "IL 6.6"], "related", "medium", "Compares three-digit numbers; orders numbers in ascending and descending order.", "Our four-digit range is above NIPUN's three-digit statement."),
    "N3.3.3": (["ILM 5.17", "ILM 6.17"], "exact", "high", "Builds and applies multiplication tables in daily life: 2, 3 and 4 (Class 2), then 5 to 10 (Class 3).", ""),
    "N3.4.3": (["ILM 6.22"], "exact", "high", "Weighs objects in grams and kilograms using a simple balance.", ""),
    "N3.3.4": (["ILM 6.17"], "related", "low", "Constructs and applies multiplication facts (tables) of 5 to 10 in daily life.", "Multiplying a two-digit number goes beyond the table facts the annexure names."),
    "N3.3.5": (["ILM 5.18", "ILM 6.18"], "exact", "high", "Division as equal sharing (Class 2) and as equal grouping or repeated subtraction (Class 3).", ""),
    "N3.3.6": (["ILM 6.19"], "related", "medium", "Chooses and applies addition or subtraction to solve problems in a situation.", "NIPUN names addition and subtraction only; multi-step problems and multiplication go beyond it."),
    # ── Literacy: Balvatika ────────────────────────────────────────────────
    "L0.1.1": (["HW 2.4", "HW 3.4"], "related", "medium", "Follows two-line simple instructions (Preschool 2); follows instructions with simple rules (Balvatika).", "This sits in the health-and-wellbeing goal, not the language goal."),
    "L0.2.1": (["ECL1 4.4"], "exact", "medium", "Identifies rhyming words in familiar poems and songs.", "NIPUN places this in Class 1; we teach it in Balvatika."),
    "L0.3.1": (["ECL1 4.8", "ECL1 3.6"], "related", "low", "Shows awareness of letter shapes and sounds while reading.", "NIPUN does not say how many letters."),
    "L0.7.1": (["HW 3.18", "ECL1 1.9"], "related", "low", "Fine-motor control for drawing and writing (Balvatika); scribbling and drawing lines (Preschool 1).", ""),
    "L0.1.2": (["ECL1 3.1", "ECL1 4.1"], "related", "medium", "Talks with teachers and friends in own language; asks questions to gain information (Class 1).", ""),
    "L0.2.2": (["ECL1 2.7", "ECL1 3.7"], "related", "low", "Identifies a particular sound in different words and repeated sounds in words.", "Clapping syllables is not named."),
    "L0.3.2": (["ECL1 3.8", "ECL1 4.8"], "related", "medium", "Uses letter-sound association when predicting text (Balvatika); letter and sound awareness (Class 1).", ""),
    "L0.7.2": (["ECL1 3.9", "HW 4.18"], "related", "low", "Takes interest in writing own and friends' names; fine-motor precision for writing.", ""),
    "L0.2.3": (["ECL1 2.7"], "exact", "medium", "Identifies a particular sound in different words.", "NIPUN places this at Preschool 2."),
    "L0.1.3": (["ECL1 3.3", "ECL1 3.2"], "exact", "medium", "Shares and narrates experiences and stories in own language, with the help of pictures.", ""),
    # ── Literacy: Grade 1 ──────────────────────────────────────────────────
    "L1.2.1": (["ECL1 4.8"], "related", "low", "Letter and sound awareness while reading.", "Blending sounds is not named."),
    "L1.3.1": (["ECL1 4.8"], "related", "medium", "Awareness of letter shapes and sounds while reading and writing.", "The annexure gives no letter list."),
    "L1.4.1": (["ECL1 4.5"], "related", "low", "Predicts and attempts to make meaning of text.", ""),
    "L1.5.1": (["ECL1 4.5", "ECL1 4.6"], "related", "medium", "Relates picture with text to predict and understand; attempts to make meaning of text.", "Sentence-reading targets (4 to 5 simple words) are in the Lakshya, outside this annexure."),
    "L1.6.1": (["ECL1 4.3", "ECL1 5.2"], "related", "medium", "Connects personal experiences with familiar stories and talks about them; talks about characters.", ""),
    "L1.7.1": (["ECL1 4.8", "ECL1 4.9"], "related", "medium", "Uses letter and sound awareness while writing; labels own drawings.", ""),
    "L1.2.2": (["ECL1 4.8"], "related", "low", "Letter and sound awareness while reading and writing.", "Segmenting into phonemes is not named."),
    "L1.3.2": (["ECL1 4.8"], "related", "low", "Letter and sound awareness while reading and writing.", "Matras are not named."),
    "L1.4.2": (["ECL1 4.5"], "related", "low", "Predicts and attempts to make meaning of text.", ""),
    "L1.6.2": (["ECL1 5.6", "ECL1 3.6"], "related", "medium", "Understands events and characters in a picture story (Class 2); arranges pictures in event order (Balvatika).", ""),
    "L1.7.2": (["ECL1 4.7", "ECL1 4.8"], "related", "medium", "Writes a few words about familiar things; uses letter-sound awareness while writing.", ""),
    "L1.3.3": (["ECL1 4.8"], "related", "low", "Letter and sound awareness while reading and writing.", "Matras are not named."),
    "L1.7.3": (["ECL1 5.8"], "related", "medium", "Writes with appropriate words and sentences in conventional writing.", "NIPUN places this in Class 2."),
    "L1.3.4": (["ECL1 4.8"], "related", "low", "Letter and sound awareness while reading and writing.", ""),
    # ── Literacy: Grade 2 ──────────────────────────────────────────────────
    "L2.3.1": (["ECL1 5.5"], "related", "low", "Attempts to read familiar and unfamiliar text using sound-symbol association.", "Conjuncts are not named."),
    "L2.4.1": (["ECL1 5.5"], "related", "low", "Attempts to read familiar and unfamiliar text using sound-symbol association.", ""),
    "L2.5.1": (["ECL1 6.6", "ECL1 5.5"], "related", "low", "Reads familiar written texts with appropriate flow (Class 3).", "Words-per-minute targets are in the Lakshya, not in this annexure."),
    "L2.6.1": (["ECL1 5.7", "ECL1 5.5"], "related", "medium", "Talks about characters and events from stories and texts; reads and responds to children's literature.", ""),
    "L2.7.1": (["ECL1 5.8"], "related", "medium", "Writes using appropriate words and sentences (conventional writing).", "Dictation is not named."),
    "L2.3.2": (["ECL1 5.5"], "related", "low", "Attempts to read familiar and unfamiliar text using sound-symbol association.", ""),
    "L2.4.2": (["ECL1 5.5"], "related", "low", "Attempts to read familiar and unfamiliar text; identifies words using prior knowledge.", ""),
    "L2.5.2": (["ECL1 6.6", "ECL1 6.4"], "related", "medium", "Reads with flow and intonation; identifies punctuation marks in texts.", "NIPUN places this in Class 3; we teach it in Grade 2."),
    "L2.6.2": (["ECL1 5.7", "ECL1 6.5"], "related", "low", "Talks about events in texts; reads with understanding and writes about texts briefly.", "Main idea is not named."),
    "L2.7.2": (["ECL1 5.8", "ECL1 5.9"], "related", "medium", "Writes with appropriate sentences; extends a story in writing.", ""),
    "L2.3.3": (["ECL1 5.5"], "related", "low", "Attempts to read familiar and unfamiliar text using sound-symbol association.", ""),
    "L2.6.3": (["ECL1 5.5"], "exact", "medium", "Predicts and reads children's literature in a familiar context.", ""),
    "L2.7.3": (["ECL1 6.6"], "exact", "medium", "Uses naming words, action words, repetition and punctuation marks while writing.", "NIPUN places this in Class 3; we teach it in Grade 2."),
    # ── Literacy: Grade 3 ──────────────────────────────────────────────────
    "L3.3.1": (["ECL1 6.5"], "related", "low", "Relates unfamiliar words from different texts while reading.", ""),
    "L3.4.1": (["ECL1 5.5", "ECL1 6.5"], "related", "medium", "Reads unfamiliar text using sound-symbol association and prior knowledge; relates unfamiliar words.", ""),
    "L3.5.1": (["ECL1 6.6"], "related", "low", "Reads familiar written texts with appropriate flow.", "Words-per-minute targets are in the Lakshya, not in this annexure."),
    "L3.6.1": (["ECL1 6.3", "ECL1 6.5"], "related", "low", "Converses, asks questions and gives opinions about characters and themes; reads with understanding.", "Inference is not named."),
    "L3.7.1": (["ECL1 6.8", "ECL1 6.9"], "related", "medium", "Writes about familiar texts in different forms; writes short messages.", ""),
    "L3.5.2": (["ECL1 6.6", "ECL1 6.4"], "exact", "medium", "Reads with flow, intonation and voice modulation; narrates with modulation, speed and fluency.", ""),
    "L3.6.2": (["ECL1 6.5"], "related", "low", "Reads with understanding different texts and writes about them briefly.", "Cause and effect is not named."),
    "L3.7.2": (["ECL1 6.6"], "related", "low", "Identifies and uses naming words, action words and punctuation in writing.", "Gender, number and tense agreement are not named."),
    "L3.6.3": (["ECL1 6.5"], "related", "medium", "Writes briefly about texts read with understanding.", ""),
    "L3.7.3": (["ECL1 6.9", "ECL1 6.8"], "exact", "medium", "Writes short messages; writes in different forms about familiar texts.", ""),
    "L3.6.4": ([], "none", "low", "", "Distinguishing fact from opinion is not named; Class 3 outcomes mention giving opinions about characters and themes."),
}

# The numeracy strands (one row of the annexure each), for the gap analysis: strand -> codes per level.
# BV = Balvatika (n=3), C1/C2/C3 = Classes 1-3 (n=4,5,6). Text is our own short paraphrase.
STRANDS = [
    ("Counting objects", {"BV": ("IL 3.9", "up to 10"), "C1": ("ILM 4.9", "up to 20"), "C2": ("ILM 5.9", "up to 100 in groups of tens"), "C3": ("ILM 6.9", "up to 1000 in tens and hundreds")}),
    ("Counting forward and backward", {"BV": ("IL 3.10", "from a number up to 9"), "C1": ("ILM 4.10", "from a number up to 20"), "C2": ("ILM 5.10", "up to 99"), "C3": ("ILM 6.10", "up to 999")}),
    ("Reading and writing numbers", {"BV": ("IL 3.11", "numerals up to 9"), "C1": ("ILM 4.11", "numerals up to 99"), "C2": ("ILM 5.11", "names and numerals up to 999"), "C3": ("ILM 6.11", "up to 9999 with place value")}),
    ("The idea of zero", {"C1": ("ILM 4.12", "develops the concept of zero"), "C2": ("ILM 5.12", "zero in the place value system"), "C3": ("ILM 6.12", "zero's properties in the four operations")}),
    ("Comparing numbers", {"BV": ("IL 3.13", "up to 10"), "C1": ("ILM 4.13", "up to 20"), "C2": ("ILM 5.13", "two-digit, greatest and smallest"), "C3": ("ILM 6.13", "three-digit, greatest and smallest")}),
    ("Addition", {"BV": ("IL 3.14", "combines two groups up to 9"), "C1": ("ILM 4.14", "facts up to 18, concrete"), "C2": ("ILM 5.14", "own strategies, sum up to 99"), "C3": ("ILM 6.14", "standard algorithm, sum up to 999")}),
    ("Subtraction", {"BV": ("IL 3.15", "takes out from a collection up to 9"), "C1": ("ILM 4.15", "facts up to 9, concrete"), "C2": ("ILM 5.15", "own strategies, up to 99"), "C3": ("ILM 6.15", "standard algorithm, up to 999")}),
    ("Relating addition and subtraction", {"C1": ("ILM 4.16", "develops the relationship"), "C2": ("ILM 5.16", "applies the relationship"), "C3": ("ILM 6.16", "applies it in 3-digit numbers")}),
    ("Multiplication", {"C1": ("ILM 4.17", "repeated addition, sum up to 20"), "C2": ("ILM 5.17", "the idea; tables of 2, 3, 4"), "C3": ("ILM 6.17", "tables of 5 to 10")}),
    ("Division", {"C2": ("ILM 5.18", "equal sharing"), "C3": ("ILM 6.18", "equal grouping, repeated subtraction")}),
    ("Choosing the operation in problems", {"C2": ("ILM 5.19", "chooses add or subtract"), "C3": ("ILM 6.19", "analyses and applies add or subtract")}),
    ("Money", {"BV": ("IL 3.20", "identifies notes"), "C1": ("ILM 4.20", "represents up to Rs 20"), "C2": ("ILM 5.20", "represents up to Rs 100"), "C3": ("ILM 6.20", "adds and subtracts amounts up to Rs 500")}),
    ("Length", {"BV": ("IL 3.21", "compares three objects"), "C1": ("ILM 4.21", "non-uniform units"), "C2": ("ILM 5.21", "uniform non-standard units"), "C3": ("ILM 6.21", "centimetres and metres")}),
    ("Weight", {"BV": ("IL 3.22", "compares two objects"), "C1": ("ILM 4.22", "compares three objects"), "C2": ("ILM 5.22", "heavier/lighter with a balance"), "C3": ("ILM 6.22", "grams and kilograms")}),
    ("Capacity", {"BV": ("IL 3.23", "compares two vessels"), "C1": ("ILM 4.23", "non-standard units"), "C2": ("ILM 5.23", "uniform non-standard units"), "C3": ("ILM 6.23", "litres")}),
    ("Temperature", {"C1": ("ILM 4.24", "hot and cold vocabulary"), "C2": ("ILM 5.24", "hotter and colder"), "C3": ("ILM 6.24", "uses a thermometer")}),
    ("Shapes", {"BV": ("IL 3.25", "2-D from faces of 3-D"), "C1": ("ILM 4.25", "3-D shapes"), "C2": ("ILM 5.25", "basic 2-D shapes"), "C3": ("ILM 6.25", "draws straight lines in orientations")}),
    ("Fractions", {"BV": ("IL 3.26", "half in daily context"), "C1": ("ILM 4.26", "half and whole by folding"), "C2": ("ILM 5.26", "half, quarter and whole"), "C3": ("ILM 6.26", "half, one-fourth, three-fourths")}),
    ("Patterns", {"BV": ("IL 3.27", "creates patterns"), "C1": ("ILM 4.27", "shapes, numbers, sounds"), "C2": ("ILM 5.27", "number patterns, tables, grid"), "C3": ("ILM 6.27", "patterns up to 3 digits")}),
    ("Data handling", {"C1": ("ILM 4.28", "collects, records, interprets"), "C2": ("ILM 5.28", "draws inferences from data"), "C3": ("ILM 6.28", "tally marks, pictorial")}),
    ("Calendar", {"BV": ("IL 3.29", "names of days and months"), "C1": ("ILM 4.29", "names of days and months"), "C2": ("ILM 5.29", "days and months on a calendar"), "C3": ("ILM 6.29", "a particular date and its day")}),
    ("Time and sequence of events", {"BV": ("IL 3.7", "time-related events in a story"), "C1": ("IL 4.7", "daily routine in order"), "C2": ("IL 5.7", "events by duration in days"), "C3": ("IL 6.7", "duration in days, months, hours")}),
]
