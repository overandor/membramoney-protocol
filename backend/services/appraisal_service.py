"""
Machine Appraisal Service

Walks the repository filesystem, assigns a dollar value to every file via the
Claude API (with prompt caching), builds a binary Merkle tree over all
(path, content-hash, value_cents) leaves, persists each hourly snapshot, and
exposes net-worth deltas between consecutive runs.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import anthropic

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]   # membramoney-protocol/
SNAPSHOT_DIR = Path(__file__).resolve().parent.parent / "appraisal_snapshots"
SNAPSHOT_DIR.mkdir(exist_ok=True)

# File extensions we will read and send to the LLM for valuation.
# Binary / generated files get a fast heuristic valuation instead.
TEXT_EXTENSIONS = {
    ".py", ".rs", ".ts", ".tsx", ".js", ".jsx",
    ".toml", ".yaml", ".yml", ".json", ".md", ".txt",
    ".sql", ".sh", ".env", ".cfg", ".ini", ".lock",
    ".html", ".css", ".scss",
}

# Paths (relative to REPO_ROOT) to skip entirely.
SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".pytest_cache",
    "target", "dist", "build", ".venv", "venv",
    "appraisal_snapshots",
}

MAX_FILE_BYTES_FOR_LLM = 12_000   # truncate large files before sending
MAX_FILES_PER_RUN = 2_000         # safety cap

# ---------------------------------------------------------------------------
# Merkle Tree
# ---------------------------------------------------------------------------

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _leaf_hash(rel_path: str, content_hash: str, value_cents: int) -> str:
    payload = f"{rel_path}|{content_hash}|{value_cents}"
    return _sha256(payload.encode())


def _pair_hash(left: str, right: str) -> str:
    return _sha256((left + right).encode())


def build_merkle_tree(leaves: List[str]) -> Tuple[str, List[List[str]]]:
    """
    Build a binary Merkle tree from a list of leaf hashes.

    Returns (root_hash, levels) where levels[0] is the leaf layer and
    levels[-1] is [root_hash].
    """
    if not leaves:
        return _sha256(b"empty"), [[_sha256(b"empty")]]

    layer = list(leaves)
    levels = [layer[:]]

    while len(layer) > 1:
        if len(layer) % 2 == 1:
            layer.append(layer[-1])   # duplicate last leaf for odd counts
        next_layer = [_pair_hash(layer[i], layer[i + 1]) for i in range(0, len(layer), 2)]
        levels.append(next_layer[:])
        layer = next_layer

    return layer[0], levels


def merkle_proof(leaves: List[str], index: int) -> List[Dict]:
    """
    Return a proof (list of {sibling, direction} dicts) for the leaf at
    `index`.  Verifiers recompute the root by hashing up the path.
    """
    if not leaves:
        return []
    layer = list(leaves)
    proof: List[Dict] = []
    idx = index

    while len(layer) > 1:
        if len(layer) % 2 == 1:
            layer.append(layer[-1])
        sibling_idx = idx ^ 1
        proof.append({
            "sibling": layer[sibling_idx],
            "direction": "right" if idx % 2 == 0 else "left",
        })
        layer = [_pair_hash(layer[i], layer[i + 1]) for i in range(0, len(layer), 2)]
        idx //= 2

    return proof

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class FileAppraisal:
    rel_path: str
    content_hash: str
    size_bytes: int
    value_cents: int           # USD cents
    rationale: str
    leaf_hash: str = field(init=False)

    def __post_init__(self):
        self.leaf_hash = _leaf_hash(self.rel_path, self.content_hash, self.value_cents)

    @property
    def value_dollars(self) -> float:
        return self.value_cents / 100.0


@dataclass
class AppraisalSnapshot:
    run_id: str
    timestamp: str
    merkle_root: str
    total_value_cents: int
    file_count: int
    files: List[FileAppraisal]
    previous_root: Optional[str] = None
    delta_cents: Optional[int] = None     # vs previous snapshot

    @property
    def total_value_dollars(self) -> float:
        return self.total_value_cents / 100.0

    @property
    def delta_dollars(self) -> Optional[float]:
        return self.delta_cents / 100.0 if self.delta_cents is not None else None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["total_value_dollars"] = self.total_value_dollars
        d["delta_dollars"] = self.delta_dollars
        return d

# ---------------------------------------------------------------------------
# File scanner
# ---------------------------------------------------------------------------

def _content_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_truncated(path: Path) -> str:
    try:
        text = path.read_text(errors="replace")
        return text[:MAX_FILE_BYTES_FOR_LLM]
    except Exception:
        return ""


def scan_files(root: Path) -> List[Path]:
    results: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            fp = Path(dirpath) / fname
            try:
                if fp.stat().st_size > 0:
                    results.append(fp)
            except OSError:
                pass
            if len(results) >= MAX_FILES_PER_RUN:
                return results
    return results

# ---------------------------------------------------------------------------
# LLM Appraiser
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a senior software asset appraiser specializing in open-source repositories.

Your job is to assign a fair market dollar value to individual source files,
configuration files, and documentation within a software project.

When appraising, consider:
- Intellectual property: uniqueness, innovation, and non-triviality of logic
- Replacement cost: how many hours a skilled developer would need to re-create it
  (assume $150/hr fully-loaded cost)
- Strategic value: does it enable a core protocol feature (smart contracts, APIs,
  security, cryptography) or is it boilerplate?
- Data value: if it contains configuration, credentials hints, or structured data
- Documentation value: well-written specs and architecture docs have value

Output ONLY valid JSON with keys: "value_cents" (integer, USD cents) and
"rationale" (one sentence, ≤ 120 chars).

Example: {"value_cents": 4500, "rationale": "Core claim-validation logic, ~30 hrs to rebuild."}
"""


