/**
 * Scenario-based tests using realistic agent error/issue patterns.
 *
 * Each describe block simulates a real-world agent incident end-to-end:
 * recording trace entries, building the incident, serializing, validating,
 * and redacting — exercising the full SDK pipeline.
 */
import { describe, it, expect, beforeEach } from "vitest";
import { Recorder } from "../src/recorder.js";
import { computeHash } from "../src/hash.js";
import { redactIncident } from "../src/redact.js";
import { validate } from "../src/schema.js";
import {
  incidentToJSON,
  incidentFromJSON,
  incidentToDict,
  incidentFromDict,
} from "../src/export.js";
import type { Incident } from "../src/types.js";

// ---------------------------------------------------------------------------
// Scenario 1: Double-refund due to spec ambiguity
// ---------------------------------------------------------------------------
describe("Scenario: Double refund (spec ambiguity)", () => {
  let incident: Incident;

  beforeEach(() => {
    const recorder = new Recorder({
      agent: "refund-bot-beta",
      framework: "langchain",
      environment: "production",
    });

    // Step 1: Agent looks up the charge
    recorder.record(
      "stripe.charges.retrieve",
      { charge_id: "ch_3xJ8qMk" },
      { id: "ch_3xJ8qMk", amount: 15000, currency: "usd", refunded: false },
      { duration_ms: 230 }
    );
    // Step 2: First refund — succeeds
    recorder.record(
      "stripe.refunds.create",
      { charge: "ch_3xJ8qMk", amount: 15000 },
      { id: "re_A1b", status: "succeeded" },
      {
        irreversible: true,
        duration_ms: 540,
        agent_reasoning: "Customer requested full refund per policy",
      }
    );
    // Step 3: Duplicate refund — also succeeds (no idempotency key!)
    recorder.record(
      "stripe.refunds.create",
      { charge: "ch_3xJ8qMk", amount: 15000 },
      { id: "re_C3d", status: "succeeded" },
      {
        irreversible: true,
        duration_ms: 480,
        agent_reasoning:
          "Retry after perceived timeout; no idempotency guard",
      }
    );

    incident = recorder.toIncident({
      fault_class: "SPEC_AMBIGUITY",
      impact_score: 4,
      loss_amount_usd: 150.0,
      constraints: [
        {
          policy: "refund_policy_r3",
          eval_result: "fail",
          version: "2.0.3",
          breach_delta: 15000,
          gaps_identified: [
            "no idempotency key required",
            "no duplicate-refund guard",
          ],
        },
      ],
      classification: {
        fault_class: "SPEC_AMBIGUITY",
        confidence: 0.92,
        classifier: "hybrid",
        status: "human_confirmed",
        evidence: ["Two refunds for same charge within 5s"],
      },
      liability: {
        primary: "spec_owner:payments-team@acme.com",
        contributing: ["agent:retry_logic"],
      },
      loss_estimate: {
        total_usd: 150.0,
        confidence: "high",
        breakdown: { duplicate_refund: 150.0 },
      },
      response: {
        actions: [
          { description: "Reverse duplicate refund", status: "done" },
          {
            description: "Add idempotency key to refund flow",
            status: "in_progress",
            owner: "alice@acme.com",
          },
        ],
        constraint_update: {
          from: "refund_policy_r3",
          to: "refund_policy_v3",
          diff: { added: { require_idempotency_key: true } },
        },
        verification: [
          {
            test: "replay_refund",
            method: "deterministic",
            result: "pass",
          },
        ],
        time_to_detect_sec: 45,
        time_to_contain_sec: 300,
        time_to_remediate_sec: 7200,
      },
    });
  });

  it("has three trace entries", () => {
    expect(incident.trace).toHaveLength(3);
  });

  it("marks both refunds as irreversible", () => {
    expect(incident.trace[1].irreversible).toBe(true);
    expect(incident.trace[2].irreversible).toBe(true);
    expect(incident.trace[0].irreversible).toBeUndefined();
  });

  it("records agent reasoning for duplicate refund", () => {
    expect(incident.trace[2].agent_reasoning).toContain("idempotency");
  });

  it("round-trips through JSON", () => {
    const json = incidentToJSON(incident, 2);
    const restored = incidentFromJSON(json);
    expect(restored.fault_class).toBe("SPEC_AMBIGUITY");
    expect(restored.impact_score).toBe(4);
    expect(restored.trace).toHaveLength(3);
    expect(restored.response?.constraint_update?.from).toBe(
      "refund_policy_r3"
    );
    expect(restored.response?.constraint_update?.to).toBe(
      "refund_policy_v3"
    );
  });

  it("validates at full level", () => {
    const dict = incidentToDict(incident);
    const errors = validate(dict, "full");
    expect(errors).toHaveLength(0);
  });

  it("produces different hashes for the two refunds (different outputs)", () => {
    expect(incident.trace[1].hash).not.toBe(incident.trace[2].hash);
  });

  it("redacts charge IDs via field redaction", () => {
    const redacted = redactIncident(incident, {
      fields: ["charge", "charge_id"],
    });
    expect(redacted.trace[0].input.charge_id).toBe("[REDACTED]");
    expect(redacted.trace[1].input.charge).toBe("[REDACTED]");
    expect(redacted.trace).toHaveLength(3);
    expect(redacted.fault_class).toBe("SPEC_AMBIGUITY");
  });
});

