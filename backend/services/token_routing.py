"""
Token Routing Service — verified adapters and chain registry.

Routes across approved assets through verified adapters.
Does NOT claim automatic support for every coin.

Components:
  - chain registry
  - token registry
  - route engine
  - bridge adapters
  - relayers
  - liquidity checks
  - ProofBook logs
"""

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class Chain(str, Enum):
    SOLANA = "solana"
    ETHEREUM = "ethereum"
    ARBITRUM = "arbitrum"
    BASE = "base"
    POLYGON = "polygon"


class RouteStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    DEPRECATED = "deprecated"
    PENDING_VERIFICATION = "pending_verification"


@dataclass
class ChainEntry:
    chain: Chain
    name: str
    chain_id: int
    rpc_url: str = ""
    explorer_url: str = ""
    is_enabled: bool = True


@dataclass
class TokenEntry:
    token_id: str
    symbol: str
    name: str
    chain: Chain
    address: str
    decimals: int = 9
    is_verified: bool = False
    min_route_amount: float = 0.0
    max_route_amount: float = float("inf")


@dataclass
class BridgeAdapter:
    adapter_id: str
    name: str
    source_chain: Chain
    dest_chain: Chain
    is_verified: bool = False
    is_enabled: bool = False
    fee_bps: int = 0  # basis points
    max_transfer_usd: float = 0.0
    avg_time_seconds: int = 0


@dataclass
class Route:
    route_id: str
    source_chain: Chain
    dest_chain: Chain
    source_token: str
    dest_token: str
    adapter_id: str
    status: RouteStatus = RouteStatus.PENDING_VERIFICATION
    min_amount: float = 0.0
    max_amount: float = float("inf")
    estimated_fee_bps: int = 0


@dataclass
class RouteProof:
    proof_id: str
    route_id: str
    tx_hash: str
    source_amount: float
    dest_amount: float
    fee_paid: float
    timestamp: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    proof_hash: str = ""


# ---------------------------------------------------------------------------
# Token Routing Service
# ---------------------------------------------------------------------------


