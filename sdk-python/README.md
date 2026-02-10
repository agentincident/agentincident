# AgentIncident Python SDK

Recorder SDK for the [AgentIncident](https://agentincident.com) incident specification -- an open format for recording, classifying, and pricing failures and near-misses produced by autonomous AI agents.

## Installation

```bash
pip install agentincident
```

With optional dependencies:

```bash
pip install agentincident[validation]    # JSON schema validation
pip install agentincident[otel]          # OpenTelemetry export
pip install agentincident[langchain]     # LangChain integration
pip install agentincident[crewai]        # CrewAI integration
pip install agentincident[openai-agents] # OpenAI Agents SDK integration
```

## Quick Start

```python
from agentincident import Recorder, Constraint, incident_to_json

# Record agent tool calls
with Recorder(agent="refund-bot", framework="langchain") as rec:
    rec.record(
        tool="stripe.refund",
        input={"charge": "ch_9xK", "amount": 47218},
        output={"refund_id": "re_Xp7", "status": "succeeded"},
        irreversible=True,
    )

    # Build the incident record
    incident = rec.to_incident(
        fault_class="SPEC_AMBIGUITY",
        impact_score=4,
        loss_amount_usd=47218.00,
        constraints=[Constraint(policy="refund_policy_v3", eval_result="pass")],
    )

print(incident_to_json(incident))
```

### Decorator Mode

```python
from agentincident import Recorder

rec = Recorder()

@rec.trace(tool="stripe.refund", irreversible=True)
def process_refund(charge_id, amount):
    # your logic here
    return {"refund_id": "re_123", "status": "succeeded"}

process_refund(charge_id="ch_9xK", amount=47218)
```

### Validation

```python
from agentincident import validate, incident_to_dict

errors = validate(incident_to_dict(incident), level="core")
if errors:
    print("Validation errors:", errors)
```

### Redaction

```python
from agentincident import redact_incident

safe = redact_incident(incident)  # Redacts emails, API keys, credit cards
```

## Specification

See [SPEC.md](../SPEC.md) for the full AgentIncident specification.

## License

Apache 2.0
