# Architecture — Membra Money Protocol

**Last updated:** 2026-05-16
**Status:** PRODUCTION ENGINEERING CANDIDATE
**Program ID:** `EXNLzDxRPN81NtxZKzNBKweG93R9FWUq8gfGoFGzxYYw`

## Overview

Membra Money is a Solana-based protocol for Bitcoin-denominated bearer-note style claims. It is intentionally simple to minimize attack surface. It does **not** implement real BTC bridges, real custody, or real money settlement. All values are simulated on Solana devnet.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        User Browser                         │
│  ┌─────────────┐ ┌─────────────┐ ┌───────────────────────┐  │
│  │ WalletPanel │ │ MintNoteCard│ │   ClaimNoteCard       │  │
│  └─────────────┘ └─────────────┘ └───────────────────────┘  │
│  ┌─────────────┐ ┌─────────────┐ ┌───────────────────────┐  │
│  │ReserveStatus│ │ RiskDiscl.  │ │   DevnetBanner        │  │
│  └─────────────┘ └─────────────┘ └───────────────────────┘  │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP / JSON
┌─────────────────────────▼───────────────────────────────────┐
│                      FastAPI Backend                        │
│  ┌─────────────┐ ┌─────────────┐ ┌───────────────────────┐  │
│  │  /health    │ │ /api/v1/... │ │  Risk Disclosure      │  │
│  │  /ready     │ │  Claims     │ │  Reserve Metadata     │  │
│  └─────────────┘ └─────────────┘ └───────────────────────┘  │
│  ┌─────────────┐ ┌─────────────┐ ┌───────────────────────┐  │
│  │ Rate Limit  │ │ Audit Log   │ │ Request ID            │  │
│  └─────────────┘ └─────────────┘ └───────────────────────┘  │
└─────────────────────────┬───────────────────────────────────┘
                          │ JSON RPC (devnet)
┌─────────────────────────▼───────────────────────────────────┐
│                Solana Devnet / Anchor Program               │
│  ┌─────────────┐ ┌─────────────┐ ┌───────────────────────┐  │
│  │ ProtocolState│ │   Note     │ │ ReserveAttestation    │  │
│  └─────────────┘ └─────────────┘ └───────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Smart Contract (Anchor / Rust)

**Location:** `programs/membramoney/src/lib.rs`

**Accounts:**
| Account | Size | Purpose |
|---------|------|---------|
| `ProtocolState` | 154 bytes | Global protocol configuration, pause toggle, authority |
| `Note` | 194 bytes | Individual bearer note: denomination, holder, expiry, claim hash, state |
| `ReserveAttestation` | 75 bytes | On-chain reserve metadata (illustrative only) |

**Instructions:**
| Instruction | Accounts | Guards |
|-------------|----------|--------|
| `initialize` | ProtocolState + authority | One-time init |
| `mint_note` | ProtocolState + Note + holder + authority | Protocol not paused, valid denomination, valid expiry |
| `transfer_note` | Note + current_holder + new_holder | Note not expired, not redeemed, sender is holder |
| `claim_note` | Note + claimant | Claim hash matches, not expired, not already claimed |
| `redeem_note` | Note + current_holder + authority | Note not expired, not already redeemed, correct signer |
| `attest_reserve` | ProtocolState + ReserveAttestation + authority | Authority only |
| `toggle_pause` | ProtocolState + authority | Authority only |

**PDAs:**
- `ProtocolState`: seeded by `["protocol_state"]`
- `Note`: seeded by `["note", note_id_u64]`
- `ReserveAttestation`: seeded by `["reserve", protocol_state.key()]`

**Error Codes:**
| Code | Value | Trigger |
|------|-------|---------|
| `ProtocolPaused` | 6000 | Any instruction when paused |
| `InvalidAmount` | 6001 | Denomination < 1 or > supply |
| `InvalidClaim` | 6002 | PIN hash mismatch |
| `NoteExpired` | 6003 | `now > expires_at` |
| `AlreadyRedeemed` | 6004 | Double redemption |
| `Unauthorized` | 6005 | Wrong signer |
| `ReserveTooLow` | 6006 | Reserve attestation below threshold |

### 2. Backend API (FastAPI / Python)

**Location:** `backend/main.py`

**Endpoints:**
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness probe |
| GET | `/ready` | Readiness probe |
| GET | `/api/v1/risk-disclosure` | Returns current risk disclosure text + hash |
| POST | `/api/v1/risk-disclosure/accept` | Records wallet acceptance of risk disclosure |
| POST | `/api/v1/claims/create` | Creates a claim link with PIN (requires risk acceptance) |
| POST | `/api/v1/claims/validate` | Validates claim ID + PIN (brute-force protected) |
| GET | `/api/v1/reserves` | Returns illustrative reserve status |
| GET | `/api/v1/stats` | Returns protocol statistics |
| GET | `/api/v1/audit/events` | Returns audit events |

