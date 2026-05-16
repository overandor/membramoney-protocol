# Threat Model — Membra Money Protocol

**Last updated:** 2026-05-15
**Status:** DEVNET / RESEARCH PREVIEW ONLY
**Classification:** Confidential — Internal Use Only

## 1. System Overview

Membra Money is a Solana-based protocol for Bitcoin-denominated bearer-note style claims. It is experimental, unaudited, and deployed to devnet only. No real BTC custody, real money, or production solvency claims exist.

### 1.1 Trust Boundaries

```
┌─────────────────────────────────────────────────────────────┐
│                    External Threat Actors                    │
│  (Users, Bots, Scanning Tools, DNS Hijackers, Phishers)      │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTPS / JSON
┌─────────────────────────▼───────────────────────────────────┐
│                         Browser / UI                         │
│  (React, Vite, Neomorphic Theme, Local Storage)              │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP / JSON
┌─────────────────────────▼───────────────────────────────────┐
│                      FastAPI Backend                       │
│  (Python, In-Memory Stores, Rate Limiting, Audit Logging)    │
└─────────────────────────┬───────────────────────────────────┘
                          │ JSON RPC (devnet)
┌─────────────────────────▼───────────────────────────────────┐
│                Solana Devnet / Anchor Program                │
│  (BPF, 502KB, Program ID: EXNLzDxRPN81NtxZKzNBKweG93R...)   │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Assets

| Asset | Value | Location | Protection |
|-------|-------|----------|------------|
| Deployer private key | Critical | `~/.config/solana/id.json` | macOS Keychain (if used) |
| Upgrade authority | Critical | On-chain (ProgramData) | Single-key |
| Claim PINs | High | In-memory (`_claims`) | SHA256 + salt + pepper |
| Risk acceptances | Medium | In-memory | None |
| Audit events | Medium | In-memory | None |
| Buffer seed phrases | Low (devnet) | Terminal history / chat | Exposed — compromised |
| GitHub tokens | High | Chat history | Exposed — must rotate |

---

## 2. Threat Actors

### 2.1 External Attackers
- **Script kiddies**: Automated scanners, brute-force bots
- **Phishers**: Fake claim links, wallet spoofing
- **Supply chain**: Malicious npm/cargo dependencies
- **Network attackers**: MITM on unencrypted connections

### 2.2 Insider Threats
- **Deployer wallet compromise**: Single key controls upgrade authority
- **Backend operator**: Can read/modify in-memory claims
- **CI/CD compromise**: Can inject malicious code into builds

### 2.3 Accidental Threats
- **Developer error**: Hardcoded secrets, exposed tokens
- **Misconfiguration**: CORS too permissive, debug mode in production
- **Data loss**: In-memory stores wiped on restart

---

## 3. Attack Surface

### 3.1 Smart Contract (Solana BPF)

| Component | Risk | Controls | Gaps |
|-----------|------|----------|------|
| `initialize` | Low | One-time init | No multi-sig for authority |
| `mint_note` | Medium | Pause toggle, amount checks | No supply cap enforced |
| `transfer_note` | Medium | Holder signature check | No expiration auto-cleanup |
| `claim_note` | **High** | Claim hash, expiry check | Backend brute-force risk |
| `redeem_note` | Medium | Holder + authority check | No timelock |
| `attest_reserve` | Low | Authority check | No oracle integration |
| `toggle_pause` | **High** | Pause authority check | No timelock, no multi-sig |

**Critical Finding:** Upgrade authority is a single key. If compromised, attacker can deploy malicious program.

### 3.2 Backend API (FastAPI)

| Endpoint | Risk | Controls | Gaps |
|----------|------|----------|------|
| `POST /claims/create` | **High** | Risk acceptance check | No idempotency (now fixed) |
| `POST /claims/validate` | **High** | Brute-force tracker | PIN only 8 chars, no lockout escalation |
| `GET /reserves` | Low | None | Returns illustrative data |
| `GET /audit/events` | Low | None | No authentication |
| CORS | Medium | Debug = allow all | Production config missing |

### 3.3 Frontend (React)

| Component | Risk | Controls | Gaps |
|-----------|------|----------|------|
| WalletPanel | **High** | Simulated wallet | No real wallet adapter |
| ClaimNoteCard | Medium | PIN input | No copy-to-clipboard warning |
| MintNoteCard | Low | Form validation | No transaction preview |
| DevnetBanner | Low | Persistent warning | Can be dismissed |
| localStorage | Medium | None | No sensitive data stored |

### 3.4 Infrastructure

| Layer | Risk | Controls | Gaps |
|-------|------|----------|------|
| DNS | Medium | None | No DNSSEC |
| TLS/HTTPS | **High** | None (local dev) | No HSTS, no cert pinning |
| CI/CD | **High** | None | No signed commits, no SLSA |
| Secrets | **High** | .env.example | No secrets manager |
| Database | **High** | None | In-memory only |

---

## 4. Threat Scenarios

### 4.1 Claim Brute-Force (High Likelihood, High Impact)

**Scenario:** Attacker enumerates claim IDs and guesses PINs.

**Path:**
```
Attacker → POST /claims/validate { claim_id: "uuid", pin: "00000000" }
  → Repeat 5x → Rate limit triggered
  → Wait 1 hour → Repeat with new claim_id
