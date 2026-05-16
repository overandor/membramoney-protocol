# Mainnet Readiness Checklist

> **This protocol is NOT ready for mainnet.**
>
> Use this checklist to track maturity. Every item must be signed off before any mainnet consideration.

## Smart Contract

- [ ] **Anchor Audit** — Independent security audit by a reputable Solana audit firm (e.g., OtterSec, Neodyme, Sec3).
- [ ] **Fuzz Testing** — Property-based tests for all instruction paths and edge cases.
- [ ] **Formal Verification** — Optional but recommended for state-machine invariants.
- [ ] **Program ID Governance** — Multi-sig or DAO-controlled upgrade authority.
- [ ] **Emergency Pause** — Verified pause/unpause works under stress and is time-locked if needed.

## Reserve / Custody

- [ ] **Reserve/Custody Review** — Independent review of any off-chain BTC backing claims.
- [ ] **Proof-of-Reserves Hardening** — Cryptographic attestations, third-party verification, public dashboards.
- [ ] **Custody Architecture** — MPC, multi-sig, or institutional custody provider integration.
- [ ] **Insurance Review** — Coverage for slippage, hacks, or operational failures.

## Legal / Compliance

- [ ] **Legal Review** — Jurisdiction-specific analysis (US, EU, Singapore, etc.).
- [ ] **Securities Analysis** — Determination of whether notes are securities in target jurisdictions.
- [ ] **KYC/AML Policy** — Customer identification, transaction monitoring, SAR filing procedures.
- [ ] **Terms of Service** — User agreements, limitation of liability, arbitration clauses.
- [ ] **Privacy Policy** — GDPR/CCPA compliance if personal data is collected.

## Operations

- [ ] **Monitoring** — On-chain and off-chain alerts (PagerDuty, Opsgenie, Discord).
- [ ] **Incident Response** — Runbook for exploits, pauses, and comms.
- [ ] **Rate Limiting** — API and RPC rate limits to prevent abuse.
- [ ] **DDoS Protection** — WAF, CDN, and edge rate limiting.
- [ ] **Backup & Recovery** — Database backups, key recovery procedures.

## Testing

- [ ] **Successful Devnet E2E Tests** — All user flows tested on devnet with real wallets.
- [ ] **Load Testing** — Backend API load tests at expected traffic levels.
- [ ] **Chaos Engineering** — Simulated RPC failures, validator downtime, and network partitions.
- [ ] **Penetration Testing** — External security assessment of APIs and UI.

## Infrastructure

- [ ] **CI/CD Hardening** — Signed builds, reproducible builds, no secrets in CI logs.
- [ ] **Infrastructure as Code** — Terraform / Pulumi for all cloud resources.
- [ ] **Secret Rotation Automation** — Automated rotation of API keys and JWT secrets.
- [ ] **SLA Definition** — Uptime targets, response times, and escalation paths.

## Final Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Security Lead | | | |
| Legal Counsel | | | |
| Compliance Officer | | | |
| CTO / Tech Lead | | | |
| External Auditor | | | |

---

**Status:** `NOT READY FOR MAINNET`
