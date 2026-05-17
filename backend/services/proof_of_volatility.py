"""
Proof-of-Volatility Oracle — MEMBRA's internal policy-consensus signal.

Verifies real market volatility, liquidity depth, Solana gas-fee conditions,
oracle freshness, and treasury coverage before allowing capped, auditable,
governance-gated tokenomic actions.

Cannot: create SOL, guarantee price, manufacture volatility, bypass governance,
or mint unlimited MEMBRA.
"""

import hashlib
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class TWAPSnapshot:
    """A single TWAP data point for an asset or gas fee."""
    asset: str
    price: float
    timestamp: float
    source: str


@dataclass
class VolatilityWindow:
    """Rolling window of TWAP snapshots for volatility calculation."""
    asset: str
    max_samples: int = 100
    samples: deque = field(default_factory=deque)

    def push(self, snapshot: TWAPSnapshot) -> None:
        self.samples.append(snapshot)
        while len(self.samples) > self.max_samples:
            self.samples.popleft()

    @property
    def twap(self) -> Optional[float]:
        if not self.samples:
            return None
        return sum(s.price for s in self.samples) / len(self.samples)

    @property
    def stddev(self) -> Optional[float]:
        if len(self.samples) < 2:
            return None
        mean = self.twap
        variance = sum((s.price - mean) ** 2 for s in self.samples) / len(self.samples)
        return variance ** 0.5

    @property
    def volatility_ratio(self) -> Optional[float]:
        """Coefficient of variation: stddev / mean."""
        mean = self.twap
        sd = self.stddev
        if mean is None or sd is None or mean == 0:
            return None
        return sd / mean

    @property
    def latest(self) -> Optional[TWAPSnapshot]:
        return self.samples[-1] if self.samples else None

    @property
    def age_seconds(self) -> Optional[float]:
        latest = self.latest
        if latest is None:
            return None
        return datetime.now(timezone.utc).timestamp() - latest.timestamp


@dataclass
class PolicyGate:
    """A single policy gate controlled by Proof-of-Volatility."""
    action: str
    unlocked: bool = False
    required_signals: List[str] = field(default_factory=list)
    last_evaluated_at: Optional[float] = None
    reason: str = ""


# ---------------------------------------------------------------------------
# Proof-of-Volatility Service
# ---------------------------------------------------------------------------


