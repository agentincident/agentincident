import { describe, it, expect } from "vitest";
import type {
  TraceEntry,
  Constraint,
  Meta,
  Classification,
  Liability,
  LossEstimate,
  ResponseAction,
  Verification,
  ConstraintUpdate,
  Response,
  Incident,
  FaultClass,
  ImpactScore,
  EvalResult,
} from "../src/types.js";

describe("types", () => {
  it("creates a valid TraceEntry", () => {
    const entry: TraceEntry = {
      seq: 1,
      tool: "stripe.refund",
      input: { charge: "ch_9xK", amount: 47218 },
      output: { refund_id: "re_Xp7", status: "succeeded" },
      ts: "2026-02-09T22:41:07Z",
      hash: "sha256:abc123",
      duration_ms: 1204,
      irreversible: true,
      agent_reasoning: "Customer requested a refund",
    };
    expect(entry.seq).toBe(1);
    expect(entry.tool).toBe("stripe.refund");
    expect(entry.irreversible).toBe(true);
  });

  it("creates a valid Constraint", () => {
    const c: Constraint = {
      policy: "refund_policy_v3",
      version: "3.1.0",
      eval_result: "pass",
      breach_delta: 2782,
      gaps_identified: ["no cumulative_exposure constraint"],
    };
    expect(c.policy).toBe("refund_policy_v3");
    expect(c.eval_result).toBe("pass");
  });

  it("creates a valid Meta", () => {
    const meta: Meta = {
      schema: "agentincident/v0.1",
      incident_id: "INC-2026-0247",
      incident_type: "INCIDENT",
      created_at: "2026-02-10T03:17:42Z",
      updated_at: "2026-02-10T10:30:00Z",
      agent: "refund-processor-v3",
      framework: "langchain",
      environment: "production",
      trigger: "support_ticket:CS-88412",
    };
    expect(meta.schema).toBe("agentincident/v0.1");
    expect(meta.environment).toBe("production");
  });

  it("creates a valid Classification", () => {
    const cls: Classification = {
      fault_class: "SPEC_AMBIGUITY",
      fault_subclass: "refund_policy_boundary/cumulative_exposure",
      confidence: 0.84,
      classifier: "hybrid",
      status: "human_confirmed",
      reviewed_by: "maria@acme.com",
      evidence: ["Policy evaluated and returned PASS"],
      counterfactuals: ["If policy included cumulative cap..."],
    };
    expect(cls.confidence).toBe(0.84);
    expect(cls.classifier).toBe("hybrid");
  });

  it("creates a valid Liability", () => {
    const l: Liability = {
      primary: "spec_owner:payments-team@acme.com",
      contributing: ["agent:selection_error"],
      policy_owner: "payments-team@acme.com",
    };
    expect(l.primary).toContain("spec_owner");
  });

  it("creates a valid LossEstimate", () => {
    const le: LossEstimate = {
      total_usd: 48868,
      confidence: "medium",
      breakdown: {
        direct_cash_loss: 47218,
        remediation_labor: 1200,
        reputational_cost: null,
      },
    };
    expect(le.total_usd).toBe(48868);
    expect(le.breakdown?.reputational_cost).toBeNull();
  });

  it("creates a valid ResponseAction", () => {
    const action: ResponseAction = {
      description: "Initiated Stripe dispute",
      status: "done",
      owner: "jake.r@acme.com",
      completed_at: "2026-02-10T00:12:00Z",
    };
    expect(action.status).toBe("done");
  });

  it("creates a valid Verification", () => {
    const v: Verification = {
      test: "Replay incident trace",
      method: "deterministic_replay",
      result: "pass",
    };
    expect(v.result).toBe("pass");
  });

  it("creates a valid ConstraintUpdate", () => {
    const cu: ConstraintUpdate = {
      from: "refund_policy_v3",
      to: "refund_policy_v4",
      diff: { added: { max_cumulative: 50000 } },
      deployed_at: "2026-02-10T04:30:00Z",
    };
    expect(cu.from).toBe("refund_policy_v3");
    expect(cu.to).toBe("refund_policy_v4");
  });

  it("creates a valid Response", () => {
    const resp: Response = {
      actions: [
        { description: "Fix deployed", status: "done" },
      ],
      constraint_update: { from: "v3", to: "v4" },
      verification: [
        { test: "Regression suite", method: "automated", result: "pass" },
      ],
      time_to_detect_sec: 357,
      time_to_contain_sec: 3177,
      time_to_remediate_sec: 20940,
    };
    expect(resp.time_to_detect_sec).toBe(357);
  });

  it("creates a valid Incident with all fields", () => {
    const incident: Incident = {
      trace: [
        {
          seq: 1,
          tool: "test.tool",
          input: { a: 1 },
          output: { b: 2 },
          ts: "2026-01-01T00:00:00Z",
          hash: "sha256:abc",
        },
      ],
      constraints: [{ policy: "test_policy", eval_result: "fail" }],
      fault_class: "AGENT_ERROR",
      impact_score: 3,
      loss_amount_usd: 1000,
      meta: { schema: "agentincident/v0.1" },
      classification: { fault_class: "AGENT_ERROR", confidence: 0.9 },
      liability: { primary: "agent:test" },
      loss_estimate: { total_usd: 1000, confidence: "high" },
      response: {
        actions: [{ description: "Fixed", status: "done" }],
      },
    };
    expect(incident.fault_class).toBe("AGENT_ERROR");
    expect(incident.trace).toHaveLength(1);
  });

  it("accepts all FaultClass values", () => {
    const classes: FaultClass[] = [
      "AGENT_ERROR",
      "SPEC_AMBIGUITY",
      "TOOL_FAILURE",
      "ADVERSARIAL_INPUT",
      "USER_FAULT",
      "UNKNOWN",
    ];
    expect(classes).toHaveLength(6);
  });

  it("accepts all ImpactScore values", () => {
    const scores: ImpactScore[] = [1, 2, 3, 4, 5];
    expect(scores).toHaveLength(5);
  });

  it("accepts all EvalResult values", () => {
    const results: EvalResult[] = ["pass", "fail"];
    expect(results).toHaveLength(2);
  });

  it("allows null loss_amount_usd", () => {
    const incident: Incident = {
      trace: [
        {
          seq: 1,
          tool: "t",
          input: {},
          output: {},
          ts: "2026-01-01T00:00:00Z",
          hash: "sha256:x",
        },
      ],
      constraints: [{ policy: "p", eval_result: "pass" }],
      fault_class: "UNKNOWN",
      impact_score: 1,
      loss_amount_usd: null,
    };
    expect(incident.loss_amount_usd).toBeNull();
  });
});