**Middleware:**
| Middleware | Purpose |
|------------|---------|
| `RequestIDMiddleware` | Injects `X-Request-ID` for request tracing |
| `AuditLoggingMiddleware` | Logs every request to stderr (JSON) |
| `RateLimitMiddleware` | Token-bucket per IP (2 req/s, burst 20) |
| `CORSMiddleware` | CORS (allow all origins in debug mode) |

**In-Memory Stores (devnet only):**
- `_claims`: Map of claim_id → claim metadata
- `_risk_acceptances`: Map of wallet_address → acceptance record
- `_brute_force_tracker`: Map of key → timestamp list
- `_audit_events`: List of audit events

### 3. Frontend (React + TypeScript + Vite)

**Location:** `ui/src/`

**Components:**
| Component | File | Purpose |
|-----------|------|---------|
| `DevnetBanner` | `components/DevnetBanner.tsx` | Persistent devnet warning banner |
| `WalletPanel` | `components/WalletPanel.tsx` | Wallet connection UI (simulated for devnet) |
| `RiskDisclosure` | `components/RiskDisclosure.tsx` | Risk disclosure display + acceptance checkbox |
| `MintNoteCard` | `components/MintNoteCard.tsx` | Note minting form |
| `ClaimNoteCard` | `components/ClaimNoteCard.tsx` | Claim validation form |
| `ReserveStatusCard` | `components/ReserveStatusCard.tsx` | Reserve status display |

**Styling:**
- Neomorphic dark theme via `styles.css`
- CSS variables for colors, shadows, spacing
- Inter + JetBrains Mono fonts
- Responsive breakpoints

**Build:**
- `npm run build` → `dist/` (151 KB JS gzipped, 9.8 KB CSS gzipped)

## Data Flows

### Mint Flow
```
User → UI (MintNoteCard)
  → POST /api/v1/claims/create
    → Check risk acceptance
    → Generate claim_id, PIN, salt
    → Store in _claims
    → Return claim_url + pin_hash
  → UI displays claim link + PIN
```

### Claim Flow
```
Recipient → UI (ClaimNoteCard)
  → POST /api/v1/claims/validate
    → Check brute-force limit
    → Verify PIN hash
    → Mark claim as consumed
    → Return denomination
  → UI displays success + amount
```

### Reserve Attestation Flow
```
Authority → Anchor: attest_reserve(reserve_ratio_bps)
  → On-chain: Update ReserveAttestation account
  → UI (ReserveStatusCard) fetches via GET /api/v1/reserves
    → Backend reads from ReserveService
    → Returns status + ratio + disclaimer
```

## Security Model

### Trust Boundaries
1. **Browser ↔ Backend**: HTTPS (devnet only, no TLS enforced in local dev)
2. **Backend ↔ Solana**: JSON RPC to devnet cluster
3. **On-chain**: Solana BPF runtime + Anchor constraints

### Threats Considered
- Brute-force on claim PINs → Rate limiting + HMAC comparison
- Replay attacks → Claim one-time semantics + expiry
- Front-running → No on-chain value transfer, only state changes
- Authority compromise → Upgrade authority held by deploy wallet

### Not Implemented (Production Blockers)
- Real wallet adapter (Phantom, Solflare)
- KYC / sanctions screening
- Real BTC custody / reserves
- External audit
- PostgreSQL persistence
- Production monitoring / alerting

## Deployment

### Devnet
```bash
cd /Users/alep/Downloads/membramoney-protocol
solana config set --url devnet
anchor deploy --provider.cluster devnet
```

### Local Development
```bash
# Terminal 1: Backend
cd backend
uvicorn main:app --reload --port 8000

# Terminal 2: UI
cd ui
npm run dev

# Terminal 3: Solana local validator
solana-test-validator
```

## Dependencies

### Smart Contract
- `anchor-lang = "0.29.0"`
- `anchor-spl = "0.29.0"`
- Solana CLI 1.17.0+
- Anchor CLI 0.30.1 (CLI) / 0.29.0 (framework)

### Backend
- Python 3.11+
- FastAPI 0.109+
- Pydantic 2.5+
- Uvicorn

### Frontend
- Node.js 20+
- React 18+
- TypeScript 5+
- Vite 5+

## Known Issues

1. **Anchor test blocked**: `cargo-build-sbf` has edition 2024 incompatibility with `constant_time_eq 0.4.2`. Workaround: use `cargo test --lib` instead of `anchor test`.
2. **Buffer accounts**: Three unfunded intermediate buffer accounts were created during failed deploy attempts. Seed phrases exposed — treat as compromised. Reclaim devnet lamports when possible.
3. **In-memory stores**: All backend data is lost on restart. Must migrate to PostgreSQL for production.

