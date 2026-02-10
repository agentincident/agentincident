import type { Recorder } from "../recorder.js";

export function createAgentIncidentStepCallback(recorder: Recorder) {
  return async (step: {
    toolCalls?: Array<{
      toolName: string;
      args: unknown;
      result?: unknown;
    }>;
  }) => {
    if (!step.toolCalls) return;
    for (const call of step.toolCalls) {
      recorder.record(
        call.toolName,
        call.args as Record<string, unknown>,
        (call.result ?? {}) as Record<string, unknown>
      );
    }
  };
}
