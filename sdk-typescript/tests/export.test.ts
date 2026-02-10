import { describe, it, expect } from "vitest";
import {
  incidentToJSON,
  incidentFromJSON,
  incidentToDict,
  incidentFromDict,
} from "../src/export.js";
import type { Incident } from "../src/types.js";

describe("export", () => {
  const sampleIncident: Incident = {
    trace: [
      {
        seq: 1,
        tool: "stripe.refund",
        input: { charge: "ch_9xK", amount: 47218 },
        output: { refund_id: "re_Xp7", status: "succeeded" },
        ts: "2026-02-09T22:41:07Z",
        hash: "sha256:abc123",
      },
    ],
    constraints: [
      { policy: "refund_policy_v3", eval_result: "fail" },
    ],
    fault_class: "SPEC_AMBIGUITY",
    impact_score: 4,
    loss_amount_usd: 47218,
    meta: {
      schema: "agentincident/v0.1",
      incident_id: "INC-2026-0001",
    },
  };

  describe("incidentToJSON / incidentFromJSON", () => {
    it("round-trips through JSON", () => {
      const json = incidentToJSON(sampleIncident);
      const restored = incidentFromJSON(json);
      expect(restored.fault_class).toBe("SPEC_AMBIGUITY");
      expect(restored.impact_score).toBe(4);
      expect(restored.trace).toHaveLength(1);
      expect(restored.trace[0].tool).toBe("stripe.refund");
      expect(restored.meta?.incident_id).toBe("INC-2026-0001");
    });

    it("supports indent parameter", () => {
      const json = incidentToJSON(sampleIncident, 2);
      expect(json).toContain("\n");
      expect(json).toContain("  ");
    });

    it("preserves null loss_amount_usd", () => {
      const inc = { ...sampleIncident, loss_amount_usd: null };
      const json = incidentToJSON(inc);
      const restored = incidentFromJSON(json);
      expect(restored.loss_amount_usd).toBeNull();
    });
  });

  describe("incidentToDict / incidentFromDict", () => {
    it("round-trips through dict", () => {
      const dict = incidentToDict(sampleIncident);
      expect(dict.fault_class).toBe("SPEC_AMBIGUITY");
      const restored = incidentFromDict(dict);
      expect(restored.fault_class).toBe("SPEC_AMBIGUITY");
      expect(restored.trace).toHaveLength(1);
    });

    it("produces a plain object (not an Incident instance)", () => {
      const dict = incidentToDict(sampleIncident);
      expect(typeof dict).toBe("object");
      expect(dict).toHaveProperty("trace");
      expect(dict).toHaveProperty("fault_class");
    });

    it("deep copies the incident", () => {
      const dict = incidentToDict(sampleIncident);
      (dict.fault_class as string) = "AGENT_ERROR";
      expect(sampleIncident.fault_class).toBe("SPEC_AMBIGUITY");
    });
  });
});