// ---------------------------------------------------------------------------
// Scenario 2: Adversarial SQL injection via tool input
// ---------------------------------------------------------------------------
describe("Scenario: Adversarial SQL injection", () => {
  const maliciousInput = "'; DROP TABLE users; --";

  function buildIncident(): Incident {
    const input1 = { channel: "support" };
    const output1 = {
      user_message: `Look up order ${maliciousInput}`,
    };
    const input2 = {
      sql: `SELECT * FROM orders WHERE id = '${maliciousInput}'`,
    };
    const output2 = {
      error: 'relation "users" does not exist',
    };

    return {
      trace: [
        {
          seq: 1,
          tool: "chat.receive",
          input: input1,
          output: output1,
          ts: "2026-03-15T14:22:00Z",
          hash: computeHash(input1, output1),
          duration_ms: 15,
        },
        {
          seq: 2,
          tool: "db.query",
          input: input2,
          output: output2,
          ts: "2026-03-15T14:22:00Z",
          hash: computeHash(input2, output2),
          duration_ms: 42,
          irreversible: true,
          agent_reasoning:
            "Constructed SQL from user input without sanitization",
        },
      ],
      constraints: [
        {
          policy: "input_sanitization_v1",
          eval_result: "fail",
          gaps_identified: [
            "no parameterized queries",
            "no input validation",
          ],
        },
        { policy: "data_access_r3", eval_result: "fail" },
      ],
      fault_class: "ADVERSARIAL_INPUT",
      impact_score: 5,
      loss_amount_usd: null,
      meta: {
        incident_id: "INC-2026-0391",
        incident_type: "INCIDENT",
        created_at: "2026-03-15T14:22:00Z",
        agent: "support-bot-v1",
        environment: "production",
      },
      classification: {
        fault_class: "ADVERSARIAL_INPUT",
        confidence: 0.99,
        classifier: "rules",
        status: "human_confirmed",
        evidence: [
          "SQL injection pattern detected in user input",
          "Unparameterized query constructed",
        ],
        counterfactuals: [
          "Parameterized query would have prevented execution",
          "Input validation would have rejected the payload",
        ],
      },
    };
  }

  it("preserves null loss_amount_usd through JSON roundtrip", () => {
    const inc = buildIncident();
    const json = incidentToJSON(inc);
    expect(json).toContain('"loss_amount_usd":null');
    const restored = incidentFromJSON(json);
    expect(restored.loss_amount_usd).toBeNull();
  });

  it("records multiple constraint failures", () => {
    const inc = buildIncident();
    expect(inc.constraints).toHaveLength(2);
    expect(inc.constraints.every((c) => c.eval_result === "fail")).toBe(true);
  });

  it("round-trips counterfactuals", () => {
    const inc = buildIncident();
    const dict = incidentToDict(inc);
    const restored = incidentFromDict(dict);
    expect(restored.classification?.counterfactuals).toHaveLength(2);
    expect(restored.classification?.counterfactuals?.[0]).toContain(
      "Parameterized"
    );
  });

  it("validates at standard level with loss_estimate added", () => {
    const inc = buildIncident();
    const dict = incidentToDict(inc) as Record<string, unknown>;
    (dict as Record<string, unknown>).loss_estimate = { total_usd: 0 };
    const errors = validate(dict, "standard");
    expect(errors).toHaveLength(0);
  });

  it("fails full-level validation (missing liability/response)", () => {
    const inc = buildIncident();
    const dict = incidentToDict(inc);
    const errors = validate(dict, "full");
    expect(errors.length).toBeGreaterThan(0);
  });
});