```

**Controls:**
- Token-bucket rate limiting per IP (2 req/s, burst 20)
- Brute-force tracker per claim_id + wallet (5 attempts/hour)
- HMAC compare_digest (timing-safe)

**Gaps:**
- PIN entropy: only 8 chars, uppercase alphanumeric = ~2 trillion combinations
- No exponential backoff
- No CAPTCHA
- No account lockout

**Mitigation (Production):**
- Increase PIN to 12+ characters
- Add exponential backoff (1s, 2s, 4s, 8s...)
- Add CAPTCHA after 3 failures
- Send email/SMS alert on brute-force detection
- Implement claim ID entropy: 128-bit minimum

### 4.2 Deployer Key Compromise (Medium Likelihood, Critical Impact)

**Scenario:** Attacker gains access to deployer wallet (`~/.config/solana/id.json`).

**Impact:**
- Deploy malicious program upgrade
- Drain program account
- Steal all claim funds
- Pause protocol permanently

**Controls:**
- macOS Keychain (if used)
- File permissions (600)

**Gaps:**
- No multi-sig
- No hardware wallet requirement
- No key ceremony
- No geographic separation

**Mitigation (Production):**
- Multi-sig governance (3-of-5)
- Hardware wallet (Ledger/Trezor)
- HSM or MPC (Fireblocks, Qredo)
- Key ceremony with legal witnesses
- Geographic key sharding

### 4.3 Claim Link Interception (High Likelihood, Medium Impact)

**Scenario:** Attacker intercepts claim link (email, chat, QR code).

**Path:**
```
Sender → copies claim URL → pastes in Discord
  → Attacker sees URL → clicks before recipient
  → Attacker guesses PIN or uses brute-force
```

**Controls:**
- Claim URL includes claim_id only (no PIN)
- PIN delivered separately (not in URL)

**Gaps:**
- No link expiration (separate from claim expiry)
- No one-time link semantics
- No sender cancel functionality
- No recipient confirmation

**Mitigation (Production):**
- One-time claim links
- Sender cancel endpoint
- Recipient wallet pre-binding
- Out-of-band PIN delivery (SMS, email)

### 4.4 Phishing / Wallet Spoofing (High Likelihood, Medium Impact)

**Scenario:** Attacker creates fake UI at `membramoney-protocol.netlify.app` (typosquatting).

**Impact:**
- Users connect real wallets to fake site
- Fake site drains wallets
- Users accept fake risk disclosures

**Controls:**
- Domain verification in UI
- No real wallet connection yet

**Gaps:**
- No domain allowlist
- No wallet adapter network validation
- No anti-phishing copy

**Mitigation (Production):**
- Register trademark
- Domain monitoring (MarkMonitor)
- Wallet adapter network enforcement
- Anti-phishing banner
- Browser extension verification

### 4.5 Backend Data Tampering (Medium Likelihood, High Impact)

**Scenario:** Attacker gains backend access or exploits in-memory store.

**Impact:**
- Modify claim metadata
- Steal PIN hashes
- Delete audit events
- Forge risk acceptances

**Controls:**
- In-memory only (ephemeral)
- Rate limiting
- Audit logging

**Gaps:**
- No persistence integrity
- No encryption at rest
- No admin action logging
- No database ACLs

**Mitigation (Production):**
- PostgreSQL with row-level security
- Encrypted columns (sensitive data)
- Immutable audit log (append-only, hash-chained)
- Admin action approval workflow
- Database access logging

### 4.6 Supply Chain Attack (Low Likelihood, Critical Impact)

**Scenario:** Malicious npm/crate published with backdoor.

**Path:**
```
Attacker → compromises @coralxyz/anchor maintainer
  → publishes anchor-lang 0.29.1 with keylogger
  → CI pulls new version → builds backdoored UI
