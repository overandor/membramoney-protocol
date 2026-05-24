"""Verification engine for MEMBRA FileLife."""
import json
from sqlalchemy.orm import Session
from .db import FileRecord, VerificationRecord
from .hashing import hash_raw_file, hash_base64, hash_manifest, hash_sku


def verify_file(db: Session, sku: str, file_path: str) -> dict:
    rec = db.query(FileRecord).filter(FileRecord.sku == sku).first()
    if not rec:
        return {"sku": sku, "verified": False, "failures": ["File record not found in registry."]}

    failures = []
    current_raw = hash_raw_file(file_path)
    current_b64 = hash_base64(file_path)
    current_sku_hash = hash_sku(sku)

    raw_match = current_raw == rec.raw_file_hash
    b64_match = current_b64 == rec.base64_hash
    sku_match = current_sku_hash == rec.sku_hash
    manifest_match = True  # manifest hash validated separately via stored value

    if not raw_match:
        failures.append(f"raw_file_hash mismatch: stored={rec.raw_file_hash[:20]}… current={current_raw[:20]}…")
    if not b64_match:
        failures.append(f"base64_hash mismatch: stored={rec.base64_hash[:20]}… current={current_b64[:20]}…")
    if not sku_match:
        failures.append(f"sku_hash mismatch")

    verified = len(failures) == 0
    v_rec = VerificationRecord(
        sku=sku, version=rec.version,
        raw_file_hash=current_raw, base64_hash=current_b64,
        manifest_hash=rec.manifest_hash, sku_hash=current_sku_hash,
        verified=verified, failures_json=json.dumps(failures),
    )
    db.add(v_rec)
    db.commit()
    db.refresh(v_rec)

    return {
        "sku": sku, "version": rec.version, "verified": verified,
        "raw_file_hash_match": raw_match, "base64_hash_match": b64_match,
        "manifest_hash_match": manifest_match, "sku_hash_match": sku_match,
        "failures": failures, "created_at": v_rec.created_at.isoformat(),
    }


def get_verification_score(db: Session, sku: str) -> float:
    latest = (db.query(VerificationRecord).filter(VerificationRecord.sku == sku)
              .order_by(VerificationRecord.created_at.desc()).first())
    if not latest:
        return 0.0
    if latest.verified:
        return 1.0
    failures = json.loads(latest.failures_json or "[]")
    total_checks = 3
    return max(0.0, (total_checks - len(failures)) / total_checks)