// ---------------------------------------------------------------------------
// Scenario 3: Tool failure cascading through multi-step workflow
// ---------------------------------------------------------------------------
describe("Scenario: Tool failure cascade", () => {
  let incident: Incident;

  beforeEach(() => {
    const rec = new Recorder({
      agent: "order-processor",
      environment: "production",
    });

    // Step 1: Fetch order — OK
    rec.record(
      "orders.get",
      { order_id: "ORD-99821" },
      { id: "ORD-99821", total: 299.99, status: "pending" },
      { duration_ms: 180 }
    );
    // Step 2: Charge payment — API timeout
    rec.record(
      "payments.charge",
      { amount: 299.99, token: "tok_visa_4242" },
      { error: "Gateway timeout after 30000ms" },
      { duration_ms: 30000 }
    );
    // Step 3: Agent incorrectly marks order as fulfilled
    rec.record(
      "orders.update",
      { order_id: "ORD-99821", status: "fulfilled" },
      { id: "ORD-99821", status: "fulfilled" },
      {
        irreversible: true,
        duration_ms: 95,
        agent_reasoning:
          "Assumed payment succeeded; did not check response",
      }
    );
    // Step 4: Shipping triggered on unfunded order
    rec.record(
      "shipping.create",
      { order_id: "ORD-99821", address: "123 Main St" },
      { tracking: "1Z999AA10123456784" },
      { irreversible: true, duration_ms: 250 }
    );

    incident = rec.toIncident({
      fault_class: "AGENT_ERROR",
      impact_score: 4,
      loss_amount_usd: 299.99,
      constraints: [
        {
          policy: "payment_verification_v1",
          eval_result: "fail",
          gaps_identified: [
            "no payment success check before fulfillment",
          ],
        },
      ],
    });
  });

  it("has four trace steps in correct order", () => {
    expect(incident.trace).toHaveLength(4);
    const tools = incident.trace.map((e) => e.tool);
    expect(tools).toEqual([
      "orders.get",
      "payments.charge",
      "orders.update",
      "shipping.create",
    ]);
  });

  it("records the payment failure", () => {
    const payment = incident.trace[1];
    expect(payment.output).toHaveProperty("error");
    expect((payment.output.error as string).toLowerCase()).toContain(
      "timeout"
    );
  });

  it("marks irreversible actions after the failure", () => {
    expect(incident.trace[2].irreversible).toBe(true);
    expect(incident.trace[3].irreversible).toBe(true);
    expect(incident.trace[0].irreversible).toBeUndefined();
    expect(incident.trace[1].irreversible).toBeUndefined();
  });

  it("tracks durations including the long timeout", () => {
    expect(incident.trace[1].duration_ms).toBe(30000);
    expect(incident.trace[0].duration_ms).toBeLessThan(1000);
  });

  it("round-trips the error through JSON", () => {
    const json = incidentToJSON(incident, 2);
    const restored = incidentFromJSON(json);
    expect((restored.trace[1].output.error as string)).toContain(
      "Gateway timeout"
    );
  });

  it("redacts payment token and address", () => {
    const redacted = redactIncident(incident, {
      fields: ["token", "address"],
    });
    expect(redacted.trace[1].input.token).toBe("[REDACTED]");
    expect(redacted.trace[3].input.address).toBe("[REDACTED]");
    // Other fields preserved
    expect(redacted.trace[0].input.order_id).toBe("ORD-99821");
  });

  it("recomputes hashes after redaction", () => {
    const redacted = redactIncident(incident, { fields: ["token"] });
    for (const entry of redacted.trace) {
      const expected = computeHash(entry.input, entry.output);
      expect(entry.hash).toBe(expected);
    }
  });

  it("has monotonically increasing seq numbers", () => {
    const seqs = incident.trace.map((e) => e.seq);
    expect(seqs).toEqual([1, 2, 3, 4]);
  });
});