class TokenRoutingService:
    """
    Universal token routing through verified adapters.

    Supported route types (approved only):
      - Solana SPL → Solana SPL
      - Solana SPL → ERC-20
      - ERC-20 → SPL
      - MEMBRA → USDC
      - SOL → USDC on another chain
    """

    # Default chain registry
    DEFAULT_CHAINS = {
        Chain.SOLANA: ChainEntry(
            chain=Chain.SOLANA, name="Solana", chain_id=101,
            rpc_url="https://api.devnet.solana.com",
            explorer_url="https://explorer.solana.com/?cluster=devnet",
        ),
        Chain.ETHEREUM: ChainEntry(
            chain=Chain.ETHEREUM, name="Ethereum", chain_id=1,
            explorer_url="https://etherscan.io",
        ),
        Chain.ARBITRUM: ChainEntry(
            chain=Chain.ARBITRUM, name="Arbitrum", chain_id=42161,
            explorer_url="https://arbiscan.io",
        ),
        Chain.BASE: ChainEntry(
            chain=Chain.BASE, name="Base", chain_id=8453,
            explorer_url="https://basescan.org",
        ),
        Chain.POLYGON: ChainEntry(
            chain=Chain.POLYGON, name="Polygon", chain_id=137,
            explorer_url="https://polygonscan.com",
        ),
    }

    def __init__(self):
        # Registries
        self._chains: Dict[Chain, ChainEntry] = dict(self.DEFAULT_CHAINS)
        self._tokens: Dict[str, TokenEntry] = {}
        self._adapters: Dict[str, BridgeAdapter] = {}
        self._routes: Dict[str, Route] = {}

        # ProofBook
        self._proofs: List[RouteProof] = []

        # Audit log
        self._events: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Chain registry
    # ------------------------------------------------------------------

    def get_chain(self, chain: Chain) -> Optional[Dict[str, Any]]:
        c = self._chains.get(chain)
        if not c:
            return None
        return {
            "chain": c.chain.value, "name": c.name, "chain_id": c.chain_id,
            "rpc_url": c.rpc_url, "explorer_url": c.explorer_url,
            "is_enabled": c.is_enabled,
        }

    def list_chains(self) -> List[Dict[str, Any]]:
        return [self.get_chain(c) for c in self._chains if self._chains[c].is_enabled]

    def enable_chain(self, chain: Chain) -> Dict[str, Any]:
        c = self._chains.get(chain)
        if not c:
            raise ValueError(f"Unknown chain: {chain}")
        c.is_enabled = True
        self._log("chain_enabled", {"chain": chain.value})
        return self.get_chain(chain)

    def disable_chain(self, chain: Chain) -> Dict[str, Any]:
        c = self._chains.get(chain)
        if not c:
            raise ValueError(f"Unknown chain: {chain}")
        c.is_enabled = False
        self._log("chain_disabled", {"chain": chain.value})
        return self.get_chain(chain)

    # ------------------------------------------------------------------
    # Token registry
    # ------------------------------------------------------------------

    def register_token(
        self, symbol: str, name: str, chain: Chain, address: str,
        decimals: int = 9, min_route: float = 0.0, max_route: float = float("inf"),
        verified: bool = False,
    ) -> Dict[str, Any]:
        token_id = f"{chain.value}:{address}"
        if token_id in self._tokens:
            raise ValueError(f"Token already registered: {token_id}")

        token = TokenEntry(
            token_id=token_id, symbol=symbol, name=name, chain=chain,
            address=address, decimals=decimals, is_verified=verified,
            min_route_amount=min_route, max_route_amount=max_route,
        )
        self._tokens[token_id] = token
        self._log("token_registered", {"token_id": token_id, "symbol": symbol, "chain": chain.value})
        return self._token_to_dict(token)

    def verify_token(self, token_id: str) -> Dict[str, Any]:
        token = self._get_token(token_id)
        token.is_verified = True
        self._log("token_verified", {"token_id": token_id})
        return self._token_to_dict(token)

    def get_token(self, token_id: str) -> Optional[Dict[str, Any]]:
        t = self._tokens.get(token_id)
        return self._token_to_dict(t) if t else None

    def list_tokens(self, chain: Optional[Chain] = None, verified_only: bool = False) -> List[Dict[str, Any]]:
        tokens = list(self._tokens.values())
        if chain:
            tokens = [t for t in tokens if t.chain == chain]
        if verified_only:
            tokens = [t for t in tokens if t.is_verified]
        return [self._token_to_dict(t) for t in tokens]

    def _token_to_dict(self, t: TokenEntry) -> Dict[str, Any]:
        return {
            "token_id": t.token_id, "symbol": t.symbol, "name": t.name,
            "chain": t.chain.value, "address": t.address, "decimals": t.decimals,
            "is_verified": t.is_verified,
            "min_route_amount": t.min_route_amount,
            "max_route_amount": t.max_route_amount,
        }

    # ------------------------------------------------------------------
    # Bridge adapters
    # ------------------------------------------------------------------

    def register_adapter(
        self, name: str, source_chain: Chain, dest_chain: Chain,
        fee_bps: int = 0, max_transfer_usd: float = 0.0,
        avg_time_seconds: int = 0, verified: bool = False,
    ) -> Dict[str, Any]:
        adapter_id = str(uuid.uuid4())
        adapter = BridgeAdapter(
            adapter_id=adapter_id, name=name,
            source_chain=source_chain, dest_chain=dest_chain,
            fee_bps=fee_bps, max_transfer_usd=max_transfer_usd,
            avg_time_seconds=avg_time_seconds, is_verified=verified,
        )
        self._adapters[adapter_id] = adapter
        self._log("adapter_registered", {
            "adapter_id": adapter_id, "name": name,
            "source": source_chain.value, "dest": dest_chain.value,
        })
        return self._adapter_to_dict(adapter)

    def verify_adapter(self, adapter_id: str) -> Dict[str, Any]:
        a = self._get_adapter(adapter_id)
        a.is_verified = True
        a.is_enabled = True
        self._log("adapter_verified", {"adapter_id": adapter_id})
        return self._adapter_to_dict(a)

    def enable_adapter(self, adapter_id: str) -> Dict[str, Any]:
        a = self._get_adapter(adapter_id)
        if not a.is_verified:
            raise ValueError("Adapter must be verified before enabling")
        a.is_enabled = True
        self._log("adapter_enabled", {"adapter_id": adapter_id})
        return self._adapter_to_dict(a)

    def disable_adapter(self, adapter_id: str) -> Dict[str, Any]:
        a = self._get_adapter(adapter_id)
        a.is_enabled = False
        self._log("adapter_disabled", {"adapter_id": adapter_id})
        return self._adapter_to_dict(a)

    def get_adapter(self, adapter_id: str) -> Optional[Dict[str, Any]]:
        a = self._adapters.get(adapter_id)
        return self._adapter_to_dict(a) if a else None

    def list_adapters(self, verified_only: bool = False) -> List[Dict[str, Any]]:
        adapters = list(self._adapters.values())
        if verified_only:
            adapters = [a for a in adapters if a.is_verified]
        return [self._adapter_to_dict(a) for a in adapters]

    def _adapter_to_dict(self, a: BridgeAdapter) -> Dict[str, Any]:
        return {
            "adapter_id": a.adapter_id, "name": a.name,
            "source_chain": a.source_chain.value, "dest_chain": a.dest_chain.value,
            "is_verified": a.is_verified, "is_enabled": a.is_enabled,
            "fee_bps": a.fee_bps, "max_transfer_usd": a.max_transfer_usd,
            "avg_time_seconds": a.avg_time_seconds,
        }

    # ------------------------------------------------------------------
    # Route engine
    # ------------------------------------------------------------------

    def create_route(
        self, source_token: str, dest_token: str, adapter_id: str,
        min_amount: float = 0.0, max_amount: float = float("inf"),
    ) -> Dict[str, Any]:
        src = self._get_token(source_token)
        dst = self._get_token(dest_token)
        adapter = self._get_adapter(adapter_id)

        if not adapter.is_verified:
            raise ValueError("Adapter not verified")
        if adapter.source_chain != src.chain:
            raise ValueError(f"Adapter source chain mismatch: {adapter.source_chain} vs {src.chain}")
        if adapter.dest_chain != dst.chain:
            raise ValueError(f"Adapter dest chain mismatch: {adapter.dest_chain} vs {dst.chain}")

        route_id = str(uuid.uuid4())
        route = Route(
            route_id=route_id,
            source_chain=src.chain, dest_chain=dst.chain,
            source_token=source_token, dest_token=dest_token,
            adapter_id=adapter_id,
            min_amount=min_amount, max_amount=max_amount,
            estimated_fee_bps=adapter.fee_bps,
        )
        self._routes[route_id] = route
        self._log("route_created", {
            "route_id": route_id, "source_token": source_token,
            "dest_token": dest_token, "adapter_id": adapter_id,
        })
        return self._route_to_dict(route)

    def verify_route(self, route_id: str) -> Dict[str, Any]:
        route = self._get_route(route_id)
        route.status = RouteStatus.ACTIVE
        self._log("route_verified", {"route_id": route_id})
        return self._route_to_dict(route)

    def pause_route(self, route_id: str) -> Dict[str, Any]:
        route = self._get_route(route_id)
        route.status = RouteStatus.PAUSED
        self._log("route_paused", {"route_id": route_id})
        return self._route_to_dict(route)

    def get_route(self, route_id: str) -> Optional[Dict[str, Any]]:
        r = self._routes.get(route_id)
        return self._route_to_dict(r) if r else None

    def find_routes(
        self, source_chain: Optional[Chain] = None, dest_chain: Optional[Chain] = None,
        source_token: Optional[str] = None, dest_token: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        results = list(self._routes.values())
        if source_chain:
            results = [r for r in results if r.source_chain == source_chain]
        if dest_chain:
            results = [r for r in results if r.dest_chain == dest_chain]
        if source_token:
            results = [r for r in results if r.source_token == source_token]
        if dest_token:
            results = [r for r in results if r.dest_token == dest_token]
        return [self._route_to_dict(r) for r in results if r.status == RouteStatus.ACTIVE]

    def _route_to_dict(self, r: Route) -> Dict[str, Any]:
        return {
            "route_id": r.route_id,
            "source_chain": r.source_chain.value, "dest_chain": r.dest_chain.value,
            "source_token": r.source_token, "dest_token": r.dest_token,
            "adapter_id": r.adapter_id, "status": r.status.value,
            "min_amount": r.min_amount, "max_amount": r.max_amount,
            "estimated_fee_bps": r.estimated_fee_bps,
        }

    # ------------------------------------------------------------------
    # Liquidity checks
    # ------------------------------------------------------------------

    def check_liquidity(self, route_id: str, amount: float) -> Dict[str, Any]:
        route = self._get_route(route_id)
        if route.status != RouteStatus.ACTIVE:
            return {"sufficient": False, "reason": f"Route is {route.status.value}"}
        if amount < route.min_amount:
            return {"sufficient": False, "reason": f"Amount {amount} below min {route.min_amount}"}
        if amount > route.max_amount:
            return {"sufficient": False, "reason": f"Amount {amount} exceeds max {route.max_amount}"}

        adapter = self._get_adapter(route.adapter_id)
        if not adapter.is_enabled:
            return {"sufficient": False, "reason": "Adapter disabled"}

        return {
            "sufficient": True,
            "estimated_fee": amount * (route.estimated_fee_bps / 10_000),
            "adapter": adapter.name,
            "avg_time_seconds": adapter.avg_time_seconds,
        }

    # ------------------------------------------------------------------
    # ProofBook
    # ------------------------------------------------------------------

    def log_route_proof(
        self, route_id: str, tx_hash: str,
        source_amount: float, dest_amount: float, fee_paid: float,
    ) -> Dict[str, Any]:
        proof_id = str(uuid.uuid4())
        proof = RouteProof(
            proof_id=proof_id, route_id=route_id, tx_hash=tx_hash,
            source_amount=source_amount, dest_amount=dest_amount,
            fee_paid=fee_paid,
        )
        proof.proof_hash = hashlib.sha256(
            f"{proof_id}:{route_id}:{tx_hash}:{source_amount}:{dest_amount}:{proof.timestamp}".encode()
        ).hexdigest()
        self._proofs.append(proof)
        self._log("route_proof_logged", {
            "proof_id": proof_id, "route_id": route_id,
            "tx_hash": tx_hash, "proof_hash": proof.proof_hash,
        })
        return {
            "proof_id": proof_id, "route_id": route_id,
            "tx_hash": tx_hash, "source_amount": source_amount,
            "dest_amount": dest_amount, "fee_paid": fee_paid,
            "proof_hash": proof.proof_hash,
        }

    def get_proofs(self, route_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        proofs = self._proofs
        if route_id:
            proofs = [p for p in proofs if p.route_id == route_id]
        return [{
            "proof_id": p.proof_id, "route_id": p.route_id,
            "tx_hash": p.tx_hash, "source_amount": p.source_amount,
            "dest_amount": p.dest_amount, "fee_paid": p.fee_paid,
            "proof_hash": p.proof_hash, "timestamp": p.timestamp,
        } for p in proofs[-limit:]]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        return {
            "chains": len([c for c in self._chains.values() if c.is_enabled]),
            "tokens": len(self._tokens),
            "verified_tokens": sum(1 for t in self._tokens.values() if t.is_verified),
            "adapters": len(self._adapters),
            "verified_adapters": sum(1 for a in self._adapters.values() if a.is_verified),
            "enabled_adapters": sum(1 for a in self._adapters.values() if a.is_enabled),
            "routes": len(self._routes),
            "active_routes": sum(1 for r in self._routes.values() if r.status == RouteStatus.ACTIVE),
            "total_proofs": len(self._proofs),
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_token(self, token_id: str) -> TokenEntry:
        t = self._tokens.get(token_id)
        if not t:
            raise ValueError(f"Token not found: {token_id}")
        return t

    def _get_adapter(self, adapter_id: str) -> BridgeAdapter:
        a = self._adapters.get(adapter_id)
        if not a:
            raise ValueError(f"Adapter not found: {adapter_id}")
        return a

    def _get_route(self, route_id: str) -> Route:
        r = self._routes.get(route_id)
        if not r:
            raise ValueError(f"Route not found: {route_id}")
        return r

    def _log(self, event_type: str, data: Dict[str, Any]) -> None:
        self._events.append({
            "event_id": str(uuid.uuid4()), "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).timestamp(), "data": data,
        })

    def get_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self._events[-limit:]
