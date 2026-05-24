"""
MEMBRA FileLife Collateral Registry — FastAPI router.
All endpoints. Privacy-first: raw file contents never returned.
"""
import json
import os
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .db import (
    get_db, FileRecord, LifecycleEvent, AppraisalRecord,
    CollateralRecord, LienRecord, VerificationRecord,
    GitHubCommit, ChainAnchor, LLMQuery,
)
from .schemas import (
    FileRegisterRequest, CollateralEvaluateRequest, PledgeRequest,
    LLMQueryRequest, ManifestSchema,
)
from .sku import generate_sku, generate_sku_hash, disassemble_sku
from .pid import generate_pid, hash_pid
from .hashing import pipeline as hash_pipeline, hash_manifest, hash_sku
from .qr_barcode import generate_qr_base64, generate_barcode_base64
from . import github_service, solana_service, lifecycle as lc_engine
from .appraisal import appraise_file, get_appraisal_history
from .collateral import calculate_collateral, save_collateral_record
from .lien import pledge_collateral, release_lien, get_lien_status
from .verification import verify_file, get_verification_score
from .llm_qa import answer_question

STAGE_LABELS = {
    0: "discovered", 1: "registered", 2: "raw hashed",
    3: "base64 encoded", 4: "committed to GitHub",
    5: "anchored on-chain", 6: "appraised", 7: "verified",
    8: "amended/new version", 9: "archived",
}

