"""Lien tracking for MEMBRA FileLife."""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from .db import LienRecord, CollateralRecord


def pledge_collateral(db: Session, sku: str, lien_holder_pid: str,
                      collateral_cert_id: str, loan_id_hash: str = None, chain_tx: str = None) -> LienRecord:
    rec = LienRecord(sku=sku, lien_holder_pid=lien_holder_pid,
                     lien_status="pledged", collateral_cert_id=collateral_cert_id,
                     loan_id_hash=loan_id_hash, chain_tx=chain_tx)
    db.add(rec)
    col = db.query(CollateralRecord).filter(CollateralRecord.sku == sku).first()
    if col:
        col.lien_status = "pledged"
        col.collateral_cert_id = collateral_cert_id
        col.loan_id_hash = loan_id_hash
    db.commit()
    db.refresh(rec)
    return rec


def release_lien(db: Session, sku: str) -> dict:
    lien = (db.query(LienRecord).filter(LienRecord.sku == sku, LienRecord.lien_status == "pledged")
            .order_by(LienRecord.created_at.desc()).first())
    if not lien:
        return {"sku": sku, "message": "No active lien found."}
    lien.lien_status = "released"
    lien.released_at = datetime.now(timezone.utc)
    col = db.query(CollateralRecord).filter(CollateralRecord.sku == sku).first()
    if col:
        col.lien_status = "none"
    db.commit()
    return {"sku": sku, "lien_id": lien.id, "message": "Lien released.", "released_at": lien.released_at.isoformat()}


def get_lien_status(db: Session, sku: str) -> dict:
    lien = (db.query(LienRecord).filter(LienRecord.sku == sku)
            .order_by(LienRecord.created_at.desc()).first())
    if not lien:
        return {"sku": sku, "lien_status": "none", "lien_holder_pid": None, "collateral_cert_id": None}
    return {
        "sku": sku, "lien_status": lien.lien_status,
        "lien_holder_pid": lien.lien_holder_pid,
        "collateral_cert_id": lien.collateral_cert_id,
        "loan_id_hash": lien.loan_id_hash,
        "created_at": lien.created_at.isoformat(),
        "released_at": lien.released_at.isoformat() if lien.released_at else None,
    }
