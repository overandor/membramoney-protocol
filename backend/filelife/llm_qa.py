"""LLM Q&A service for MEMBRA FileLife. Privacy-first — no raw file contents."""
import json
import os
from sqlalchemy.orm import Session
from .db import (FileRecord, LifecycleEvent, GitHubCommit, ChainAnchor,
                 AppraisalRecord, CollateralRecord, LienRecord, VerificationRecord, LLMQuery)

_SYSTEM = """You are a financial document registry assistant for MEMBRA FileLife.
Answer questions using ONLY the provided metadata. Never invent. Never expose raw file contents.
Reply with valid JSON only: {"answer": "<string>", "sources": ["manifest", "lifecycle", ...], "confidence": <0.0-1.0>}
If the answer requires hidden content, respond: {"answer": "Access denied — content is private.", "sources": [], "confidence": 1.0}"""


def _build_context(db: Session, sku: str) -> dict:
    rec = db.query(FileRecord).filter(FileRecord.sku == sku).first()
    if not rec:
        return {}
    ctx: dict = {
        "manifest": {
            "sku": rec.sku, "category": rec.category, "subcategory": rec.subcategory,
            "kind": rec.kind, "lifecycle_stage": rec.lifecycle_stage, "version": rec.version,
            "jurisdiction": rec.jurisdiction, "raw_file_hash": rec.raw_file_hash,
            "base64_hash": rec.base64_hash, "manifest_hash": rec.manifest_hash,
            "sku_hash": rec.sku_hash, "content_exposed": rec.content_exposed,
            "identity_exposed": rec.identity_exposed,
            "created_at": rec.created_at.isoformat(), "updated_at": rec.updated_at.isoformat(),
        },
    }
    events = db.query(LifecycleEvent).filter(LifecycleEvent.sku == sku).all()
    ctx["lifecycle"] = [{"stage": e.stage, "event_type": e.event_type, "created_at": e.created_at.isoformat()} for e in events]
    gh = db.query(GitHubCommit).filter(GitHubCommit.sku == sku).order_by(GitHubCommit.created_at.desc()).first()
    if gh:
        ctx["github"] = {"repo": gh.repo, "commit_sha": gh.commit_sha, "commit_url": gh.commit_url, "branch": gh.branch}
    anchor = db.query(ChainAnchor).filter(ChainAnchor.sku == sku).order_by(ChainAnchor.created_at.desc()).first()
    if anchor:
        ctx["chain"] = {"network": anchor.network, "anchor_tx": anchor.anchor_tx, "explorer_url": anchor.explorer_url}
    appraisals = db.query(AppraisalRecord).filter(AppraisalRecord.sku == sku).all()
    ctx["appraisals"] = [{"value_usd": a.appraisal_value_usd, "confidence": a.confidence, "rationale": a.rationale, "created_at": a.created_at.isoformat()} for a in appraisals]
    col = db.query(CollateralRecord).filter(CollateralRecord.sku == sku).first()
    if col:
        ctx["collateral"] = {"eligible": col.eligible, "class": col.collateral_class,
                             "lendable_value_usd": col.lendable_value_usd, "lien_status": col.lien_status}
    lien = db.query(LienRecord).filter(LienRecord.sku == sku).order_by(LienRecord.created_at.desc()).first()
    if lien:
        ctx["lien"] = {"status": lien.lien_status, "created_at": lien.created_at.isoformat()}
    verif = db.query(VerificationRecord).filter(VerificationRecord.sku == sku).order_by(VerificationRecord.created_at.desc()).first()
    if verif:
        ctx["verification"] = {"verified": verif.verified, "created_at": verif.created_at.isoformat()}
    return ctx


async def answer_question(db: Session, sku: str, question: str) -> dict:
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    context = _build_context(db, sku)
    if not context:
        return {"sku": sku, "question": question, "answer": "File not found in registry.", "sources": [], "confidence": 1.0}

    if api_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            user_msg = f"SKU: {sku}\n\nContext:\n{json.dumps(context, indent=2)}\n\nQuestion: {question}"
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001", max_tokens=512,
                system=[{"type": "text", "text": _SYSTEM, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": user_msg}],
            )
            raw = resp.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)
            answer = str(data.get("answer", ""))
            sources = list(data.get("sources", []))
            confidence = float(data.get("confidence", 0.5))
        except Exception as e:
            answer = f"LLM unavailable: {str(e)[:100]}. Context keys available: {list(context.keys())}"
            sources = list(context.keys())
            confidence = 0.3
    else:
        answer = f"ANTHROPIC_API_KEY not configured. Available metadata: {', '.join(context.keys())}."
        sources = []
        confidence = 0.0

    q_rec = LLMQuery(sku=sku, question=question, answer=answer,
                     sources_json=json.dumps(sources), confidence=confidence)
    db.add(q_rec)
    db.commit()
    return {"sku": sku, "question": question, "answer": answer, "sources": sources, "confidence": confidence}
