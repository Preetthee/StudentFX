import json
import math
from pathlib import Path

from tools import DATA, READ, audit, require

EXPENSES_FILE = Path(__file__).parent / "expenses.json"


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _rates():
    rates = {}
    for corridor, rate in DATA["mid_rates"].items():
        source, target = corridor.split("-", 1)
        rates.setdefault(source, {})[target] = rate
        rates.setdefault(target, {})[source] = 1 / rate
    return rates


def _rate(source, target):
    if source == target:
        return 1.0
    rates = _rates()
    pending = [(source, 1.0)]
    visited = {source}
    while pending:
        currency, value = pending.pop(0)
        for next_currency, rate in rates.get(currency, {}).items():
            if next_currency in visited:
                continue
            converted = value * rate
            if next_currency == target:
                return converted
            visited.add(next_currency)
            pending.append((next_currency, converted))
    raise ValueError(f"unsupported currency pair {source}-{target}")


def load_expenses(tier=READ):
    action = "load_expenses"
    require(tier, READ, action)
    try:
        expenses = json.loads(EXPENSES_FILE.read_text())
        if not isinstance(expenses, list):
            raise ValueError("expenses must be a list")
        audit(action, tier, True, {"count": len(expenses)})
        return expenses
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        audit(action, tier, False, str(exc))
        raise


def to_home_currency(amount, cur, home, tier=READ):
    action = "to_home_currency"
    require(tier, READ, action)
    try:
        if not _number(amount) or amount < 0:
            raise ValueError("amount must be a non-negative number")
        source, target = str(cur).upper(), str(home).upper()
        converted = round(amount * _rate(source, target), 2)
        audit(action, tier, True, {"amount": amount, "currency": source, "home": target})
        return converted
    except (TypeError, ValueError) as exc:
        audit(action, tier, False, str(exc))
        raise


def budget_summary(home="USD", tier=READ):
    action = "budget_summary"
    require(tier, READ, action)
    try:
        home = str(home).upper()
        by_category = {}
        by_currency = {}
        monthly_total = 0.0
        for expense in load_expenses(tier=tier):
            amount = expense["amount"]
            currency = str(expense["currency"]).upper()
            category = expense["category"]
            if not _number(amount) or amount < 0:
                raise ValueError("expense amount must be a non-negative number")
            by_currency[currency] = round(by_currency.get(currency, 0) + amount, 2)
            converted = to_home_currency(amount, currency, home, tier=tier)
            by_category[category] = round(by_category.get(category, 0) + converted, 2)
            monthly_total = round(monthly_total + converted, 2)
        result = {
            "home_currency": home,
            "by_category": by_category,
            "by_currency": by_currency,
            "monthly_total": monthly_total,
        }
        audit(action, tier, True, {"home": home, "monthly_total": monthly_total})
        return result
    except (KeyError, TypeError, ValueError) as exc:
        audit(action, tier, False, str(exc))
        raise


def budget_alerts(limits, tier=READ):
    action = "budget_alerts"
    require(tier, READ, action)
    try:
        if not isinstance(limits, dict) or any(not _number(value) for value in limits.values()):
            raise ValueError("limits must be a category-to-number mapping")
        summary = budget_summary(tier=tier)
        alerts = [category for category, limit in limits.items()
                   if summary["by_category"].get(category, 0) > limit]
        audit(action, tier, True, {"alerts": alerts})
        return alerts
    except (TypeError, ValueError) as exc:
        audit(action, tier, False, str(exc))
        raise
