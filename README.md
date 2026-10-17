# StudentFX

StudentFX is a cross-border and student finance assistant for comparing routes and tracking multi-currency spending.

Built for FinTechathon 2026, International Track, Topic C

## Mock data notice

All rates, fees, providers, and expenses are mock data. This project does not connect to banks, payment providers, or live FX services. It does not move real money or access real accounts.

## Features

- Route recommender for mock cross-border transfers
- Multi-currency budget summaries and spending alerts
- Simulated transfer flow with permission tiers and audit logging

## Architecture

```text
request > parser > validator > tools > audit log
                         \> mock data (providers.json, expenses.json)
```

## Setup

StudentFX requires Python 3.11 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

The Anthropic parser is optional. Set `ANTHROPIC_API_KEY` in your environment, or copy `.env.example` as a reference. The demo works offline with the built-in keyword parser when no key is set.

## Run

```powershell
python main.py
python agent.py
```

Example agent inputs when running without an API key:

- `send 1000 USD to BDT by tomorrow` returns a mock route recommendation with the `USD-BDT` corridor and provider quotes.
- `how much did I spend on food?` returns a mock budget summary with category totals and a monthly total.
- `/tier execute` switches to the sandbox tier; `/quit` exits the agent.

The transfer result is always marked `SIMULATED_SETTLED`; no real transfer occurs.

## Permission tiers

| Tier | Allows | Extra requirement |
| --- | --- | --- |
| `READ` | Load expenses, convert currencies, summarize budgets, and check alerts | Mock data only |
| `SUGGEST` | Everything in `READ`, plus route recommendations | No transfer execution |
| `EXECUTE_SANDBOX` | Simulated transfer execution | User must type the confirmation token directly |

Every allowed or denied action is appended to the local `audit_log.jsonl`, which is ignored by Git.

## Tests

```powershell
pytest -q
```

The tests cover route selection and deadlines, permission enforcement, confirmation requirements, unsupported corridors, budget conversion and alerts, tool whitelisting, invalid arguments, and rejection of model-supplied confirmation tokens.

## Project structure

- `tools.py` - existing route, permission, confirmation, transfer, and audit functions
- `budget.py` - mock expense loading, currency conversion, summaries, and alerts
- `agent.py` - Anthropic or offline keyword chat CLI with validation
- `main.py` - deterministic route and simulated-transfer demo
- `providers.json` - mock providers, rates, fees, and corridors
- `expenses.json` - mock multi-currency student expenses
- `test_tools.py` - route and transfer tests
- `test_studentfx.py` - budget and agent validation tests
- `requirements.txt` - runtime and test dependencies
- `.env.example` - API-key environment variable template
- `.gitignore` - local secrets and generated artifacts excluded from Git

## Known risks

- The audit log is a local append-only file without tamper detection.
- Confirmation tokens are predictable and intended only for this sandbox.
- Permission tiers are process-local and are not user authentication.
- LLM output is schema-validated, but prompt injection and incorrect intent remain possible.
- The full risk inventory is documented in the Security Self-Assessment Report.

## Team

[Team name], [members]
