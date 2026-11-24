"""Contadores locais: relógio fictício, sem rede ou dados privados."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import sqlite3

import pytest


def make_limiter(tmp_path, clock, **changes):
    from academic_assistant.rate_limit import RateLimiter, RateLimitSettings

    settings = replace(RateLimitSettings(database=tmp_path / "limits.sqlite3"), **changes)
    return RateLimiter(settings, clock=lambda: clock[0])


def test_per_ip_windows_and_global_budget(tmp_path):
    clock = [86_400]
    limiter = make_limiter(
        tmp_path, clock, ip_minute=1, ip_day=2, global_minute=2, global_day=3
    )
    assert limiter.consume("192.0.2.1") == 0
    assert limiter.consume("192.0.2.1") == 60
    assert limiter.consume("192.0.2.2") == 0
    assert limiter.consume("192.0.2.3") == 60
    clock[0] += 60
    assert limiter.consume("192.0.2.1") == 0
    assert limiter.consume("192.0.2.1") == 86_340
    assert limiter.consume("192.0.2.3") == 86_340
    clock[0] = 2 * 86_400
    assert limiter.consume("192.0.2.1") == 0


def test_denied_requests_do_not_consume_other_windows(tmp_path):
    clock = [86_400]
    limiter = make_limiter(
        tmp_path, clock, ip_minute=1, ip_day=2, global_minute=2, global_day=2
    )
    assert limiter.consume("192.0.2.1") == 0
    for _ in range(10):
        assert limiter.consume("192.0.2.1") == 60
    assert limiter.consume("192.0.2.2") == 0


def test_database_is_lazy_and_persists_without_raw_ip(tmp_path):
    clock = [86_400]
    limiter = make_limiter(tmp_path, clock, ip_minute=1)
    database = tmp_path / "limits.sqlite3"
    assert not database.exists()
    assert limiter.consume("192.0.2.1") == 0
    restarted = make_limiter(tmp_path, clock, ip_minute=1)
    assert restarted.consume("192.0.2.1") == 60
    with sqlite3.connect(database) as db:
        dump = "\n".join(db.iterdump())
    assert "192.0.2.1" not in dump


def test_expired_records_are_removed(tmp_path):
    clock = [86_400]
    limiter = make_limiter(tmp_path, clock)
    assert limiter.consume("192.0.2.1") == 0
    clock[0] = 3 * 86_400
    assert limiter.consume("192.0.2.2") == 0
    with sqlite3.connect(tmp_path / "limits.sqlite3") as db:
        assert db.execute("SELECT COUNT(*) FROM rate_limits").fetchone()[0] == 4


def test_concurrent_instances_share_atomic_limits(tmp_path):
    clock = [86_400]

    def consume(_):
        limiter = make_limiter(tmp_path, clock, ip_minute=3)
        return limiter.consume("192.0.2.1")

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(consume, range(20)))
    assert results.count(0) == 3
    assert results.count(60) == 17


def test_mapped_ipv4_cannot_bypass_ip_limit(tmp_path):
    clock = [86_400]
    limiter = make_limiter(tmp_path, clock, ip_minute=1)
    assert limiter.consume("192.0.2.1") == 0
    assert limiter.consume("::ffff:192.0.2.1") == 60


@pytest.mark.parametrize("field", ["ip_minute", "ip_day", "global_minute", "global_day"])
@pytest.mark.parametrize("value", [0, -1, True])
def test_settings_reject_invalid_limits(tmp_path, field, value):
    with pytest.raises(ValueError, match=field):
        make_limiter(tmp_path, [86_400], **{field: value})


def test_empty_database_configuration_is_rejected(tmp_path, monkeypatch):
    from academic_assistant.rate_limit import RateLimitSettings

    monkeypatch.setenv("WEB_RATE_LIMIT_DB", " ")
    with pytest.raises(ValueError, match="WEB_RATE_LIMIT_DB"):
        RateLimitSettings.from_env(tmp_path / "limits.sqlite3")
