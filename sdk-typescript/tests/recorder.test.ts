import { describe, it, expect, vi, beforeEach } from "vitest";
import { Recorder } from "../src/recorder.js";

describe("Recorder", () => {
  let recorder: Recorder;

  beforeEach(() => {
    recorder = new Recorder({
      agent: "test-agent",
      framework: "test-framework",
      environment: "development",
    });
  });

  describe("record()", () => {
    it("records a trace entry with auto-incrementing seq", () => {
      const e1 = recorder.record("tool.a", { x: 1 }, { y: 2 });
      const e2 = recorder.record("tool.b", { x: 3 }, { y: 4 });
      expect(e1.seq).toBe(1);
      expect(e2.seq).toBe(2);
    });

    it("auto-generates timestamp", () => {
      const entry = recorder.record("tool.a", {}, {});
      expect(entry.ts).toBeTruthy();
      // Should be a valid ISO 8601 string
      expect(new Date(entry.ts).toISOString()).toBeTruthy();
    });

    it("auto-generates hash", () => {
      const entry = recorder.record("tool.a", { key: "value" }, { result: "ok" });
      expect(entry.hash).toMatch(/^sha256:[a-f0-9]+$/);
    });

    it("records optional fields", () => {
      const entry = recorder.record("tool.a", {}, {}, {
        irreversible: true,
        agent_reasoning: "because reasons",
        duration_ms: 500,
      });
      expect(entry.irreversible).toBe(true);
      expect(entry.agent_reasoning).toBe("because reasons");
      expect(entry.duration_ms).toBe(500);
    });

    it("does not include optional fields when not provided", () => {
      const entry = recorder.record("tool.a", {}, {});
      expect(entry.irreversible).toBeUndefined();
      expect(entry.agent_reasoning).toBeUndefined();
      expect(entry.duration_ms).toBeUndefined();
    });
  });

  describe("entries", () => {
    it("returns recorded entries as readonly", () => {
      recorder.record("tool.a", {}, {});
      recorder.record("tool.b", {}, {});
      const entries = recorder.entries;
      expect(entries).toHaveLength(2);
    });
  });

  describe("wrap()", () => {
    it("wraps a sync function and records the call", async () => {
      const fn = (a: number, b: number) => a + b;
      const wrapped = recorder.wrap("math.add", fn);
      const result = await wrapped(3, 4);
      expect(result).toBe(7);
      expect(recorder.entries).toHaveLength(1);
      expect(recorder.entries[0].tool).toBe("math.add");
    });

    it("wraps an async function and records the call", async () => {
      const fn = async (s: string) => `hello ${s}`;
      const wrapped = recorder.wrap("greet", fn);
      const result = await wrapped("world");
      expect(result).toBe("hello world");
      expect(recorder.entries).toHaveLength(1);
    });

    it("records duration_ms for wrapped calls", async () => {
      const fn = async () => {
        await new Promise((r) => setTimeout(r, 50));
        return "done";
      };
      const wrapped = recorder.wrap("slow.fn", fn);
      await wrapped();
      expect(recorder.entries[0].duration_ms).toBeGreaterThanOrEqual(40);
    });

    it("passes irreversible option through wrap", async () => {
      const fn = () => "ok";
      const wrapped = recorder.wrap("tool", fn, { irreversible: true });
      await wrapped();
      expect(recorder.entries[0].irreversible).toBe(true);
    });
  });

  describe("toIncident()", () => {
    it("creates an incident from recorded entries", () => {
      recorder.record("tool.a", { x: 1 }, { y: 2 });
      const incident = recorder.toIncident({
        fault_class: "AGENT_ERROR",
        impact_score: 3,
        loss_amount_usd: 1000,
        constraints: [{ policy: "test_policy", eval_result: "fail" }],
      });
      expect(incident.trace).toHaveLength(1);
      expect(incident.fault_class).toBe("AGENT_ERROR");
      expect(incident.impact_score).toBe(3);
      expect(incident.loss_amount_usd).toBe(1000);
      expect(incident.constraints).toHaveLength(1);
    });

    it("includes meta from constructor options", () => {
      recorder.record("tool.a", {}, {});
      const incident = recorder.toIncident({
        fault_class: "UNKNOWN",
        impact_score: 1,
        loss_amount_usd: null,
        constraints: [{ policy: "p", eval_result: "pass" }],
      });
      expect(incident.meta?.agent).toBe("test-agent");
      expect(incident.meta?.framework).toBe("test-framework");
      expect(incident.meta?.schema).toBe("agentincident/v0.1");
    });

    it("merges user-provided meta over constructor options", () => {
      recorder.record("tool.a", {}, {});
      const incident = recorder.toIncident({
        fault_class: "UNKNOWN",
        impact_score: 1,
        loss_amount_usd: null,
        constraints: [{ policy: "p", eval_result: "pass" }],
        meta: { agent: "override-agent", incident_id: "INC-2026-0001" },
      });
      expect(incident.meta?.agent).toBe("override-agent");
      expect(incident.meta?.incident_id).toBe("INC-2026-0001");
    });

    it("includes optional extended fields", () => {
      recorder.record("tool.a", {}, {});
      const incident = recorder.toIncident({
        fault_class: "SPEC_AMBIGUITY",
        impact_score: 4,
        loss_amount_usd: null,
        constraints: [{ policy: "p", eval_result: "fail" }],
        classification: { fault_class: "SPEC_AMBIGUITY", confidence: 0.84 },
        liability: { primary: "spec_owner:team@co.com" },
        loss_estimate: { total_usd: 48868 },
        response: { actions: [{ description: "Fixed", status: "done" }] },
      });
      expect(incident.classification?.confidence).toBe(0.84);
      expect(incident.liability?.primary).toContain("spec_owner");
      expect(incident.loss_estimate?.total_usd).toBe(48868);
      expect(incident.response?.actions).toHaveLength(1);
    });
  });

  describe("toJSON()", () => {
    it("throws if no incident has been created", () => {
      expect(() => recorder.toJSON()).toThrow("No incident created yet");
    });

    it("returns JSON string of the incident", () => {
      recorder.record("tool.a", {}, {});
      recorder.toIncident({
        fault_class: "UNKNOWN",
        impact_score: 1,
        loss_amount_usd: null,
        constraints: [{ policy: "p", eval_result: "pass" }],
      });
      const json = recorder.toJSON();
      const parsed = JSON.parse(json);
      expect(parsed.fault_class).toBe("UNKNOWN");
    });

    it("supports indent parameter", () => {
      recorder.record("tool.a", {}, {});
      recorder.toIncident({
        fault_class: "UNKNOWN",
        impact_score: 1,
        loss_amount_usd: null,
        constraints: [{ policy: "p", eval_result: "pass" }],
      });
      const json = recorder.toJSON(2);
      expect(json).toContain("\n");
    });
  });

  describe("validate()", () => {
    it("returns errors when no entries recorded", () => {
      const errors = recorder.validate();
      expect(errors.length).toBeGreaterThan(0);
    });

    it("returns no errors for valid core incident", () => {
      recorder.record("tool.a", {}, {});
      recorder.toIncident({
        fault_class: "UNKNOWN",
        impact_score: 1,
        loss_amount_usd: null,
        constraints: [{ policy: "p", eval_result: "pass" }],
      });
      const errors = recorder.validate("core");
      expect(errors).toHaveLength(0);
    });

    it("reports missing fields for standard level", () => {
      recorder.record("tool.a", {}, {});
      recorder.toIncident({
        fault_class: "UNKNOWN",
        impact_score: 1,
        loss_amount_usd: null,
        constraints: [{ policy: "p", eval_result: "pass" }],
      });
      const errors = recorder.validate("standard");
      expect(errors.some((e) => e.includes("classification"))).toBe(true);
      expect(errors.some((e) => e.includes("loss_estimate"))).toBe(true);
    });

    it("reports missing fields for full level", () => {
      recorder.record("tool.a", {}, {});
      recorder.toIncident({
        fault_class: "UNKNOWN",
        impact_score: 1,
        loss_amount_usd: null,
        constraints: [{ policy: "p", eval_result: "pass" }],
      });
      const errors = recorder.validate("full");
      expect(errors.some((e) => e.includes("liability"))).toBe(true);
      expect(errors.some((e) => e.includes("response"))).toBe(true);
    });
  });
});