class LLMAppraiser:
    """
    Batch-appraises files using the Claude API with prompt caching on the
    system prompt to minimise token costs across many files in one run.
    """

    def __init__(self, model: str = "claude-haiku-4-5-20251001"):
        self.client = anthropic.Anthropic()
        self.model = model
        # value_cache: content_hash -> (value_cents, rationale)
        self._value_cache: Dict[str, Tuple[int, str]] = {}

    def _heuristic_value(self, path: Path) -> Tuple[int, str]:
        """Fast dollar estimate for binary/generated files without calling LLM."""
        size = path.stat().st_size
        # $0.001 per KB for generic binary assets
        cents = max(50, int(size / 1024 * 0.1))
        return cents, f"Binary/generated asset, size-based estimate ({size} bytes)."

    def appraise_file(self, path: Path) -> Tuple[int, str]:
        ext = path.suffix.lower()
        if ext not in TEXT_EXTENSIONS:
            return self._heuristic_value(path)

        try:
            chash = _content_hash(path)
        except OSError:
            return 50, "Unreadable file."

        if chash in self._value_cache:
            return self._value_cache[chash]

        content = _read_truncated(path)
        if not content.strip():
            result = (25, "Empty or whitespace-only file.")
            self._value_cache[chash] = result
            return result

        rel = str(path.relative_to(REPO_ROOT))
        user_msg = f"File: {rel}\n\n```\n{content}\n```"

        try:
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=128,
                system=[
                    {
                        "type": "text",
                        "text": _SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": user_msg}],
            )
            raw = resp.content[0].text.strip()
            # strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)
            value_cents = max(1, int(data.get("value_cents", 100)))
            rationale = str(data.get("rationale", ""))[:200]
        except Exception as exc:
            value_cents = 100
            rationale = f"LLM error, default value applied ({exc!s:.60})."

        self._value_cache[chash] = (value_cents, rationale)
        return value_cents, rationale

    def appraise_all(self, files: List[Path]) -> List[FileAppraisal]:
        results: List[FileAppraisal] = []
        for fp in files:
            try:
                size = fp.stat().st_size
                chash = _content_hash(fp)
            except OSError:
                continue
            value_cents, rationale = self.appraise_file(fp)
            rel = str(fp.relative_to(REPO_ROOT))
            results.append(FileAppraisal(
                rel_path=rel,
                content_hash=chash,
                size_bytes=size,
                value_cents=value_cents,
                rationale=rationale,
            ))
        return results

# ---------------------------------------------------------------------------
# Snapshot persistence
# ---------------------------------------------------------------------------

def _snapshot_path(run_id: str) -> Path:
    return SNAPSHOT_DIR / f"{run_id}.json"


def save_snapshot(snap: AppraisalSnapshot) -> None:
    path = _snapshot_path(snap.run_id)
    path.write_text(json.dumps(snap.to_dict(), indent=2))


def load_snapshot(run_id: str) -> Optional[AppraisalSnapshot]:
    path = _snapshot_path(run_id)
    if not path.exists():
        return None
    raw = json.loads(path.read_text())
    files = [
        FileAppraisal(
            rel_path=f["rel_path"],
            content_hash=f["content_hash"],
            size_bytes=f["size_bytes"],
            value_cents=f["value_cents"],
            rationale=f["rationale"],
        )
        for f in raw.get("files", [])
    ]
    return AppraisalSnapshot(
        run_id=raw["run_id"],
        timestamp=raw["timestamp"],
        merkle_root=raw["merkle_root"],
        total_value_cents=raw["total_value_cents"],
        file_count=raw["file_count"],
        files=files,
        previous_root=raw.get("previous_root"),
        delta_cents=raw.get("delta_cents"),
    )


def list_snapshot_ids() -> List[str]:
    ids = [p.stem for p in sorted(SNAPSHOT_DIR.glob("*.json"))]
    return ids


def latest_snapshot() -> Optional[AppraisalSnapshot]:
    ids = list_snapshot_ids()
    return load_snapshot(ids[-1]) if ids else None

# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class AppraisalEngine:
    def __init__(self):
        self._appraiser = LLMAppraiser()

    def run(self) -> AppraisalSnapshot:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        timestamp = datetime.now(timezone.utc).isoformat()

        files = scan_files(REPO_ROOT)
        appraisals = self._appraiser.appraise_all(files)

        # Sort deterministically so Merkle tree is stable for identical inputs
        appraisals.sort(key=lambda a: a.rel_path)

        leaves = [a.leaf_hash for a in appraisals]
        root, _ = build_merkle_tree(leaves)
        total_cents = sum(a.value_cents for a in appraisals)

        prev = latest_snapshot()
        prev_root = prev.merkle_root if prev else None
        delta_cents = (total_cents - prev.total_value_cents) if prev else None

        snap = AppraisalSnapshot(
            run_id=run_id,
            timestamp=timestamp,
            merkle_root=root,
            total_value_cents=total_cents,
            file_count=len(appraisals),
            files=appraisals,
            previous_root=prev_root,
            delta_cents=delta_cents,
        )
        save_snapshot(snap)
        return snap
