# Smart Contract Specification — Membra Money Protocol

**Last updated:** 2026-05-15
**Status:** DEVNET / RESEARCH PREVIEW ONLY
**Program ID:** `EXNLzDxRPN81NtxZKzNBKweG93R9FWUq8gfGoFGzxYYw`
**Anchor Framework:** 0.29.0
**Solana Version:** 1.17.0

## 1. Program Overview

The Membra Money protocol is an Anchor-based Solana program for Bitcoin-denominated bearer-note style claims. It manages:
- Protocol state (pause toggle, authority, counters)
- Bearer notes (mint, transfer, claim, redeem)
- Reserve attestations (illustrative only on devnet)

## 2. Account Schemas

### 2.1 ProtocolState

```rust
pub struct ProtocolState {
    pub is_initialized: bool,         // 1 byte
    pub authority: Pubkey,          // 32 bytes
    pub total_notes_minted: u64,    // 8 bytes
    pub reserve_attestation: Pubkey, // 32 bytes (optional, Pubkey::default if none)
    pub last_attestation_at: i64,     // 8 bytes (unix timestamp)
    pub reserve_ratio_bps: u16,     // 2 bytes (basis points, 10000 = 100%)
    pub total_value_locked: u64,    // 8 bytes (satoshis)
    pub pause_authority: Pubkey,    // 32 bytes
    pub paused: bool,               // 1 byte
}

// Total: 1 + 32 + 8 + 32 + 8 + 2 + 8 + 32 + 1 = 124 bytes
// With padding/alignment: 154 bytes
pub const SIZE: usize = 154;
```

**PDA Derivation:**
```
seeds = ["protocol_state"]
bump = u8
```

### 2.2 Note

```rust
pub struct Note {
    pub id: u64,                    // 8 bytes (monotonically increasing)
    pub issuer: Pubkey,             // 32 bytes
    pub current_holder: Pubkey,     // 32 bytes
    pub claim_hash: [u8; 32],      // 32 bytes (SHA256 of "pin:salt")
    pub denomination: u64,          // 8 bytes (satoshis)
    pub created_at: i64,            // 8 bytes (unix timestamp)
    pub expires_at: i64,            // 8 bytes (unix timestamp)
    pub is_claimed: bool,           // 1 byte
    pub claimed_by: Pubkey,         // 32 bytes (Pubkey::default if unclaimed)
    pub is_redeemed: bool,         // 1 byte
    pub bump: u8,                   // 1 byte
}

// Total: 8 + 32 + 32 + 32 + 8 + 8 + 8 + 1 + 32 + 1 + 1 = 163 bytes
// With padding/alignment: 194 bytes
pub const SIZE: usize = 194;
```

**PDA Derivation:**
```
seeds = ["note", note_id.to_le_bytes().as_ref()]
bump = u8
```

### 2.3 ReserveAttestation

```rust
pub struct ReserveAttestation {
    pub authority: Pubkey,          // 32 bytes
    pub reserve_ratio_bps: u16,   // 2 bytes
    pub attested_at: i64,           // 8 bytes
    pub attestation_hash: [u8; 32], // 32 bytes
    pub bump: u8,                   // 1 byte
}

// Total: 32 + 2 + 8 + 32 + 1 = 75 bytes
pub const SIZE: usize = 75;
```

**PDA Derivation:**
```
seeds = ["reserve", protocol_state.key().as_ref()]
bump = u8
```

## 3. Instruction Set

### 3.1 initialize

Initializes the global ProtocolState account. Can only be called once.

**Accounts:**
| # | Name | Type | Constraints |
|---|------|------|-------------|
| 1 | `protocol_state` | `Account<ProtocolState>` | `init`, `payer = authority`, `space = 8 + ProtocolState::SIZE` |
| 2 | `authority` | `Signer` | Pays for account creation |
| 3 | `system_program` | `Program<System>` | Required for `init` |

**Arguments:** None

**Effects:**
- Sets `is_initialized = true`
- Sets `authority = signer`
- Sets `pause_authority = signer`
- Sets `paused = false`
- Sets counters to 0

**Errors:** None (Anchor `init` constraints enforce uniqueness)

---

### 3.2 mint_note

Mints a new bearer note denominated in satoshis.

