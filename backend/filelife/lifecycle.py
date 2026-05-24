"""Lifecycle engine for MEMBRA FileLife."""
import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from .db import LifecycleEvent
from .hashing import hash_lifecycle_event

STAGE_LABELS = {
    0: "discovered", 1: "registered", 2: "raw hashed",
    3: "base64 encoded", 4: "committed to GitHub",
    5: "anchored on-chain", 6: "appraised", 7: "verified",
    8: "amended/new version", 9: "archived",
}


def record_event(db: Session, sku: str, stage: int, event_type: str, metadata: Dict[str, Any]) -> LifecycleEvent:
    ts = datetime.now(timezone.utc).isoformat()
    event_dict = {"sku": sku, "stage": stage, "event_type": event_type, "metadata": metadata, "timestamp": ts}
    event_hash = hash_lifecycle_event(event_dict)
    ev = LifecycleEvent(
        sku=sku,
        stage=stage,
        event_type=event_type,
        event_hash=event_hash,
        metadata_json=json.dumps(metadata),
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


def get_timeline(db: Session, sku: str) -> List[dict]:
    events = db.query(LifecycleEvent).filter(LifecycleEvent.sku == sku).order_by(LifecycleEvent.created_at).all()
    return [
        {
            "id": e.id, "sku": e.sku, "stage": e.stage,
            "stage_label": STAGE_LABELS.get(e.stage, "unknown"),
            "event_type": e.event_type, "event_hash": e.event_hash,
            "metadata": json.loads(e.metadata_json or "{}"),
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]


def advance_to_stage(db: Session, file_record, new_stage: int, metadata: Dict[str, Any] = {}) -> None:
    record_event(db, file_record.sku, new_stage, f"stage_{new_stage}", metadata)
    file_record.lifecycle_stage = new_stage
    db.commit()