// ---------------------------------------------------------------------------
// Scenario 4: Near-miss caught by constraints
// ---------------------------------------------------------------------------
describe("Scenario: Near-miss blocked by constraints", () => {
  function buildIncident(): Incident {
    const input = {
      table: "customers",
      format: "csv",
      filter: "all",
    };
    const output = {
      error: "BLOCKED by policy: bulk_export_restricted",
    };
    return {
      trace: [
        {
          seq: 1,
          tool: "data.export",
          input,
          output,
          ts: "2026-04-01T09:00:00Z",
          hash: computeHash(input, output),
          agent_reasoning:
            "User asked for full customer list export",
        },
      ],
      constraints: [
        { policy: "data_access_v3", eval_result: "pass", version: "3.2.0" },
        {
          policy: "bulk_export_restriction",
          eval_result: "pass",
          version: "1.0.0",
        },
      ],
      fault_class: "USER_FAULT",
      impact_score: 1,
      loss_amount_usd: 0,
      meta: {
        incident_type: "NEAR_MISS",
        agent: "data-assistant",
        environment: "production",
      },
    };
  }

  it("has NEAR_MISS incident type", () => {
    expect(buildIncident().meta?.incident_type).toBe("NEAR_MISS");
  });

  it("has zero loss", () => {
    expect(buildIncident().loss_amount_usd).toBe(0);
  });

  it("has all passing constraints (they blocked the action)", () => {
    const inc = buildIncident();
    expect(inc.constraints.every((c) => c.eval_result === "pass")).toBe(
      true
    );
  });

  it("records the block in the trace output", () => {
    expect(buildIncident().trace[0].output.error).toContain("BLOCKED");
  });

  it("validates at core level", () => {
    const dict = incidentToDict(buildIncident());
    const errors = validate(dict, "core");
    expect(errors).toHaveLength(0);
  });

  it("round-trips preserving near-miss metadata", () => {
    const inc = buildIncident();
    const json = incidentToJSON(inc, 2);
    const restored = incidentFromJSON(json);
    expect(restored.meta?.incident_type).toBe("NEAR_MISS");
    expect(restored.loss_amount_usd).toBe(0);
    expect(restored.fault_class).toBe("USER_FAULT");
  });
});

// ---------------------------------------------------------------------------
// Scenario 5: Recorder.wrap() with error capture
// ---------------------------------------------------------------------------
describe("Scenario: Wrapped function error capture", () => {
  it("records successful calls in sequence", async () => {
    const rec = new Recorder({ agent: "calculator" });

    const divide = rec.wrap(
      "math.divide",
      (a: number, b: number) => {
        if (b === 0) throw new Error("Division by zero");
        return a / b;
      }
    );

    const result1 = await divide(10, 2);
    expect(result1).toBe(5);

    const result2 = await divide(20, 4);
    expect(result2).toBe(5);

    expect(rec.entries).toHaveLength(2);
    expect(rec.entries[0].output).toEqual({ result: 5 });
    expect(rec.entries[1].output).toEqual({ result: 5 });
    // Seq is monotonic
    expect(rec.entries[0].seq).toBe(1);
    expect(rec.entries[1].seq).toBe(2);
  });

  it("propagates errors from wrapped functions", async () => {
    const rec = new Recorder();
    const fail = rec.wrap("fail.op", () => {
      throw new Error("boom");
    });
    await expect(fail()).rejects.toThrow("boom");
  });

  it("tracks duration for async functions", async () => {
    const rec = new Recorder();
    const slow = rec.wrap("slow.op", async () => {
      await new Promise((r) => setTimeout(r, 60));
      return "done";
    });
    await slow();
    expect(rec.entries[0].duration_ms).toBeGreaterThanOrEqual(50);
  });
});

