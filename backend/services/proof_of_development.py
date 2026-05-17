"""
Proof-of-Development Service — CI/CD hooks → governance proposals.

A push alone does not adjust MEMBRA supply.
Verified, tested, community-approved development may unlock capped developer
or ecosystem emissions.

Flow:
  push code → tests pass → security scan passes → community reviews
  → governance approves → Proof-of-Development is logged
  → capped supply adjustment executes
"""

import hashlib
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class Phase(str, Enum):
    PUSH = "push"
    TESTS = "tests"
    SECURITY = "security_scan"
    REVIEW = "community_review"
    GOVERNANCE = "governance"
    EXECUTED = "executed"
    REJECTED = "rejected"


@dataclass
class DevProof:
    proof_id: str
    commit_sha: str
    branch: str = ""
    author: str = ""
    message: str = ""
    phase: Phase = Phase.PUSH
    tests_passed: bool = False
    tests_total: int = 0
    tests_failed: int = 0
    security_clean: bool = False
    security_criticals: int = 0
    community_votes: int = 0
    community_required: int = 3
    governance_approved: bool = False
    governance_tx: str = ""
    emission_amount: int = 0
    emission_cap: int = 10_000
    created_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    completed_at: Optional[float] = None
    proof_hash: str = ""


class ProofOfDevelopmentService:
    """Tracks development lifecycle from push to capped emission."""

    def __init__(self, community_required: int = 3, emission_cap: int = 10_000):
        self.community_required = community_required
        self.emission_cap = emission_cap
        self._proofs: Dict[str, DevProof] = {}
        self._votes: Dict[str, set] = defaultdict(set)
        self._events: List[Dict[str, Any]] = []

    # -- Phase 1: Push --------------------------------------------------

    def record_push(
        self, commit_sha: str, branch: str, author: str, message: str
    ) -> Dict[str, Any]:
        proof_id = str(uuid.uuid4())
        proof = DevProof(
            proof_id=proof_id, commit_sha=commit_sha,
            branch=branch, author=author, message=message,
            emission_cap=self.emission_cap,
        )
        self._proofs[proof_id] = proof
        self._log("push_recorded", {"proof_id": proof_id, "commit_sha": commit_sha})
        return {"proof_id": proof_id, "phase": Phase.PUSH.value,
                "message": "Push recorded. Awaiting tests."}

    # -- Phase 2: Tests -------------------------------------------------

    def record_tests(
        self, proof_id: str, total: int, passed: int, failed: int,
        logs_url: str = ""
    ) -> Dict[str, Any]:
        proof = self._get_proof(proof_id)
        proof.tests_total = total
        proof.tests_failed = failed
        proof.tests_passed = (failed == 0)

        if proof.tests_passed:
            proof.phase = Phase.TESTS
            msg = "Tests passed. Awaiting security scan."
        else:
            proof.phase = Phase.REJECTED
            proof.completed_at = datetime.now(timezone.utc).timestamp()
            msg = f"Tests FAILED ({failed}/{total}). Proof rejected."

        self._log("tests_recorded", {"proof_id": proof_id, "passed": proof.tests_passed})
        return {"proof_id": proof_id, "phase": proof.phase.value, "message": msg}

    # -- Phase 3: Security Scan -----------------------------------------

    def record_security(
        self, proof_id: str, criticals: int = 0, highs: int = 0,
        report_url: str = ""
    ) -> Dict[str, Any]:
        proof = self._get_proof(proof_id)
        if proof.phase != Phase.TESTS:
            raise ValueError(f"Expected phase=tests, got {proof.phase}")

        proof.security_criticals = criticals
        proof.security_clean = (criticals == 0)

        if proof.security_clean:
            proof.phase = Phase.SECURITY
            msg = f"Security scan clean. Awaiting community review ({self.community_required} votes needed)."
        else:
            proof.phase = Phase.REJECTED
            proof.completed_at = datetime.now(timezone.utc).timestamp()
            msg = f"Security scan found {criticals} criticals. Proof rejected."

        self._log("security_recorded", {"proof_id": proof_id, "criticals": criticals})
        return {"proof_id": proof_id, "phase": proof.phase.value, "message": msg}

    # -- Phase 4: Community Review --------------------------------------

    def cast_vote(self, proof_id: str, voter: str, approve: bool = True) -> Dict[str, Any]:
        proof = self._get_proof(proof_id)
        if proof.phase not in (Phase.SECURITY, Phase.REVIEW):
            raise ValueError(f"Cannot vote in phase {proof.phase}")

        if approve:
            self._votes[proof_id].add(voter)
        else:
            self._votes[proof_id].discard(voter)

        proof.community_votes = len(self._votes[proof_id])
        proof.phase = Phase.REVIEW

        if proof.community_votes >= proof.community_required:
            proof.phase = Phase.GOVERNANCE
            msg = f"Community approved ({proof.community_votes}/{proof.community_required}). Awaiting governance."
        else:
            msg = f"Vote recorded ({proof.community_votes}/{proof.community_required})."

        self._log("vote_cast", {"proof_id": proof_id, "voter": voter, "approve": approve})
        return {"proof_id": proof_id, "phase": proof.phase.value,
                "votes": proof.community_votes, "required": proof.community_required,
                "message": msg}

    # -- Phase 5: Governance --------------------------------------------

    def approve_governance(
        self, proof_id: str, emission_amount: int, governance_tx: str = ""
    ) -> Dict[str, Any]:
        proof = self._get_proof(proof_id)
        if proof.phase != Phase.GOVERNANCE:
            raise ValueError(f"Expected phase=governance, got {proof.phase}")
        if emission_amount > proof.emission_cap:
            raise ValueError(f"Emission {emission_amount} exceeds cap {proof.emission_cap}")

        proof.governance_approved = True
        proof.governance_tx = governance_tx
        proof.emission_amount = emission_amount
        proof.phase = Phase.EXECUTED
        proof.completed_at = datetime.now(timezone.utc).timestamp()
        proof.proof_hash = hashlib.sha256(
            f"{proof.proof_id}:{proof.commit_sha}:{emission_amount}:{proof.completed_at}".encode()
        ).hexdigest()

        self._log("governance_approved", {
            "proof_id": proof_id, "emission_amount": emission_amount,
            "governance_tx": governance_tx, "proof_hash": proof.proof_hash,
        })
        return {
            "proof_id": proof_id, "phase": Phase.EXECUTED.value,
            "emission_amount": emission_amount, "proof_hash": proof.proof_hash,
            "message": f"Proof-of-Development executed. {emission_amount} MEMBRA emission authorized.",
        }

    def reject_governance(self, proof_id: str, reason: str = "") -> Dict[str, Any]:
        proof = self._get_proof(proof_id)
        proof.phase = Phase.REJECTED
        proof.completed_at = datetime.now(timezone.utc).timestamp()
        self._log("governance_rejected", {"proof_id": proof_id, "reason": reason})
        return {"proof_id": proof_id, "phase": Phase.REJECTED.value, "reason": reason}

    # -- Queries --------------------------------------------------------

    def get_proof(self, proof_id: str) -> Optional[Dict[str, Any]]:
        p = self._proofs.get(proof_id)
        if not p:
            return None
        return {
            "proof_id": p.proof_id, "commit_sha": p.commit_sha,
            "branch": p.branch, "author": p.author, "phase": p.phase.value,
            "tests_passed": p.tests_passed, "security_clean": p.security_clean,
            "community_votes": p.community_votes,
            "community_required": p.community_required,
            "governance_approved": p.governance_approved,
            "emission_amount": p.emission_amount,
            "proof_hash": p.proof_hash,
            "created_at": p.created_at, "completed_at": p.completed_at,
        }

    def list_proofs(self, phase: Optional[str] = None) -> List[Dict[str, Any]]:
        proofs = list(self._proofs.values())
        if phase:
            proofs = [p for p in proofs if p.phase.value == phase]
        return [self.get_proof(p.proof_id) for p in sorted(proofs, key=lambda x: x.created_at)]

    def get_stats(self) -> Dict[str, Any]:
        proofs = list(self._proofs.values())
        return {
            "total_proofs": len(proofs),
            "executed": sum(1 for p in proofs if p.phase == Phase.EXECUTED),
            "rejected": sum(1 for p in proofs if p.phase == Phase.REJECTED),
            "pending": sum(1 for p in proofs if p.phase not in (Phase.EXECUTED, Phase.REJECTED)),
            "total_emissions_authorized": sum(p.emission_amount for p in proofs if p.phase == Phase.EXECUTED),
        }

    # -- Internal -------------------------------------------------------

    def _get_proof(self, proof_id: str) -> DevProof:
        p = self._proofs.get(proof_id)
        if not p:
            raise ValueError("Proof not found")
        return p

    def _log(self, event_type: str, data: Dict[str, Any]) -> None:
        self._events.append({
            "event_id": str(uuid.uuid4()), "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).timestamp(), "data": data,
        })

    def get_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self._events[-limit:]
