# Production Gaps — Membra Money Protocol

**Current Status:** DEVNET / RESEARCH PREVIEW ONLY
**Program ID:** `EXNLzDxRPN81NtxZKzNBKweG93R9FWUq8gfGoFGzxYYw` (devnet)
**Last Updated:** 2026-05-15

## Classification

- [x] DEVNET / RESEARCH PREVIEW
- [ ] TESTNET CANDIDATE
- [ ] MAINNET PRODUCTION

## Hard Blockers (P0 — Do Not Launch)

| # | Item | Status |
|---|------|--------|
| 1 | Legal classification memo (MSB, stored value, prepaid access, securities) | NOT STARTED |
| 2 | AML/sanctions compliance program | NOT STARTED |
| 3 | Real BTC custody architecture (non-custodial, custodial, or hybrid) | NOT STARTED |
| 4 | Audited proof-of-reserves system with liability matching | NOT STARTED |
| 5 | External smart contract audit | NOT STARTED |
| 6 | Production redemption backend with operational controls | NOT STARTED |
| 7 | HSM/MPC key management for treasury | NOT STARTED |
| 8 | Production treasury controls (dual approval, multi-sig, segregation) | NOT STARTED |
| 9 | Compliance operations (KYC, screening, monitoring, SAR filing) | NOT STARTED |
| 10 | Production incident response plan (tested, staffed, on-call) | NOT STARTED |
| 11 | External penetration test (backend, frontend, cloud, contract) | NOT STARTED |
| 12 | Mainnet go-live approval (legal, compliance, security, board) | NOT STARTED |
| 13 | Terms of Service, Privacy Policy, Risk Disclosure, Custody Agreement | NOT STARTED |
| 14 | Sanctions screening integration (OFAC, chainalysis) | NOT STARTED |
| 15 | Real wallet adapter integration (Phantom, Solflare, Backpack) | NOT STARTED |

## Completed Devnet Items

| # | Item | Status |
|---|------|--------|
| 1 | Anchor program written and compiled | COMPLETE |
| 2 | Devnet deployment successful | COMPLETE |
| 3 | Backend API scaffold (FastAPI, routes, models) | COMPLETE |
| 4 | Neomorphic dark UI (React + TypeScript) | COMPLETE |
| 5 | Pre-flight check script | COMPLETE |
| 6 | Backend unit tests (pytest) | COMPLETE |
| 7 | Docker + deployment configs | COMPLETE |
| 8 | Documentation (README, SECURITY, DEVNET_DEPLOYMENT, MAINNET_READINESS) | COMPLETE |
| 9 | UI production build (dist/ generated) | COMPLETE |

## Known Issues

1. **Anchor test blocked**: `Cargo.lock` version 4 incompatibility with `cargo-build-sbf v4.0.0`. Workaround: use `--no-idl` flag for builds.
2. **Buffer accounts**: Three unfunded intermediate buffer accounts were created during failed deploy attempts. Seed phrases exposed in terminal/chat — treat as compromised. Reclaim devnet lamports when possible.
3. **GitHub token**: Previously exposed token was rotated and replaced.
4. **In-memory backend**: Current backend uses in-memory stores for devnet. Must migrate to PostgreSQL for production.

## Next Steps Toward Production

1. **Legal review**: Engage counsel for product classification, jurisdiction map, MSB determination.
2. **Compliance program**: Design AML/sanctions workflow, KYC policy, screening integration.
3. **Custody architecture**: Decide non-custodial vs custodial, select HSM/MPC vendor, design key ceremony.
4. **Smart contract audit**: Freeze instruction set, engage external auditor, fix findings, re-review.
5. **Reserve system**: Design liability tracking, Merkle tree proof, reconciliation, attestation.
6. **Backend hardening**: PostgreSQL migration, rate limiting, auth, audit logging, idempotency.
7. **Frontend hardening**: Real wallet adapters, transaction previews, error states, accessibility.
8. **Infrastructure**: Production cloud account, IaC, CI/CD, monitoring, alerting, incident response.
9. **Security engineering**: Threat model, penetration test, dependency scanning, bug bounty.
10. **QA**: E2E tests, load tests, chaos tests, contract invariant tests.

## Disclaimer

This repository is a **research preview** and **devnet candidate only**. It is **not production-ready financial infrastructure**. No real funds, no real BTC custody, no real redemption, and no production solvency claims should be made until all P0 blockers are closed and independently reviewed.
