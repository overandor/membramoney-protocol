"""MIP-001: MIR — Membra Inference Receipt"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


def sha256_json(obj: Any) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


class PrivacyClass(str, Enum):
    PRIVATE = "private"
    SHARED = "shared"
    PUBLIC = "public"


class RiskTier(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RoutingPolicy(str, Enum):
    LOCAL_FIRST = "local_first"
    CHEAPEST = "cheapest"
    FASTEST = "fastest"
    TRUSTED = "trusted"
    QUORUM = "quorum"


class ModelFamily(str, Enum):
    LLAMA = "llama"
    QWEN = "qwen"
    DEEPSEEK = "deepseek"
    MISTRAL = "mistral"
    PHI = "phi"
    CUSTOM = "custom"


class Runtime(str, Enum):
    OLLAMA = "ollama"
    LLAMA_CPP = "llama.cpp"
    VLLM = "vllm"
    TRANSFORMERS = "transformers"
    CUSTOM = "custom"


class ValidationResult(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISPUTED = "disputed"


class SettlementChain(str, Enum):
    MEMBRA = "membra"
    SOLANA = "solana"
    OFFCHAIN = "offchain"


class MirLifecycleState(str, Enum):
    CREATED = "CREATED"
    ROUTED = "ROUTED"
    EXECUTING = "EXECUTING"
    ATTESTED = "ATTESTED"
    VALIDATED = "VALIDATED"
    SETTLED = "SETTLED"
    DISPUTED = "DISPUTED"
    SLASHED = "SLASHED"
    REPLAY_REQUIRED = "REPLAY_REQUIRED"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"


@dataclass
class MembraInferenceReceipt:
    """Membra Inference Receipt (MIR) - MIP-001"""
    mir_version: str = "mip-001"
    mir_id: str = field(default_factory=lambda: f"mir_{uuid.uuid4().hex}")
    job_id: str = field(default_factory=lambda: f"job_{uuid.uuid4().hex}")
    agent_id: str = "agent_unknown"
    wallet_id: str = "wallet_unknown"
    created_at: int = field(default_factory=lambda: int(time.time()))
    lifecycle_state: MirLifecycleState = MirLifecycleState.CREATED

    input_hash: str = ""
    context_hash: str = ""
    tool_manifest_hash: str = ""
    privacy_class: PrivacyClass = PrivacyClass.PRIVATE
    risk_tier: RiskTier = RiskTier.LOW

    router_id: str = "router_default"
    routing_policy: RoutingPolicy = RoutingPolicy.LOCAL_FIRST
    selected_m5_nodes: List[str] = field(default_factory=list)
    fallback_nodes: List[str] = field(default_factory=list)

    model_id_hash: str = ""
    model_family: ModelFamily = ModelFamily.CUSTOM
    runtime: Runtime = Runtime.CUSTOM
    started_at: Optional[int] = None
    completed_at: Optional[int] = None
    latency_ms: Optional[int] = None
    input_tokens: int = 0
    output_tokens: int = 0
    gpu_ms: int = 0
    cpu_ms: int = 0
    ram_mb_peak: int = 0

    output_hash: str = ""
    artifact_hashes: List[str] = field(default_factory=list)
    redacted_summary: str = ""
    deterministic_replay_available: bool = False

    validator_ids: List[str] = field(default_factory=list)
    validator_result: ValidationResult = ValidationResult.PENDING
    quorum_required: int = 1
    quorum_reached: bool = False
    validator_signature_hashes: List[str] = field(default_factory=list)

    settlement_chain: SettlementChain = SettlementChain.OFFCHAIN
    tx_hash: Optional[str] = None
    reward_amount: float = 0.0
    reward_asset: str = "MEMBRA"
    sponsor_pool: str = "free_tx_pool"
    settled_at: Optional[int] = None

    parent_mir_id: Optional[str] = None
    child_mir_ids: List[str] = field(default_factory=list)
    signature: Optional[str] = None

    def merkle_payload(self) -> Dict[str, Any]:
        data = asdict(self)
        data.pop("signature", None)
        for key, value in data.items():
            if isinstance(value, Enum):
                data[key] = value.value
        return data

    def merkle_root(self) -> str:
        return sha256_json(self.merkle_payload())

    def signable_receipt(self) -> Dict[str, Any]:
        data = asdict(self)
        for key, value in data.items():
            if isinstance(value, Enum):
                data[key] = value.value
        data["merkle_root"] = self.merkle_root()
        return data

    def public_receipt(self) -> Dict[str, Any]:
        return {
            "mir_version": self.mir_version,
            "mir_id": self.mir_id,
            "job_id": self.job_id,
            "agent_id": self.agent_id,
            "created_at": self.created_at,
            "lifecycle_state": self.lifecycle_state.value,
            "privacy_class": self.privacy_class.value,
            "risk_tier": self.risk_tier.value,
            "routing_policy": self.routing_policy.value,
            "selected_m5_nodes": self.selected_m5_nodes,
            "model_family": self.model_family.value,
            "runtime": self.runtime.value,
            "latency_ms": self.latency_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "validator_result": self.validator_result.value,
            "quorum_reached": self.quorum_reached,
            "settlement_chain": self.settlement_chain.value,
            "tx_hash": self.tx_hash,
            "reward_amount": self.reward_amount,
            "reward_asset": self.reward_asset,
            "redacted_summary": self.redacted_summary,
            "merkle_root": self.merkle_root(),
        }