**Accounts:**
| # | Name | Type | Constraints |
|---|------|------|-------------|
| 1 | `protocol_state` | `Account<ProtocolState>` | `has_one = authority`, `mut` |
| 2 | `note` | `Account<Note>` | `init`, `payer = authority`, `space = 8 + Note::SIZE` |
| 3 | `holder` | `AccountInfo` | The initial holder of the note |
| 4 | `authority` | `Signer` | Must match `protocol_state.authority` |
| 5 | `system_program` | `Program<System>` | Required for `init` |

**Arguments:**
```rust
pub struct MintNoteArgs {
    pub note_id: u64,
    pub denomination: u64,        // >= MIN_DENOMINATION (1)
    pub claim_hash: [u8; 32],    // SHA256 of "pin:salt"
    pub expires_at: i64,         // <= now + MAX_EXPIRY_SECONDS (90 days)
}
```

**Guards:**
- `!protocol_state.paused`
- `denomination >= MIN_DENOMINATION`
- `expires_at <= now + MAX_EXPIRY_SECONDS`
- `expires_at > now`

**Effects:**
- Creates Note account with given parameters
- Increments `protocol_state.total_notes_minted`
- Adds `denomination` to `protocol_state.total_value_locked`

**Errors:**
- `ProtocolPaused` (6000)
- `InvalidAmount` (6001)

---

### 3.3 transfer_note

Transfers an unexpired, unredeemed note to a new holder.

**Accounts:**
| # | Name | Type | Constraints |
|---|------|------|-------------|
| 1 | `note` | `Account<Note>` | `mut`, `has_one = current_holder` |
| 2 | `current_holder` | `Signer` | Must match `note.current_holder` |
| 3 | `new_holder` | `AccountInfo` | The recipient |

**Arguments:** None

**Guards:**
- `!note.is_claimed`
- `!note.is_redeemed`
- `now < note.expires_at`
- `current_holder.is_signer`

**Effects:**
- Sets `note.current_holder = new_holder`

**Errors:**
- `NoteExpired` (6003)
- `AlreadyRedeemed` (6004)
- `Unauthorized` (6005)

---

### 3.4 claim_note

Claims a note by providing the correct PIN preimage.

**Accounts:**
| # | Name | Type | Constraints |
|---|------|------|-------------|
| 1 | `note` | `Account<Note>` | `mut` |
| 2 | `claimant` | `Signer` | The claimer |

**Arguments:**
```rust
pub struct ClaimNoteArgs {
    pub pin: String,  // The preimage that hashes to claim_hash
}
```

**Guards:**
- `!note.is_claimed`
- `!note.is_redeemed`
- `now < note.expires_at`
- `SHA256("pin:salt") == note.claim_hash`

**Effects:**
- Sets `note.is_claimed = true`
- Sets `note.claimed_by = claimant`
- Sets `note.current_holder = claimant`

**Errors:**
- `InvalidClaim` (6002)
- `NoteExpired` (6003)
- `AlreadyRedeemed` (6004)

---

### 3.5 redeem_note

Redeems a note back to the issuer, returning rent.

**Accounts:**
| # | Name | Type | Constraints |
|---|------|------|-------------|
| 1 | `note` | `Account<Note>` | `mut`, `has_one = current_holder` |
| 2 | `current_holder` | `Signer` | Must match `note.current_holder` |
| 3 | `authority` | `Signer` | Protocol authority (for closing account) |

**Arguments:** None

**Guards:**
- `!note.is_redeemed`
- `now < note.expires_at`
- `current_holder.is_signer`

**Effects:**
- Sets `note.is_redeemed = true`
- Transfers account lamports to `current_holder` (rent refund)
- Decrements `protocol_state.total_value_locked`

**Errors:**
- `NoteExpired` (6003)
- `AlreadyRedeemed` (6004)
- `Unauthorized` (6005)

---

### 3.6 attest_reserve

Creates or updates the reserve attestation (authority only).

**Accounts:**
| # | Name | Type | Constraints |
|---|------|------|-------------|
| 1 | `protocol_state` | `Account<ProtocolState>` | `mut`, `has_one = authority` |
| 2 | `reserve_attestation` | `Account<ReserveAttestation>` | `init` or `mut` |
| 3 | `authority` | `Signer` | Must match `protocol_state.authority` |
| 4 | `system_program` | `Program<System>` | Required for `init` |

**Arguments:**
```rust
pub struct AttestReserveArgs {
    pub reserve_ratio_bps: u16,      // 0-10000
    pub attestation_hash: [u8; 32], // SHA256 of external proof
}
```

