# Data Flow — Membra Money Protocol

**Last updated:** 2026-05-15
**Status:** DEVNET / RESEARCH PREVIEW ONLY

## 1. Mint Note Flow

```
┌────────┐     POST /api/v1/claims/create     ┌──────────┐
│ User   │ ──────────────────────────────────> │ Backend  │
│ Browser│  { wallet, denomination, expiry }  │ FastAPI  │
└────────┘                                    └──────────┘
     │                                            │
     │                                            │ Check risk acceptance
     │                                            │ (in-memory lookup)
     │                                            │
     │                                            │ Generate: claim_id, PIN, salt
     │                                            │ Hash PIN with pepper
     │                                            │ Store claim metadata
     │                                            │
     │     { claim_id, claim_url, pin_hash }      │
     │ <──────────────────────────────────────────│
     │
     │   (User copies claim link + PIN)
     │
     │   Optionally: Anchor on-chain mint_note
     │   (currently simulated on devnet)
```

**Data Stored:**
```json
{
  "claim_id": "uuid",
  "issuer_wallet": "CFvvtu...StL",
  "denomination_sats": 1000000,
  "pin_hash": "sha256(PIN:salt:pepper)",
  "salt": "uuid",
  "expires_at": 1700000000,
  "claimed": false,
  "claimant_wallet": null,
  "created_at": 1700000000
}
```

**Validation:**
- Wallet must have accepted risk disclosure
- Denomination ≥ 1 satoshi
- Expiry ≥ 1 minute, ≤ 90 days

---

## 2. Claim Note Flow

```
┌────────────┐     POST /api/v1/claims/validate    ┌──────────┐
│ Recipient  │ ───────────────────────────────────> │ Backend  │
│ Browser    │  { claim_id, pin, claimant_wallet } │ FastAPI  │
└────────────┘                                      └──────────┘
     │                                                  │
     │                                                  │ Check brute-force tracker
     │                                                  │ (per claim_id + wallet)
     │                                                  │
     │                                                  │ Look up claim metadata
     │                                                  │ Verify not expired
     │                                                  │ Verify not already claimed
     │                                                  │ HMAC compare PIN hash
     │                                                  │
     │      { valid, claim_id, denomination_sats }      │
     │ <──────────────────────────────────────────────────│
     │
     │   (Recipient now has claim to note)
     │
     │   Optionally: Anchor on-chain claim_note
     │   (currently simulated on devnet)
```

**Data Mutations:**
```json
{
  "claimed": true,
  "claimant_wallet": "recipient...pubkey"
}
```

**Validation:**
- Claim must exist
- Not already claimed
- Not expired
- PIN hash must match (HMAC compare_digest)
- Brute-force attempts ≤ 5 per hour per claim + wallet

---

## 3. Redeem Note Flow

```
┌────────────┐     Anchor: redeem_note()     ┌──────────────┐
│ Current    │ ────────────────────────────> │ Solana       │
│ Holder     │  { note_pda, authority_sig } │ Devnet       │
└────────────┘                                └──────────────┘
     │                                              │
     │                                              │ Verify note exists
     │                                              │ Verify not expired
     │                                              │ Verify not already redeemed
     │                                              │ Verify signer == current_holder
     │                                              │
     │     Transaction success: note marked        │
     │     redeemed, lamports returned             │
     │ <────────────────────────────────────────────│
```

**On-Chain State Changes:**
- `note.redeemed = true`
- Account lamports returned to holder (rent refund)

---

## 4. Reserve Attestation Flow

```
┌──────────┐     Anchor: attest_reserve()    ┌──────────────┐
│ Authority│ ────────────────────────────────> │ Solana       │
│ Wallet   │  { reserve_ratio_bps }           │ Devnet       │
└──────────┘                                   └──────────────┘
     │                                              │
     │                                              │ Verify signer == protocol authority
     │                                              │ Create/Update ReserveAttestation PDA
     │                                              │
     │ <────────────────────────────────────────────│
     │
     │   (Reserve status now on-chain)
     │
     │   GET /api/v1/reserves
     │   Backend reads ReserveService
     │   Returns: { status, ratio, disclaimer }
```

**On-Chain Data:**
```rust
ReserveAttestation {
    authority: Pubkey,           // 32 bytes
    reserve_ratio_bps: u16,    // 2 bytes (basis points, e.g. 10000 = 100%)
    attested_at: i64,            // 8 bytes (unix timestamp)
    attestation_hash: [u8; 32],  // 32 bytes (SHA256 of external proof)
    bump: u8,                    // 1 byte (PDA bump)
}
```

**Important:** Reserve attestation is **illustrative only**. No real BTC custody or reserve backing exists on devnet.

---

## 5. Risk Disclosure Acceptance Flow

```
┌────────┐     GET /api/v1/risk-disclosure    ┌──────────┐
│ User   │ ────────────────────────────────>  │ Backend  │
│ Browser│                                    │ FastAPI  │
└────────┘                                    └──────────┘
     │                                             │
     │    { version, text, hash }                  │
     │ <───────────────────────────────────────────│
     │
     │   (User reads risk disclosure)
     │
     │   POST /api/v1/risk-disclosure/accept
     │   { wallet_address, accepted_version, signature }
     │
     │ ─────────────────────────────────────────────>│
     │                                               │ Verify version matches current
     │                                               │ Store acceptance in-memory
     │                                               │ Add audit event
     │                                               │
     │    { accepted, wallet, accepted_at, version }  │
     │ <─────────────────────────────────────────────│
```

**Data Stored:**
```json
{
  "wallet_address": "CFvvtu...StL",
  "accepted_version": "v1.0.0",
  "accepted_at": "2026-05-15T10:00:00Z"
}
```

---

## 6. Audit Event Flow

```
Every API mutation → Audit Event

POST /api/v1/claims/create       → audit: "claim_created"
POST /api/v1/claims/validate     → audit: "claim_validated"
POST /api/v1/risk-disclosure/accept → audit: "risk_disclosure_accepted"

Stored in _audit_events (in-memory, devnet only)
GET /api/v1/audit/events returns last N events
```

**Audit Event Schema:**
```json
{
  "event_id": "uuid",
  "event_type": "claim_created",
  "timestamp": "2026-05-15T10:00:00Z",
  "details": {
    "claim_id": "...",
    "issuer": "wallet...",
    "denomination_sats": 1000000
  }
}
```

---

## 7. Protocol Pause Flow

```
┌──────────┐     Anchor: toggle_pause()     ┌──────────────┐
│ Authority│ ──────────────────────────────> │ Solana       │
│ Wallet   │                                │ Devnet       │
└──────────┘                                └──────────────┘
     │                                            │
     │                                            │ Verify signer == protocol authority
     │                                            │ Flip ProtocolState.paused boolean
     │                                            │
     │ <──────────────────────────────────────────│
     │
     │   (All mutating instructions now fail with ProtocolPaused)
```

---

## Data Retention

| Data | Location | Persistence | Retention |
|------|----------|-------------|-----------|
| Claims | Backend `_claims` | In-memory (devnet) | Lost on restart |
| Risk Acceptances | Backend `_risk_acceptances` | In-memory (devnet) | Lost on restart |
| Audit Events | Backend `_audit_events` | In-memory (devnet) | Lost on restart |
| Notes | Solana on-chain | Permanent (until closed/redeemed) | Forever |
| Protocol State | Solana on-chain | Permanent | Forever |
| Reserve Attestation | Solana on-chain | Overwritten on new attestation | Latest only |

**Production Requirement:** Migrate in-memory stores to PostgreSQL with proper retention policies.
