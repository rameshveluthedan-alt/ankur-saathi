"""
PIN rules, PIN hashing and signed tokens. No database needed.

    python backend/tests/test_auth_pin.py
"""
import os
import sys
import time

os.environ.setdefault("SESSION_SECRET", "test-secret-for-unit-tests")
os.environ["PIN_HASH_ITERATIONS"] = "2000"          # fast for tests; the real default is 600,000
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")]

from app.core.config import get_settings
from app.services import auth_service as a

failures = []


def check(label, ok):
    print(f"  {'OK ' if ok else 'FAIL'} {label}")
    if not ok:
        failures.append(label)


print("password rules (6 to 12 letters or digits; a 6-digit number is fine)")
for pw, ok, why in (("482615", True, "six digits: easy to key in on a phone"), ("k7m4qx", True, "six letters and digits"), ("Sunita26", True, "letters and digits, in capitals and small"), ("a1b2c3d4e5f6", True, "twelve is the longest"),
                    ("246810", True, "even steps are not a run"), ("4826", False, "too short (a shared demo account keeps its fixed four digits, but nobody can SET one)"), ("48261599999999", False, "too long"),
                    ("48a6!5", False, "a symbol is not allowed"), ("482 615", False, "a space is not allowed"), ("111111", False, "one digit repeated"), ("aaaaaa", False, "one letter repeated"),
                    ("123456", False, "ascending run"), ("654321", False, "descending run"), ("password", False, "a common password"), ("QWERTY", False, "a common password in capitals"), ("abcdef", False, "a common password"),
                    ("000000", False, "zeros"), ("", False, "empty"), (None, False, "nothing")):
    check(f"{str(pw)!r:>18} {'allowed' if ok else 'refused'}: {why}", (a.validate_pin(pw) is None) == ok)
check("the employee code itself is refused as a password, in any case", a.validate_pin("mpt101", "MPT101") is not None and a.validate_pin("MPT101", "MPT101") is not None)
check("...but another password is fine for that code", a.validate_pin("482615", "MPT101") is None)
check("an account made before codes: the end of its phone number is refused", a.validate_pin("000199", "hash_9000000199") is not None)
check("...and another password is fine for that account", a.validate_pin("482615", "hash_9000000199") is None)
check("every refusal says why, in words a teacher can act on", all(isinstance(a.validate_pin(x), str) and len(a.validate_pin(x)) > 20 for x in ("4826", "111111", "123456", "password", "48a6!5")))

print("employee codes")
for raw, want in (("MPT101", "MPT101"), ("mpt101", "MPT101"), (" MPA123 ", "MPA123"), ("m1p2t3", "M1P2T3"), ("MPT10", None), ("MPT1011", None), ("MP-101", None), ("MPT 10", None), ("", None), (None, None), ("९८७६५४", None)):
    check(f"{str(raw)!r:>12} -> {want!r}", a.normalise_code(raw) == want)
check("a code is shown as it is; an old phone-number name shows only the last four digits", a.display_code("MPT101") == "MPT101" and a.display_code("hash_9876543210") == "••••3210")

print("hashing")
h = a.hash_pin("4826"); h2 = a.hash_pin("4826")
check("the stored value is not the PIN", "4826" not in h and h.startswith("pbkdf2_sha256$2000$"))
check("the right PIN verifies", a.verify_pin("4826", h))
check("a wrong PIN does not", not a.verify_pin("4827", h))
check("the same PIN hashes differently each time (salted)", h != h2)
check("a malformed stored value fails safely", not a.verify_pin("4826", "garbage") and not a.verify_pin("4826", None))
check("a temporary password is 6 digits and passes the rules", all(len(t) == 6 and a.validate_pin(t) is None for t in (a.temporary_pin() for _ in range(50))))
check("join codes are 6 readable characters", all(len(c) == 6 and not set(c) & set("01OIL") for c in (a.new_join_code() for _ in range(50))))

print("tokens")
tok = a.make_token({"tid": "abc", "role": "teacher", "pv": 3})
c = a.read_token(tok)
check("a token reads back", c["tid"] == "abc" and c["pv"] == 3 and c["exp"] > time.time())
body, sig = tok.split(".")


def refused(t, code):
    try:
        a.read_token(t)
        return False
    except a.AuthError as e:
        return e.code == code


check("a changed payload is refused", refused(a._b64(b'{"tid":"someone-else","exp":9999999999}') + "." + sig, "invalid_token"))
check("a changed signature is refused", refused(body + "." + sig[:-2] + ("AA" if not sig.endswith("AA") else "BB"), "invalid_token"))
check("garbage is refused", refused("not-a-token", "invalid_token") and refused("", "invalid_token"))
check("an expired token is refused", refused(a.make_token({"tid": "abc"}, hours=-1), "expired"))
old = get_settings().session_secret
get_settings().session_secret = "a-different-secret"
check("a token signed with another secret is refused", refused(tok, "invalid_token"))
get_settings().session_secret = old
check("...and works again with the right one", a.read_token(tok)["tid"] == "abc")

if failures:
    print(f"\nFAILED ({len(failures)})")
    sys.exit(1)
print("\nOK: password rules, employee codes, hashing and tokens behave")
