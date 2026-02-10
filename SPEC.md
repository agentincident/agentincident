# AgentIncident Specification v0.1

**Status:** Draft
**Date:** 2026-02-10
**Authors:** agentincident.com
**License:** Apache 2.0

---

## Abstract

AgentIncident is an open, vendor-neutral specification for recording, classifying, and pricing failures and near-misses produced by autonomous AI agents.

The goal is to create a shared incident format that enables: deterministic replay of agent actions, standardized fault attribution, economic loss estimation, and closed-loop remediation tracking — producing artifacts that are useful for engineering postmortems, compliance audits, and actuarial pricing.

This specification defines the canonical JSON schema for an AgentIncident record.

---

## 1. Design Principles

1. **Minimal by default.** Five core fields. Everything else is optional. A valid AgentIncident record can be produced in under a minute.
2. **Defense artifact, not confession.** The closed-loop format (incident → classification → response → verification) is designed to demonstrate due diligence, not document negligence.
3. **Spec spreads through tooling.** The schema is embedded in recorder SDKs and report generators. Adoption happens through usage, not evangelism.
4. **Priceable.** Every design decision optimizes for producing data that actuaries can consume. If a field doesn't contribute to pricing agent risk, it doesn't belong in the core schema.
5. **Replayable.** Traces must support deterministic reconstruction of the agent's action sequence. If you can't replay it, you can't adjudicate it.
6. **Contestable.** Classifications are claims, not assertions. They carry confidence scores, evidence, counterfactuals, and review status. Disputed classifications are a first-class concept.

---

## 2. Incident Types

Every AgentIncident record MUST specify one of two types:

| Type | Definition |
|------|-----------|
| `INCIDENT` | An agent action that resulted in confirmed or estimated economic loss, policy violation, or unintended real-world effect. |
| `NEAR_MISS` | An agent action that was blocked by a constraint, guardrail, or human review before causing damage, but would have caused damage if unblocked. |

Near-misses produce the same schema as incidents. They are first-class records because they generate the distributional data required for actuarial pricing without requiring actual damage.

---

## 3. Core Schema

A valid AgentIncident record is a JSON object with the following five REQUIRED fields.

### 3.1 `trace` (array of objects)

An ordered sequence of tool calls, API requests, or decisions made by the agent. This is the deterministic replay log.

Each entry in the trace array MUST contain:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `seq` | integer | YES | Sequential index starting at 1. |
| `tool` | string | YES | Identifier of the tool, API, or action invoked. Use dot notation for namespacing (e.g., `stripe.refund`, `github.pr.create`). |
| `input` | object | YES | The input parameters passed to the tool. |
| `output` | object | YES | The output returned by the tool. |
| `ts` | string (ISO 8601) | YES | Timestamp of invocation. |
| `hash` | string | YES | Content hash of input + output for tamper evidence. Format: `sha256:<hex>`. |
| `duration_ms` | integer | NO | Execution duration in milliseconds. |
| `irreversible` | boolean | NO | If `true`, this action cannot be undone (e.g., funds transferred, email sent, data deleted). Defaults to `false`. |
| `agent_reasoning` | string | NO | The agent's stated reasoning or chain-of-thought for this action, if available. |

Example:

```json
{
  "seq": 1,
  "tool": "stripe.charges.list",
  "input": {"customer": "cus_4491", "limit": 10},
  "output": {"charges": ["ch_9xK", "ch_A2m"]},
  "ts": "2026-02-09T22:41:04.112Z",
  "duration_ms": 892,
  "hash": "sha256:a3f8c1d7e..."
}
```

### 3.2 `constraints` (array of objects)

The set of policies, guardrails, or constraints that were active and evaluated at the time of the incident.

