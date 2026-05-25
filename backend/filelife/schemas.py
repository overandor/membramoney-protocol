"""Pydantic v2 schemas for MEMBRA FileLife Collateral Registry."""
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FileRegisterRequest(BaseModel):
    file_path: str
    category: str = "FIN"
    subcategory: str = "ACC"
    kind: str = "INV"
    jurisdiction: str = "US"
    subject_pid: Optional[str] = None


class LifecycleEventOut(BaseModel):
    id: int
    sku: str
    stage: int
    stage_label: str
    event_type: str
    event_hash: str
    metadata: Dict[str, Any]
    created_at: str


class AppraisalOut(BaseModel):
    id: int
    sku: str
    version: int
    appraisal_value_usd: float
    confidence: float
    rationale: str
    llm_model: str
    created_at: str


class CollateralOut(BaseModel):
    sku: str
    eligible_for_collateral: bool
    collateral_class: str
    face_value_usd: float
    appraised_value_usd: float
    advance_rate_percent: float
    lendable_value_usd: float
    haircut_percent: float
    liquidity_score: int
    default_risk_score: int
    fraud_risk_score: int
    verification_score: float
    audit_score: float
    payment_probability: int
    days_to_maturity: int
    lien_status: str
    collateral_cert_id: Optional[str]
    loan_id_hash: Optional[str]
    chain_anchor_tx: Optional[str]
    last_revalued_at: str


class LienOut(BaseModel):
    id: int
    sku: str
    lien_holder_pid: str
    lien_status: str
    collateral_cert_id: Optional[str]
    loan_id_hash: Optional[str]
    chain_tx: Optional[str]
    created_at: str
    released_at: Optional[str]


class VerificationOut(BaseModel):
    sku: str
    version: int
    verified: bool
    raw_file_hash_match: bool
    base64_hash_match: bool
    manifest_hash_match: bool
    sku_hash_match: bool
    failures: List[str]
    created_at: str


class GitHubCommitOut(BaseModel):
    sku: str
    repo_alias: str
    repo: str
    branch: str
    commit_sha: str
    commit_short: str
    commit_url: str
    created_at: str


class ChainAnchorOut(BaseModel):
    sku: str
    network_code: str
    network: str
    anchor_tx: str
    anchor_tx_short: str
    explorer_url: str
    payload: Dict[str, Any]
    created_at: str


class ManifestSchema(BaseModel):
    sku: str
    semantic_explanation: str
    object_type: str = "file"
    category: str
    subcategory: str
    kind: str
    lifecycle_stage: int
    lifecycle_label: str
    version: int
    jurisdiction: str
    subject_pid_hash: str
    raw_file_hash: str
    base64_hash: str
    manifest_hash: str
    sku_hash: str
    content_exposed: bool = False
    identity_exposed: bool = False
    github: Optional[Dict[str, Any]] = None
    chain: Optional[Dict[str, Any]] = None
    qr_url: str
    barcode_value: str
    previous_sku: Optional[str] = None
    created_at: str
    updated_at: str


class SKUSegment(BaseModel):
    value: str
    meaning: str


class SKUExplanation(BaseModel):
    sku: str
    valid: bool
    checksum_valid: bool
    segments: Dict[str, SKUSegment]
    semantic_explanation: str
    privacy_explanation: str
    github_reference: str
    solana_reference: str
    lifecycle_meaning: str
    collateral_meaning: str


class LLMQueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)


class LLMQueryResponse(BaseModel):
    sku: str
    question: str
    answer: str
    sources: List[str]
    confidence: float


class CollateralEvaluateRequest(BaseModel):
    face_value_usd: float = Field(..., ge=0)
    collateral_class: str = "invoice"
    advance_rate_percent: Optional[float] = None
    days_to_maturity: int = 0
    loan_id_hash: Optional[str] = None


class PledgeRequest(BaseModel):
    lien_holder_pid: str
    loan_id_hash: Optional[str] = None


class FileListItem(BaseModel):
    sku: str
    category: str
    subcategory: str
    kind: str
    lifecycle_stage: int
    version: int
    jurisdiction: str
    created_at: str
    updated_at: str


class RegisterResponse(BaseModel):
    sku: str
    manifest: ManifestSchema
    qr_url: str
    barcode_value: str
    message: str = "File registered successfully."
