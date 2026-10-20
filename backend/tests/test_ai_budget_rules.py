"""
The arithmetic of the AI budget, with no database: tokens to money, the reserve rule, the India-time day, and that every reason a
call can be stopped has a message.

    python backend/tests/test_ai_budget_rules.py
"""
import os
import sys
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
IST = timezone(timedelta(hours=5, minutes=30))        # fixed offsets: Windows has no time zone database unless tzdata is installed

sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")]
from app.core.config import get_settings
from app.services import ai_budget as b

s = get_settings()
failures = []


def check(label, ok):
    print(f"  {'OK ' if ok else 'FAIL'} {label}")
    if not ok:
        failures.append(label)


s.ai_price_input_per_mtok, s.ai_price_output_per_mtok = 2.0, 10.0
print("tokens to money")
check("6,000 in + 9,000 out at $2 / $10 per million = $0.102", abs(b.cost_usd(6000, 9000) - 0.102) < 1e-9)
check("an SDK usage object is read", b.tokens_of(SimpleNamespace(input_tokens=11, output_tokens=22)) == (11, 22))
check("a dict is read", b.tokens_of({"input_tokens": 5, "output_tokens": 7}) == (5, 7))
check("junk counts as zero instead of breaking a request", b.tokens_of("u") == (0, 0) and b.tokens_of(None) == (0, 0) and b.tokens_of({}) == (0, 0))
s.ai_price_output_per_mtok = 15.0
check("a corrected price changes the same tokens' cost (so history can be re-priced)", abs(b.cost_usd(6000, 9000) - (0.012 + 0.135)) < 1e-9)
s.ai_price_output_per_mtok = 10.0

print("the reserve rule")
s.ai_allocation_usd, s.ai_spend_offset_usd, s.ai_reserve_usd, s.ai_reserve_from, s.ai_final_margin_usd = 500.0, 3.0, 250.0, "2026-11-01", 10.0
check("before 1 Nov, spending is held to 500 - 3 - 250 = $247 (nothing spent yet)", abs(b.available_usd(0, date(2026, 10, 25)) - 247.0) < 1e-9)
check("...and $100 spent leaves $147", abs(b.available_usd(100, date(2026, 10, 25)) - 147.0) < 1e-9)
check("development spending $247 leaves nothing it may use", abs(b.available_usd(247, date(2026, 10, 25))) < 1e-9)
check("on 1 Nov the reserve is released: only the $10 margin is held back", abs(b.available_usd(247, date(2026, 11, 1)) - 240.0) < 1e-9)
check("when everything but the margin is spent, nothing is available", b.available_usd(487, date(2026, 11, 5)) <= 0)

print("a day is an India day")
s.ai_timezone = "Asia/Kolkata"
b.NOW_OVERRIDE = datetime(2026, 10, 25, 23, 30, tzinfo=timezone.utc)           # 05:00 on the 26th in India
check("23:30 UTC on the 25th is already the 26th in India", b.day_start().date() == date(2026, 10, 26) and b.day_start().hour == 0)
b.NOW_OVERRIDE = datetime(2026, 10, 25, 12, 0, tzinfo=IST)
check("midday on the 25th starts the day at 00:00 IST on the 25th", b.day_start().date() == date(2026, 10, 25) and b.day_start().utcoffset() == timedelta(hours=5, minutes=30))
b.NOW_OVERRIDE = None

print("a machine with no time zone database (Windows without the tzdata package)")
import zoneinfo
real_zone = b.ZoneInfo
def _missing(name):
    raise zoneinfo.ZoneInfoNotFoundError(name)
b.ZoneInfo = _missing
try:
    s.ai_timezone = "Asia/Kolkata"
    check("India falls back to the fixed +05:30 offset instead of failing", b._tz().utcoffset(None) == timedelta(hours=5, minutes=30))
    b.NOW_OVERRIDE = datetime(2026, 10, 25, 23, 30, tzinfo=timezone.utc)
    check("...and the day still starts at midnight India time", b.day_start().date() == date(2026, 10, 26))
    b.NOW_OVERRIDE = None
    s.ai_timezone = "Europe/Nowhere"
    check("an unknown zone falls back to UTC (with a warning) instead of crashing", b._tz() == timezone.utc)
finally:
    b.ZoneInfo = real_zone
    s.ai_timezone = "Asia/Kolkata"

print("messages")
reasons = ["disabled", "expired", "exhausted", "reserve", "global_daily", "school_daily", "teacher_daily"]
check("every reason has a Hindi and English message", all(r in b.MESSAGES and "(" in b.MESSAGES[r] for r in reasons))
e = b.AICapReached("teacher_daily")
check("the exception carries its reason and message", e.reason == "teacher_daily" and e.message == b.MESSAGES["teacher_daily"])
check("the recorded sample plans are found", {"N2.2.1", "N2.3.2"} <= set(b.sample_skills()) and b.sample_plan_for("N2.3.2") is not None and b.sample_plan_for("NOPE") is None)

if failures:
    print(f"\nFAILED ({len(failures)})")
    sys.exit(1)
print("\nOK: the budget arithmetic behaves")