Each entry MUST contain:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `policy` | string | YES | Identifier of the policy or constraint (e.g., `refund_policy_v3`). |
| `version` | string | NO | Version string of the policy. |
| `eval_result` | enum | YES | `pass` or `fail`. |
| `breach_delta` | number | NO | Numeric distance between the evaluated value and the policy boundary. Positive = within bounds. Negative = breach. |
| `gaps_identified` | array of strings | NO | Policy gaps discovered during or after the incident (e.g., `"no cumulative_exposure constraint"`). |

Example:

```json
{
  "policy": "refund_policy_v3",
  "version": "3.1.0",
  "eval_result": "pass",
  "breach_delta": 2782,
  "gaps_identified": ["no cumulative_exposure constraint"]
}
```

### 3.3 `fault_class` (enum)

Top-level fault attribution. MUST be one of:

| Value | Definition |
|-------|-----------|
| `AGENT_ERROR` | The agent took an action that violated its constraints or produced an incorrect result within a well-specified policy. The spec was clear; the agent got it wrong. |
| `SPEC_AMBIGUITY` | The agent operated within its stated constraints, but the constraints failed to capture the intended business rule. The spec was incomplete or ambiguous. |
| `TOOL_FAILURE` | An external tool, API, or service failed, returned unexpected results, or timed out, causing the agent to produce an incorrect outcome. |
| `ADVERSARIAL_INPUT` | The agent was manipulated by adversarial input (prompt injection, data poisoning, social engineering via user input). |
| `USER_FAULT` | The user provided incorrect instructions, approved a bad action, or misconfigured the agent. |
| `UNKNOWN` | Fault cannot be determined from available evidence. Requires further investigation. |

The `fault_class` enum is intentionally small and stable. It exists for cross-vendor, cross-industry comparability. Specificity is provided by optional extended classification fields (see Section 4).

### 3.4 `impact_score` (integer, 1–5)

Economic blast radius. Scoring criteria:

| Score | Label | Criteria |
|-------|-------|----------|
| 1 | Negligible | No economic loss. No customer impact. Internal only. |
| 2 | Low | Minor economic loss (<$1,000). Easily reversible. No customer notification required. |
| 3 | Moderate | Meaningful economic loss ($1,000–$25,000). Customer impact possible. Reversible with effort. |
| 4 | High | Significant economic loss ($25,000–$250,000). Customer impact confirmed. Partial irreversibility. |
| 5 | Critical | Severe economic loss (>$250,000). Regulatory exposure. Reputational damage. Irreversible consequences. |

Scoring is tied to economic outcomes, not technical severity. A catastrophic system crash with no customer impact is a 1. A minor bug that leaks PII to a regulator is a 5.

### 3.5 `loss_amount_usd` (number, nullable)

Actual confirmed dollar loss attributable to this incident. `null` if loss has not been confirmed or is not applicable (e.g., near-misses).

This is the actuarial anchor. Insurers price expected loss, not abstract severity. If this field is populated across a large corpus, underwriting becomes possible.

When `loss_amount_usd` is null, the `loss_estimate` extended field (Section 4) SHOULD be populated.

---

## 4. Extended Schema

The following fields are OPTIONAL but RECOMMENDED for production use. They transform the core record from a log entry into a defense artifact.

### 4.1 `meta` (object)

Record metadata.

| Field | Type | Description |
|-------|------|-------------|
| `schema` | string | Always `"agentincident/v0.1"`. |
| `incident_id` | string | Unique identifier. Recommended format: `INC-YYYY-NNNN`. |
| `incident_type` | enum | `INCIDENT` or `NEAR_MISS`. |
| `created_at` | string (ISO 8601) | When this record was created. |
| `updated_at` | string (ISO 8601) | When this record was last modified. |
| `agent` | string | Identifier of the agent (e.g., `refund-processor-v3`). |
| `framework` | string | Agent framework (e.g., `langchain`, `crewai`, `openai-agents`). |
| `environment` | enum | `production`, `staging`, `development`, `sandbox`. |
| `trigger` | string | What initiated the agent's action (e.g., `support_ticket:CS-88412`). |

