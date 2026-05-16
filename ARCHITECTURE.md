# Architecture — Membra Money Protocol

**Last updated:** 2026-05-15
**Status:** DEVNET / RESEARCH PREVIEW ONLY
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
