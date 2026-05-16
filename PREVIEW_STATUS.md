# Preview / Devnet Status — Membra Money Protocol

**Last updated:** 2026-05-15
**Classification:** DEVNET / RESEARCH PREVIEW ONLY

## What Works Today

| Component | Status | Details |
|-----------|--------|---------|
| Anchor program | Deployed to devnet | `EXNLzDxRPN81NtxZKzNBKweG93R9FWUq8gfGoFGzxYYw` |
| Program size | 502,384 bytes | Slot 462,659,832 |
| Program instructions | 7 instructions | `initialize`, `mint_note`, `transfer_note`, `claim_note`, `redeem_note`, `attest_reserve`, `toggle_pause` |
| Backend API | Scaffold complete | FastAPI with health, ready, risk disclosure, claims, reserves |
| Backend tests | Passing | 9/9 pytest tests |
| UI | Production build ready | Neomorphic dark theme, React + TypeScript, `dist/` generated |
| Pre-flight checks | Passing | 17/17 checks |
| `cargo test --lib` | Passing | 24 passed, 0 failed |
| Rust tests | Passing | Boundary, edge case, negative tests |
| Backend middleware | Added | Request ID, audit logging, rate limiting |
| Idempotency keys | Added | Claim creation deduplication |
| Documentation | Complete | ARCHITECTURE, DATA_FLOW, SMART_CONTRACT_SPEC, THREAT_MODEL |

## Devnet Program Details

- **Program ID:** `EXNLzDxRPN81NtxZKzNBKweG93R9FWUq8gfGoFGzxYYw`
- **Upgrade Authority:** `CFvvtuX8JMia5MY4m3tkjJ6uG45Xwbm7swS7qgDXsStL`
- **ProgramData Address:** `GsC31JfPhYEbgj8bwN8ov6RZFnUhCHezWk2s7vCkCBpf`
- **Last Deployed Slot:** 462,659,832
- **Balance:** 3.49779672 SOL

## Known Limitations

1. **No real wallet integration** — UI uses simulated wallet for devnet.
2. **No real BTC custody** — All values are simulated on devnet.
3. **No real redemption** — Redemption is a protocol instruction, not backed by operational BTC treasury.
4. **In-memory backend** — Claims and risk acceptance are stored in memory, not PostgreSQL.
5. **No sanctions screening** — No OFAC, chain-analysis, or KYC integration.
6. **No external audit** — Smart contract has not been reviewed by an external auditor.
7. **No reserve attestation oracle** — Reserve status is illustrative only.
8. **Anchor test blocked** — `cargo-build-sbf` has edition 2024 incompatibility; use `cargo test --lib` instead.

## How to Verify

```bash
cd /Users/alep/Downloads/membramoney-protocol
solana config set --url devnet
solana program show EXNLzDxRPN81NtxZKzNBKweG93R9FWUq8gfGoFGzxYYw
bash scripts/pre_flight_check.sh
cd ui && npm run build
```

## What Does NOT Work (Production Blockers)

See [PRODUCTION_GAPS.md](PRODUCTION_GAPS.md) for the full 15 P0 blockers and 880-item checklist.

## Disclaimer

This is experimental software. Do not use with real funds. Do not present as production-ready financial infrastructure. All claims, notes, and reserves are simulated on Solana devnet.