### 4.2 `classification` (object)

Extended fault attribution with evidence and contestability.

| Field | Type | Description |
|-------|------|-------------|
| `fault_class` | enum | Same as core field. Included here for self-contained classification objects. |
| `fault_subclass` | string | Freeform but structured specificity. Convention: `domain/detail` (e.g., `refund_policy_boundary/cumulative_exposure`). |
| `fault_vector` | string | Structured representation. Convention: `CATEGORY:value` segments separated by `/` (e.g., `SPEC:refund_policy_v3/BOUNDARY:cumulative/ACTION:stripe.refund`). |
| `confidence` | number (0–1) | Classifier confidence in the fault_class assignment. |
| `classifier` | enum | `rules`, `llm`, `hybrid`, `human`. How the classification was produced. |
| `status` | enum | `draft`, `human_confirmed`, `disputed`, `revised`. |
| `reviewed_by` | string | Email or identifier of the human who confirmed/disputed. |
| `reviewed_at` | string (ISO 8601) | When the classification was reviewed. |
| `evidence` | array of strings | Factual observations supporting the classification. |
| `counterfactuals` | array of strings | Alternative scenarios that would have produced a different classification. |
| `review_notes` | string | Freeform notes from the reviewer. |
| `revision_history` | array of objects | Previous classification states, for audit trail. |

### 4.3 `liability` (object)

Blame graph for organizational routing.

| Field | Type | Description |
|-------|------|-------------|
| `primary` | string | Primary responsible party. Convention: `role:identifier` (e.g., `spec_owner:payments-team@acme.com`). |
| `contributing` | array of strings | Contributing factors. Same convention. |
| `policy_owner` | string | Recommended owner for remediation (e.g., `payments-team@acme.com`). |

### 4.4 `loss_estimate` (object)

Estimated loss when `loss_amount_usd` is null or as supplementary detail.

| Field | Type | Description |
|-------|------|-------------|
| `total_usd` | number | Total estimated loss in USD. |
| `confidence` | enum | `low`, `medium`, `high`. |
| `breakdown` | object | Key-value pairs of loss categories and amounts. |

Standard breakdown categories:

- `direct_cash_loss` — money directly lost (refunds, charges, transfers)
- `remediation_labor` — engineering and support time to fix
- `fees` — third-party fees (processing, reversal, dispute)
- `downtime_cost` — estimated cost of service interruption
- `reputational_cost` — estimated reputational damage (nullable)
- `regulatory_exposure` — estimated regulatory penalty exposure (nullable)

Example:

```json
{
  "total_usd": 48868,
  "confidence": "medium",
  "breakdown": {
    "direct_cash_loss": 47218,
    "remediation_labor": 1200,
    "fees": 450,
    "downtime_cost": 0,
    "reputational_cost": null,
    "regulatory_exposure": null
  }
}
```

### 4.5 `response` (object)

Closed-loop remediation tracking. This is what transforms the record from a confession into a defense artifact.

| Field | Type | Description |
|-------|------|-------------|
| `actions` | array of objects | Remediation actions taken. Each has: `description` (string), `status` (enum: `done`, `in_progress`, `planned`), `owner` (string), `completed_at` (ISO 8601, nullable). |
| `constraint_update` | object | Policy change made in response. Fields: `from` (string), `to` (string), `diff` (string or object), `deployed_at` (ISO 8601, nullable). |
| `verification` | array of objects | Tests run to verify the fix. Each has: `test` (string), `method` (string), `result` (enum: `pass`, `fail`, `pending`). |
| `time_to_detect_sec` | integer | Seconds from incident to detection. |
| `time_to_contain_sec` | integer | Seconds from incident to containment (agent suspended, action reversed). |
| `time_to_remediate_sec` | integer | Seconds from incident to remediation (fix deployed). |

---

## 5. Minimal Valid Record

The smallest valid AgentIncident record:

