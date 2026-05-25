"""
PID (Privacy-preserving Identifier) generator for MEMBRA FileLife.
PID format: PID-{NAMESPACE}-{ROLE}-{REGION}-{YEAR}-{HASHFRAG}
"""
import hashlib
import os
from datetime import datetime, timezone


def generate_pid(
    namespace: str = "MBR",
    role: str = "OWNER",
    region: str = "US",
    year: int = None,
    seed: str = None,
) -> str:
    """
    Generate a privacy-preserving identifier.

    Format: PID-{NAMESPACE}-{ROLE}-{REGION}-{YEAR}-{HASHFRAG}
    """
    if year is None:
        year = datetime.now(timezone.utc).year

    if seed:
        seed_bytes = seed.encode("utf-8")
    else:
        seed_bytes = os.urandom(16)

    hash_frag = hashlib.sha256(seed_bytes).hexdigest()[:6].upper()
    pid = f"PID-{namespace.upper()}-{role.upper()}-{region.upper()}-{year}-{hash_frag}"
    return pid


def hash_pid(pid: str) -> str:
    """
    Hash a PID for storage/reference without exposing identity.
    Returns sha256: prefixed hex digest.
    """
    digest = hashlib.sha256(pid.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
