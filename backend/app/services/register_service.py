"""
Class register: enrol a class in bulk, and register a new teacher.

A register file lists the children by GRADE and the school's own ROLL number, and optionally a starting level per subject
(the teacher's own judgement). It holds no names: the app identifies children by number only.

Numbering. Everything in the app looks a child up by one number within the teacher's class. In a multi-grade class the
school's rolls repeat (roll 5 of Grade 1 and roll 5 of Grade 3), so:
  * if the rolls are unique across the whole class (1 to 30 straight through), they are used as they are ("plain");
  * otherwise each child's CLASS NUMBER carries the grade: grade x 100 + roll (Grade 3, roll 5 = 305; Balvatika keeps its
    roll). The child writes that one number on a worksheet, so no second box is needed, and the school roll and grade are
    stored so the app can show "Grade 3, roll 5".

Nothing is written until the teacher has seen the preview and confirmed.
"""

import csv
import io
import re
import unicodedata

from app.services import names_service

DOMAINS = ("numeracy", "r1_literacy")
LEVELS = ("beginner", "progressor", "proficient")
DEFAULT_LEVEL = "progressor"        # until a baseline or the daily evidence says otherwise

TEMPLATE_CSV = (
    "grade,roll_number,name,numeracy_level,literacy_level\n"
    "# One child per line. grade is 0 (Balvatika), 1, 2 or 3. roll_number is the school's own roll (1 to 99).\n"
    "# name is optional. Names stay in this app, visible only to you: they are never sent to the AI and never go into the officer report.\n"
    "# numeracy_level and literacy_level are optional: beginner, progressor or proficient (or शुरुआती, प्रगतिशील, दक्ष).\n"
    "# Leave the levels empty if you do not know yet: the child starts as progressor.\n"
    "# Delete these example lines, then add your class:\n"
    "# 1,5,Asha,beginner,progressor\n"
    "# 3,5,Ravi,proficient,proficient\n"
)

_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_HEADERS = {
    "grade": {"grade", "class", "std", "standard", "कक्षा", "ग्रेड", "श्रेणी"},
    "roll": {"roll", "rollno", "rollnumber", "roll_number", "rollnum", "रोल", "रोलनंबर", "रोलनं", "क्रमांक"},
    "name": {"name", "studentname", "childname", "student", "child", "नाम", "बच्चेकानाम", "छात्रकानाम", "विद्यार्थीकानाम"},
    "numeracy": {"numeracy", "numeracylevel", "numeracy_level", "maths", "math", "गणित", "गणितस्तर"},
    "literacy": {"literacy", "literacylevel", "literacy_level", "hindi", "language", "हिंदी", "हिन्दी", "भाषा", "साक्षरता"},
}
_LEVEL_WORDS = {
    "beginner": "beginner", "शुरुआती": "beginner", "आरंभिक": "beginner",
    "progressor": "progressor", "प्रगतिशील": "progressor",
    "proficient": "proficient", "दक्ष": "proficient",
}


def _clean(v) -> str:
    return unicodedata.normalize("NFC", str(v if v is not None else "")).strip().translate(_DIGITS)


def _header_key(h) -> str:
    return re.sub(r"[\s._\-]+", "", _clean(h).lower())


def normalise_grade(raw):
    """'grade_2' for 2, 'Grade 2', 'कक्षा 2', '२', 'II'; 'balvatika' for 0 / Balvatika / बालवाटिका. None if not a grade we serve."""
    v = _clean(raw).lower()
    if not v:
        return None
    if v in ("balvatika", "बालवाटिका", "bal vatika", "0", "grade_0", "pre-primary", "preprimary"):
        return "balvatika"
    m = re.fullmatch(r"(?:grade|class|कक्षा|ग्रेड|std|standard)?[\s_\-.]*([123])(?:st|nd|rd)?", v)
    if m:
        return f"grade_{m.group(1)}"
    roman = {"i": 1, "ii": 2, "iii": 3}.get(re.sub(r"^(?:grade|class|std|standard)[\s_\-.]*", "", v))
    return f"grade_{roman}" if roman else None