```json
{
  "trace": [
    {
      "seq": 1,
      "tool": "stripe.refund",
      "input": {"charge": "ch_9xK", "amount": 47218},
      "output": {"refund_id": "re_Xp7", "status": "succeeded"},
      "ts": "2026-02-09T22:41:07Z",
      "hash": "sha256:e1d4f60..."
    }
  ],
  "constraints": [
    {
      "policy": "refund_policy_v3",
      "eval_result": "pass"
    }
  ],
  "fault_class": "SPEC_AMBIGUITY",
  "impact_score": 4,
  "loss_amount_usd": 47218.00
}
```

Five fields. One tool call. One constraint. One classification. One number. Enough to start an actuarial table.

---

## 6. Complete Record Example

```json
{
  "meta": {
    "schema": "agentincident/v0.1",
    "incident_id": "INC-2026-0247",
    "incident_type": "INCIDENT",
    "created_at": "2026-02-10T03:17:42Z",
    "updated_at": "2026-02-10T10:30:00Z",
    "agent": "refund-processor-v3",
    "framework": "langchain",
    "environment": "production",
    "trigger": "support_ticket:CS-88412"
  },
  "trace": [
    {
      "seq": 1,
      "tool": "stripe.charges.list",
      "input": {"customer": "cus_4491", "limit": 10},
      "output": {"charges": ["ch_9xK ($47,218, Feb 1)", "ch_A2m ($47,218, Feb 3)"]},
      "ts": "2026-02-09T22:41:04.112Z",
      "duration_ms": 892,
      "hash": "sha256:a3f8c1d7e...",
      "irreversible": false
    },
    {
      "seq": 2,
      "tool": "policy.evaluate",
      "input": {"policy": "refund_policy_v3", "amount": 47218},
      "output": {"pass": true, "margin": 2782, "gaps": ["no cumulative_exposure"]},
      "ts": "2026-02-09T22:41:06.004Z",
      "duration_ms": 41,
      "hash": "sha256:7b2e9d4f1...",
      "irreversible": false
    },
    {
      "seq": 3,
      "tool": "stripe.refund",
      "input": {"charge": "ch_9xK", "amount": 47218},
      "output": {"refund_id": "re_Xp7", "status": "succeeded"},
      "ts": "2026-02-09T22:41:07.331Z",
      "duration_ms": 1204,
      "hash": "sha256:e1d4f60a2...",
      "irreversible": true
    },
    {
      "seq": 4,
      "tool": "email.send",
      "input": {"to": "customer@example.com", "template": "refund_confirmation", "amount": 47218},
      "output": {"message_id": "msg_abc123", "status": "sent"},
      "ts": "2026-02-09T22:41:08.102Z",
      "duration_ms": 310,
      "hash": "sha256:bc9012de...",
      "irreversible": true
    }
  ],
  "constraints": [
    {
      "policy": "refund_policy_v3",
      "version": "3.1.0",
      "eval_result": "pass",
      "breach_delta": 2782,
      "gaps_identified": ["no cumulative_exposure constraint"]
    }
  ],
  "fault_class": "SPEC_AMBIGUITY",
  "impact_score": 4,
  "loss_amount_usd": null,
  "classification": {
    "fault_class": "SPEC_AMBIGUITY",
    "fault_subclass": "refund_policy_boundary/cumulative_exposure",
    "fault_vector": "SPEC:refund_policy_v3/BOUNDARY:cumulative/ACTION:stripe.refund",
    "confidence": 0.84,
    "classifier": "hybrid",
    "status": "human_confirmed",
    "reviewed_by": "maria.chen@acme.com",
    "reviewed_at": "2026-02-10T01:15:00Z",
    "evidence": [
      "Constraint refund_policy_v3 evaluated and returned PASS (margin to limit: $2,782)",
      "Policy contains no cumulative_refund_per_customer_per_cycle constraint",
      "Agent action was consistent with policy as written",
      "Agent selected original transaction (ch_9xK) instead of duplicate (ch_A2m)"
    ],
    "counterfactuals": [
      "If refund_policy_v3 included a cumulative exposure cap, the refund would have been blocked → classify as AGENT_ERROR",
      "If the agent had selected ch_A2m instead of ch_9xK, no incident would have occurred",
      "If stripe.refund returned an error, this would classify as TOOL_FAILURE"
    ],
    "review_notes": "Primary cause is policy gap. Agent selection error is contributing but secondary.",
    "revision_history": [
      {
        "fault_class": "AGENT_ERROR",
        "confidence": 0.52,
        "classifier": "llm",
        "status": "draft",
        "ts": "2026-02-10T03:17:42Z"
      }
    ]
  },
  "liability": {
    "primary": "spec_owner:payments-team@acme.com",
    "contributing": ["agent:selection_error"],
    "policy_owner": "payments-team@acme.com"
  },
  "loss_estimate": {
    "total_usd": 48868,
    "confidence": "medium",
    "breakdown": {
      "direct_cash_loss": 47218,
      "remediation_labor": 1200,
      "fees": 450,
      "downtime_cost": 0,
      "reputational_cost": null,
      "regulatory_exposure": null
    }
  },
  "response": {
    "actions": [
      {
        "description": "Initiated Stripe dispute for refund re_Xp7",
        "status": "done",
        "owner": "jake.r@acme.com",
        "completed_at": "2026-02-10T00:12:00Z"
      },
      {
        "description": "Contacted customer to explain billing correction",
        "status": "done",
        "owner": "support@acme.com",
        "completed_at": "2026-02-10T09:00:00Z"
      },
      {
        "description": "Suspended refund-processor-v3 from production",
        "status": "done",
        "owner": "maria.chen@acme.com",
        "completed_at": "2026-02-09T23:40:00Z"
      },
      {
        "description": "Manual review of all refunds issued in last 72 hours",
        "status": "in_progress",
        "owner": "ops-team@acme.com",
        "completed_at": null
      }
    ],
    "constraint_update": {
      "from": "refund_policy_v3",
      "to": "refund_policy_v4",
      "diff": {
        "added": {
          "max_cumulative_per_customer_30d": 50000,
          "escalation_threshold": 10000,
          "require_human_approval_above": 10000,
          "duplicate_refund_preference": "most_recent_first"
        },
        "changed": {
          "max_per_transaction": {"from": 50000, "to": 10000}
        }
      },
      "deployed_at": "2026-02-10T04:30:00Z"
    },
    "verification": [
      {"test": "Replay incident trace against refund_policy_v4", "method": "deterministic_replay", "result": "pass"},
      {"test": "Cumulative exposure exceeds $50k → blocked", "method": "synthetic", "result": "pass"},
      {"test": "Single refund $10,001 → escalates to human", "method": "synthetic", "result": "pass"},
      {"test": "Duplicate charge → most recent refunded first", "method": "synthetic", "result": "pass"},
      {"test": "Regression suite (412 existing test cases)", "method": "automated", "result": "pass"},
      {"test": "72-hour canary deployment with shadow mode", "method": "production_canary", "result": "pending"}
    ],
    "time_to_detect_sec": 357,
    "time_to_contain_sec": 3177,
    "time_to_remediate_sec": 20940
  }
}
```

