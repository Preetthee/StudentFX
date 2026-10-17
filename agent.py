import json
import math
import os
import re

from budget import budget_alerts, budget_summary
from tools import (
    EXECUTE_SANDBOX,
    SUGGEST,
    audit,
    new_confirmation,
    recommend_routes,
    require,
    simulate_transfer,
)

TOOL_WHITELIST = {
    "recommend_routes",
    "budget_summary",
    "budget_alerts",
    "simulate_transfer",
}


def _reject(tier, detail):
    audit("agent_rejection", tier, False, detail)
    raise ValueError(detail)


def _number(value):
    return (isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value))


def validate_request(payload, tier=SUGGEST):
    if not isinstance(payload, dict) or set(payload) != {"tool", "args"}:
        _reject(tier, "request must contain only tool and args")
    tool, args = payload["tool"], payload["args"]
    if tool not in TOOL_WHITELIST:
        _reject(tier, f"tool is not allowed: {tool}")
    if not isinstance(args, dict):
        _reject(tier, "args must be an object")
    if any(key in args for key in ("confirm_token", "expected_token", "token")):
        _reject(tier, "confirmation tokens must come from direct user input")

    schemas = {
        "recommend_routes": {"amount", "src", "dst", "deadline_hours"},
        "budget_summary": set(),
        "budget_alerts": {"limits"},
        "simulate_transfer": {"amount"},
    }
    required = schemas[tool]
    if not required.issubset(args) or set(args) - required:
        _reject(tier, f"invalid args for {tool}")

    if tool in {"recommend_routes", "simulate_transfer"}:
        if not _number(args["amount"]) or args["amount"] <= 0:
            _reject(tier, "amount must be a positive number")
    if tool == "recommend_routes":
        if not all(isinstance(args[key], str) for key in ("src", "dst")):
            _reject(tier, "currencies must be strings")
        if not _number(args["deadline_hours"]) or args["deadline_hours"] <= 0:
            _reject(tier, "deadline_hours must be a positive number")
    elif tool == "budget_summary":
        if "home" in args and not isinstance(args["home"], str):
            _reject(tier, "home must be a string")
    elif tool == "budget_alerts":
        if (not isinstance(args["limits"], dict)
                or any(not _number(value) or value < 0 for value in args["limits"].values())):
            _reject(tier, "limits must map categories to non-negative numbers")
    audit("agent_request_validated", tier, True, {"tool": tool})
    return tool, args


def _simple_parse(sentence, tier):
    text = sentence.lower()
    transfer = re.search(
        r"send\s+(?P<amount>\d+(?:\.\d+)?)\s+(?P<src>[a-z]{3})\s+to\s+(?P<dst>[a-z]{3})(?:\s+by\s+(?P<deadline>\d+)\s*hours?)?",
        text,
    )
    if transfer:
        deadline = 24 if "tomorrow" in text else float(transfer.group("deadline") or 48)
        return {
            "tool": "recommend_routes",
            "args": {
                "amount": float(transfer.group("amount")),
                "src": transfer.group("src").upper(),
                "dst": transfer.group("dst").upper(),
                "deadline_hours": deadline,
            },
        }
    if "spend" in text or "spent" in text or "budget" in text:
        return {"tool": "budget_summary", "args": {}}
    _reject(tier, "could not parse request without ANTHROPIC_API_KEY")


def _llm_parse(sentence, tier):
    try:
        import anthropic
    except ImportError:
        return _simple_parse(sentence, tier)
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest"),
        max_tokens=300,
        system=("Return only JSON with exactly two keys: tool and args. "
                "The tool must be one of recommend_routes, budget_summary, "
                "budget_alerts, simulate_transfer. Never provide confirmation tokens."),
        messages=[{"role": "user", "content": sentence}],
    )
    text = response.content[0].text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        _reject(tier, "LLM response was not valid JSON")


def parse_sentence(sentence, tier=SUGGEST):
    require(tier, SUGGEST, "agent_parse")
    if not os.getenv("ANTHROPIC_API_KEY"):
        payload = _simple_parse(sentence, tier)
    else:
        payload = _llm_parse(sentence, tier)
    tool, args = validate_request(payload, tier=tier)
    audit("agent_parse", tier, True, {"tool": tool})
    return tool, args


def dispatch(tool, args, tier, state):
    require(tier, SUGGEST, "agent_dispatch")
    if tool == "recommend_routes":
        result = recommend_routes(tier=tier, **args)
        route = result["cheapest_on_time"] or result["fastest"]
        state["route"] = route
        audit("agent_dispatch", tier, True, {"tool": tool})
        return result
    if tool == "budget_summary":
        result = budget_summary(tier=tier, **args)
    elif tool == "budget_alerts":
        result = budget_alerts(tier=tier, **args)
    else:
        require(tier, EXECUTE_SANDBOX, "simulate_transfer")
        route = state.get("route")
        if route is None:
            _reject(tier, "request a route before simulating a transfer")
        token = input("Type the confirmation token shown for this transfer: ")
        expected = new_confirmation(route, args["amount"])
        result = simulate_transfer(route, args["amount"], tier, token, expected)
    audit("agent_dispatch", tier, True, {"tool": tool})
    return result


def run_cli():
    tier = SUGGEST
    state = {}
    print("StudentFX agent. Use /tier execute to enable simulated transfers; /quit exits.")
    while True:
        sentence = input("agent> ").strip()
        if sentence == "/quit":
            return
        if sentence.lower() in {"/tier execute", "/tier execute_sandbox"}:
            tier = EXECUTE_SANDBOX
            audit("agent_tier_switch", tier, True, {"tier": "EXECUTE_SANDBOX"})
            print("Session tier: EXECUTE_SANDBOX")
            continue
        try:
            tool, args = parse_sentence(sentence, tier=tier)
            result = dispatch(tool, args, tier, state)
            print(json.dumps(result, indent=2))
        except (PermissionError, ValueError, KeyError, TypeError) as exc:
            print(f"Rejected: {exc}")


if __name__ == "__main__":
    run_cli()
