# Custody Architecture Decision — Membra Money Protocol

> **Status:** DESIGN DRAFT — requires legal, compliance, and security review.
> P0 blocker #3 from PRODUCTION_GAPS.md.
>
> Last updated: 2026-05-17

---

## Decision Required

The protocol must choose a custody model before mainnet launch. The three options
are analysed below. **Recommendation: Non-custodial with optional instant-liquidity bridge.**

---

## Option A — Non-Custodial (Recommended for launch)

Notes are denominated in satoshis but backed by on-chain collateral (SOL, USDC,
or a wrapped BTC such as cbBTC or tBTC). The protocol never holds user BTC.

```
User deposits USDC/cbBTC → Protocol mints BTC-denominated note
User redeems note       → Protocol releases USDC/cbBTC at spot rate
```

**Advantages:**
- No BTC custody risk; no money-transmitter treatment for BTC custody.
- Collateral is verifiable on-chain at any time (proof-of-reserves is automatic).
- Simpler regulatory posture (similar to on-chain stablecoin).
- No HSM/MPC required for BTC key management.

**Disadvantages:**
- Redemption value fluctuates with collateral price (not a fixed BTC peg).
- Requires an oracle (Pyth, Switchboard) for BTC/USDC price.
- Users receive economic exposure to BTC, not BTC itself.

**Implementation path:**
1. Accept cbBTC or tBTC deposits via a Solana SPL token account.
2. Mint notes denominated in sats at deposit time (lock rate at mint).
3. On redemption, release the locked collateral back to the user.
4. Reserve attestation = SPL token balance of the collateral vault.

**Required before launch:**
- Legal opinion: does collateral-backed note constitute a security?
- Choose oracle provider and set staleness threshold.
- Set maximum note denomination (to bound oracle manipulation risk).
- Audit collateral vault program.

---

## Option B — Custodial (Higher regulatory complexity)

The protocol holds real BTC in a custodial wallet and issues notes redeemable 1:1.

```
User sends BTC to deposit address → Protocol mints BTC-denominated note
User redeems note                → Protocol sends BTC to user's BTC address
```

**Advantages:**
- True 1:1 BTC peg; no collateral price risk.
- Familiar model (similar to Tether/USDT for BTC).

**Disadvantages:**
- Requires MSB / money-transmitter licence in most U.S. states.
- Requires HSM/MPC for BTC key management.
- Requires custodial insurance.
- Proof-of-reserves requires attestation of BTC balance.
- Regulatory burden is 10× higher than Option A.

**Not recommended for initial launch.**

---

## Option C — Hybrid (Non-custodial notes + optional BTC bridge)

Launch with Option A (non-custodial). After regulatory clarity, add a BTC
Lightning bridge for instant BTC in/out.

```
Phase 1: USDC/cbBTC collateral (non-custodial)
Phase 2: Lightning bridge for sub-second BTC redemption
Phase 3: Optional L1 BTC custody for large redemptions
```

**Recommended long-term path.**

---

## If Proceeding with Option A (Non-Custodial)

### Collateral Vault Architecture

```
┌─────────────────────────────────────────────┐
│           Collateral Vault Program           │
│  (Anchor PDA — controlled by protocol auth) │
│                                             │
│  ┌──────────┐   ┌──────────┐               │
│  │ cbBTC    │   │  USDC    │               │
│  │ SPL acct │   │ SPL acct │               │
│  └──────────┘   └──────────┘               │
└─────────────────────────────────────────────┘
         ↑ deposit              ↓ redeem
┌──────────────────┐   ┌──────────────────────┐
│   User Wallet    │   │  Note Account (PDA)  │
│  (Phantom/       │   │  denomination_sats   │
│   Solflare)      │   │  locked_collateral   │
└──────────────────┘   └──────────────────────┘
```

### Reserve Attestation (Automatic)

The existing `ReserveAttestation` on-chain account is updated by the protocol
after every deposit and redemption. Because collateral is SPL tokens on Solana,
the reserve ratio is verifiable without a custodian attestation:

```
reserve_ratio_bps = (vault_token_balance / total_outstanding_notes) * 10_000
```

This can be computed permissionlessly by anyone reading Solana account state.

### Oracle Integration (Pyth)

```rust
// In MintNote instruction — add oracle price check
let price_feed = &ctx.accounts.btc_usd_price_feed;
let price = pyth_sdk_solana::load_price_feed_from_account_info(price_feed)?;
let btc_usd = price.get_price_unchecked();
require!(btc_usd.conf < MAX_PRICE_CONFIDENCE, ErrorCode::OraclePriceUncertain);
```

### Multi-Sig Vault Control (Squads Protocol)

The vault's upgrade authority and withdrawal authority must be held by a
multi-signature wallet (recommended: Squads v4).

```bash
# Transfer upgrade authority to Squads multisig after deployment
solana program set-upgrade-authority <program-id> \
  --new-upgrade-authority <squads-multisig-pubkey>
```

Require M-of-N signatures (recommended: 3-of-5) for:
- Vault withdrawals above threshold
- Program upgrades
- Emergency pause

---

## Key Management (HSM/MPC) — Required for Option B

If Option B (custodial) is chosen, BTC private keys must be managed by:

1. **HSM (Hardware Security Module)**: Thales Luna, AWS CloudHSM, Azure Dedicated HSM.
   - FIPS 140-2 Level 3 minimum.
   - Key ceremony with M-of-N shamir shares.
   - Offline backup with geographic distribution.

2. **MPC (Multi-Party Computation)**: Fireblocks, Copper, Fordefi, ZenGo.
   - No single point of key exposure.
   - Threshold signing without assembling the full key.
   - Audit trail for every signing event.

**Vendor selection requires legal and compliance sign-off.**

---

## Next Steps

- [ ] Legal opinion on collateral-backed note classification
- [ ] Select oracle provider (Pyth recommended)
- [ ] Select collateral token (cbBTC or tBTC — assess counterparty risk)
- [ ] Design collateral vault Anchor program
- [ ] Audit vault program (separate from main protocol audit)
- [ ] Set up Squads multi-sig for vault authority
- [ ] Document key ceremony procedure
