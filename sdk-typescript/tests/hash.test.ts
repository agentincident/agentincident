import { describe, it, expect } from "vitest";
import { computeHash, stableStringify } from "../src/hash.js";

describe("hash", () => {
  describe("stableStringify", () => {
    it("sorts object keys recursively", () => {
      const result = stableStringify({ b: 2, a: 1 });
      expect(result).toBe('{"a":1,"b":2}');
    });

    it("handles nested objects with sorted keys", () => {
      const result = stableStringify({ nested: { z: 1, a: 2 } });
      expect(result).toBe('{"nested":{"a":2,"z":1}}');
    });

    it("handles arrays", () => {
      const result = stableStringify([1, 2, 3]);
      expect(result).toBe("[1,2,3]");
    });

    it("handles null", () => {
      expect(stableStringify(null)).toBe("null");
    });

    it("handles booleans", () => {
      expect(stableStringify(true)).toBe("true");
      expect(stableStringify(false)).toBe("false");
    });

    it("handles strings with escaping", () => {
      expect(stableStringify("hello")).toBe('"hello"');
    });

    it("handles empty objects", () => {
      expect(stableStringify({})).toBe("{}");
    });

    it("handles empty arrays", () => {
      expect(stableStringify([])).toBe("[]");
    });

    it("handles mixed arrays", () => {
      const result = stableStringify([null, true, false]);
      expect(result).toBe("[null,true,false]");
    });
  });

  describe("computeHash", () => {
    it("returns sha256-prefixed hex string", () => {
      const hash = computeHash({ key: "value" }, { result: "ok" });
      expect(hash).toMatch(/^sha256:[a-f0-9]{64}$/);
    });

    it("is deterministic", () => {
      const h1 = computeHash({ a: 1, b: 2 }, { x: 3 });
      const h2 = computeHash({ b: 2, a: 1 }, { x: 3 });
      expect(h1).toBe(h2);
    });

    it("produces different hashes for different inputs", () => {
      const h1 = computeHash({ a: 1 }, { b: 2 });
      const h2 = computeHash({ a: 2 }, { b: 2 });
      expect(h1).not.toBe(h2);
    });
  });

  describe("cross-language test vectors", () => {
    it("vector 1: simple key-value", () => {
      const hash = computeHash({ key: "value" }, { result: "ok" });
      expect(hash).toBe(
        "sha256:b1e26688d9320cf0a74b44b7b739007983d568c697596dbcd8331ba1ffc128ac"
      );
    });

    it("vector 2: empty objects", () => {
      const hash = computeHash({}, {});
      expect(hash).toBe(
        "sha256:d99d8cdc6149e8c7f34a7327163384f915f4448f9513ad82f4ed84078cc3f711"
      );
    });

    it("vector 3: numbers and arrays", () => {
      const hash = computeHash({ a: 1, b: 2 }, { x: [1, 2, 3] });
      expect(hash).toBe(
        "sha256:76a8d21de525be677b92f0517d6b6cc8570cbb83e5021d64638a777af7666c07"
      );
    });

    it("vector 4: nested objects with null/boolean", () => {
      const hash = computeHash(
        { nested: { z: 1, a: 2 } },
        { arr: [null, true, false] }
      );
      expect(hash).toBe(
        "sha256:b1f98b2b35ab08dea66e370897f91514174fdbf23f4758f929fd189ff194b2f5"
      );
    });

    it("vector 5: unicode strings", () => {
      const hash = computeHash(
        { unicode: "h\u00e9llo w\u00f6rld" },
        { emoji: "test" }
      );
      expect(hash).toBe(
        "sha256:4fc17566bd6cabb0f2ba48c21817b3af3829533187637c89794a5b9bbf4f03bb"
      );
    });
  });
});
