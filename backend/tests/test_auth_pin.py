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


print("PIN rules")
for pin, ok, why in (("4826", True, "a normal PIN"), ("482615", True, "six digits"), ("482", False, "too short"), ("4826159", False, "too long"), ("48a6", False, "not all digits"),
                     ("1111", False, "one digit repeated"), ("1234", False, "ascending run"), ("4321", False, "descending run"), ("2580", False, "a common PIN"),
                     ("0000", False, "zeros"), ("", False, "empty"), ("246810", True, "even steps are fine")):
    check(f"{pin!r:>10} {'allowed' if ok else 'refused'}: {why}", (a.validate_pin(pin) is None) == ok)
check("the end of the phone number is refused", a.validate_pin("3210", "hash_9876543210") is not None)
check("...but another PIN is fine for that phone", a.validate_pin("4826", "hash_9876543210") is None)

print("hashing")
h = a.hash_pin("4826"); h2 = a.hash_pin("4826")
check("the stored value is not the PIN", "4826" not in h and h.startswith("pbkdf2_sha256$2000$"))
check("the right PIN verifies", a.verify_pin("4826", h))
check("a wrong PIN does not", not a.verify_pin("4827", h))
check("the same PIN hashes differently each time (salted)", h != h2)
check("a malformed stored value fails safely", not a.verify_pin("4826", "garbage") and not a.verify_pin("4826", None))
check("a temporary PIN is 6 digits and passes the rules", all(len(t) == 6 and a.validate_pin(t) is None for t in (a.temporary_pin() for _ in range(50))))
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
print("\nOK: PIN rules, hashing and tokens behave")
