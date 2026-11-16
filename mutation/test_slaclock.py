# ai-generated: 100% - Gemini wrote contract-based unit tests for slaclock.py to kill mutants and pass rewrites
from datetime import datetime, timedelta
import pytest

from slaclock import (
    add_business_minutes,
    business_minutes_between,
    escalation_tier,
    is_business_time,
    parse_duration,
    priority_of,
    sla_state,
    targets,
)


def test_priority_of_all_valid_cells_and_vip():
    expected_non_vip = {
        (1, 1): "P1",
        (1, 2): "P2",
        (2, 1): "P2",
        (1, 3): "P3",
        (2, 2): "P3",
        (3, 1): "P3",
        (2, 3): "P4",
        (3, 2): "P4",
        (3, 3): "P4",
    }
    for (imp, urg), prio in expected_non_vip.items():
        assert priority_of(imp, urg) == prio
        assert priority_of(imp, urg, False) == prio
        assert priority_of(impact=imp, urgency=urg, vip=False) == prio

    expected_vip = {
        (1, 1): "P1",
        (1, 2): "P2",
        (2, 1): "P2",
        (1, 3): "P2",
        (2, 2): "P2",
        (3, 1): "P2",
        (2, 3): "P2",
        (3, 2): "P2",
        (3, 3): "P2",
    }
    for (imp, urg), prio in expected_vip.items():
        assert priority_of(imp, urg, True) == prio
        assert priority_of(impact=imp, urgency=urg, vip=True) == prio


@pytest.mark.parametrize(
    "bad_impact,bad_urgency",
    [
        (0, 1),
        (1, 0),
        (4, 1),
        (1, 4),
        (-1, 2),
        (2, -1),
        (True, 1),
        (1, True),
        (False, 1),
        (1, False),
        (2.0, 1),
        (1, 2.0),
        ("1", 1),
        (1, "1"),
        (None, 1),
        (1, None),
    ],
)
def test_priority_of_invalid_inputs(bad_impact, bad_urgency):
    with pytest.raises(ValueError):
        priority_of(bad_impact, bad_urgency)


def test_targets_valid_and_invalid():
    assert targets("P1") == (15, 240)
    assert targets("P2") == (60, 480)
    assert targets("P3") == (240, 1440)
    assert targets("P4") == (480, 4320)

    for bad in ["p1", "p2", "p3", "p4", " P1", "P1 ", "P0", "P5", "", "1"]:
        with pytest.raises(ValueError):
            targets(bad)


def test_sla_state_boundaries_and_errors():
    # target = 15 -> 75% is 11.25
    assert sla_state(0, 15) == "ok"
    assert sla_state(11, 15) == "ok"
    assert sla_state(12, 15) == "warning"
    assert sla_state(15, 15) == "warning"
    assert sla_state(16, 15) == "breached"

    # target = 100 -> exact 75% boundary
    assert sla_state(0, 100) == "ok"
    assert sla_state(74, 100) == "ok"
    assert sla_state(75, 100) == "warning"
    assert sla_state(99, 100) == "warning"
    assert sla_state(100, 100) == "warning"
    assert sla_state(101, 100) == "breached"

    # target = 4 -> 75% is 3
    assert sla_state(2, 4) == "ok"
    assert sla_state(3, 4) == "warning"
    assert sla_state(4, 4) == "warning"
    assert sla_state(5, 4) == "breached"

    # target = 1
    assert sla_state(0, 1) == "ok"
    assert sla_state(1, 1) == "warning"
    assert sla_state(2, 1) == "breached"

    for elapsed, target in [(-1, 10), (-5, 1), (0, 0), (5, 0), (5, -1), (-1, 0)]:
        with pytest.raises(ValueError):
            sla_state(elapsed, target)


def test_is_business_time_boundaries():
    # 2026-11-16 is Monday, 2026-11-20 is Friday, 2026-11-21 is Saturday, 2026-11-22 is Sunday
    for day in range(16, 21):
        assert is_business_time(datetime(2026, 11, day, 7, 59)) is False
        assert is_business_time(datetime(2026, 11, day, 8, 0)) is True
        assert is_business_time(datetime(2026, 11, day, 8, 0, 59, 999999)) is True
        assert is_business_time(datetime(2026, 11, day, 12, 30)) is True
        assert is_business_time(datetime(2026, 11, day, 15, 59, 59, 999999)) is True
        assert is_business_time(datetime(2026, 11, day, 16, 0)) is False
        assert is_business_time(datetime(2026, 11, day, 16, 1)) is False
        assert is_business_time(datetime(2026, 11, day, 0, 0)) is False
        assert is_business_time(datetime(2026, 11, day, 23, 59)) is False

    for weekend_day in (21, 22):
        assert is_business_time(datetime(2026, 11, weekend_day, 8, 0)) is False
        assert is_business_time(datetime(2026, 11, weekend_day, 12, 0)) is False
        assert is_business_time(datetime(2026, 11, weekend_day, 15, 59)) is False


