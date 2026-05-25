"""Collateral scoring engine for MEMBRA FileLife."""
import hashlib
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from .db import CollateralRecord

ADVANCE_RATES = {
    "accounts_receivable": 0.85, "invoice": 0.80,
    "contract_receivable": 0.75, "inventory_document": 0.60,
    "tax_credit": 0.70, "royalty_stream": 0.55, "appraisal_asset": 0.65,
}


def _cert_id(sku: str) -> str:
    seed = f"{sku}{datetime.now(timezone.utc).isoformat()}"
    return "COLCERT-" + hashlib.sha256(seed.encode()).hexdigest()[:12].upper()


def calculate_collateral(
    sku: str, face_value_usd: float, appraised_value_usd: float,
    collateral_class: str, advance_rate_percent: Optional[float] = None,
    lifecycle_stage: int = 0, verification_score: float = 0.0,
    audit_score: float = 0.0, days_to_maturity: int = 0,
    chain_anchored: bool = False, git_versioned: bool = False,
) -> dict:
    advance_rate = (advance_rate_percent / 100.0) if advance_rate_percent else ADVANCE_RATES.get(collateral_class, 0.70)
    ver_factor = 0.5 + 0.5 * verification_score
    liq_factor = max(0.3, 1.0 - days_to_maturity / 365) if days_to_maturity else 0.8
    risk_factor = 0.7 + (0.1 if chain_anchored else 0) + (0.1 if git_versioned else 0) + (0.1 if lifecycle_stage >= 7 else 0)
    lendable = appraised_value_usd * advance_rate * ver_factor * liq_factor * risk_factor
    kpi = min(9, max(0, int(ver_factor * 3 + (lifecycle_stage / 9) * 3 + (chain_anchored + git_versioned) * 1.5)))
    return {
        "sku": sku, "eligible_for_collateral": lendable > 0,
        "collateral_class": collateral_class, "face_value_usd": face_value_usd,
        "appraised_value_usd": appraised_value_usd,
        "advance_rate_percent": round(advance_rate * 100, 1),
        "lendable_value_usd": round(lendable, 2),
        "haircut_percent": round((1 - advance_rate) * 100, 1),
        "liquidity_score": round(liq_factor * 100),
        "default_risk_score": round((1 - risk_factor) * 100),
        "fraud_risk_score": max(0, 30 - round(verification_score * 30)),
        "verification_score": round(verification_score * 100, 1),
        "audit_score": round(audit_score * 100, 1),
        "payment_probability": round(50 + verification_score * 50),
        "days_to_maturity": days_to_maturity, "kpi_profile": kpi,
        "collateral_cert_id": _cert_id(sku), "lien_status": "none",
    }


def save_collateral_record(db: Session, sku: str, kpis: dict) -> CollateralRecord:
    existing = db.query(CollateralRecord).filter(CollateralRecord.sku == sku).first()
    if existing:
        for k, v in kpis.items():
            if hasattr(existing, k):
                setattr(existing, k, v)
        existing.eligible = kpis.get("eligible_for_collateral", False)
        db.commit()
        db.refresh(existing)
        return existing
    rec = CollateralRecord(
        sku=sku, eligible=kpis.get("eligible_for_collateral", False),
        collateral_class=kpis.get("collateral_class", ""),
        face_value_usd=kpis.get("face_value_usd", 0),
        appraised_value_usd=kpis.get("appraised_value_usd", 0),
        advance_rate_percent=kpis.get("advance_rate_percent", 0),
        lendable_value_usd=kpis.get("lendable_value_usd", 0),
        haircut_percent=kpis.get("haircut_percent", 0),
        liquidity_score=kpis.get("liquidity_score", 0),
        default_risk_score=kpis.get("default_risk_score", 0),
        fraud_risk_score=kpis.get("fraud_risk_score", 0),
        verification_score=kpis.get("verification_score", 0),
        audit_score=kpis.get("audit_score", 0),
        payment_probability=kpis.get("payment_probability", 0),
        days_to_maturity=kpis.get("days_to_maturity", 0),
        lien_status="none", collateral_cert_id=kpis.get("collateral_cert_id"),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec
