# Membra Money Production Readiness Master Plan

Status: **NOT PRODUCTION READY**  
Classification: **Devnet / research preview / engineering candidate**  
Scope: Convert the current experimental Solana devnet bearer-note protocol into defensible production infrastructure.

This checklist is intentionally strict. A production label is not allowed until every P0 gate is complete, independently verified, and signed off.

---

## 0. Non-negotiable production gates

Production is blocked until all of these are true:

- [ ] Smart contract audited by at least one independent Solana/Anchor security firm.
- [ ] All audit findings remediated or formally accepted with written risk ownership.
- [ ] Mainnet deployment procedure rehearsed on devnet and staging with reproducible artifacts.
- [ ] Real BTC custody design approved by legal, security, and treasury owners.
- [ ] No user-facing claim implies real BTC backing unless backing, custody, and redemption are live and monitored.
- [ ] Proof-of-reserves design is implemented, monitored, and independently reviewable.
- [ ] Redemption backend exists, is tested, and has explicit failure handling.
- [ ] Treasury/key management uses HSM, MPC, or equivalent controlled signing architecture.
- [ ] Incident response, disaster recovery, and rollback playbooks are tested.
- [ ] Compliance review is complete for all launch jurisdictions.
- [ ] KYC/AML/sanctions policy is either implemented or legal has documented why it is not required.
- [ ] Production observability is live: metrics, logs, tracing, alerting, dashboards, and paging.
- [ ] All CI checks pass from a fresh clone without local-only assumptions.
- [ ] Secret scanning confirms no leaked GitHub tokens, API keys, seeds, private keys, or production credentials.
- [ ] Terms, risk disclosures, privacy policy, and support process are published.

---

## 1. Smart contract and Solana program

- [ ] Freeze exact Anchor and Solana versions.
- [ ] Make builds reproducible from a clean machine.
- [ ] Generate deterministic/verifiable build artifacts.
- [ ] Remove placeholder/dummy IDs from all files.
- [ ] Confirm deployed program ID matches `declare_id!`, Anchor.toml, UI env, backend env, and docs.
- [ ] Document every PDA seed and signer constraint.
- [ ] Add invariant tests for note lifecycle: minted -> transferred -> claimed -> redeemed.
- [ ] Add negative tests for unauthorized mint, transfer, claim, redeem, pause, unpause, reserve attest.
- [ ] Add duplicate-claim tests.
- [ ] Add expiry tests.
- [ ] Add replay tests.
- [ ] Add paused-state tests.
- [ ] Add malformed input tests.
- [ ] Add max denomination and overflow tests.
- [ ] Add fuzz/property tests for note IDs, claim hashes, state transitions, and account constraints.
- [ ] Run `anchor test` on a clean validator.
- [ ] Run `cargo test --lib` in CI.
- [ ] Run `cargo clippy` and resolve actionable warnings.
- [ ] Run SBF stack-size checks and eliminate unsafe stack overflows.
- [ ] Produce IDL artifact and verify it matches generated client code.
- [ ] Decide upgrade authority policy: immutable, timelock, multisig, or governance-controlled.
- [ ] Implement upgrade authority custody with multisig or governance.
- [ ] Document emergency pause authority and operational controls.
- [ ] Ensure pause cannot be abused without accountable governance.
- [ ] Add on-chain event emission for lifecycle actions.
- [ ] Index events for auditability.
- [ ] Verify rent-exemption assumptions.
- [ ] Verify account close/refund behavior.
- [ ] Verify no instruction accepts unchecked accounts where checked accounts are required.
- [ ] Verify all signers are explicit.
- [ ] Verify all mutability requirements are minimal.
- [ ] Verify all arithmetic is checked.
- [ ] Verify all timestamps/slots are used consistently.
- [ ] Verify no unbounded loops or account growth risks.
- [ ] Verify reserve attestation cannot be spoofed by unauthorized accounts.
- [ ] Complete independent audit.
- [ ] Complete post-audit remediation.
- [ ] Publish audit summary.

---

## 2. BTC custody and reserve system

