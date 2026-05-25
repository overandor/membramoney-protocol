"""
5-hash pipeline for MEMBRA FileLife.
Generates: raw_file_hash, base64_hash, manifest_hash, sku_hash, lifecycle_event_hash.
No raw file contents are ever returned.
"""
import base64
import hashlib
import json
import os


def hash_raw_file(file_path: str) -> str:
    """
    Read file in binary chunks and return sha256 hash.
    Returns "sha256:{hexdigest}"
    """
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return f"sha256:{sha.hexdigest()}"


def hash_base64(file_path: str) -> str:
    """
    Read file, base64-encode it, then hash the base64 string.
    Returns "sha256:{hexdigest}"
    """
    with open(file_path, "rb") as f:
        raw = f.read()
    b64 = base64.b64encode(raw)
    digest = hashlib.sha256(b64).hexdigest()
    return f"sha256:{digest}"


def hash_manifest(manifest_dict: dict) -> str:
    """
    Canonically serialize manifest dict, sha256 hash it.
    Returns "sha256:{hexdigest}"
    """
    canonical = json.dumps(manifest_dict, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    return f"sha256:{digest}"


def hash_sku(sku: str) -> str:
    """
    sha256 hash of SKU string bytes.
    Returns "sha256:{hexdigest}"
    """
    digest = hashlib.sha256(sku.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def hash_lifecycle_event(event_dict: dict) -> str:
    """
    Canonically serialize event dict, sha256 hash it.
    Returns "sha256:{hexdigest}"
    """
    canonical = json.dumps(event_dict, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    return f"sha256:{digest}"


def pipeline(file_path: str) -> dict:
    """
    Run the hash pipeline on a file.
    Returns raw_file_hash, base64_hash, and file metadata.
    Never returns file contents.
    """
    raw_file_hash = hash_raw_file(file_path)
    b64_hash = hash_base64(file_path)
    file_size = os.path.getsize(file_path)
    file_name_hash = hashlib.sha256(os.path.basename(file_path).encode()).hexdigest()[:16]

    return {
        "raw_file_hash": raw_file_hash,
        "base64_hash": b64_hash,
        "file_size_bytes": file_size,
        # Only expose a hash of the filename, not the actual name
        "file_name_hash": file_name_hash,
    }
