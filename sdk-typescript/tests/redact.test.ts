import { describe, it, expect } from "vitest";
import { redactIncident } from "../src/redact.js";
import type { Incident } from "../src/types.js";
import { computeHash } from "../src/hash.js";

describe("redact", () => {
  function makeIncident(
    input: Record<string, unknown>,
    output: Record<string, unknown>
  ): Incident {
    return {
      trace: [
        {
          seq: 1,
          tool: "test.tool",
          input,
          output,
          ts: "2026-01-01T00:00:00Z",
          hash: computeHash(input, output),
        },
      ],
      constraints: [{ policy: "p", eval_result: "pass" as const }],
      fault_class: "UNKNOWN",
      impact_score: 1,
      loss_amount_usd: null,
    };
  }

  it("redacts email addresses", () => {
    const incident = makeIncident(
      { to: "user@example.com" },
      { status: "sent" }
    );
    const redacted = redactIncident(incident);
    expect(redacted.trace[0].input.to).toBe("[REDACTED]");
  });

  it("redacts credit card numbers", () => {
    const incident = makeIncident(
      { card: "4111 1111 1111 1111" },
      { ok: true }
    );
    const redacted = redactIncident(incident);
    expect(redacted.trace[0].input.card).toBe("[REDACTED]");
  });

  it("redacts API keys (sk-*)", () => {
    const incident = makeIncident(
      { key: "sk-abc123def456ghi789jkl012" },
      { ok: true }
    );
    const redacted = redactIncident(incident);
    expect(redacted.trace[0].input.key).toBe("[REDACTED]");
  });

  it("redacts Bearer tokens", () => {
    const incident = makeIncident(
      { auth: "Bearer eyJhbGciOiJIUzI1NiJ9.test" },
      { ok: true }
    );
    const redacted = redactIncident(incident);
    expect(redacted.trace[0].input.auth).toBe("[REDACTED]");
  });

  it("recomputes hashes after redaction", () => {
    const incident = makeIncident(
      { to: "user@example.com" },
      { status: "sent" }
    );
    const originalHash = incident.trace[0].hash;
    const redacted = redactIncident(incident);
    expect(redacted.trace[0].hash).not.toBe(originalHash);
    // Verify the new hash matches the redacted content
    const expected = computeHash(
      redacted.trace[0].input,
      redacted.trace[0].output
    );
    expect(redacted.trace[0].hash).toBe(expected);
  });

  it("does not modify the original incident", () => {
    const incident = makeIncident(
      { to: "user@example.com" },
      { status: "sent" }
    );
    redactIncident(incident);
    expect(incident.trace[0].input.to).toBe("user@example.com");
  });

  it("supports custom patterns", () => {
    const incident = makeIncident(
      { secret: "CUSTOM-abc123" },
      { ok: true }
    );
    const redacted = redactIncident(incident, {
      patterns: [/CUSTOM-[a-z0-9]+/g],
    });
    expect(redacted.trace[0].input.secret).toBe("[REDACTED]");
  });

  it("supports field-level redaction", () => {
    const incident = makeIncident(
      { password: "mysecret", name: "Alice" },
      { ok: true }
    );
    const redacted = redactIncident(incident, {
      fields: ["password"],
    });
    expect(redacted.trace[0].input.password).toBe("[REDACTED]");
    expect(redacted.trace[0].input.name).toBe("Alice");
  });

  it("handles nested values", () => {
    const incident = makeIncident(
      { data: { email: "test@test.com", count: 5 } },
      { ok: true }
    );
    const redacted = redactIncident(incident);
    const data = redacted.trace[0].input.data as Record<string, unknown>;
    expect(data.email).toBe("[REDACTED]");
    expect(data.count).toBe(5);
  });

  it("handles arrays with redactable values", () => {
    const incident = makeIncident(
      { emails: ["a@b.com", "c@d.com"] },
      { ok: true }
    );
    const redacted = redactIncident(incident);
    const emails = redacted.trace[0].input.emails as string[];
    expect(emails[0]).toBe("[REDACTED]");
    expect(emails[1]).toBe("[REDACTED]");
  });
});