- [ ] Define whether BTC is held by company, custodian, smart contract bridge, federation, or user self-custody.
- [ ] Obtain legal signoff on custody model.
- [ ] Implement treasury wallet policy.
- [ ] Implement cold/hot wallet split.
- [ ] Implement HSM/MPC signing policy.
- [ ] Require multisig approval for material treasury moves.
- [ ] Implement transaction approval workflow.
- [ ] Implement withdrawal velocity limits.
- [ ] Implement emergency freeze policy.
- [ ] Implement key rotation process.
- [ ] Implement custody disaster recovery.
- [ ] Implement custody reconciliation.
- [ ] Implement BTC address ownership proofs.
- [ ] Implement reserve ingestion from BTC nodes or custodian APIs.
- [ ] Implement proof-of-reserves calculation.
- [ ] Implement proof-of-liabilities calculation.
- [ ] Implement reserve-ratio monitoring.
- [ ] Implement solvency threshold alerts.
- [ ] Implement independent attestation export.
- [ ] Prevent UI from showing reserve claims unless data is real and fresh.
- [ ] Mark stale reserve data as stale.
- [ ] Mark unavailable reserve data as degraded.
- [ ] Store reserve snapshots immutably.
- [ ] Publish reserve policy.
- [ ] Define user redemption rights and limitations.

---

## 3. Redemption and settlement backend

- [ ] Implement real redemption request flow.
- [ ] Implement redemption eligibility rules.
- [ ] Implement redemption queue.
- [ ] Implement redemption approval/rejection states.
- [ ] Implement payment execution integration.
- [ ] Implement idempotency for all state-changing endpoints.
- [ ] Implement anti-replay protections.
- [ ] Implement claimant wallet verification.
- [ ] Implement claim code/PIN brute-force limits.
- [ ] Implement claim code/PIN expiration and lockout.
- [ ] Implement support escalation flow.
- [ ] Implement failed redemption retry policy.
- [ ] Implement accounting ledger entries for each redemption.
- [ ] Implement audit log for every status transition.
- [ ] Implement webhook or job worker for asynchronous settlement.
- [ ] Implement human review for high-value redemptions.
- [ ] Implement suspicious activity flags.
- [ ] Implement reconciliation between on-chain state, backend DB, and treasury state.

---

## 4. Backend production hardening

- [ ] Replace all in-memory stores with PostgreSQL persistence.
- [ ] Add migrations with rollback strategy.
- [ ] Add database connection pooling.
- [ ] Add retry logic for transient DB failures.
- [ ] Add request ID middleware.
- [ ] Add structured logging.
- [ ] Add audit logging to immutable storage.
- [ ] Add rate limiting backed by Redis or equivalent.
- [ ] Add circuit breakers for external calls.
- [ ] Add timeouts on all external requests.
- [ ] Add input validation on every endpoint.
- [ ] Add output schemas on every endpoint.
- [ ] Add consistent error envelope.
- [ ] Add auth middleware.
- [ ] Add wallet signature authentication.
- [ ] Add role-based access control for admin endpoints.
- [ ] Add API versioning policy.
- [ ] Add CORS allowlist by environment.
- [ ] Add security headers.
- [ ] Add CSRF protections where browser credentials are used.
- [ ] Add payload size limits.
- [ ] Add OpenAPI examples.
- [ ] Add health, readiness, and liveness probes.
- [ ] Add graceful shutdown.
- [ ] Add background worker process.
- [ ] Add dead-letter queue for failed jobs.
- [ ] Add admin audit viewer.
- [ ] Add database backup and restore procedures.
- [ ] Add production config validation at startup.
- [ ] Add dependency vulnerability scan.

---

## 5. Frontend and UX

- [ ] Replace simulated wallet flow with real wallet adapter.
- [ ] Support Phantom/Solflare/backpack or explicitly document supported wallets.
- [ ] Show network mismatch warning.
- [ ] Block mainnet interactions until mainnet release gate is approved.
- [ ] Display `EXPERIMENTAL DEVNET ONLY` on every screen until production approval.
- [ ] Ensure no text implies real BTC custody before custody is implemented.
- [ ] Ensure no text implies guaranteed solvency.
- [ ] Implement accessible error states.
- [ ] Implement loading skeletons.
- [ ] Implement empty states.
- [ ] Implement transaction status display.
- [ ] Implement Solana Explorer links.
- [ ] Implement QR claim flow with expiration display.
- [ ] Implement copy-safe claim links.
- [ ] Implement risk disclosure acceptance with version tracking.
- [ ] Implement responsive mobile layout.
- [ ] Add accessibility audit: keyboard, contrast, focus, labels.
- [ ] Add Cypress/Playwright tests for critical flows.
- [ ] Add visual regression tests.
- [ ] Add Sentry or equivalent frontend error reporting.
- [ ] Add CSP-compatible frontend build.

---

## 6. Infrastructure and deployment