## References

- [PRODUCTION_GAPS.md](PRODUCTION_GAPS.md) — 15 P0 blockers and 880-item checklist
- [PREVIEW_STATUS.md](PREVIEW_STATUS.md) — Current devnet status
- [DEVNET_DEPLOYMENT.md](DEVNET_DEPLOYMENT.md) — Deployment procedures
- [SECURITY.md](SECURITY.md) — Security policy

## Production Services (Backend)

### Identity Service (`backend/services/identity_service.py`)
Human-readable usernames as routing aliases. Wallet keys remain cryptographically random.
| Feature | Status |
|---------|--------|
| Username registration | Implemented |
| Receive tag generation | Implemented |
| Username → tag resolution | Implemented |
| Tag rotation | Implemented |
| Device registration | Implemented |
| Device revocation | Implemented |

### Claim-Note Service (`backend/services/claimnote_service.py`)
Full lifecycle for transferable reserve-backed digital claims.
| Operation | Status |
|-----------|--------|
| Create claim | Implemented |
| Transfer claim | Implemented |
| Split claim | Implemented |
| Merge claims | Implemented |
| Burn claim | Implemented |
| Revoke claim | Implemented |
| Nullifier registry | Implemented (in-memory) |
| Replay nonce | Implemented |

### Ledger Service (`backend/services/ledger_service.py`)
ACID event-sourced internal ledger.
| Feature | Status |
|---------|--------|
| Account creation | Implemented |
| Double-entry posting | Implemented |
| Idempotency keys | Implemented |
| Event sourcing | Implemented |
| Optimistic concurrency | Implemented (version field) |
| Snapshots | Implemented |
| Reconciliation | Implemented |

### Treasury Service (`backend/services/treasury_service.py`)
Reserve custody and attestation tracking.
| Feature | Status |
|---------|--------|
| Wallet registration (hot/warm/cold) | Implemented |
| Balance updates | Implemented |
| Reserve total calculation | Implemented |
| Reserve attestation | Implemented |
| Settlement batch tracking | Implemented |

### Settlement Engine (`backend/services/settlement_engine.py`)
Batched blockchain settlement with fee estimation.
| Feature | Status |
|---------|--------|
| Submit settlement request | Implemented |
| Fee estimation | Implemented |
| Batch creation | Implemented |
| Batch approval | Implemented |
| Broadcast tracking | Implemented |
| Confirmation tracking | Implemented |

### Redemption Service (`backend/services/redemption_service.py`)
External redemption flow with fraud and compliance controls.
| Step | Status |
|------|--------|
| Validate claim | Implemented |
| Fraud check | Implemented |
| Compliance check | Implemented |
| Fee quote | Implemented |
| Burn claim | Implemented |
| Submit settlement | Implemented |
| Receipt generation | Implemented |

### Compliance Service (`backend/services/compliance_service.py`)
KYC/AML and sanctions screening scaffolding.
| Feature | Status |
|---------|--------|
| Sanctions screening | Implemented (OFAC placeholder) |
| Risk score calculation | Implemented |
| Quarantine queue | Implemented |
| Quarantine resolution | Implemented |

### Security Service (`backend/services/security_service.py`)
Behavioral fraud detection and anomaly monitoring.
| Feature | Status |
|---------|--------|
| Transaction velocity tracking | Implemented |
| Velocity limits (1h/24h) | Implemented |
| Anomaly detection | Implemented |
| Alert generation | Implemented |

## Test Coverage

| Suite | Tests | Status |
|-------|-------|--------|
| Backend integration | 48 | Passing |
| Production services | 11 | Passing |
| **Total** | **59** | **All passing** |

## Remaining Work to Production

1. **Database persistence**: Migrate in-memory stores to PostgreSQL with SQLAlchemy ORM
2. **Rust smart contracts**: Expand to full production claim-note model on Solana
3. **Frontend UX**: Update React app for username-based send/receive, QR codes, NFC
4. **Wallet integration**: Real Phantom/Solflare adapter with transaction signing
5. **MPC/Threshold signing**: Replace single-key treasury with multi-party computation
6. **External APIs**: Integrate sanctions screening (OFAC), KYC providers (SumSub, Onfido)
7. **Observability**: Prometheus metrics, Grafana dashboards, structured logging
8. **DevOps**: Terraform/CDK for infrastructure, GitHub Actions CI/CD with proper token scopes
9. **Legal/compliance**: Terms of service, privacy policy, regulatory registrations
10. **Security audit**: External penetration test, smart contract audit, SOC2 readiness
