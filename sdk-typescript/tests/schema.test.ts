import { describe, it, expect } from "vitest";
import { getSchema, validate } from "../src/schema.js";

describe("schema", () => {
  describe("getSchema()", () => {
    it("loads the schema JSON", () => {
      const schema = getSchema();
      expect(schema.$id).toBe("https://schema.agentincident.com/v0.1.json");
      expect(schema.title).toBe("AgentIncident v0.1");
    });

    it("returns the same instance on repeated calls", () => {
      const s1 = getSchema();
      const s2 = getSchema();
      expect(s1).toBe(s2);
    });
  });

  describe("validate()", () => {
    it("validates a minimal core record", () => {
      const data = {
        trace: [
          {
            seq: 1,
            tool: "test.tool",
            input: {},
            output: {},
            ts: "2026-01-01T00:00:00Z",
            hash: "sha256:abc123def456",
          },
        ],
        constraints: [{ policy: "test_policy", eval_result: "pass" }],
        fault_class: "UNKNOWN",
        impact_score: 1,
        loss_amount_usd: null,
      };
      const errors = validate(data, "core");
      expect(errors).toHaveLength(0);
    });

    it("reports errors for invalid core record", () => {
      const data = {
        trace: [],
        constraints: [],
        fault_class: "INVALID",
        impact_score: 0,
        loss_amount_usd: null,
      };
      const errors = validate(data, "core");
      expect(errors.length).toBeGreaterThan(0);
    });

    it("validates a standard record", () => {
      const data = {
        trace: [
          {
            seq: 1,
            tool: "test.tool",
            input: {},
            output: {},
            ts: "2026-01-01T00:00:00Z",
            hash: "sha256:abc123def456",
          },
        ],
        constraints: [{ policy: "test", eval_result: "fail" }],
        fault_class: "AGENT_ERROR",
        impact_score: 3,
        loss_amount_usd: 1000,
        meta: { schema: "agentincident/v0.1" },
        classification: { fault_class: "AGENT_ERROR" },
        loss_estimate: { total_usd: 1000 },
      };
      const errors = validate(data, "standard");
      expect(errors).toHaveLength(0);
    });

    it("reports missing meta for standard level", () => {
      const data = {
        trace: [
          {
            seq: 1,
            tool: "t",
            input: {},
            output: {},
            ts: "2026-01-01T00:00:00Z",
            hash: "sha256:abc",
          },
        ],
        constraints: [{ policy: "p", eval_result: "pass" }],
        fault_class: "UNKNOWN",
        impact_score: 1,
        loss_amount_usd: null,
      };
      const errors = validate(data, "standard");
      expect(errors.length).toBeGreaterThan(0);
    });

    it("validates a full record", () => {
      const data = {
        trace: [
          {
            seq: 1,
            tool: "test.tool",
            input: {},
            output: {},
            ts: "2026-01-01T00:00:00Z",
            hash: "sha256:abc123def456",
          },
        ],
        constraints: [{ policy: "test", eval_result: "fail" }],
        fault_class: "AGENT_ERROR",
        impact_score: 3,
        loss_amount_usd: 1000,
        meta: { schema: "agentincident/v0.1" },
        classification: { fault_class: "AGENT_ERROR" },
        loss_estimate: { total_usd: 1000 },
        liability: { primary: "agent:test" },
        response: {
          actions: [{ description: "Fixed", status: "done" }],
          constraint_update: { from: "v1", to: "v2" },
          verification: [
            { test: "Regression", method: "automated", result: "pass" },
          ],
        },
      };
      const errors = validate(data, "full");
      expect(errors).toHaveLength(0);
    });
  });
});
