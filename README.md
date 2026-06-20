# AgentIncident

**The AI Agent Risk & Reliability Operating System.** Instrument once → Detect, Investigate, Respond, Comply, Insure, and Prevent.

AgentIncident is a vendor-agnostic, open-core platform that turns structured incident reports into the de-facto standard for AI agent observability, forensics, risk quantification, and regulatory compliance — with a hosted SaaS layer on Cloudflare.

## Open Standard (Apache 2.0)

The spec spreads through tooling, exactly like OpenTelemetry did for observability:

| Package | Install | Description |
|---------|---------|-------------|
| [schema](./schema/) | — | JSON Schema ([core](./schema/) + [extended](./schema/extended.json)) |
| [sdk-python](./sdk-python/) | `pip install agentincident` | Python recorder SDK |
| [sdk-typescript](./sdk-typescript/) | `npm install agentincident` | TypeScript recorder SDK |
| [cli](./cli/) | `pip install agentincident-cli` | CLI report generator |
| [classifier-reference](./classifier-reference/) | `pip install agentincident-classifier` | Reference rules classifier |
| [examples](./examples/) | — | Sample incidents |

## Platform

Hosted at [agentincident.com](https://agentincident.com) on **Cloudflare Workers + D1 + Pages**:

| Module | Capability |
|--------|------------|
| SDK & Ingestion | Batch/stream ingestion (`/api/ingest/*`) |
| Live Dashboard | Real-time fleet view, stats, event stream |
| Forensic Replay | Step-by-step trace playback + action graphs |
| RCA + Auto-Report | LLM root cause + remediation playbooks |
| Risk & Insurance | Composite risk scoring, insurability, carrier export |
| Compliance | EU AI Act, NIST, ISO 42001 one-click exports |
| Containment | `pause_agent`, `kill_swarm`, `human_approve` webhooks |

- **Free** — Paste a trace → full 11-section investigation report
- **Team / Pro** — Dashboard, fleet view, alerts, multi-user ($49–299/mo)
- **Enterprise** — SSO, compliance exports, SLAs ($5k–50k+/yr)

API reference: [platform/docs/api.md](./platform/docs/api.md) · [OpenAPI](./platform/docs/openapi.yaml)

**Stack mapping** (spec → production): Workers+Hono replaces FastAPI; D1 replaces Postgres; Vite/React replaces Next.js; Workers AI replaces LangGraph for RCA; Cloudflare KV + D1 ingest replaces Kafka/NATS.

### Quick Start (SDK)

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

### CLI

```bash
agentincident report examples/minimal-core.json
agentincident validate examples/INC-2026-0247-full.json --level full
```

## Framework Integrations

- **LangChain:** `pip install agentincident[langchain]`
- **CrewAI:** `pip install agentincident[crewai]`
- **OpenAI Agents:** `pip install agentincident[openai-agents]`
- **Vercel AI SDK:** `import { createAgentIncidentStepCallback } from "agentincident/integrations/vercel-ai"`

## The Spec

See [SPEC.md](./SPEC.md) for the full specification.

## License

Apache 2.0