```

**Controls:**
- `Cargo.lock` pinned
- `package-lock.json` pinned

**Gaps:**
- No dependency scanning (Snyk, Dependabot)
- No SLSA provenance
- No reproducible builds

**Mitigation (Production):**
- Dependabot alerts
- Snyk/OWASP dependency check
- Vendor security reviews
- SLSA Level 3+ provenance
- Reproducible builds
- SBOM generation

---

## 5. Risk Matrix

| Threat | Likelihood | Impact | Risk | Priority |
|--------|-----------|--------|------|----------|
| Claim brute-force | High | High | **Critical** | P0 |
| Deployer key compromise | Medium | Critical | **Critical** | P0 |
| Claim link interception | High | Medium | **High** | P1 |
| Phishing / spoofing | High | Medium | **High** | P1 |
| Backend data tampering | Medium | High | **High** | P1 |
| Supply chain attack | Low | Critical | **Medium** | P2 |
| DoS / rate limit bypass | Medium | Low | **Medium** | P2 |
| Front-running | Low | Low | **Low** | P3 |

---

## 6. Mitigation Roadmap

### 6.1 Before Any Production Label
- [ ] External smart contract audit (P0)
- [ ] Multi-sig upgrade authority (P0)
- [ ] Real wallet adapter with network validation (P0)
- [ ] PostgreSQL persistence with encryption (P0)
- [ ] CAPTCHA + exponential backoff on claims (P0)
- [ ] Secrets manager (HashiCorp Vault, AWS SM) (P0)
- [ ] Dependency scanning + SBOM (P1)
- [ ] Domain monitoring + anti-phishing (P1)
- [ ] Immutable audit log (P1)
- [ ] Incident response plan (P1)

### 6.2 Before Mainnet Deployment
- [ ] Formal verification of critical invariants (P0)
- [ ] Bug bounty program (P0)
- [ ] Reproducible builds (P0)
- [ ] HSM/MPC key management (P0)
- [ ] Insurance review (P1)
- [ ] Legal classification memo (P0)
- [ ] Compliance program (AML, sanctions) (P0)

---

## 7. Assumptions

1. Solana devnet is not economically secure (free SOL, no real value).
2. Backend is single-instance, no horizontal scaling.
3. No real BTC custody exists — all values are simulated.
4. Users are technical early adopters, not retail consumers.
5. Attackers have standard tooling (curl, Python scripts, browser DevTools).

---

## 8. Out of Scope

- Physical security of developer machines
- Social engineering of individual users
- Solana consensus-layer attacks
- Quantum computing threats
- Nation-state level APT (assumed infinite budget)

---

## 9. Review Schedule

| Trigger | Action |
|---------|--------|
| New major feature | Update threat model |
| External audit | Integrate findings |
| Incident | Post-mortem + model update |
| Quarterly | Scheduled review |
| Pre-mainnet | Full re-assessment |

## 10. References

- [PRODUCTION_GAPS.md](PRODUCTION_GAPS.md) — Production readiness checklist
- [ARCHITECTURE.md](ARCHITECTURE.md) — System architecture
- [DATA_FLOW.md](DATA_FLOW.md) — Data flows
- [SMART_CONTRACT_SPEC.md](SMART_CONTRACT_SPEC.md) — Contract specification
- OWASP ASVS 4.0
- NIST Cybersecurity Framework 2.0
