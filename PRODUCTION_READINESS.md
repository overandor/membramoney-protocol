# Membra Money Protocol — Production Readiness Gate

**Repository:** `overandor/membramoney-protocol`  
**Status:** experimental devnet prototype  
**Release target:** production-safe devnet preview, not mainnet money movement  
**Version:** `0.1.0-devnet`

> **EXPERIMENTAL DEVNET ONLY — NOT REAL MONEY**
>
> This repository must not be described as mainnet-ready, audited, custody-ready, or real-money-ready until all critical gates below are satisfied and independently reviewed.

---

## Executive verdict

The repository has meaningful product scaffolding: FastAPI backend, React UI, Anchor/Solana program, service modules, SDKs, deployment templates, and devnet safety copy.

It is **not production-ready for real funds**.

The correct near-term target is:

**Production-safe devnet demo / investor preview**

That means:

- no real BTC custody,
- no mainnet settlement,
- no real-money claims,
- no private-key handling in application code,
- no investment/profit language,
- strict environment checks,
- reproducible startup,
- health/readiness probes,
- source-controlled release runbook,
- CI guardrails.

---

## Production readiness levels

| Level | Label | Meaning | Current status |
|---|---|---|---:|
| L0 | Concept | README/prototype only | Passed |
| L1 | Devnet demo | Runs locally or on Replit/devnet with clear warnings | Mostly passed |
| L2 | Production-safe preview | Public demo can run without real-money risk | In progress |
| L3 | Staging candidate | Secrets, database, CI, monitoring, rollback, and runbooks verified | Not passed |
| L4 | Mainnet candidate | External audit, legal review, custody model, incident response, and compliance controls | Not passed |
| L5 | Real-money production | Approved release with operational, legal, security, and financial controls | Not passed |

---

## Critical gates before public preview

These gates are enforced or documented by this production-readiness update.

### Safety gates

- [x] Every public page/API description must say **EXPERIMENTAL DEVNET ONLY — NOT REAL MONEY**.
- [x] Mainnet program ID must remain empty unless an explicit audited mainnet release process exists.
- [x] Backend must refuse unsafe production configuration through `backend/core/production_guard.py`.
- [x] Fee sponsoring may only run when explicitly enabled and configured.
- [ ] Wallet signature verification must be real, not placeholder logic.
- [ ] Claim/PIN lifecycle must be backed by durable storage in deployed environments.
- [ ] All real-money, custody, reserve, and redemption claims must remain disabled or clearly illustrative.

### Security gates

- [x] Default placeholder secrets are detected as release blockers.
- [x] `debug=true` is detected as a release blocker in production-like environments.
- [x] Wildcard/empty CORS origin configuration is detected as unsafe for production-like environments.
- [ ] Security headers should be verified in an integration test.
- [ ] Rate limits should use durable shared state in multi-instance deployments.
- [ ] Dependency and secret scanning must run in CI.
- [ ] Threat model must be reviewed against the actual deployed architecture.

### Reliability gates

- [x] `/health` and `/ready` endpoints exist.
- [x] A production-readiness CI workflow exists.
- [ ] Database migration command must be documented and tested.
- [ ] Replit/container startup command must be smoke-tested.
- [ ] Graceful fallback behavior must be tested.
- [ ] Backup/restore must be validated against the selected production database.

### Evidence gates

- [x] Existing overclaims are replaced with an explicit gate-based report.
- [x] Missing or unverified files must not be listed as complete.
- [ ] Any claim of fuzz tests, monitoring dashboards, or production infra must link to an actual file path.
- [ ] Appraisal/investor copy must separate demo value from production readiness.

---

## Hard release blockers

Do not market or deploy this as production-ready while any of these are true:

1. `JWT_SECRET`, `HMAC_PEPPER`, or `CLAIM_SALT` are default/placeholder values.
2. `DEBUG=true` in a production-like environment.
3. CORS allows `*` or is not explicitly configured.
4. Any endpoint implies real BTC custody, real settlement, guaranteed redemption, yield, profit, or investment return.
5. Mainnet RPC/program IDs are enabled without audit, legal review, and a signed release approval.
6. Wallet signature verification remains simulated.
7. Claims/PINs depend on in-memory storage in a public deployment.
8. No rollback plan exists.
9. No incident response owner exists.
10. No external security review has been completed.

---

## What changed in this production-readiness pass

This pass adds a practical, enforceable release layer:

- `backend/core/production_guard.py` — deterministic production-safety evaluator.
- `backend/tests/test_production_guard.py` — pytest coverage for safe/unsafe environment profiles.
- `.github/workflows/production-readiness.yml` — CI workflow for the guard tests.
- `ops/PRODUCTION_RELEASE_RUNBOOK.md` — release checklist and operational runbook.
- This document — honest readiness status and blocker list.

---

## Recommended next engineering steps

1. Wire `assert_production_safe()` into backend startup after imports are stabilized.
2. Replace placeholder wallet signature validation with verified Solana signature checks.
3. Move all deployed mutable state to PostgreSQL or another durable database.
4. Add migration tests and a deployment smoke test.
5. Add security-header integration tests.
6. Add secret scanning and dependency scanning to CI.
7. Convert unsupported README claims into file-backed evidence links.
8. Add a public `/release-status` endpoint that returns this readiness level.
9. Create a staging deployment with explicit `CORS_ALLOWED_ORIGINS`.
10. Complete external review before any mainnet or real-money language.

---

## Approved public description

Use this wording for demos and investor previews:

> Membra Money Protocol is an experimental devnet-only prototype for BTC-denominated bearer-note style claims on Solana. It demonstrates note lifecycle, risk disclosure, reserve metadata, fee-sponsorship economics, and auditability concepts. It does not custody real BTC, does not settle real money, and is not audited for production use.

---

## Disallowed public description

Do not say:

- “production-ready protocol,”
- “mainnet-ready,”
- “real BTC settlement,”
- “guaranteed redemption,”
- “audited,”
- “risk-free,”
- “profit opportunity,”
- “investment product.”

---

## Release decision

**Current release decision:** approved only for controlled devnet demo work.

**Production-safe public preview:** allowed after the production guard, runbook, CI, and deployment smoke test pass.

**Mainnet / real-money release:** blocked.
