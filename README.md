# agentincident

The open incident format for autonomous AI agents.

AgentIncident is a vendor-neutral specification for recording, classifying, and pricing failures and near-misses produced by autonomous AI agents. It produces structured incident records designed for engineering postmortems, compliance audits, and actuarial pricing.

## Quick Start

### Record an incident (Python)

```python
from agentincident import Recorder

with Recorder(agent="my-agent", framework="langchain") as rec:
    rec.record("stripe.refund", {"charge": "ch_9xK", "amount": 47218},
               {"refund_id": "re_Xp7", "status": "succeeded"}, irreversible=True)
    incident = rec.to_incident(
        fault_class="SPEC_AMBIGUITY", impact_score=4, loss_amount_usd=47218.00,
        constraints=[{"policy": "refund_policy_v3", "eval_result": "pass"}])
print(incident.to_json())
```

### Record an incident (TypeScript)

```typescript
import { Recorder } from "agentincident";

const rec = new Recorder({ agent: "my-agent", framework: "langchain" });
rec.record("stripe.refund", { charge: "ch_9xK", amount: 47218 },
           { refund_id: "re_Xp7", status: "succeeded" }, { irreversible: true });
const incident = rec.toIncident({
  fault_class: "SPEC_AMBIGUITY", impact_score: 4, loss_amount_usd: 47218.00,
  constraints: [{ policy: "refund_policy_v3", eval_result: "pass" }],
});
console.log(rec.toJSON(2));
```

### Generate a report

```bash
agentincident report examples/minimal-core.json
```

### Validate a record

```bash
agentincident validate examples/INC-2026-0247-full.json --level full
```

## Packages

| Package | Install | Description |
|---------|---------|-------------|
| [schema](./schema/) | — | JSON Schema v0.1 |
| [sdk-python](./sdk-python/) | `pip install agentincident` | Python recorder SDK |
| [sdk-typescript](./sdk-typescript/) | `npm install agentincident` | TypeScript recorder SDK |
| [cli](./cli/) | `pip install agentincident-cli` | CLI report generator |
| [classifier-reference](./classifier-reference/) | `pip install agentincident-classifier` | Reference rules classifier |
| [examples](./examples/) | — | Sample incidents |

## The Spec

See [SPEC.md](./SPEC.md) for the full specification.

## Framework Integrations

- **LangChain:** `pip install agentincident[langchain]`
- **CrewAI:** `pip install agentincident[crewai]`
- **OpenAI Agents:** `pip install agentincident[openai-agents]`
- **Vercel AI SDK:** `import { createAgentIncidentStepCallback } from "agentincident/integrations/vercel-ai"`

## License

Apache 2.0