// ---------------------------------------------------------------------------
// Scenario 6: Full pipeline — record → incident → export → redact → validate
// ---------------------------------------------------------------------------
describe("Scenario: Full pipeline with PII", () => {
  it("records, builds, redacts, exports, and validates end-to-end", () => {
    // 1. Record trace with PII
    const rec = new Recorder({
      agent: "support-bot",
      environment: "production",
    });
    rec.record(
      "crm.lookup",
      { email: "john.doe@example.com" },
      {
        name: "John Doe",
        card_on_file: "4532-0150-0000-1234",
        api_key: "sk-abcdef1234567890abcdef",
      }
    );
    rec.record(
      "email.send",
      {
        to: "john.doe@example.com",
        body: "Your refund is being processed.",
      },
      {
        status: "sent",
        auth_header: "Bearer eyJhbGciOiJIUzI1NiJ9.payload.sig",
      }
    );

    // 2. Build incident
    const incident = rec.toIncident({
      fault_class: "AGENT_ERROR",
      impact_score: 3,
      loss_amount_usd: 50.0,
      constraints: [{ policy: "pii_handling_v1", eval_result: "fail" }],
    });

    // 3. Validate before redaction
    const dict = incidentToDict(incident);
    const errorsBeforeRedact = validate(dict, "core");
    expect(errorsBeforeRedact).toHaveLength(0);

    // 4. Redact PII
    const redacted = redactIncident(incident);

    // 5. Verify PII is gone
    const crmOutput = JSON.stringify(redacted.trace[0].output);
    expect(crmOutput).not.toContain("4532");
    expect(crmOutput).not.toContain("sk-abcdef");
    const crmInput = JSON.stringify(redacted.trace[0].input);
    expect(crmInput).not.toContain("john.doe@example.com");
    const emailOutput = JSON.stringify(redacted.trace[1].output);
    expect(emailOutput).not.toContain("Bearer");

    // 6. Hashes recomputed
    for (const entry of redacted.trace) {
      expect(entry.hash).toBe(computeHash(entry.input, entry.output));
    }

    // 7. Export redacted incident
    const json = incidentToJSON(redacted, 2);
    const restored = incidentFromJSON(json);
    expect(restored.trace).toHaveLength(2);
    expect(restored.fault_class).toBe("AGENT_ERROR");

    // 8. Validate redacted incident
    const redactedDict = incidentToDict(restored);
    const errorsAfterRedact = validate(redactedDict, "core");
    expect(errorsAfterRedact).toHaveLength(0);
  });

  it("does not modify the original incident", () => {
    const rec = new Recorder();
    rec.record(
      "t",
      { email: "secret@test.com" },
      { key: "sk-test_abcdefghijklmnopqrst" }
    );
    const incident = rec.toIncident({
      fault_class: "UNKNOWN",
      impact_score: 1,
      loss_amount_usd: null,
      constraints: [{ policy: "p", eval_result: "pass" }],
    });
    const originalEmail = incident.trace[0].input.email;
    redactIncident(incident);
    expect(incident.trace[0].input.email).toBe(originalEmail);
  });
});

// ---------------------------------------------------------------------------
// Scenario 7: Complex nested data in trace
// ---------------------------------------------------------------------------
describe("Scenario: Complex nested data", () => {
  it("round-trips deeply nested objects through JSON", () => {
    const entryInput = {
      query: {
        filters: [
          { field: "status", op: "eq", value: "active" },
          { field: "amount", op: "gt", value: 1000 },
        ],
        pagination: { page: 1, per_page: 50 },
      },
    };
    const entryOutput = {
      results: [
        { id: 1, nested: { deep: { value: true } } },
        { id: 2, nested: { deep: { value: false } } },
      ],
      meta: { total: 2, pages: 1 },
    };
    const inc: Incident = {
      trace: [
        {
          seq: 1,
          tool: "search",
          input: entryInput,
          output: entryOutput,
          ts: "2026-01-01T00:00:00Z",
          hash: computeHash(entryInput, entryOutput),
        },
      ],
      constraints: [{ policy: "p", eval_result: "pass" }],
      fault_class: "UNKNOWN",
      impact_score: 1,
      loss_amount_usd: null,
    };
    const json = incidentToJSON(inc, 2);
    const restored = incidentFromJSON(json);
    const q = restored.trace[0].input.query as Record<string, unknown>;
    const filters = q.filters as Record<string, unknown>[];
    expect(filters[1].value).toBe(1000);
    const results = restored.trace[0].output.results as Record<
      string,
      unknown
    >[];
    const nested = results[0].nested as Record<string, unknown>;
    const deep = nested.deep as Record<string, unknown>;
    expect(deep.value).toBe(true);
  });

  it("handles special characters in values", () => {
    const inc: Incident = {
      trace: [
        {
          seq: 1,
          tool: "chat",
          input: { message: 'Line 1\nLine 2\t"quoted"' },
          output: { response: "Unicode & <html> \u00a9 2026" },
          ts: "2026-01-01T00:00:00Z",
          hash: computeHash(
            { message: 'Line 1\nLine 2\t"quoted"' },
            { response: "Unicode & <html> \u00a9 2026" }
          ),
        },
      ],
      constraints: [{ policy: "p", eval_result: "pass" }],
      fault_class: "UNKNOWN",
      impact_score: 1,
      loss_amount_usd: null,
    };
    const json = incidentToJSON(inc);
    const restored = incidentFromJSON(json);
    expect(restored.trace[0].input.message).toBe(
      'Line 1\nLine 2\t"quoted"'
    );
  });

  it("handles empty input/output", () => {
    const inc: Incident = {
      trace: [
        {
          seq: 1,
          tool: "noop",
          input: {},
          output: {},
          ts: "2026-01-01T00:00:00Z",
          hash: computeHash({}, {}),
        },
      ],
      constraints: [{ policy: "p", eval_result: "pass" }],
      fault_class: "UNKNOWN",
      impact_score: 1,
      loss_amount_usd: null,
    };
    const json = incidentToJSON(inc);
    const restored = incidentFromJSON(json);
    expect(restored.trace[0].input).toEqual({});
    expect(restored.trace[0].output).toEqual({});
  });
});