def test_add_business_minutes():
    # Zero minutes inside business hours returns start (with seconds/microseconds stripped)
    assert add_business_minutes(datetime(2026, 11, 16, 8, 0, 45, 123), 0) == datetime(2026, 11, 16, 8, 0)
    assert add_business_minutes(datetime(2026, 11, 16, 15, 59, 30), 0) == datetime(2026, 11, 16, 15, 59)

    # Zero minutes outside business hours moves to next opening
    assert add_business_minutes(datetime(2026, 11, 16, 7, 59, 59), 0) == datetime(2026, 11, 16, 8, 0)
    assert add_business_minutes(datetime(2026, 11, 16, 16, 0), 0) == datetime(2026, 11, 17, 8, 0)
    assert add_business_minutes(datetime(2026, 11, 20, 16, 0), 0) == datetime(2026, 11, 23, 8, 0)
    assert add_business_minutes(datetime(2026, 11, 21, 10, 0), 0) == datetime(2026, 11, 23, 8, 0)
    assert add_business_minutes(datetime(2026, 11, 22, 10, 0), 0) == datetime(2026, 11, 23, 8, 0)

    # Exact closing boundary: ends at 16:00 same day, NOT 08:00 next day
    assert add_business_minutes(datetime(2026, 11, 16, 8, 0), 480) == datetime(2026, 11, 16, 16, 0)
    assert add_business_minutes(datetime(2026, 11, 16, 7, 0), 480) == datetime(2026, 11, 16, 16, 0)
    assert add_business_minutes(datetime(2026, 11, 16, 15, 59), 1) == datetime(2026, 11, 16, 16, 0)
    assert add_business_minutes(datetime(2026, 11, 16, 15, 59), 2) == datetime(2026, 11, 17, 8, 1)
    assert add_business_minutes(datetime(2026, 11, 16, 8, 0), 481) == datetime(2026, 11, 17, 8, 1)

    # Across weekend (Friday 15:00 + 120m -> Monday 09:00)
    assert add_business_minutes(datetime(2026, 11, 20, 15, 0), 60) == datetime(2026, 11, 20, 16, 0)
    assert add_business_minutes(datetime(2026, 11, 20, 15, 0), 61) == datetime(2026, 11, 23, 8, 1)
    assert add_business_minutes(datetime(2026, 11, 20, 15, 0), 120) == datetime(2026, 11, 23, 9, 0)

    # Multi-week span and MAX_DAYS (366) boundary
    start = datetime(2026, 1, 1, 8, 0)  # Thursday
    # Exactly 366 days after 2026-01-01 is 2027-01-02 (Saturday), 365 days is 2027-01-01 (Friday)
    # 2026 has 261 weekdays; 262 * 480 = 125280 minutes (ends 2026-12-31 16:00, offset 364)
    # Plus Friday 2027-01-01 (offset 365): +480 = 125760 minutes -> ends 2027-01-01 16:00
    assert add_business_minutes(start, 262 * 480) == datetime(2027, 1, 1, 16, 0)

    # Starting on Friday 2026-01-02, offset 366 is Saturday 2027-01-03; starting Sunday 2026-01-04, offset 366 is Monday 2027-01-05
    start_sun = datetime(2026, 1, 4, 8, 0)
    # 261 weekdays in the 366-day window [2026-01-04 .. 2027-01-05]
    due_max = add_business_minutes(start_sun, 262 * 480)
    assert (due_max.date() - start_sun.date()).days == 366
    with pytest.raises(ValueError):
        add_business_minutes(start_sun, 262 * 480 + 1)

    with pytest.raises(ValueError):
        add_business_minutes(datetime(2026, 11, 16, 8, 0), -1)


