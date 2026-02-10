import { createHash } from "node:crypto";

/**
 * Escape non-ASCII characters to \uXXXX sequences, matching Python's
 * json.dumps ensure_ascii=True (default) behavior.
 */
function escapeNonAscii(s: string): string {
  let result = "";
  for (let i = 0; i < s.length; i++) {
    const code = s.charCodeAt(i);
    if (code > 127) {
      result += "\\u" + code.toString(16).padStart(4, "0");
    } else {
      result += s[i];
    }
  }
  return result;
}

/**
 * JSON-encode a string matching Python's json.dumps(ensure_ascii=True).
 * Uses JSON.stringify for base escaping, then escapes remaining non-ASCII.
 */
function stringifyString(s: string): string {
  return escapeNonAscii(JSON.stringify(s));
}

export function stableStringify(obj: unknown): string {
  if (obj === null) return "null";
  if (typeof obj === "boolean") return obj ? "true" : "false";
  if (typeof obj === "number") return JSON.stringify(obj);
  if (typeof obj === "string") return stringifyString(obj);
  if (Array.isArray(obj)) {
    return "[" + obj.map((v) => stableStringify(v)).join(",") + "]";
  }
  if (typeof obj === "object") {
    const keys = Object.keys(obj as Record<string, unknown>).sort();
    return (
      "{" +
      keys
        .map(
          (k) =>
            stringifyString(k) +
            ":" +
            stableStringify((obj as Record<string, unknown>)[k])
        )
        .join(",") +
      "}"
    );
  }
  return String(obj);
}

export function computeHash(
  input: Record<string, unknown>,
  output: Record<string, unknown>
): string {
  const canonical = stableStringify({ input, output });
  return `sha256:${createHash("sha256").update(canonical, "utf-8").digest("hex")}`;
}
