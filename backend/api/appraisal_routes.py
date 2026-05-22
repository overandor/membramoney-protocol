"""
Appraisal API Routes

Exposes machine-appraisal endpoints:
  POST /api/v1/appraisal/run          — trigger an immediate appraisal run
  GET  /api/v1/appraisal/latest       — most recent snapshot summary
  GET  /api/v1/appraisal/history      — list all snapshot summaries
  GET  /api/v1/appraisal/{run_id}     — full snapshot (all files + values)
  GET  /api/v1/appraisal/{run_id}/proof/{file_path} — Merkle inclusion proof
  GET  /api/v1/appraisal/delta        — net-worth change between last two runs
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional

from services.appraisal_service import (
    AppraisalEngine,
    AppraisalSnapshot,
    load_snapshot,
    list_snapshot_ids,
    latest_snapshot,
    build_merkle_tree,
    merkle_proof,
)

router = APIRouter(prefix="/api/v1/appraisal", tags=["appraisal"])

_engine: Optional[AppraisalEngine] = None
_running = False   # simple guard against concurrent runs


def _get_engine() -> AppraisalEngine:
    global _engine
    if _engine is None:
        _engine = AppraisalEngine()
    return _engine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _summary(snap: AppraisalSnapshot) -> dict:
    return {
        "run_id": snap.run_id,
        "timestamp": snap.timestamp,
        "merkle_root": snap.merkle_root,
        "previous_root": snap.previous_root,
        "total_value_dollars": snap.total_value_dollars,
        "delta_dollars": snap.delta_dollars,
        "file_count": snap.file_count,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/run")
async def trigger_appraisal(background_tasks: BackgroundTasks):
    """
    Start a full machine appraisal in the background.  Each file is valued
    by the Claude LLM; results are committed into a Merkle tree and persisted.
    """
    global _running
    if _running:
        raise HTTPException(status_code=409, detail="Appraisal already in progress.")
    _running = True

    def _run():
        global _running
        try:
            _get_engine().run()
        finally:
            _running = False

    background_tasks.add_task(_run)
    return {"status": "started", "message": "Appraisal running in background. Poll /latest for results."}


@router.get("/latest")
async def get_latest():
    """Return the most recent appraisal snapshot summary."""
    snap = latest_snapshot()
    if snap is None:
        raise HTTPException(status_code=404, detail="No appraisal runs found. POST /run first.")
    return _summary(snap)


@router.get("/history")
async def get_history():
    """Return summaries of all historical appraisal runs, newest first."""
    ids = list_snapshot_ids()
    summaries = []
    for sid in reversed(ids):
        snap = load_snapshot(sid)
        if snap:
            summaries.append(_summary(snap))
    return {"runs": summaries, "count": len(summaries)}


@router.get("/delta")
async def get_delta():
    """
    Show net-worth change between the last two appraisal runs along with the
    files that changed value, appeared, or disappeared.
    """
    ids = list_snapshot_ids()
    if len(ids) < 2:
        raise HTTPException(status_code=404, detail="Need at least two runs for a delta.")

    curr = load_snapshot(ids[-1])
    prev = load_snapshot(ids[-2])

    curr_map = {f.rel_path: f for f in curr.files}
    prev_map = {f.rel_path: f for f in prev.files}

    added = []
    removed = []
    changed = []

    for path, fa in curr_map.items():
        if path not in prev_map:
            added.append({"file": path, "value_dollars": fa.value_dollars})
        elif fa.content_hash != prev_map[path].content_hash:
            changed.append({
                "file": path,
                "prev_dollars": prev_map[path].value_dollars,
                "curr_dollars": fa.value_dollars,
                "diff_dollars": fa.value_dollars - prev_map[path].value_dollars,
            })

    for path in prev_map:
        if path not in curr_map:
            removed.append({"file": path, "value_dollars": prev_map[path].value_dollars})

    return {
        "from_run": prev.run_id,
        "to_run": curr.run_id,
        "from_root": prev.merkle_root,
        "to_root": curr.merkle_root,
        "prev_net_worth_dollars": prev.total_value_dollars,
        "curr_net_worth_dollars": curr.total_value_dollars,
        "delta_dollars": curr.total_value_dollars - prev.total_value_dollars,
        "files_added": added,
        "files_removed": removed,
        "files_changed": changed,
    }


@router.get("/status")
async def appraisal_status():
    """Show whether an appraisal is currently running."""
    return {"running": _running}


@router.get("/{run_id}")
async def get_snapshot(run_id: str):
    """Return the full snapshot for a given run including per-file valuations."""
    snap = load_snapshot(run_id)
    if snap is None:
        raise HTTPException(status_code=404, detail=f"Snapshot {run_id} not found.")
    return snap.to_dict()


@router.get("/{run_id}/proof/{file_path:path}")
async def get_proof(run_id: str, file_path: str):
    """
    Return the Merkle inclusion proof for a specific file in a snapshot.
    Clients can verify the file's appraised value is committed in the tree root.
    """
    snap = load_snapshot(run_id)
    if snap is None:
        raise HTTPException(status_code=404, detail=f"Snapshot {run_id} not found.")

    snap.files.sort(key=lambda a: a.rel_path)
    leaves = [f.leaf_hash for f in snap.files]

    try:
        idx = next(i for i, f in enumerate(snap.files) if f.rel_path == file_path)
    except StopIteration:
        raise HTTPException(status_code=404, detail=f"File {file_path!r} not in snapshot.")

    fa = snap.files[idx]
    proof = merkle_proof(leaves, idx)

    return {
        "run_id": run_id,
        "merkle_root": snap.merkle_root,
        "file": file_path,
        "leaf_hash": fa.leaf_hash,
        "value_dollars": fa.value_dollars,
        "proof": proof,
        "verify_hint": (
            "Hash leaf_hash with each sibling in proof order "
            "(left|right or right|left depending on direction) "
            "up to the root. Result must equal merkle_root."
        ),
    }