class ProofOfVolatilityService:
    """
    Tracks TWAP feeds, detects volatility, and manages policy gates.

    Watched assets:
      - MEMBRA/USDC TWAP
      - SOL/USDC TWAP (for gas-fee context)
      - Solana gas-fee TWAP (lamports per signature)

    Policy gates unlocked by PoV:
      - rebase_execution
      - rebase_pause
      - capped_emission_proposal
      - gasvault_adjustment
      - reward_rate_adjustment
      - treasury_risk_alert
    """

    # Thresholds (configurable)
    DEFAULT_MAX_ORACLE_AGE_SECONDS = 300       # 5 minutes
    DEFAULT_VOLATILITY_HIGH_THRESHOLD = 0.05    # 5% CV triggers high-volatility
    DEFAULT_VOLATILITY_LOW_THRESHOLD = 0.01     # 1% CV = low volatility
    DEFAULT_MIN_LIQUIDITY_DEPTH_USD = 10_000    # minimum liquidity for gates
    DEFAULT_MIN_TREASURY_COVERAGE_BPS = 10_000  # 100% coverage required

    # All known policy gates
    POLICY_ACTIONS = [
        "rebase_execution",
        "rebase_pause",
        "capped_emission_proposal",
        "gasvault_adjustment",
        "reward_rate_adjustment",
        "treasury_risk_alert",
    ]

    def __init__(
        self,
        max_oracle_age_seconds: float = DEFAULT_MAX_ORACLE_AGE_SECONDS,
        volatility_high_threshold: float = DEFAULT_VOLATILITY_HIGH_THRESHOLD,
        volatility_low_threshold: float = DEFAULT_VOLATILITY_LOW_THRESHOLD,
        min_liquidity_depth_usd: float = DEFAULT_MIN_LIQUIDITY_DEPTH_USD,
        min_treasury_coverage_bps: int = DEFAULT_MIN_TREASURY_COVERAGE_BPS,
    ):
        self.max_oracle_age = max_oracle_age_seconds
        self.vol_high = volatility_high_threshold
        self.vol_low = volatility_low_threshold
        self.min_liquidity = min_liquidity_depth_usd
        self.min_coverage = min_treasury_coverage_bps

        # TWAP windows
        self._membra_window = VolatilityWindow(asset="MEMBRA/USDC")
        self._sol_window = VolatilityWindow(asset="SOL/USDC")
        self._gas_window = VolatilityWindow(asset="SOL_GAS_FEE")

        # External data (updated by oracle feeds)
        self._liquidity_depth_usd: float = 0.0
        self._treasury_coverage_bps: int = 0
        self._gasvault_coverage_ratio: float = 0.0

        # Policy gates
        self._gates: Dict[str, PolicyGate] = {
            action: PolicyGate(action=action) for action in self.POLICY_ACTIONS
        }

        # Proof log
        self._proofs: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Oracle feed ingestion
    # ------------------------------------------------------------------

    def feed_membra_twap(self, price: float, source: str = "oracle") -> TWAPSnapshot:
        snap = TWAPSnapshot(
            asset="MEMBRA/USDC",
            price=price,
            timestamp=datetime.now(timezone.utc).timestamp(),
            source=source,
        )
        self._membra_window.push(snap)
        self._evaluate_gates()
        return snap

    def feed_sol_twap(self, price: float, source: str = "oracle") -> TWAPSnapshot:
        snap = TWAPSnapshot(
            asset="SOL/USDC",
            price=price,
            timestamp=datetime.now(timezone.utc).timestamp(),
            source=source,
        )
        self._sol_window.push(snap)
        self._evaluate_gates()
        return snap

    def feed_gas_fee(self, lamports_per_sig: float, source: str = "rpc") -> TWAPSnapshot:
        snap = TWAPSnapshot(
            asset="SOL_GAS_FEE",
            price=lamports_per_sig,
            timestamp=datetime.now(timezone.utc).timestamp(),
            source=source,
        )
        self._gas_window.push(snap)
        self._evaluate_gates()
        return snap

    def update_liquidity_depth(self, usd_value: float) -> None:
        self._liquidity_depth_usd = usd_value
        self._evaluate_gates()

    def update_treasury_coverage(self, coverage_bps: int) -> None:
        self._treasury_coverage_bps = coverage_bps
        self._evaluate_gates()

    def update_gasvault_coverage(self, ratio: float) -> None:
        self._gasvault_coverage_ratio = ratio
        self._evaluate_gates()

    # ------------------------------------------------------------------
    # Oracle freshness
    # ------------------------------------------------------------------

    @property
    def membra_oracle_fresh(self) -> bool:
        age = self._membra_window.age_seconds
        return age is not None and age <= self.max_oracle_age

    @property
    def sol_oracle_fresh(self) -> bool:
        age = self._sol_window.age_seconds
        return age is not None and age <= self.max_oracle_age

    @property
    def gas_oracle_fresh(self) -> bool:
        age = self._gas_window.age_seconds
        return age is not None and age <= self.max_oracle_age

    @property
    def all_oracles_fresh(self) -> bool:
        return self.membra_oracle_fresh and self.sol_oracle_fresh and self.gas_oracle_fresh

    # ------------------------------------------------------------------
    # Volatility classification
    # ------------------------------------------------------------------

    @property
    def membra_volatility_ratio(self) -> Optional[float]:
        return self._membra_window.volatility_ratio

    @property
    def sol_volatility_ratio(self) -> Optional[float]:
        return self._sol_window.volatility_ratio

    @property
    def gas_volatility_ratio(self) -> Optional[float]:
        return self._gas_window.volatility_ratio

    def volatility_state(self) -> str:
        """Returns: 'high', 'normal', 'low', or 'unknown'."""
        vr = self.membra_volatility_ratio
        if vr is None:
            return "unknown"
        if vr >= self.vol_high:
            return "high"
        if vr <= self.vol_low:
            return "low"
        return "normal"

    # ------------------------------------------------------------------
    # Liquidity & coverage checks
    # ------------------------------------------------------------------

    @property
    def liquidity_sufficient(self) -> bool:
        return self._liquidity_depth_usd >= self.min_liquidity

    @property
    def treasury_coverage_sufficient(self) -> bool:
        return self._treasury_coverage_bps >= self.min_coverage

    @property
    def gasvault_coverage_sufficient(self) -> bool:
        return self._gasvault_coverage_ratio >= 1.0

    # ------------------------------------------------------------------
    # Policy gate evaluation
    # ------------------------------------------------------------------

    def _evaluate_gates(self) -> None:
        """Re-evaluate all policy gates based on current signals."""
        now = datetime.now(timezone.utc).timestamp()
        fresh = self.all_oracles_fresh
        vol = self.volatility_state()
        liq = self.liquidity_sufficient
        cov = self.treasury_coverage_sufficient
        gcov = self.gasvault_coverage_sufficient

        # Base requirements for any gate to unlock
        base_ok = fresh and liq and cov

        gate_rules = {
            "rebase_execution": base_ok and vol in ("high", "normal"),
            "rebase_pause": True,  # can always pause
            "capped_emission_proposal": base_ok and vol == "normal",
            "gasvault_adjustment": base_ok and gcov,
            "reward_rate_adjustment": base_ok and vol in ("normal", "low"),
            "treasury_risk_alert": not cov or not fresh or vol == "high",
        }

        for action, unlocked in gate_rules.items():
            gate = self._gates[action]
            gate.unlocked = unlocked
            gate.last_evaluated_at = now
            gate.reason = self._build_reason(action, unlocked, fresh, vol, liq, cov, gcov)

    def _build_reason(
        self, action: str, unlocked: bool, fresh: bool, vol: str,
        liq: bool, cov: bool, gcov: bool
    ) -> str:
        reasons = []
        if not fresh:
            reasons.append("oracles stale")
        if not liq:
            reasons.append("liquidity insufficient")
        if not cov:
            reasons.append("treasury under-collateralized")
        if not gcov and action == "gasvault_adjustment":
            reasons.append("GasVault coverage insufficient")
        if vol == "high" and action in ("capped_emission_proposal", "reward_rate_adjustment"):
            reasons.append("volatility too high")
        if vol == "unknown":
            reasons.append("volatility unknown")
        if not reasons:
            return "all signals nominal"
        return "unlocked" if unlocked else f"blocked: {', '.join(reasons)}"

    # ------------------------------------------------------------------
    # Gate queries
    # ------------------------------------------------------------------

    def is_unlocked(self, action: str) -> bool:
        gate = self._gates.get(action)
        return gate.unlocked if gate else False

    def get_gate(self, action: str) -> Optional[PolicyGate]:
        return self._gates.get(action)

    def get_all_gates(self) -> Dict[str, Dict[str, Any]]:
        return {
            action: {
                "unlocked": gate.unlocked,
                "reason": gate.reason,
                "last_evaluated_at": gate.last_evaluated_at,
            }
            for action, gate in self._gates.items()
        }

    # ------------------------------------------------------------------
    # Proof logging
    # ------------------------------------------------------------------

    def log_proof(
        self, action: str, approved: bool, metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        proof = {
            "proof_id": str(uuid.uuid4()),
            "proof_type": "proof_of_volatility",
            "action": action,
            "approved": approved,
            "volatility_state": self.volatility_state(),
            "membra_twap": self._membra_window.twap,
            "sol_twap": self._sol_window.twap,
            "gas_fee_twap": self._gas_window.twap,
            "oracles_fresh": self.all_oracles_fresh,
            "liquidity_depth_usd": self._liquidity_depth_usd,
            "treasury_coverage_bps": self._treasury_coverage_bps,
            "gasvault_coverage_ratio": self._gasvault_coverage_ratio,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).timestamp(),
            "proof_hash": hashlib.sha256(
                f"{action}:{approved}:{datetime.now(timezone.utc).timestamp()}".encode()
            ).hexdigest(),
        }
        self._proofs.append(proof)
        return proof

    def get_proofs(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._proofs[-limit:]

    # ------------------------------------------------------------------
    # Full state snapshot
    # ------------------------------------------------------------------

    def get_state(self) -> Dict[str, Any]:
        return {
            "membra": {
                "twap": self._membra_window.twap,
                "stddev": self._membra_window.stddev,
                "volatility_ratio": self.membra_volatility_ratio,
                "samples": len(self._membra_window.samples),
                "age_seconds": self._membra_window.age_seconds,
                "fresh": self.membra_oracle_fresh,
            },
            "sol": {
                "twap": self._sol_window.twap,
                "stddev": self._sol_window.stddev,
                "volatility_ratio": self.sol_volatility_ratio,
                "samples": len(self._sol_window.samples),
                "age_seconds": self._sol_window.age_seconds,
                "fresh": self.sol_oracle_fresh,
            },
            "gas": {
                "twap": self._gas_window.twap,
                "stddev": self._gas_window.stddev,
                "volatility_ratio": self.gas_volatility_ratio,
                "samples": len(self._gas_window.samples),
                "age_seconds": self._gas_window.age_seconds,
                "fresh": self.gas_oracle_fresh,
            },
            "volatility_state": self.volatility_state(),
            "liquidity_depth_usd": self._liquidity_depth_usd,
            "liquidity_sufficient": self.liquidity_sufficient,
            "treasury_coverage_bps": self._treasury_coverage_bps,
            "treasury_coverage_sufficient": self.treasury_coverage_sufficient,
            "gasvault_coverage_ratio": self._gasvault_coverage_ratio,
            "gasvault_coverage_sufficient": self.gasvault_coverage_sufficient,
            "gates": self.get_all_gates(),
        }
