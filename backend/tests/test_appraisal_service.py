"""Unit tests for the machine appraisal service (no LLM calls)."""

import hashlib
import pytest
from services.appraisal_service import (
    build_merkle_tree,
    merkle_proof,
    _leaf_hash,
    _pair_hash,
    _sha256,
    FileAppraisal,
)


# ---------------------------------------------------------------------------
# Merkle tree correctness
# ---------------------------------------------------------------------------

def test_empty_tree():
    root, levels = build_merkle_tree([])
    assert root == _sha256(b"empty")
    assert levels == [[_sha256(b"empty")]]


def test_single_leaf():
    leaf = "abc123"
    root, levels = build_merkle_tree([leaf])
    assert root == leaf
    assert levels[0] == [leaf]


def test_two_leaves():
    a, b = "leaf_a", "leaf_b"
    root, levels = build_merkle_tree([a, b])
    expected = _pair_hash(a, b)
    assert root == expected
    assert len(levels) == 2


def test_three_leaves_duplicates_last():
    a, b, c = "x", "y", "z"
    root, levels = build_merkle_tree([a, b, c])
    # layer 0: [a, b, c, c(dup)]  → pairs (a,b) and (c,c)
    ab = _pair_hash(a, b)
    cc = _pair_hash(c, c)
    expected_root = _pair_hash(ab, cc)
    assert root == expected_root


def test_deterministic_for_same_input():
    leaves = ["one", "two", "three", "four"]
    r1, _ = build_merkle_tree(leaves)
    r2, _ = build_merkle_tree(leaves)
    assert r1 == r2


def test_different_input_different_root():
    r1, _ = build_merkle_tree(["a", "b"])
    r2, _ = build_merkle_tree(["a", "c"])
    assert r1 != r2


# ---------------------------------------------------------------------------
# Merkle proof verification
# ---------------------------------------------------------------------------

def _verify_proof(leaf: str, proof: list, root: str) -> bool:
    current = leaf
    for step in proof:
        sibling = step["sibling"]
        direction = step["direction"]
        if direction == "right":
            current = _pair_hash(current, sibling)
        else:
            current = _pair_hash(sibling, current)
    return current == root


def test_proof_verifies_for_each_leaf():
    leaves = ["a", "b", "c", "d"]
    root, _ = build_merkle_tree(leaves)
    for i, leaf in enumerate(leaves):
        proof = merkle_proof(leaves, i)
        assert _verify_proof(leaf, proof, root), f"Proof failed for leaf index {i}"


def test_proof_verifies_for_three_leaves():
    leaves = ["x", "y", "z"]
    root, _ = build_merkle_tree(leaves)
    for i, leaf in enumerate(leaves):
        proof = merkle_proof(leaves, i)
        assert _verify_proof(leaf, proof, root), f"Proof failed for leaf index {i}"


def test_proof_fails_for_tampered_value():
    leaves = ["a", "b", "c", "d"]
    root, _ = build_merkle_tree(leaves)
    proof = merkle_proof(leaves, 0)
    tampered_leaf = "tampered"
    assert not _verify_proof(tampered_leaf, proof, root)


# ---------------------------------------------------------------------------
# FileAppraisal leaf hash
# ---------------------------------------------------------------------------

def test_file_appraisal_leaf_hash_changes_with_value():
    fa1 = FileAppraisal("src/foo.py", "abc", 1024, 500, "reason")
    fa2 = FileAppraisal("src/foo.py", "abc", 1024, 501, "reason")
    assert fa1.leaf_hash != fa2.leaf_hash


def test_file_appraisal_leaf_hash_changes_with_path():
    fa1 = FileAppraisal("src/foo.py", "abc", 1024, 500, "reason")
    fa2 = FileAppraisal("src/bar.py", "abc", 1024, 500, "reason")
    assert fa1.leaf_hash != fa2.leaf_hash


def test_file_appraisal_value_dollars():
    fa = FileAppraisal("x", "h", 0, 1550, "r")
    assert abs(fa.value_dollars - 15.50) < 0.001