def grade_number(grade: str) -> int:
    return 0 if grade == "balvatika" else int(grade.split("_")[1])


def normalise_level(raw):
    """(level or None, ok). Empty is fine (the default is used); an unrecognised word is not."""
    v = _clean(raw).lower()
    if not v:
        return None, True
    if v in _LEVEL_WORDS:
        return _LEVEL_WORDS[v], True
    return None, False


def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return data.decode("latin-1")


def _rows_from_table(table: list) -> list:
    """table: a list of rows (lists of cell values), the first non-empty one being the header."""
    header_i = next((i for i, r in enumerate(table) if any(_clean(c) for c in r)), None)
    if header_i is None:
        raise ValueError("The file is empty.")
    cols = {}
    for ci, h in enumerate(table[header_i]):
        key = _header_key(h)
        for name, aliases in _HEADERS.items():
            if key in {_header_key(a) for a in aliases}:
                cols.setdefault(name, ci)
    if "grade" not in cols or "roll" not in cols:
        raise ValueError("The first line must have the columns grade and roll_number. Download the template and use its first line.")
    out = []
    for ri in range(header_i + 1, len(table)):
        r = table[ri]
        if not any(_clean(c) for c in r) or _clean(r[0] if r else "").startswith("#"):
            continue
        get = lambda n: r[cols[n]] if n in cols and cols[n] < len(r) else ""
        out.append({"row": ri + 1, "grade": _clean(get("grade")), "roll": _clean(get("roll")), "name": names_service.clean_name(get("name")),
                    "numeracy": _clean(get("numeracy")), "literacy": _clean(get("literacy"))})
    return out


