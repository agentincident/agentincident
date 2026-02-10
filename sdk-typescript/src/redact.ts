import { computeHash } from "./hash.js";
import type { Incident, TraceEntry } from "./types.js";

const DEFAULT_PATTERNS: RegExp[] = [
  /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g, // emails
  /\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b/g, // credit cards
  /\bsk-[a-zA-Z0-9]{20,}\b/g, // API keys (sk-*)
  /\bBearer\s+[a-zA-Z0-9._\-]+/g, // Bearer tokens
];

const REDACTED = "[REDACTED]";

function redactValue(value: unknown, patterns: RegExp[]): unknown {
  if (typeof value === "string") {
    let result = value;
    for (const pattern of patterns) {
      // Reset lastIndex for global patterns
      pattern.lastIndex = 0;
      result = result.replace(pattern, REDACTED);
    }
    return result;
  }
  if (Array.isArray(value)) {
    return value.map((v) => redactValue(v, patterns));
  }
  if (value !== null && typeof value === "object") {
    return redactObject(
      value as Record<string, unknown>,
      patterns,
      []
    );
  }
  return value;
}

function redactObject(
  obj: Record<string, unknown>,
  patterns: RegExp[],
  fields: string[]
): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const [key, val] of Object.entries(obj)) {
    if (fields.includes(key)) {
      result[key] = REDACTED;
    } else {
      result[key] = redactValue(val, patterns);
    }
  }
  return result;
}

function redactEntry(
  entry: TraceEntry,
  patterns: RegExp[],
  fields: string[]
): TraceEntry {
  const input = redactObject(entry.input, patterns, fields);
  const output = redactObject(entry.output, patterns, fields);
  return {
    ...entry,
    input,
    output,
    hash: computeHash(input, output),
  };
}

export function redactIncident(
  incident: Incident,
  options?: { patterns?: RegExp[]; fields?: string[] }
): Incident {
  const patterns = options?.patterns ?? DEFAULT_PATTERNS;
  const fields = options?.fields ?? [];

  const redactedTrace = incident.trace.map((entry) =>
    redactEntry(entry, patterns, fields)
  );

  return {
    ...incident,
    trace: redactedTrace,
  };
}
