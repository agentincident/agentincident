"""Tests for deterministic hashing, including cross-language test vectors."""
from __future__ import annotations

from agentincident import compute_hash


# Cross-language test vectors (shared with TypeScript SDK)
HASH_TEST_VECTORS = [
    (
        {"key": "value"},
        {"result": "ok"},
        "sha256:b1e26688d9320cf0a74b44b7b739007983d568c697596dbcd8331ba1ffc128ac",
    ),
    (
        {},
        {},
        "sha256:d99d8cdc6149e8c7f34a7327163384f915f4448f9513ad82f4ed84078cc3f711",
    ),
    (
        {"a": 1, "b": 2},
        {"x": [1, 2, 3]},
        "sha256:76a8d21de525be677b92f0517d6b6cc8570cbb83e5021d64638a777af7666c07",
    ),
    (
        {"nested": {"z": 1, "a": 2}},
        {"arr": [None, True, False]},
        "sha256:b1f98b2b35ab08dea66e370897f91514174fdbf23f4758f929fd189ff194b2f5",
    ),
    (
        {"unicode": "h\u00e9llo w\u00f6rld"},
        {"emoji": "test"},
        "sha256:4fc17566bd6cabb0f2ba48c21817b3af3829533187637c89794a5b9bbf4f03bb",
    ),
]


class TestComputeHash:
    def test_deterministic(self):
        h1 = compute_hash({"a": 1}, {"b": 2})
        h2 = compute_hash({"a": 1}, {"b": 2})
        assert h1 == h2

    def test_format(self):
        h = compute_hash({}, {})
        assert h.startswith("sha256:")
        hex_part = h.split(":")[1]
        assert len(hex_part) == 64
        # All hex chars
        int(hex_part, 16)

    def test_different_inputs_different_hashes(self):
        h1 = compute_hash({"a": 1}, {})
        h2 = compute_hash({"b": 1}, {})
        assert h1 != h2

    def test_key_order_independence(self):
        """Keys are sorted during canonicalization, so order doesn't matter."""
        h1 = compute_hash({"b": 2, "a": 1}, {})
        h2 = compute_hash({"a": 1, "b": 2}, {})
        assert h1 == h2


class TestCrossLanguageVectors:
    """These test vectors MUST match the TypeScript SDK implementation."""

    def test_vector_0_simple(self):
        inp, out, expected = HASH_TEST_VECTORS[0]
        result = compute_hash(inp, out)
        print(f"Vector 0: {result}")
        assert result == expected

    def test_vector_1_empty(self):
        inp, out, expected = HASH_TEST_VECTORS[1]
        result = compute_hash(inp, out)
        print(f"Vector 1: {result}")
        assert result == expected

    def test_vector_2_arrays(self):
        inp, out, expected = HASH_TEST_VECTORS[2]
        result = compute_hash(inp, out)
        print(f"Vector 2: {result}")
        assert result == expected

    def test_vector_3_nested_with_null(self):
        inp, out, expected = HASH_TEST_VECTORS[3]
        result = compute_hash(inp, out)
        print(f"Vector 3: {result}")
        assert result == expected

    def test_vector_4_unicode(self):
        inp, out, expected = HASH_TEST_VECTORS[4]
        result = compute_hash(inp, out)
        print(f"Vector 4: {result}")
        assert result == expected

    def test_all_vectors(self):
        """Run all vectors and print results for TS SDK reference."""
        for i, (inp, out, expected) in enumerate(HASH_TEST_VECTORS):
            result = compute_hash(inp, out)
            print(f"Vector {i}: input={inp}, output={out}")
            print(f"  Expected: {expected}")
            print(f"  Got:      {result}")
            assert result == expected, f"Vector {i} mismatch"