// ---------------------------------------------------------------------------
// Scenario 8: Redaction edge cases
// ---------------------------------------------------------------------------
describe("Scenario: Redaction edge cases", () => {
  function makeInc(
    input: Record<string, unknown>,
    output: Record<string, unknown>
  ): Incident {
    return {
      trace: [
        {
          seq: 1,
          tool: "t",
          input,
          output,
          ts: "2026-01-01T00:00:00Z",
          hash: computeHash(input, output),
        },
      ],
      constraints: [{ policy: "p", eval_result: "pass" }],
      fault_class: "UNKNOWN",
      impact_score: 1,
      loss_amount_usd: null,
    };
  }

  it("redacts multiple emails in one string", () => {
    const inc = makeInc(
      { msg: "CC alice@a.com and bob@b.com on this" },
      {}
    );
    const redacted = redactIncident(inc);
    const msg = redacted.trace[0].input.msg as string;
    expect(msg).not.toContain("alice@a.com");
    expect(msg).not.toContain("bob@b.com");
  });

  it("redacts credit card without separators", () => {
    const inc = makeInc({ card: "4111111111111111" }, {});
    const redacted = redactIncident(inc);
    expect(redacted.trace[0].input.card).not.toContain(
      "4111111111111111"
    );
  });

  it("leaves non-string values unchanged", () => {
    const inc = makeInc(
      { count: 42, active: true, ratio: 3.14 },
      { items: [1, 2, 3] }
    );
    const redacted = redactIncident(inc);
    expect(redacted.trace[0].input.count).toBe(42);
    expect(redacted.trace[0].input.active).toBe(true);
    expect(redacted.trace[0].input.ratio).toBe(3.14);
    expect(redacted.trace[0].output.items).toEqual([1, 2, 3]);
  });

  it("redacts deeply nested PII", () => {
    const inc = makeInc(
      {
        level1: {
          level2: { level3: { email: "deep@nested.com" } },
        },
      },
      {}
    );
    const redacted = redactIncident(inc);
    const l1 = redacted.trace[0].input.level1 as Record<string, unknown>;
    const l2 = l1.level2 as Record<string, unknown>;
    const l3 = l2.level3 as Record<string, unknown>;
    expect(l3.email).not.toContain("deep@nested.com");
    expect(l3.email).toBe("[REDACTED]");
  });

  it("combines field-level and pattern-level redaction", () => {
    const inc = makeInc(
      { password: "myp@ss", note: "Contact admin@co.com" },
      { token: "sk-abcdefghijklmnopqrstuvwxyz" }
    );
    const redacted = redactIncident(inc, { fields: ["password"] });
    expect(redacted.trace[0].input.password).toBe("[REDACTED]");
    expect((redacted.trace[0].input.note as string)).not.toContain(
      "admin@co.com"
    );
    expect(JSON.stringify(redacted.trace[0].output)).not.toContain(
      "sk-abcdef"
    );
  });

  it("supports custom patterns", () => {
    const inc = makeInc({ secret: "INTERNAL-KEY-abc123xyz" }, {});
    const redacted = redactIncident(inc, {
      patterns: [/INTERNAL-KEY-\w+/g],
    });
    expect(
      (redacted.trace[0].input.secret as string)
    ).not.toContain("INTERNAL-KEY");
  });
});

