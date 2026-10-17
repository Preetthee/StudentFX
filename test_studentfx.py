import pytest

from agent import validate_request
from budget import budget_alerts, budget_summary, to_home_currency


def test_budget_conversion_supports_direct_inverse_and_cross_rates():
    assert to_home_currency(100, "USD", "BDT") == 12200.0
    assert to_home_currency(12200, "BDT", "USD") == 100.0
    assert to_home_currency(1, "GBP", "USD") == round(155 / 122, 2)


def test_budget_alerts_returns_categories_over_limit():
    alerts = budget_alerts({"housing": 100, "food": 10000})
    assert alerts == ["housing"]
    assert budget_summary()["monthly_total"] > 0


def test_unknown_tool_is_rejected():
    with pytest.raises(ValueError, match="tool is not allowed"):
        validate_request({"tool": "delete_account", "args": {}})


def test_bad_arguments_are_rejected():
    with pytest.raises(ValueError, match="invalid args"):
        validate_request({"tool": "recommend_routes", "args": {"amount": "100"}})


def test_llm_payload_cannot_supply_confirmation_token():
    with pytest.raises(ValueError, match="confirmation tokens"):
        validate_request({
            "tool": "simulate_transfer",
            "args": {"amount": 100, "confirm_token": "CONFIRM-BankWire-100"},
        })
