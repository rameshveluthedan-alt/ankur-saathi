"""
The names of the demonstration accounts, in ONE place (docs/DEMO_ACCESS.md). An account is signed into with a 6-character EMPLOYEE CODE
(letters and digits, capitals): the role is NEVER read from the letters, it is stored with the account.

  MPT101  the demo teacher: the 30-child multi-grade class
  MPT102 to MPT106 (up to MPT198)  test teachers, each with their own multi-grade class (use one each)
  MPT199  the practice account: change its password, reset it as the leader, lock it out; nothing else is affected
  MPA101  the school leader (the head teacher): teaches grade 1, looks after the school's accounts

Accounts made before employee codes were named 'hash_' + a phone number; `migrate_to_employee_codes.py` renames them (data stays with the account).
"""
import re

DEMO_SCHOOL = "MP-DEMO-001"
LEADER = "MPA101"
DEMO_TEACHER = "MPT101"
PRACTICE = "MPT199"
TEST_CODE_RE = r"^MPT(10[2-9]|1[1-8][0-9]|19[0-8])$"          # MPT102 to MPT198: never the demo teacher MPT101 and never the practice account MPT199
OLD_TEST_SCHOOL_PREFIX = "MP-TEST-"
OLD_TEST_ADMIN = "hash_9000000100"                              # the test school's admin of the old layout: no longer needed (the leader of the demo school is the only admin)
OLD_FIXED = {"hash_9876543210": DEMO_TEACHER, "hash_9876500000": LEADER, "hash_9000000199": PRACTICE}
_OLD_TEST = re.compile(r"^hash_90000001(0[1-9]|[1-8][0-9]|9[0-7])$")       # 9000000101 to 9000000197


def test_code(n: int) -> str:
    """Test teacher number 1, 2, 3 ... is MPT102, MPT103, MPT104 ... (up to MPT198)."""
    if not 1 <= n <= 97:
        raise ValueError("There can be 1 to 97 test teachers.")
    return f"MPT{101 + n}"


def new_code_for(old: str):
    """The employee code an old phone-number identifier becomes, or None (the old test admin goes away; anything else is left alone)."""
    if old in OLD_FIXED:
        return OLD_FIXED[old]
    m = _OLD_TEST.match(old or "")
    return test_code(int(m.group(1))) if m else None


async def wipe_teachers(db, ids: list):
    """Remove teachers and everything hanging off them (evidence and plans are not cascaded by the schema)."""
    if not ids:
        return 0
    await db.execute("DELETE FROM assessment_evidence WHERE teacher_id = ANY($1::uuid[])", ids)
    await db.execute("DELETE FROM child_competency_status WHERE child_id IN (SELECT id FROM children WHERE teacher_id = ANY($1::uuid[]))", ids)
    await db.execute("DELETE FROM daily_plans WHERE teacher_id = ANY($1::uuid[])", ids)
    await db.execute("DELETE FROM teachers WHERE id = ANY($1::uuid[])", ids)
    return len(ids)