// ---------------------------------------------------------------------------
// Scenario 9: Schema validation edge cases
// ---------------------------------------------------------------------------
describe("Scenario: Schema validation edge cases", () => {
  const makeBase = () => ({
    trace: [
      {
        seq: 1,
        tool: "t",
        input: {},
        output: {},
        ts: "2026-01-01T00:00:00Z",
        hash: "sha256:abc123def456",
      },
    ],
    constraints: [{ policy: "p", eval_result: "pass" }],
    fault_class: "UNKNOWN",
    loss_amount_usd: null,
  });

  it("accepts all valid impact scores (1-5)", () => {
    for (const score of [1, 2, 3, 4, 5]) {
      const data = { ...makeBase(), impact_score: score };
      const errors = validate(data, "core");
      expect(errors).toHaveLength(0);
    }
  });

  it("rejects invalid impact scores", () => {
    for (const score of [0, 6, -1, 100]) {
      const data = { ...makeBase(), impact_score: score };
      const errors = validate(data, "core");
      expect(errors.length).toBeGreaterThan(0);
    }
  });

  it("accepts all valid fault classes", () => {
    const validClasses = [
      "AGENT_ERROR",
      "SPEC_AMBIGUITY",
      "TOOL_FAILURE",
      "ADVERSARIAL_INPUT",
      "USER_FAULT",
      "UNKNOWN",
    ];
    for (const fc of validClasses) {
      const data = { ...makeBase(), fault_class: fc, impact_score: 1 };
      const errors = validate(data, "core");
      expect(errors).toHaveLength(0);
    }
  });

  it("rejects invalid eval_result", () => {
    const data = {
      ...makeBase(),
      impact_score: 1,
      constraints: [{ policy: "p", eval_result: "maybe" }],
    };
    const errors = validate(data, "core");
    expect(errors.length).toBeGreaterThan(0);
  });

  it("accepts null loss_amount_usd", () => {
    const data = { ...makeBase(), impact_score: 1 };
    const errors = validate(data, "core");
    expect(errors).toHaveLength(0);
  });

  it("accepts zero loss_amount_usd", () => {
    const data = {
      ...makeBase(),
      impact_score: 1,
      loss_amount_usd: 0,
    };
    const errors = validate(data, "core");
    expect(errors).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// Scenario 10: Recorder meta merging
// ---------------------------------------------------------------------------
describe("Scenario: Recorder meta merging", () => {
  it("constructor options provide defaults for meta", () => {
    const rec = new Recorder({
      agent: "default-agent",
      framework: "default-fw",
      environment: "staging",
    });
    rec.record("t", {}, {});
    const inc = rec.toIncident({
      fault_class: "UNKNOWN",
      impact_score: 1,
      loss_amount_usd: null,
      constraints: [{ policy: "p", eval_result: "pass" }],
    });
    expect(inc.meta?.agent).toBe("default-agent");
    expect(inc.meta?.framework).toBe("default-fw");
    expect(inc.meta?.environment).toBe("staging");
  });

  it("user-provided meta overrides constructor defaults", () => {
    const rec = new Recorder({ agent: "default-agent" });
    rec.record("t", {}, {});
    const inc = rec.toIncident({
      fault_class: "UNKNOWN",
      impact_score: 1,
      loss_amount_usd: null,
      constraints: [{ policy: "p", eval_result: "pass" }],
      meta: { agent: "override-agent", incident_id: "INC-CUSTOM" },
    });
    expect(inc.meta?.agent).toBe("override-agent");
    expect(inc.meta?.incident_id).toBe("INC-CUSTOM");
  });

  it("toJSON throws before toIncident", () => {
    const rec = new Recorder();
    rec.record("t", {}, {});
    expect(() => rec.toJSON()).toThrow("No incident created yet");
  });
});
