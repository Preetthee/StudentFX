import pytest
from tools import *


def test_cheapest_respects_deadline():
    r = recommend_routes(1000, "USD", "BDT", 30)
    assert r["cheapest_on_time"]["provider"] == "FinTechPay"


def test_tight_deadline_picks_fast_provider():
    r = recommend_routes(1000, "USD", "BDT", 2)
    assert r["cheapest_on_time"]["provider"] == "InstaSend"


def test_no_provider_meets_deadline():
    r = recommend_routes(1000, "GBP", "BDT", 1)
    assert r["cheapest_on_time"] is None


def test_read_tier_cannot_recommend():
    with pytest.raises(PermissionError):
        recommend_routes(100, "USD", "BDT", 24, tier=READ)


def test_transfer_needs_execute_tier():
    route = recommend_routes(100, "USD", "BDT", 48)["cheapest_on_time"]
    with pytest.raises(PermissionError):
        simulate_transfer(route, 100, tier=SUGGEST)


def test_transfer_needs_confirmation():
    route = recommend_routes(100, "USD", "BDT", 48)["cheapest_on_time"]
    with pytest.raises(PermissionError):
        simulate_transfer(route, 100, tier=EXECUTE_SANDBOX, confirm_token="wrong", expected_token="right")


def test_unsupported_corridor():
    with pytest.raises(ValueError):
        recommend_routes(100, "GBP", "INR", 24)
