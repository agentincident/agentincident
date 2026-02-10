# agentincident (TypeScript SDK)

Recorder SDK for the [AgentIncident](https://agentincident.com) incident specification.

## Install

```bash
npm install agentincident
```

For schema validation, also install ajv (optional peer dependency):

```bash
npm install ajv ajv-formats
```

## Quick Start

```typescript
import { Recorder } from "agentincident";

const recorder = new Recorder({
  agent: "refund-processor-v3",
  framework: "langchain",
  environment: "production",
});

// Record tool calls
recorder.record(
  "stripe.refund",
  { charge: "ch_9xK", amount: 47218 },
  { refund_id: "re_Xp7", status: "succeeded" },
  { irreversible: true }
);

// Create the incident
const incident = recorder.toIncident({
  fault_class: "SPEC_AMBIGUITY",
  impact_score: 4,
  loss_amount_usd: 47218,
  constraints: [
    { policy: "refund_policy_v3", eval_result: "fail" },
  ],
});

// Export as JSON
console.log(recorder.toJSON(2));
```

## Wrap Tool Functions

```typescript
const search = recorder.wrap("stripe.charges.list", async (customerId: string) => {
  return await stripe.charges.list({ customer: customerId });
});

const result = await search("cus_4491");
// Automatically recorded with duration_ms
```

## Vercel AI SDK Integration

```typescript
import { Recorder } from "agentincident";
import { createAgentIncidentStepCallback } from "agentincident/integrations/vercel-ai";

const recorder = new Recorder({ agent: "my-agent" });
const onStepFinish = createAgentIncidentStepCallback(recorder);

// Pass to generateText or streamText
const result = await generateText({
  model,
  tools,
  onStepFinish,
});
```

## Redaction

```typescript
import { redactIncident } from "agentincident";

const redacted = redactIncident(incident);
// Emails, credit cards, API keys, Bearer tokens are redacted
// Hashes are recomputed
```

## Schema Validation

```typescript
import { validate } from "agentincident";

const errors = validate(data, "standard"); // "core" | "standard" | "full"
```

## Specification

See [SPEC.md](../SPEC.md) for the full AgentIncident specification.

## License

Apache 2.0
