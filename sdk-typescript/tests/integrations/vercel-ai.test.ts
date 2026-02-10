import { describe, it, expect } from "vitest";
import { Recorder } from "../../src/recorder.js";
import { createAgentIncidentStepCallback } from "../../src/integrations/vercel-ai.js";

describe("vercel-ai integration", () => {
  it("records tool calls from step callback", async () => {
    const recorder = new Recorder({ agent: "vercel-test" });
    const callback = createAgentIncidentStepCallback(recorder);

    await callback({
      toolCalls: [
        {
          toolName: "search",
          args: { query: "test" },
          result: { results: ["a", "b"] },
        },
        {
          toolName: "fetch",
          args: { url: "https://example.com" },
          result: { body: "ok" },
        },
      ],
    });

    expect(recorder.entries).toHaveLength(2);
    expect(recorder.entries[0].tool).toBe("search");
    expect(recorder.entries[0].input).toEqual({ query: "test" });
    expect(recorder.entries[1].tool).toBe("fetch");
  });

  it("handles step without toolCalls", async () => {
    const recorder = new Recorder();
    const callback = createAgentIncidentStepCallback(recorder);

    await callback({});
    expect(recorder.entries).toHaveLength(0);
  });

  it("handles empty toolCalls array", async () => {
    const recorder = new Recorder();
    const callback = createAgentIncidentStepCallback(recorder);

    await callback({ toolCalls: [] });
    expect(recorder.entries).toHaveLength(0);
  });

  it("handles tool call with no result", async () => {
    const recorder = new Recorder();
    const callback = createAgentIncidentStepCallback(recorder);

    await callback({
      toolCalls: [
        {
          toolName: "fire_and_forget",
          args: { action: "do_thing" },
        },
      ],
    });

    expect(recorder.entries).toHaveLength(1);
    expect(recorder.entries[0].output).toEqual({});
  });

  it("auto-generates hashes for recorded calls", async () => {
    const recorder = new Recorder();
    const callback = createAgentIncidentStepCallback(recorder);

    await callback({
      toolCalls: [
        {
          toolName: "tool",
          args: { x: 1 },
          result: { y: 2 },
        },
      ],
    });

    expect(recorder.entries[0].hash).toMatch(/^sha256:[a-f0-9]+$/);
  });
});