- [ ] Define environments: local, devnet, staging, production.
- [ ] Separate secrets by environment.
- [ ] Add Terraform or IaC for production infra.
- [ ] Add Kubernetes or managed container deployment manifests.
- [ ] Add autoscaling policy.
- [ ] Add load balancer config.
- [ ] Add TLS certificates.
- [ ] Add WAF rules.
- [ ] Add DDoS protection.
- [ ] Add CDN/cache policy for UI.
- [ ] Add production domain policy.
- [ ] Add DNS failover plan.
- [ ] Add blue/green or canary deployment flow.
- [ ] Add rollback playbook.
- [ ] Add database migration deployment order.
- [ ] Add seed data policy for non-production only.
- [ ] Add container image signing.
- [ ] Add SBOM generation.
- [ ] Add deployment approvals.
- [ ] Add environment smoke tests after deployment.

---

## 7. Observability and operations

- [ ] Metrics endpoint live.
- [ ] Prometheus scraping configured.
- [ ] Grafana dashboards configured.
- [ ] Error tracking configured.
- [ ] Distributed tracing configured.
- [ ] Request logs centralized.
- [ ] Audit logs tamper-resistant.
- [ ] Alerting rules for API failures.
- [ ] Alerting rules for chain/RPC failures.
- [ ] Alerting rules for reserve degradation.
- [ ] Alerting rules for redemption backlog.
- [ ] Alerting rules for brute-force attempts.
- [ ] Alerting rules for treasury movement anomalies.
- [ ] On-call rotation defined.
- [ ] Runbooks written.
- [ ] Incident drills performed.
- [ ] Status page prepared.
- [ ] Customer support escalation path defined.

---

## 8. Security program

- [ ] Threat model complete and reviewed.
- [ ] Secure SDLC defined.
- [ ] Branch protection enabled.
- [ ] Required CI checks enabled.
- [ ] Dependabot or equivalent enabled.
- [ ] Secret scanning enabled.
- [ ] CodeQL or SAST enabled.
- [ ] Container scanning enabled.
- [ ] Infrastructure scanning enabled.
- [ ] DAST against staging enabled.
- [ ] Penetration test completed.
- [ ] Smart contract audit completed.
- [ ] Wallet/auth flow reviewed.
- [ ] Key management review completed.
- [ ] Data retention review completed.
- [ ] Privacy review completed.
- [ ] Vulnerability disclosure process published.
- [ ] Security contact published.
- [ ] Security incident response tested.

---

## 9. Legal, compliance, and product policy

- [ ] Determine whether product is money transmission, stored value, prepaid access, securities, commodities, or other regulated activity in target jurisdictions.
- [ ] Obtain legal memo for launch scope.
- [ ] Decide jurisdiction restrictions.
- [ ] Implement geofencing if required.
- [ ] Implement sanctions screening if required.
- [ ] Implement KYC/KYB if required.
- [ ] Implement AML monitoring if required.
- [ ] Implement suspicious activity reporting workflow if required.
- [ ] Publish terms of service.
- [ ] Publish privacy policy.
- [ ] Publish risk disclosures.
- [ ] Publish redemption policy.
- [ ] Publish support policy.
- [ ] Publish custody/reserve policy.
- [ ] Define dispute resolution process.
- [ ] Define records retention policy.
- [ ] Complete tax/accounting review.

---

## 10. Quality, testing, and release gates

- [ ] Fresh clone install passes.
- [ ] Backend unit tests pass.
- [ ] Backend integration tests pass.
- [ ] Frontend typecheck passes.
- [ ] Frontend build passes.
- [ ] Frontend E2E tests pass.
- [ ] Rust unit tests pass.
- [ ] Anchor tests pass.
- [ ] SBF build passes.
- [ ] CI passes on GitHub.
- [ ] Load tests pass target throughput.
- [ ] Soak tests pass for at least 24-72 hours on staging.
- [ ] Chaos tests run against staging.
- [ ] Backup restore test passes.
- [ ] Rollback test passes.
- [ ] Staging release candidate signed off.
- [ ] Production release checklist signed off.

---

## 11. Current allowed label

Until all P0 gates are closed, the correct public label is:

> **Experimental devnet preview. Not production financial infrastructure. Not mainnet-ready. Do not use with real funds.**

---

## 12. Done-definition for production

Membra Money becomes production-ready only when engineering, security, legal, compliance, treasury, and operations each sign off in writing, and every production gate above is checked with evidence links.
