"""Tests for MIR - MIP-001"""
import pytest
from core.mir import (
    MembraInferenceReceipt,
    PrivacyClass,
    RiskTier,
    RoutingPolicy,
    ModelFamily,
    Runtime,
    ValidationResult,
    SettlementChain,
    MirLifecycleState,
    sha256_json,
)

def test_sha256_json():
    obj = {"foo": "bar", "baz": 123}
    result = sha256_json(obj)
    assert isinstance(result, str)
    assert len(result) == 64

def test_mir_creation():
    mir = MembraInferenceReceipt()
    assert mir.mir_version == "mip-001"
    assert mir.mir_id.startswith("mir_")
    assert mir.lifecycle_state == MirLifecycleState.CREATED

def test_mir_with_custom_values():
    mir = MembraInferenceReceipt(
        agent_id="agent_test",
        wallet_id="wallet_test",
        input_hash="hash123",
        model_family=ModelFamily.LLAMA,
        runtime=Runtime.OLLAMA,
    )
    assert mir.agent_id == "agent_test"
    assert mir.model_family == ModelFamily.LLAMA

def test_merkle_root():
    mir = MembraInferenceReceipt(agent_id="agent_test")
    root = mir.merkle_root()
    assert isinstance(root, str)
    assert len(root) == 64

def test_public_receipt():
    mir = MembraInferenceReceipt(agent_id="agent_test")
    public = mir.public_receipt()
    assert "input_hash" not in public
    assert "mir_id" in public
    assert "merkle_root" in public