---

## 7. Conformance Levels

Implementations MAY declare conformance at one of three levels:

| Level | Requirements |
|-------|-------------|
| **Core** | All five required fields present and valid. Sufficient for basic incident logging. |
| **Standard** | Core + `meta` + `classification` + `loss_estimate`. Sufficient for engineering postmortems and internal reporting. |
| **Full** | Standard + `liability` + `response` (including `constraint_update` and `verification`). Sufficient for compliance audits, legal defense artifacts, and actuarial data contribution. |

Recorders and report generators SHOULD target Full conformance. Manual paste-and-generate tools MAY start at Core and progressively enhance.

---

## 8. Interoperability

### 8.1 Relationship to Agent Trace (Cognition)

Agent Trace is an authorship and provenance layer: it records who (human or AI) wrote which code and why. AgentIncident is an accountability and liability layer: it records what broke, whose fault it was, and what it cost. They are complementary. Agent Trace provides provenance data that can feed into AgentIncident's trace and classification fields.

### 8.2 Relationship to OpenTelemetry

OpenTelemetry provides general-purpose distributed tracing. AgentIncident is a domain-specific incident schema layered on top. AgentIncident recorders SHOULD export via OpenTelemetry where possible, using AgentIncident-specific attributes on spans. The `trace` field in an AgentIncident record MAY reference OpenTelemetry trace and span IDs.

