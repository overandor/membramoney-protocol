"""LLM-powered appraisal engine for MEMBRA FileLife."""
import json
import os
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from .db import AppraisalRecord, FileRecord

_SYSTEM_PROMPT = """You are a financial document appraiser specializing in file-as-collateral valuation.
Given only metadata about a file (no raw contents are available), estimate its financial value in USD.
Consider: document type, lifecycle stage, blockchain anchoring, GitHub version history, verification status.
Output ONLY valid JSON: {"value_usd": <float>, "confidence": <float 0.0-1.0>, "rationale": "<one sentence ≤120 chars>"}"""


def _heuristic_value(manifest: dict) -> tuple[float, float, str]:
    base = 100.0
    base += manifest.get("lifecycle_stage", 0) * 50
    if manifest.get("github"):
        base += 200
    if manifest.get("chain"):
        base += 300
    size = manifest.get("file_size_bytes", 0)
    base += min(500, size / 1000)
    return round(base, 2), 0.3, "Heuristic estimate (no API key configured)."


async def appraise_file(db: Session, sku: str, manifest: dict, llm_model: str = "claude-haiku-4-5-20251001") -> dict:
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    file_rec = db.query(FileRecord).filter(FileRecord.sku == sku).first()
    version = file_rec.version if file_rec else 1

    if api_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            context = {
                "kind": manifest.get("kind"), "category": manifest.get("category"),
                "subcategory": manifest.get("subcategory"),
                "lifecycle_stage": manifest.get("lifecycle_stage"),
                "lifecycle_label": manifest.get("lifecycle_label"),
                "version": manifest.get("version"),
                "jurisdiction": manifest.get("jurisdiction"),
                "github_anchored": bool(manifest.get("github")),
                "chain_anchored": bool(manifest.get("chain")),
                "file_size_bytes": manifest.get("file_size_bytes", 0),
            }
            resp = client.messages.create(
                model=llm_model, max_tokens=128,
                system=[{"type": "text", "text": _SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": f"File metadata:\n{json.dumps(context, indent=2)}"}],
            )
            raw = resp.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)
            value_usd = max(0.0, float(data.get("value_usd", 100)))
            confidence = max(0.0, min(1.0, float(data.get("confidence", 0.5))))
            rationale = str(data.get("rationale", ""))[:200]
        except Exception as e:
            value_usd, confidence, rationale = _heuristic_value(manifest)
            llm_model = "heuristic"
    else:
        value_usd, confidence, rationale = _heuristic_value(manifest)
        llm_model = "heuristic"

    rec = AppraisalRecord(
        sku=sku, version=version,
        appraisal_value_usd=value_usd,
        confidence=confidence, rationale=rationale, llm_model=llm_model,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return {
        "id": rec.id, "sku": sku, "version": version,
        "appraisal_value_usd": value_usd, "confidence": confidence,
        "rationale": rationale, "llm_model": llm_model,
        "created_at": rec.created_at.isoformat(),
    }


def get_appraisal_history(db: Session, sku: str) -> list:
    recs = db.query(AppraisalRecord).filter(AppraisalRecord.sku == sku).order_by(AppraisalRecord.created_at).all()
    return [{"id": r.id, "sku": r.sku, "version": r.version, "appraisal_value_usd": r.appraisal_value_usd,
             "confidence": r.confidence, "rationale": r.rationale, "llm_model": r.llm_model,
             "created_at": r.created_at.isoformat()} for r in recs]