**Guards:**
- `authority.is_signer`
- `reserve_ratio_bps <= 10000`

**Effects:**
- Creates/updates `ReserveAttestation` account
- Updates `protocol_state.reserve_ratio_bps`
- Updates `protocol_state.last_attestation_at`
- Updates `protocol_state.reserve_attestation`

**Errors:**
- `Unauthorized` (6005)
- `ReserveTooLow` (6006)

---

### 3.7 toggle_pause

Pauses or unpauses the protocol (pause authority only).

**Accounts:**
| # | Name | Type | Constraints |
|---|------|------|-------------|
| 1 | `protocol_state` | `Account<ProtocolState>` | `mut`, `has_one = pause_authority` |
| 2 | `pause_authority` | `Signer` | Must match `protocol_state.pause_authority` |

**Arguments:** None

**Guards:**
- `pause_authority.is_signer`

**Effects:**
- Flips `protocol_state.paused`

**Errors:**
- `Unauthorized` (6005)

## 4. Error Codes

| Code | Value | Message | Trigger |
|------|-------|---------|---------|
| `ProtocolPaused` | 6000 | "Protocol is currently paused" | Any mutating instruction when `paused == true` |
| `InvalidAmount` | 6001 | "Invalid amount or parameter" | `denomination < 1` or `denomination > supply` |
| `InvalidClaim` | 6002 | "Invalid claim preimage" | PIN hash mismatch |
| `NoteExpired` | 6003 | "Note has expired" | `now > expires_at` |
| `AlreadyRedeemed` | 6004 | "Note already redeemed" | `is_redeemed == true` |
| `Unauthorized` | 6005 | "Unauthorized action" | Wrong signer |
| `ReserveTooLow` | 6006 | "Reserve ratio too low or invalid" | `reserve_ratio_bps > 10000` |

## 5. Constants

```rust
pub const MAX_EXPIRY_SECONDS: i64 = 90 * 24 * 60 * 60; // 7,776,000 seconds (90 days)
pub const MIN_DENOMINATION: u64 = 1; // 1 satoshi
```

## 6. Security Considerations

### 6.1 Brute-Force Protection
- Claim hash uses SHA256 with a random salt
- PIN verification happens off-chain in the backend
- On-chain, the `claim_hash` is compared directly
- Backend rate-limits claim attempts (5 per hour per claim)

### 6.2 Authority Model
- `authority`: Can mint notes, attest reserves, upgrade program
- `pause_authority`: Can pause/unpause protocol (separable from authority)
- Both default to the deployer wallet

### 6.3 Rent and Account Closure
- Notes are closed on redemption, returning rent to holder
- ProtocolState and ReserveAttestation are permanent

### 6.4 Front-Running
- No on-chain value transfer (SOL or tokens)
- Only state changes, so front-running is low-risk
- In production with real value, consider commit-reveal patterns

## 7. Upgrade Path

- Upgrade authority is the deployer wallet
- Program is deployed as `UpgradeableLoader` BPF
- To upgrade: `solana program deploy <new.so> --program-id <PROGRAM_ID>`

## 8. Testing

### 8.1 Unit Tests (Rust)
```bash
cd /Users/alep/Downloads/membramoney-protocol
cargo test --lib
```

Current coverage:
- Program ID consistency
- Constant boundaries
- Account size calculations
- Error code enumeration
- Expiry calculations
- Claim hash uniqueness
- Pubkey parsing

### 8.2 Integration Tests (TypeScript)
```bash
cd /Users/alep/Downloads/membramoney-protocol
anchor test
```

**Note:** `anchor test` is currently blocked by `cargo-build-sbf` edition 2024 incompatibility. Use `cargo test --lib` for now.

## 9. Known Limitations

1. **No real BTC custody**: Reserve attestation is illustrative only
2. **No multi-sig**: Single authority controls protocol
3. **No timelock**: Pause can be toggled instantly
4. **No automatic expiry cleanup**: Expired notes remain on-chain until redeemed/closed
5. **No batch operations**: Each note requires individual transaction

## 10. Production Hardening Required

Before mainnet deployment:
1. External security audit
2. Multi-sig or DAO governance for authority
3. Timelock on pause/unpause
4. Automated expiry cleanup mechanism
5. Batch mint/transfer operations
6. Comprehensive fuzz testing
7. Formal verification of critical invariants