### 8.3 Relationship to CVSS

The `impact_score` field is analogous to CVSS severity scores but calibrated to economic outcomes rather than technical exploitability. The `fault_vector` field in the extended classification is inspired by CVSS vector strings.

---

## 9. Security and Privacy

- **Default ephemeral.** Recorders SHOULD NOT persist incident records beyond the current session unless the user explicitly opts in to storage.
- **Redaction.** Implementations MUST provide a mechanism to redact PII, credentials, and sensitive business data from traces before storage or sharing.
- **Hashing.** The `hash` field on trace entries provides tamper evidence but MUST NOT be used as the sole integrity mechanism. Implementations SHOULD sign complete records with a separate cryptographic signature when used for legal or insurance purposes.
- **Corpus contribution.** Any system that aggregates anonymized incident records across organizations MUST strip all identifying information, including agent names, customer identifiers, internal policy names, and email addresses. Aggregation MUST be opt-in and revocable.

---

## 10. Versioning

This specification follows semantic versioning. The current version is `0.1`.

- **Patch versions** (0.1.x): clarifications and typo fixes. No schema changes.
- **Minor versions** (0.x): additive changes only. New optional fields. No breaking changes to existing fields.
- **Major versions** (x.0): breaking changes. Field removals, type changes, or semantic redefinitions.

All records MUST include `"schema": "agentincident/v0.1"` in their `meta` object (or as a top-level field for Core-level records) to enable version detection.

---

## 11. FAQ

**Why only six fault classes?**
Comparability. The enum must be small enough that every company, framework, and industry maps to the same categories. Specificity is provided by `fault_subclass` and `fault_vector`, which are freeform and can evolve organically.

**Why is `loss_amount_usd` nullable?**
Because most early adopters won't have clean cost accounting pipelines for agent actions. The `loss_estimate` extended field with its breakdown categories provides a structured alternative. Over time, as financial instrumentation improves, the confirmed field will be populated more often.

**Why include near-misses?**
Near-misses are 100x more frequent than incidents and carry zero political cost to report. They produce the same distributional data that actuaries need. The ASRS (Aviation Safety Reporting System) demonstrated that near-miss reporting is the foundation of safety culture and actuarial pricing in aviation. The same principle applies to agents.

**Why is classification contestable?**
Because the fault_class label determines who is liable. The person or team who gets blamed has strong incentives to challenge the classification. A classification that cannot be contested will be ignored or gamed. The `status`, `evidence`, `counterfactuals`, and `revision_history` fields make classification a falsifiable claim rather than an authoritative assertion.

**Why is the response section part of the spec?**
An incident report without remediation is discoverable evidence of negligence. An incident report with remediation is evidence of due diligence. The closed loop is not a feature — it is the mechanism that makes the entire format legally safe to adopt.

---

## 12. License

This specification is released under the Apache 2.0 license. You may implement, extend, and redistribute it freely. Attribution is appreciated but not required.

The AgentIncident name and schema format are not trademarked. The goal is adoption, not control.

---

*agentincident.com — Paste your agent logs. Get a professional incident report in 2 minutes.*