def parse_register(data: bytes, filename: str = "") -> list:
    """CSV (commas, semicolons or tabs; UTF-8 or Excel's encodings) or Excel (.xlsx). Returns the raw rows with their line numbers."""
    name = (filename or "").lower()
    if name.endswith((".xlsx", ".xlsm")) or data[:2] == b"PK":
        try:
            from openpyxl import load_workbook
        except ImportError:
            raise ValueError("Excel files need the openpyxl library on the server. Save the sheet as CSV (UTF-8) and upload that.")
        ws = load_workbook(io.BytesIO(data), data_only=True).active
        return _rows_from_table([[c for c in row] for row in ws.iter_rows(values_only=True)])
    text = _decode(data)
    header = next((ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")), "")
    counts = {d: header.count(d) for d in (",", ";", "\t")}          # the separator that appears most in the header line
    delim = max(counts, key=lambda d: counts[d]) if any(counts.values()) else ","
    return _rows_from_table(list(csv.reader(io.StringIO(text), delimiter=delim)))


def plan_register(rows: list, existing: list, teacher_grades=None) -> dict:
    """
    Validate and number the rows. existing: the teacher's current children as
    [{'roll_number', 'enrolled_grade', 'school_roll'}]. Returns the rows with status new / exists / error, and the numbering used.
    """
    teacher_grades = set(teacher_grades or [])
    out, seen = [], {}
    for raw in rows:
        r = {"row": raw.get("row"), "errors": [], "warnings": [], "status": "new"}
        r["name"] = names_service.clean_name(raw.get("name"))
        if len(r["name"]) > names_service.MAX_NAME:
            r["errors"].append(f"the name is longer than {names_service.MAX_NAME} characters")
        r["grade"] = normalise_grade(raw.get("grade"))
        if r["grade"] is None:
            r["errors"].append(f"grade '{raw.get('grade')}' is not 0, 1, 2 or 3")
        roll = _clean(raw.get("roll"))
        if re.fullmatch(r"\d{1,2}", roll) and 1 <= int(roll) <= 99:
            r["school_roll"] = int(roll)
        else:
            r["school_roll"] = None
            r["errors"].append(f"roll '{raw.get('roll')}' must be a number from 1 to 99")
        for subject, key in (("numeracy", "numeracy"), ("literacy", "literacy")):
            level, ok = normalise_level(raw.get(key))
            r[f"{subject}_level"] = level or DEFAULT_LEVEL
            r[f"{subject}_given"] = level is not None
            if not ok:
                r["errors"].append(f"{subject} level '{raw.get(key)}' is not beginner, progressor or proficient")
        if not r["errors"]:
            k = (r["grade"], r["school_roll"])
            if k in seen:
                r["errors"].append(f"duplicate of line {seen[k]}: grade {grade_number(r['grade'])}, roll {r['school_roll']}")
            else:
                seen[k] = r["row"]
            if teacher_grades and r["grade"] not in teacher_grades:
                r["warnings"].append(f"grade {grade_number(r['grade'])} is not in your profile: it will be added")
        out.append(r)

    def match(ch, r):
        """The same child: same grade and same school roll (for a child enrolled before this register existed, its class number was its roll)."""
        school_roll = ch["roll_number"] if ch.get("school_roll") is None else ch["school_roll"]
        return ch["enrolled_grade"] == r["grade"] and school_roll == r["school_roll"]

    for r in out:
        if r["errors"]:
            r["status"] = "error"
            continue
        found = next((ch for ch in existing if match(ch, r)), None)
        if found:
            r["status"] = "exists"
            if r["name"] and r["name"] != (found.get("name") or ""):     # a register that adds or corrects a name for a child already enrolled
                r["name_action"], r["child_id"] = ("update" if found.get("name") else "set"), found.get("id")
    new = [r for r in out if r["status"] == "new"]

    taken = {ch["roll_number"] for ch in existing}
    plain_rolls = [r["school_roll"] for r in new]
    plain_ok = (len(set(plain_rolls)) == len(plain_rolls) and not (set(plain_rolls) & taken) and not any(t >= 100 for t in taken))
    numbering = "plain" if plain_ok else "composite"
    for r in new:
        r["class_number"] = r["school_roll"] if numbering == "plain" else grade_number(r["grade"]) * 100 + r["school_roll"]
        if r["class_number"] in taken:
            r["status"], r["errors"] = "error", [f"class number {r['class_number']} is already used by another child"]
        taken.add(r["class_number"])
    for r in out:
        r.setdefault("class_number", None)
    by_grade = {}
    for r in out:
        if r["status"] == "new":
            by_grade[r["grade"]] = by_grade.get(r["grade"], 0) + 1
    warnings = []
    if new and numbering == "composite":
        warnings.append("The school rolls repeat across grades, so each child gets a class number that carries the grade (Grade 3, roll 5 = 305). "
                        "Children write that number on worksheets.")
    unplaced = sum(1 for r in new if not r["numeracy_given"] or not r["literacy_given"])
    if unplaced:
        warnings.append(f"{unplaced} child(ren) have no starting level for a subject: they start as progressor until a baseline or the daily evidence says otherwise.")
    names_to_save = sum(1 for r in out if r["status"] == "new" and r["name"]) + sum(1 for r in out if r.get("name_action"))
    return {"rows": out, "numbering": numbering, "by_grade": by_grade, "warnings": warnings, "names_to_save": names_to_save,
            "counts": {"new": len(new), "exists": sum(1 for r in out if r["status"] == "exists"), "error": sum(1 for r in out if r["status"] == "error"), "total": len(out)}}


async def _existing(db, teacher_id):
    if await names_service.table_exists(db):
        q = """SELECT c.id, c.roll_number, c.enrolled_grade, c.school_roll, cn.name FROM children c
               LEFT JOIN child_names cn ON cn.child_id = c.id WHERE c.teacher_id = $1 AND c.is_active = TRUE"""
    else:
        q = "SELECT id, roll_number, enrolled_grade, school_roll, NULL AS name FROM children WHERE teacher_id = $1 AND is_active = TRUE"
    return [dict(r) for r in await db.fetch(q, teacher_id)]


async def preview_register(db, teacher_id: str, data: bytes, filename: str) -> dict:
    teacher = await db.fetchrow("SELECT enrolled_grades FROM teachers WHERE id = $1", teacher_id)
    if not teacher:
        raise LookupError("Teacher not found")
    rows = parse_register(data, filename)
    if not rows:
        raise ValueError("No children found in the file.")
    if len(rows) > 400:
        raise ValueError("A register can have at most 400 children per upload.")
    plan = plan_register(rows, await _existing(db, teacher_id), teacher["enrolled_grades"])
    plan["raw_rows"] = rows              # what the commit step sends back, so it re-validates exactly this
    plan["names_available"] = await names_service.table_exists(db)
    if plan["names_to_save"] and not plan["names_available"]:
        plan["warnings"].append("Names were found but cannot be saved yet: run db/schema/08_child_names.sql and restart the backend. Everything else will be enrolled.")
    return plan


async def _default_competency(db, domain: str, grade: str, cache: dict):
    key = (domain, grade)
    if key not in cache:
        cache[key] = await db.fetchval(
            """SELECT c.id FROM competencies c JOIN subdomains s ON s.id = c.subdomain_id
               WHERE s.domain_id = $1 AND c.grade_level = $2 AND c.is_active ORDER BY s.sort_order, c.sort_order LIMIT 1""", domain, grade)
    return cache[key]


async def commit_register(db, teacher_id: str, rows: list, filename: str = "") -> dict:
    """Enrol the new children (the same planning as the preview, so a changed request cannot slip anything in)."""
    teacher = await db.fetchrow("SELECT enrolled_grades FROM teachers WHERE id = $1", teacher_id)
    if not teacher:
        raise LookupError("Teacher not found")
    plan = plan_register(rows, await _existing(db, teacher_id), teacher["enrolled_grades"])
    new = [r for r in plan["rows"] if r["status"] == "new"]
    cache, added, names_saved = {}, 0, 0
    names_ok = await names_service.table_exists(db)
    async with db.transaction():
        grades = sorted(set(teacher["enrolled_grades"]) | {r["grade"] for r in new}, key=lambda g: grade_number(g))
        await db.execute("UPDATE teachers SET enrolled_grades = $2, is_multigrade = $3 WHERE id = $1", teacher_id, grades, len(grades) > 1)
        for r in new:
            child_id = await db.fetchval(
                """INSERT INTO children (teacher_id, roll_number, enrolled_grade, school_roll) VALUES ($1, $2, $3, $4)
                   ON CONFLICT (teacher_id, roll_number) DO NOTHING RETURNING id""", teacher_id, r["class_number"], r["grade"], r["school_roll"])
            if not child_id:
                continue
            added += 1
            if r["name"] and names_ok:
                await names_service.save_name(db, child_id, r["name"])
                names_saved += 1
            for domain, level in (("numeracy", r["numeracy_level"]), ("r1_literacy", r["literacy_level"])):
                comp = await _default_competency(db, domain, r["grade"], cache)
                if comp:
                    await db.execute(
                        """INSERT INTO child_lakshya_positions (child_id, domain_id, current_competency_id, bpp_level, source, last_assessed)
                           VALUES ($1, $2, $3, $4, 'baseline_internal', NOW()) ON CONFLICT (child_id, domain_id) DO NOTHING""", child_id, domain, comp, level)
        if names_ok:
            for r in plan["rows"]:
                if r.get("name_action") and r.get("child_id"):
                    await names_service.save_name(db, r["child_id"], r["name"])
                    names_saved += 1
        await db.execute("INSERT INTO register_uploads (teacher_id, filename, rows_total, rows_added, rows_skipped, numbering) VALUES ($1, $2, $3, $4, $5, $6)",
                         teacher_id, filename, plan["counts"]["total"], added, plan["counts"]["total"] - added, plan["numbering"])
    total = await db.fetchval("SELECT count(*) FROM children WHERE teacher_id = $1 AND is_active = TRUE", teacher_id)
    return {"added": added, "skipped_existing": plan["counts"]["exists"], "errors": plan["counts"]["error"], "numbering": plan["numbering"],
            "total_children": total, "enrolled_grades": grades, "names_saved": names_saved}


class ConsentRequired(ValueError):
    """A NEW school may only be created by someone who confirms the consent statement (the API asks for it; the operator's own scripts do not)."""


async def register_teacher(db, phone_hash: str, school_code: str, grades: list, pin_hash: str = None, join_code: str = None, enforce_join: bool = True,
                           require_consent: bool = False, consent_version: str = None) -> dict:
    """
    A new teacher. A NEW school code creates the school: its first teacher becomes the school admin and the school gets a join code.
    For a school that already exists the teacher must give its join code (which the admin shares), so that knowing a school's name
    is not enough to attach to it. enforce_join=False is for the operator's own scripts only.
    require_consent=True (the API sets it): a NEW school is created only when consent_version names the current wording of the consent statement, and the confirmation is kept in the same
    transaction as the school and its admin, so a school cannot exist without it. Joining an existing school asks for nothing: the school confirmed when it was created.
    """
    import hmac
    from app.services import auth_service
    code = re.sub(r"\s+", "", _clean(school_code)).upper()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9\-_]{2,24}", code):
        raise ValueError("School code must be 3 to 25 letters, digits or dashes.")
    wanted = sorted({g for g in (normalise_grade(x) for x in grades or []) if g}, key=grade_number)
    if not wanted:
        raise ValueError("Choose at least one grade (0, 1, 2 or 3).")
    ident = _clean(phone_hash)
    as_code = auth_service.normalise_code(ident)          # an employee code (six letters or digits) is stored in capitals
    if not (as_code or len(ident) >= 8):                   # (an account made before employee codes is named 'hash_' + a phone number)
        raise ValueError("Enter an employee code: six letters or digits, for example MPT101.")
    phone_hash = as_code or phone_hash
    if await db.fetchval("SELECT 1 FROM teachers WHERE phone_hash = $1", phone_hash):
        raise FileExistsError("This employee code is already registered. Please log in.")
    if require_consent:
        await auth_service.ensure_consent_table(db)            # before the transaction: a failure here cannot abort it
    async with db.transaction():
        school = await db.fetchrow("SELECT id, join_code FROM schools WHERE school_code = $1", code)
        role, new_code = "teacher", None
        if not school:
            if require_consent and not consent_version:
                raise ConsentRequired("To create a new school, confirm the consent statement. (नया स्कूल बनाने के लिए सहमति की पुष्टि करें।)")
            if require_consent and consent_version != auth_service.CONSENT_VERSION:
                raise ConsentRequired("The consent wording has changed: reload the page and read it again. (शब्द बदल गए हैं: पेज दोबारा खोलकर पढ़ें।)")
            from app.services.auth_service import new_join_code
            new_code = new_join_code()
            school_id = await db.fetchval("INSERT INTO schools (state_id, school_code, join_code) VALUES ('mp', $1, $2) RETURNING id", code, new_code)
            role = "school_admin"
        else:
            school_id = school["id"]
            if enforce_join:
                given = re.sub(r"\s+", "", _clean(join_code)).upper()
                if not school["join_code"]:
                    raise PermissionError("This school has no join code yet. Ask its school admin to create one.")
                if not given or not hmac.compare_digest(given, school["join_code"]):
                    raise PermissionError("The school join code is missing or wrong. Ask your school admin for it.")
        teacher_id = await db.fetchval(
            """INSERT INTO teachers (school_id, phone_hash, enrolled_grades, is_multigrade, role, pin_hash, pin_changed_at)
               VALUES ($1, $2, $3, $4, $5, $6, CASE WHEN $6::text IS NULL THEN NULL ELSE now() END) RETURNING id""",
            school_id, phone_hash, wanted, len(wanted) > 1, role, pin_hash)
        if new_code and require_consent:
            await auth_service.record_consent(db, school_id, teacher_id)          # the school, its admin and its confirmation: together or not at all
    return {"teacher_id": str(teacher_id), "school_code": code, "enrolled_grades": wanted, "total_children": 0, "role": role, "join_code": new_code}