def test_business_minutes_between_and_roundtrip():
    t0 = datetime(2026, 11, 16, 10, 0, 50)
    t1 = datetime(2026, 11, 16, 10, 0, 10)
    # Seconds ignored, so t0 and t1 are equal at minute resolution -> 0
    assert business_minutes_between(t0, t1) == 0

    # End before start at minute resolution raises ValueError
    with pytest.raises(ValueError):
        business_minutes_between(datetime(2026, 11, 16, 10, 1), datetime(2026, 11, 16, 10, 0))

    # Full business day and multi-day intervals
    assert business_minutes_between(datetime(2026, 11, 16, 6, 0), datetime(2026, 11, 16, 18, 0)) == 480
    assert business_minutes_between(datetime(2026, 11, 16, 8, 0), datetime(2026, 11, 16, 16, 0)) == 480
    assert business_minutes_between(datetime(2026, 11, 16, 8, 30), datetime(2026, 11, 16, 9, 15)) == 45
    assert business_minutes_between(datetime(2026, 11, 20, 15, 0), datetime(2026, 11, 23, 9, 0)) == 120
    assert business_minutes_between(datetime(2026, 11, 21, 8, 0), datetime(2026, 11, 22, 16, 0)) == 0

    # Roundtrip property required by spec
    for s in [
        datetime(2026, 11, 16, 7, 15),
        datetime(2026, 11, 16, 8, 0),
        datetime(2026, 11, 16, 12, 34),
        datetime(2026, 11, 20, 16, 30),
        datetime(2026, 11, 21, 11, 0),
    ]:
        for mins in [0, 1, 15, 60, 479, 480, 481, 960, 2400]:
            due = add_business_minutes(s, mins)
            assert business_minutes_between(s, due) == mins

    # MAX_DAYS (366) calendar days apart is allowed; 367 raises ValueError
    d_start = datetime(2026, 1, 4, 23, 0)
    d_366 = datetime(2027, 1, 5, 9, 0)  # 366 calendar days apart
    assert (d_366.date() - d_start.date()).days == 366
    assert business_minutes_between(d_start, d_366) == 261 * 480 + 60

    d_367 = datetime(2027, 1, 6, 8, 0)
    with pytest.raises(ValueError):
        business_minutes_between(d_start, d_367)


def test_escalation_tier_all_combinations():
    # P1: base 1, breached +2 (-> 3), reopens>=2 +1 (capped at 3)
    assert escalation_tier("P1", False, 0) == 1
    assert escalation_tier("P1", False, 1) == 1
    assert escalation_tier("P1", False, 2) == 2
    assert escalation_tier("P1", False, 5) == 2
    assert escalation_tier("P1", True, 0) == 3
    assert escalation_tier("P1", True, 1) == 3
    assert escalation_tier("P1", True, 2) == 3

    # P2: base 1, breached +1, reopens>=2 +1
    assert escalation_tier("P2", False, 0) == 1
    assert escalation_tier("P2", False, 1) == 1
    assert escalation_tier("P2", False, 2) == 2
    assert escalation_tier("P2", True, 0) == 2
    assert escalation_tier("P2", True, 1) == 2
    assert escalation_tier("P2", True, 2) == 3
    assert escalation_tier("P2", True, 10) == 3

    # P3 and P4: base 0, breached +1, reopens>=2 +1
    for p in ("P3", "P4"):
        assert escalation_tier(p, False, 0) == 0
        assert escalation_tier(p, False, 1) == 0
        assert escalation_tier(p, False, 2) == 1
        assert escalation_tier(p, False, 3) == 1
        assert escalation_tier(p, True, 0) == 1
        assert escalation_tier(p, True, 1) == 1
        assert escalation_tier(p, True, 2) == 2
        assert escalation_tier(p, True, 4) == 2

    for bad_p in ("p1", "P0", "P5", ""):
        with pytest.raises(ValueError):
            escalation_tier(bad_p, False, 0)

    for p in ("P1", "P2", "P3", "P4"):
        with pytest.raises(ValueError):
            escalation_tier(p, False, -1)


def test_parse_duration_valid_and_invalid():
    valid_cases = {
        "1m": 1,
        "90m": 90,
        "60m": 60,
        "0h60m": 60,
        "0d0h60m": 60,
        "0d120m": 120,
        "4h": 240,
        "1h0m": 60,
        "1h30m": 90,
        "1h59m": 119,
        "2d": 2880,
        "1d0h": 1440,
        "1d4h": 1680,
        "1d0h5m": 1445,
        "1d0h59m": 1499,
        "0d1h59m": 119,
        "  1h30m  ": 90,
        "\t2d\n": 2880,
        "0d4h": 240,
        "30h": 1800,
    }
    for text, expected in valid_cases.items():
        assert parse_duration(text) == expected

    invalid_cases = [
        "",
        "   ",
        "0m",
        "0h",
        "0d",
        "0d0h0m",
        "1h60m",
        "2h60m",
        "1d60m",
        "1d0h60m",
        "1d1h60m",
        "1h90m",
        "1.5h",
        "30m1h",
        "1h2d",
        "1m1d",
        "-5m",
        "-1h",
        "+10m",
        "1 h",
        "1d 4h",
        "1H",
        "30M",
        "2D",
        "1d2d",
        "1h1h",
        "10m10m",
        "10s",
        "abc",
    ]
    for bad in invalid_cases:
        with pytest.raises(ValueError):
            parse_duration(bad)