router = APIRouter(prefix="/api", tags=["filelife"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_manifest(rec: FileRecord, db: Session) -> dict:
    gh = db.query(GitHubCommit).filter(GitHubCommit.sku == rec.sku).order_by(GitHubCommit.created_at.desc()).first()
    anchor = db.query(ChainAnchor).filter(ChainAnchor.sku == rec.sku).order_by(ChainAnchor.created_at.desc()).first()
    appraisal = db.query(AppraisalRecord).filter(AppraisalRecord.sku == rec.sku).order_by(AppraisalRecord.created_at.desc()).first()
    sku_expl = disassemble_sku(rec.sku)
    m = {
        "sku": rec.sku, "semantic_explanation": sku_expl.get("semantic_explanation", ""),
        "object_type": "file", "category": rec.category, "subcategory": rec.subcategory,
        "kind": rec.kind, "lifecycle_stage": rec.lifecycle_stage,
        "lifecycle_label": STAGE_LABELS.get(rec.lifecycle_stage, "unknown"),
        "version": rec.version, "jurisdiction": rec.jurisdiction,
        "subject_pid_hash": hash_pid(rec.subject_pid) if rec.subject_pid else "sha256:none",
        "raw_file_hash": rec.raw_file_hash, "base64_hash": rec.base64_hash,
        "manifest_hash": rec.manifest_hash, "sku_hash": rec.sku_hash,
        "content_exposed": rec.content_exposed, "identity_exposed": rec.identity_exposed,
        "github": {
            "provider": "github", "repo_alias": gh.repo_alias, "repo": gh.repo,
            "branch": gh.branch, "commit_sha": gh.commit_sha,
            "commit_short": gh.commit_short, "commit_url": gh.commit_url,
        } if gh else None,
        "chain": {
            "network_code": anchor.network_code, "network": anchor.network,
            "anchor_tx": anchor.anchor_tx, "anchor_tx_short": anchor.anchor_tx_short,
            "explorer_url": anchor.explorer_url,
        } if anchor else None,
        "latest_appraisal_usd": appraisal.appraisal_value_usd if appraisal else None,
        "qr_url": f"/f/{rec.sku}", "barcode_value": rec.sku,
        "created_at": rec.created_at.isoformat(), "updated_at": rec.updated_at.isoformat(),
    }
    return m


def _require_file(db: Session, sku: str) -> FileRecord:
    rec = db.query(FileRecord).filter(FileRecord.sku == sku).first()
    if not rec:
        raise HTTPException(404, f"File with SKU {sku!r} not found.")
    return rec


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@router.get("/health/filelife")
async def health_filelife():
    return {"status": "ok", "service": "MEMBRA FileLife Collateral Registry", "devnet": True}


# ---------------------------------------------------------------------------
# File registration
# ---------------------------------------------------------------------------

@router.post("/files/register")
async def register_file(req: FileRegisterRequest, db: Session = Depends(get_db)):
    if not os.path.exists(req.file_path):
        raise HTTPException(400, f"File not found: {req.file_path}")

    # Hash pipeline
    hashes = hash_pipeline(req.file_path)

    # PID
    pid = req.subject_pid or generate_pid(role="OWNER", region=req.jurisdiction)
    pid_hash = hash_pid(pid)

    # Check for existing registration (same raw_file_hash)
    existing = db.query(FileRecord).filter(FileRecord.raw_file_hash == hashes["raw_file_hash"]).first()
    version = (existing.version + 1) if existing else 1

    # Initial SKU (no git/solana yet)
    sku = generate_sku(
        category=req.category, subcategory=req.subcategory, kind=req.kind,
        lifecycle_stage=1, version=version, jurisdiction=req.jurisdiction,
        repo_alias="NOREPO", commit_short="00000000", tx_short="00000000",
        kpi_profile=0, collateral_flag=False, raw_file_hash=hashes["raw_file_hash"],
    )
    sku_hash = generate_sku_hash(sku)

    # Build partial manifest to hash
    partial_manifest = {
        "sku": sku, "category": req.category, "subcategory": req.subcategory,
        "kind": req.kind, "lifecycle_stage": 1, "version": version,
        "jurisdiction": req.jurisdiction, "subject_pid_hash": pid_hash,
        "raw_file_hash": hashes["raw_file_hash"], "base64_hash": hashes["base64_hash"],
        "content_exposed": False, "identity_exposed": False,
    }
    manifest_hash = hash_manifest(partial_manifest)

    # Save file record
    rec = FileRecord(
        sku=sku, sku_hash=sku_hash,
        raw_file_hash=hashes["raw_file_hash"], base64_hash=hashes["base64_hash"],
        manifest_hash=manifest_hash, category=req.category, subcategory=req.subcategory,
        kind=req.kind, lifecycle_stage=1, version=version, jurisdiction=req.jurisdiction,
        subject_pid=pid, content_exposed=False, identity_exposed=False,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    # Lifecycle event LC1
    lc_engine.record_event(db, sku, 1, "registered", {
        "file_size_bytes": hashes["file_size_bytes"],
        "file_name_hash": hashes["file_name_hash"],
        "version": version,
    })

    manifest = _build_manifest(rec, db)
    return {
        "sku": sku, "manifest": manifest,
        "qr_url": f"/f/{sku}", "barcode_value": sku,
        "subject_pid": pid,
        "message": "File registered successfully. No file contents were stored or exposed.",
    }


@router.get("/files")
async def list_files(db: Session = Depends(get_db)):
    recs = db.query(FileRecord).order_by(FileRecord.created_at.desc()).limit(200).all()
    return [{"sku": r.sku, "category": r.category, "subcategory": r.subcategory,
             "kind": r.kind, "lifecycle_stage": r.lifecycle_stage,
             "lifecycle_label": STAGE_LABELS.get(r.lifecycle_stage, ""),
             "version": r.version, "jurisdiction": r.jurisdiction,
             "created_at": r.created_at.isoformat()} for r in recs]


@router.get("/files/{sku}")
async def get_file(sku: str, db: Session = Depends(get_db)):
    rec = _require_file(db, sku)
    return _build_manifest(rec, db)


@router.get("/files/{sku}/manifest")
async def get_manifest(sku: str, db: Session = Depends(get_db)):
    rec = _require_file(db, sku)
    return _build_manifest(rec, db)


@router.get("/files/{sku}/timeline")
async def get_timeline(sku: str, db: Session = Depends(get_db)):
    _require_file(db, sku)
    return lc_engine.get_timeline(db, sku)


@router.get("/files/{sku}/appraisals")
async def get_appraisals(sku: str, db: Session = Depends(get_db)):
    _require_file(db, sku)
    return get_appraisal_history(db, sku)


@router.post("/files/{sku}/appraise")
async def run_appraisal(sku: str, db: Session = Depends(get_db)):
    rec = _require_file(db, sku)
    manifest = _build_manifest(rec, db)
    result = await appraise_file(db, sku, manifest)
    lc_engine.advance_to_stage(db, rec, 6, {"appraisal_value_usd": result["appraisal_value_usd"]})
    return result


@router.post("/files/{sku}/anchor-appraisal")
async def anchor_appraisal(sku: str, db: Session = Depends(get_db)):
    rec = _require_file(db, sku)
    appraisal = db.query(AppraisalRecord).filter(AppraisalRecord.sku == sku).order_by(AppraisalRecord.created_at.desc()).first()
    if not appraisal:
        raise HTTPException(404, "No appraisal found. Run /appraise first.")
    import hashlib
    appraisal_hash = "sha256:" + hashlib.sha256(f"{appraisal.sku}:{appraisal.appraisal_value_usd}:{appraisal.created_at}".encode()).hexdigest()
    result = await solana_service.anchor_hashes({
        "sku_hash": rec.sku_hash, "manifest_hash": rec.manifest_hash,
        "raw_file_hash": rec.raw_file_hash, "base64_hash": rec.base64_hash,
        "lifecycle_event_hash": appraisal_hash,
    })
    anchor = ChainAnchor(
        sku=sku, network_code=result["network_code"], network=result["network"],
        anchor_tx=result["anchor_tx"], anchor_tx_short=result["anchor_tx_short"],
        explorer_url=result["explorer_url"], payload_json=json.dumps(result.get("payload", {})),
    )
    db.add(anchor)
    db.commit()
    return result


@router.get("/files/{sku}/qr")
async def get_qr(sku: str, db: Session = Depends(get_db)):
    _require_file(db, sku)
    qr_data = generate_qr_base64(f"/f/{sku}")
    return {"sku": sku, "qr_data_url": qr_data, "qr_target": f"/f/{sku}"}


@router.get("/files/{sku}/barcode")
async def get_barcode(sku: str, db: Session = Depends(get_db)):
    _require_file(db, sku)
    bc_data = generate_barcode_base64(sku)
    return {"sku": sku, "barcode_data_url": bc_data, "barcode_value": sku}


@router.post("/files/{sku}/commit-to-github")
async def commit_to_github(sku: str, db: Session = Depends(get_db)):
    rec = _require_file(db, sku)
    manifest = _build_manifest(rec, db)
    gh_result = await github_service.commit_manifest(sku, manifest)
    gh_rec = GitHubCommit(
        sku=sku, repo_alias=gh_result["repo_alias"], repo=gh_result["repo"],
        branch=gh_result["branch"], commit_sha=gh_result["commit_sha"],
        commit_short=gh_result["commit_short"], commit_url=gh_result["commit_url"],
    )
    db.add(gh_rec)
    # Regenerate SKU with github info
    new_sku = generate_sku(
        category=rec.category, subcategory=rec.subcategory, kind=rec.kind,
        lifecycle_stage=4, version=rec.version, jurisdiction=rec.jurisdiction,
        repo_alias=gh_result["repo_alias"], commit_short=gh_result["commit_short"],
        tx_short="00000000", kpi_profile=0, collateral_flag=False,
        raw_file_hash=rec.raw_file_hash,
    )
    rec.sku = new_sku
    rec.sku_hash = generate_sku_hash(new_sku)
    rec.lifecycle_stage = 4
    gh_rec.sku = new_sku
    db.commit()
    lc_engine.record_event(db, new_sku, 4, "committed_to_github", gh_result)
    return {"sku": new_sku, "github": gh_result}


@router.post("/files/{sku}/anchor")
async def anchor_on_chain(sku: str, db: Session = Depends(get_db)):
    rec = _require_file(db, sku)
    gh = db.query(GitHubCommit).filter(GitHubCommit.sku == sku).order_by(GitHubCommit.created_at.desc()).first()
    payload = {
        "sku_hash": rec.sku_hash, "manifest_hash": rec.manifest_hash,
        "raw_file_hash": rec.raw_file_hash, "base64_hash": rec.base64_hash,
        "lifecycle_event_hash": "sha256:lc5",
        "git_commit_sha": gh.commit_sha if gh else "",
    }
    result = await solana_service.anchor_hashes(payload)
    anchor = ChainAnchor(
        sku=sku, network_code=result["network_code"], network=result["network"],
        anchor_tx=result["anchor_tx"], anchor_tx_short=result["anchor_tx_short"],
        explorer_url=result["explorer_url"], payload_json=json.dumps(result.get("payload", {})),
    )
    db.add(anchor)
    # Regenerate SKU with solana info
    gh_alias = gh.repo_alias if gh else "NOREPO"
    gh_commit = gh.commit_short if gh else "00000000"
    new_sku = generate_sku(
        category=rec.category, subcategory=rec.subcategory, kind=rec.kind,
        lifecycle_stage=5, version=rec.version, jurisdiction=rec.jurisdiction,
        repo_alias=gh_alias, commit_short=gh_commit, tx_short=result["anchor_tx_short"],
        kpi_profile=0, collateral_flag=False, raw_file_hash=rec.raw_file_hash,
    )
    rec.sku = new_sku
    rec.sku_hash = generate_sku_hash(new_sku)
    rec.lifecycle_stage = 5
    anchor.sku = new_sku
    db.commit()
    lc_engine.record_event(db, new_sku, 5, "anchored_on_chain", result)
    return {"sku": new_sku, "chain": result}


@router.get("/files/{sku}/verify")
async def verify(sku: str, file_path: str, db: Session = Depends(get_db)):
    rec = _require_file(db, sku)
    if not os.path.exists(file_path):
        raise HTTPException(400, f"File not found at path: {file_path}")
    result = verify_file(db, sku, file_path)
    if result["verified"]:
        lc_engine.advance_to_stage(db, rec, 7, {"verification": "passed"})
    return result


@router.post("/files/{sku}/ask")
async def ask_question(sku: str, req: LLMQueryRequest, db: Session = Depends(get_db)):
    _require_file(db, sku)
    return await answer_question(db, sku, req.question)


@router.get("/sku/{sku}/explain")
async def explain_sku(sku: str):
    return disassemble_sku(sku)


# ---------------------------------------------------------------------------
# Collateral endpoints
# ---------------------------------------------------------------------------

@router.post("/collateral/evaluate/{sku}")
async def evaluate_collateral(sku: str, req: CollateralEvaluateRequest, db: Session = Depends(get_db)):
    rec = _require_file(db, sku)
    v_score = get_verification_score(db, sku)
    latest_appraisal = db.query(AppraisalRecord).filter(AppraisalRecord.sku == sku).order_by(AppraisalRecord.created_at.desc()).first()
    appraised_value = latest_appraisal.appraisal_value_usd if latest_appraisal else req.face_value_usd
    gh = db.query(GitHubCommit).filter(GitHubCommit.sku == sku).first()
    anchor = db.query(ChainAnchor).filter(ChainAnchor.sku == sku).first()
    kpis = calculate_collateral(
        sku=sku, face_value_usd=req.face_value_usd,
        appraised_value_usd=appraised_value, collateral_class=req.collateral_class,
        advance_rate_percent=req.advance_rate_percent,
        lifecycle_stage=rec.lifecycle_stage, verification_score=v_score,
        audit_score=v_score, days_to_maturity=req.days_to_maturity,
        chain_anchored=anchor is not None, git_versioned=gh is not None,
    )
    col_rec = save_collateral_record(db, sku, kpis)
    # Regenerate SKU with KPI profile
    gh_alias = gh.repo_alias if gh else "NOREPO"
    gh_commit = gh.commit_short if gh else "00000000"
    anc_short = anchor.anchor_tx_short if anchor else "00000000"
    new_sku = generate_sku(
        category=rec.category, subcategory=rec.subcategory, kind=rec.kind,
        lifecycle_stage=rec.lifecycle_stage, version=rec.version, jurisdiction=rec.jurisdiction,
        repo_alias=gh_alias, commit_short=gh_commit, tx_short=anc_short,
        kpi_profile=kpis["kpi_profile"], collateral_flag=kpis["eligible_for_collateral"],
        raw_file_hash=rec.raw_file_hash,
    )
    if new_sku != rec.sku:
        rec.sku = new_sku
        rec.sku_hash = generate_sku_hash(new_sku)
        db.commit()
    kpis["sku"] = new_sku
    kpis["last_revalued_at"] = col_rec.updated_at.isoformat()
    return kpis


@router.post("/collateral/pledge/{sku}")
async def pledge(sku: str, req: PledgeRequest, db: Session = Depends(get_db)):
    _require_file(db, sku)
    col = db.query(CollateralRecord).filter(CollateralRecord.sku == sku).first()
    if not col:
        raise HTTPException(400, "Run /collateral/evaluate first before pledging.")
    lien_rec = pledge_collateral(db, sku, req.lien_holder_pid,
                                  col.collateral_cert_id, req.loan_id_hash)
    return {"sku": sku, "lien_status": "pledged", "lien_holder_pid": req.lien_holder_pid,
            "collateral_cert_id": col.collateral_cert_id, "created_at": lien_rec.created_at.isoformat()}


@router.post("/collateral/release/{sku}")
async def release(sku: str, db: Session = Depends(get_db)):
    _require_file(db, sku)
    return release_lien(db, sku)


@router.get("/collateral/{sku}/certificate")
async def get_certificate(sku: str, db: Session = Depends(get_db)):
    _require_file(db, sku)
    col = db.query(CollateralRecord).filter(CollateralRecord.sku == sku).first()
    if not col:
        raise HTTPException(404, "No collateral record. Run /collateral/evaluate first.")
    lien = get_lien_status(db, sku)
    return {
        "sku": sku, "collateral_cert_id": col.collateral_cert_id,
        "eligible": col.eligible, "collateral_class": col.collateral_class,
        "face_value_usd": col.face_value_usd, "appraised_value_usd": col.appraised_value_usd,
        "lendable_value_usd": col.lendable_value_usd, "advance_rate_percent": col.advance_rate_percent,
        "haircut_percent": col.haircut_percent, "lien_status": lien,
        "created_at": col.created_at.isoformat(), "updated_at": col.updated_at.isoformat(),
        "disclaimer": "This is a collateral-eligible estimate. Not a guarantee of value.",
    }


@router.get("/collateral/{sku}/risk")
async def get_risk(sku: str, db: Session = Depends(get_db)):
    _require_file(db, sku)
    col = db.query(CollateralRecord).filter(CollateralRecord.sku == sku).first()
    if not col:
        raise HTTPException(404, "No collateral record.")
    return {"sku": sku, "default_risk_score": col.default_risk_score,
            "fraud_risk_score": col.fraud_risk_score, "verification_score": col.verification_score,
            "audit_score": col.audit_score, "payment_probability": col.payment_probability}


@router.get("/collateral/{sku}/liquidity")
async def get_liquidity(sku: str, db: Session = Depends(get_db)):
    _require_file(db, sku)
    col = db.query(CollateralRecord).filter(CollateralRecord.sku == sku).first()
    if not col:
        raise HTTPException(404, "No collateral record.")
    return {"sku": sku, "liquidity_score": col.liquidity_score, "days_to_maturity": col.days_to_maturity,
            "lendable_value_usd": col.lendable_value_usd, "advance_rate_percent": col.advance_rate_percent}


@router.get("/collateral/{sku}/lien-status")
async def lien_status(sku: str, db: Session = Depends(get_db)):
    _require_file(db, sku)
    return get_lien_status(db, sku)
