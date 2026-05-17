# MIP-001: MIR — Membra Inference Receipt

**Status:** Proposed  
**Created:** 2026-05-17  
**Author:** MEMBRA Protocol  
**Type:** Standards Track

## Abstract

MIR (Membra Inference Receipt) is the atomic primitive for verifiable, payable, routable, and auditable LLM/compute work within the MEMBRA network. A MIR is a cryptographically hashed record of an LLM or agent workload executed by one or more M5 nodes, containing input hashes, output hashes, node attestations, policy tier, resource usage, validator signatures, reward routing, and settlement status—without exposing private prompts, secrets, files, or chain-of-thought.

## Motivation

M5 nodes perform four core functions:
1. Host models
2. Provide compute
3. Run inference
4. Confirm transactions

Without a unified receipt object, MEMBRA is merely "distributed inference plus blockchain." MIR binds these four actions together, transforming MEMBRA into **a verifiable AI execution network**.

## Specification

### Core Definition

A MIR proves:
- What job was requested
- Where it was routed
- What resources were used
- What output was produced
- Who validated it
- What policy allowed it
- What transaction/reward followed

**MEMBRA does not prove what the LLM "thought."** It proves execution, not reasoning.

### Lifecycle States

```
CREATED
↓
ROUTED
↓
EXECUTING
↓
ATTESTED
↓
VALIDATED
↓
SETTLED
```

Optional failure states:
- DISPUTED
- SLASHED
- REPLAY_REQUIRED
- EXPIRED
- REJECTED

### Schema

```json
{
  "mir_version": "mip-001",
  "mir_id": "mir_...",
  "job_id": "job_...",
  "agent_id": "agent_...",
  "wallet_id": "wallet_...",
  "created_at": 0,

  "request": {
    "input_hash": "sha256...",
    "context_hash": "sha256...",
    "tool_manifest_hash": "sha256...",
    "privacy_class": "private | shared | public",
    "risk_tier": "LOW | MEDIUM | HIGH | CRITICAL"
  },

  "routing": {
    "router_id": "router_...",
    "routing_policy": "local_first | cheapest | fastest | trusted | quorum",
    "selected_m5_nodes": ["m5_1", "m5_2"],
    "fallback_nodes": []
  },

  "execution": {
    "model_id_hash": "sha256...",
    "model_family": "llama | qwen | deepseek | mistral | phi | custom",
    "runtime": "ollama | llama.cpp | vllm | transformers | custom",
    "started_at": 0,
    "completed_at": 0,
    "latency_ms": 0,
    "input_tokens": 0,
    "output_tokens": 0,
    "gpu_ms": 0,
    "cpu_ms": 0,
    "ram_mb_peak": 0
  },

  "output": {
    "output_hash": "sha256...",
    "artifact_hashes": [],
    "redacted_summary": "human-safe summary",
    "deterministic_replay_available": false
  },

  "validation": {
    "validator_ids": [],
    "validator_result": "approved | rejected | disputed",
    "quorum_required": 2,
    "quorum_reached": true,
    "validator_signature_hashes": []
  },

  "settlement": {
    "settlement_chain": "membra | solana | offchain",
    "tx_hash": null,
    "reward_amount": 0,
    "reward_asset": "MEMBRA",
    "sponsor_pool": "free_tx_pool",
    "settled_at": null
  },

  "audit": {
    "parent_mir_id": null,
    "child_mir_ids": [],
    "merkle_root": "sha256...",
    "signature": "node_or_protocol_signature"
  }
}
```

### Composite MIR (CMIR)

A single LLM job can split into multiple subjobs across multiple M5 nodes:

```
Parent MIR
├── Child MIR: planning node
├── Child MIR: code node
├── Child MIR: validation node
├── Child MIR: transaction node
└── Child MIR: memory node
```

This proves:
1. One agent used many machines
2. Many machines improved one result
3. Each machine produced verifiable contribution
4. Each contribution can be rewarded

### Production Primitive Names

- **MIR**: Membra Inference Receipt
- **CMIR**: Composite Membra Inference Receipt
- **M5A**: M5 Attestation
- **M5Q**: M5 Quorum
- **MIR Root**: Merkle root of receipts
- **MIR Page**: Public shareable proof page

## Implementation

### Python Reference Implementation

See `backend/core/mir.py` for the canonical dataclass implementation.

### Agent Instruction

Every meaningful MEMBRA action must produce a MIR:

> If an agent routes inference, generates code, validates output, confirms a transaction, updates memory, deploys an artifact, or earns rewards, it must create or update a Membra Inference Receipt.
>
> Never store raw secrets.
> Never store private prompts publicly.
> Never store chain-of-thought.
> Store hashes, summaries, resource metrics, validator attestations, policy decisions, and settlement status.

A job without a MIR is not economically valid inside MEMBRA.

## Business Impact

MIR enables monetization of:
- Inference
- Validation
- Routing
- Agent work
- Transaction sponsorship
- Model hosting
- Compute staking
- Proof pages
- Enterprise audit logs
- Developer API access

### Virality

Every completed job can become a public MIR Page:
> "Built by Agent X using 3 M5 nodes, validated by 2 validators, settled through MEMBRA."

This becomes the shareable proof artifact.

## Security Considerations

1. **Privacy**: MIR stores hashes, not raw prompts or outputs
2. **Redaction**: `redacted_summary` field for human-safe summaries
3. **Determinism**: `deterministic_replay_available` for reproducible verification
4. **Quorum**: Validator quorum prevents single-point-of-failure
5. **Slashing**: Disputed/SLASHED states enable economic penalties

## Backward Compatibility

This is a new primitive. No backward compatibility concerns.

## Future Work

- MIR Page frontend for public proof sharing
- MIR indexing and search
- MIR analytics and metrics
- MIR-based reputation scoring for M5 nodes
- Cross-chain MIR settlement

## References

- MEMBRA Protocol Architecture
- M5 Node Specification
- MEMBRA Settlement Layer
