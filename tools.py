import json, time, uuid
from pathlib import Path

DATA = json.loads((Path(__file__).parent / "providers.json").read_text())
AUDIT_FILE = Path(__file__).parent / "audit_log.jsonl"

# permission tiers
READ, SUGGEST, EXECUTE_SANDBOX = 0, 1, 2
TIER_NAMES = {0: "READ", 1: "SUGGEST", 2: "EXECUTE_SANDBOX"}


def audit(action, tier, ok, detail=None):
    row = {"ts": time.time(), "action": action, "tier": TIER_NAMES[tier], "ok": ok, "detail": detail}
    with open(AUDIT_FILE, "a") as f:
        f.write(json.dumps(row) + "\n")


def require(tier, needed, action):
    if tier < needed:
        audit(action, tier, False, f"needs {TIER_NAMES[needed]}")
        raise PermissionError(f"{action} needs {TIER_NAMES[needed]}, session has {TIER_NAMES[tier]}")


def quote(provider, amount, corridor):
    mid = DATA["mid_rates"][corridor]
    fee = provider["flat_fee"] + provider["pct_fee"] * amount
    received = (amount - fee) * mid * (1 - provider["fx_margin"])
    ideal = amount * mid
    return {
        "provider": provider["name"],
        "fee": round(fee, 2),
        "received": round(received, 2),
        "total_cost_pct": round((1 - received / ideal) * 100, 2),
        "hours": provider["hours"],
    }


def recommend_routes(amount, src, dst, deadline_hours, tier=SUGGEST):
    require(tier, SUGGEST, "recommend_routes")
    corridor = f"{src}-{dst}"
    if corridor not in DATA["mid_rates"]:
        audit("recommend_routes", tier, False, f"unsupported corridor {corridor}")
        raise ValueError(f"unsupported corridor {corridor}")
    quotes = [quote(p, amount, corridor) for p in DATA["providers"] if corridor in p["corridors"]]
    on_time = [q for q in quotes if q["hours"] <= deadline_hours]
    cheapest = max(on_time, key=lambda q: q["received"]) if on_time else None
    fastest = min(quotes, key=lambda q: q["hours"])
    result = {"corridor": corridor, "cheapest_on_time": cheapest, "fastest": fastest, "all": quotes}
    audit("recommend_routes", tier, True, {"amount": amount, "corridor": corridor, "deadline_hours": deadline_hours})
    return result


def explain(result):
    c, f = result["cheapest_on_time"], result["fastest"]
    if c is None:
        return f"No provider meets the deadline. Fastest is {f['provider']} ({f['hours']}h)."
    msg = f"Best on-time: {c['provider']}, receive {c['received']:,.2f}, total cost {c['total_cost_pct']}% in {c['hours']}h."
    if f["provider"] != c["provider"]:
        extra = c["received"] - f["received"]
        msg += f" Fastest is {f['provider']} ({f['hours']}h) but you receive {extra:,.2f} less."
    return msg


def simulate_transfer(route, amount, tier, confirm_token=None, expected_token=None):
    require(tier, EXECUTE_SANDBOX, "simulate_transfer")
    if confirm_token is None or confirm_token != expected_token:
        audit("simulate_transfer", tier, False, "missing or wrong confirmation")
        raise PermissionError("explicit confirmation required")
    tx = {"tx_id": str(uuid.uuid4())[:8], "provider": route["provider"], "amount": amount, "status": "SIMULATED_SETTLED"}
    audit("simulate_transfer", tier, True, tx)
    return tx


def new_confirmation(route, amount):
    # user must echo this token back to approve a transfer
    return f"CONFIRM-{route['provider']}-{int(amount)}"
