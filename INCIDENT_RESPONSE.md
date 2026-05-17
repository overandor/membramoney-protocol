# Incident Response Plan — Membra Money Protocol

> **Status:** DRAFT — requires legal, compliance, and security review before production use.
> Must be tested (tabletop exercise) and staffed (on-call rota) before mainnet launch.

---

## Severity Definitions

| Severity | Description | Response SLA | Examples |
|----------|-------------|-------------|---------|
| P0 — Critical | Active exploit, fund loss, or key compromise | 15 min acknowledge / immediate action | Smart contract exploit, deployer key stolen, double-spend |
| P1 — High | Service down, data breach, sanctions hit | 30 min acknowledge / 2 hr resolution | Backend down, database leak, OFAC match in live transfer |
| P2 — Medium | Partial degradation, compliance concern | 2 hr acknowledge / 8 hr resolution | Rate limiter failure, reserve attestation stale, failed settlement |
| P3 — Low | Non-critical issues | 24 hr acknowledge / 72 hr resolution | UI errors, slow queries, stale docs |

---

## On-Call Rota

> Assign real names and contact info before production.

| Role | Responsibility |
|------|---------------|
| On-call Engineer | First responder for technical incidents |
| On-call Compliance | First responder for regulatory/AML events |
| Security Lead | Key compromise, breach response |
| Incident Commander | Coordinates P0/P1 response, external comms |
| Legal Counsel | Regulatory notifications, disclosure obligations |

---

## Runbook: Protocol Pause (P0 / P1)

Use when: active exploit suspected, key compromise, reserve shortfall, regulatory demand.

```bash
# 1. Confirm incident — do NOT pause speculatively on noise
# 2. Notify Incident Commander + Security Lead via secure channel

# 3. Pause the protocol (requires deployer keypair)
anchor invoke pause_protocol \
  --program-id EXNLzDxRPN81NtxZKzNBKweG93R9FWUq8gfGoFGzxYYw \
  --provider.cluster mainnet-beta

# 4. Confirm pause on-chain
solana account <protocol_state_PDA>

# 5. Update status page / notify users
# 6. Begin forensic investigation
# 7. Document timeline in incident log
```

**Before unpausing:** require dual approval (Incident Commander + Compliance Lead) plus written sign-off that root cause is identified and mitigated.

---

## Runbook: Deployer Key Compromise (P0)

1. **Immediately pause the protocol** (if key is not yet used maliciously).
2. Deploy a new program version with a new keypair and transfer authority.
3. Notify all users of the incident within 72 hours (legal obligation in many jurisdictions).
4. Engage external security firm for forensic investigation.
5. Rotate ALL secrets (JWT, HMAC pepper, claim salt, database passwords, API keys).
6. File incident reports as required by legal counsel (FinCEN SAR, state regulators).

---

## Runbook: Smart Contract Exploit / Fund Loss (P0)

1. **Pause protocol immediately.**
2. Take snapshot of on-chain state (all Note accounts, ProtocolState, ReserveAttestation).
3. Freeze backend — stop accepting new mints and claims.
4. Engage external auditor and legal counsel within 1 hour.
5. Do not delete logs — preserve all evidence.
6. Prepare user notification (see Communication Templates below).
7. Work with Solana Foundation and Anchor team if needed for validator-level response.

---

## Runbook: Sanctions / OFAC Match (P1)

1. Quarantine the flagged note/user in the compliance system.
2. Block all transfers involving the flagged wallet.
3. Notify Compliance Lead within 30 minutes.
4. File SAR within 30 days (or jurisdiction-specific deadline) if confirmed.
5. Do NOT tip off the subject.
6. Document all actions in the compliance audit log.

---

## Runbook: Backend Outage (P1)

1. Check health endpoint: `GET /health` and `GET /ready`
2. Check container logs: `docker logs membra-backend`
3. Check database connectivity: `psql $DATABASE_URL -c "SELECT 1"`
4. Check Redis: `redis-cli ping`
5. Restart containers if no data loss risk: `docker-compose restart backend`
6. If database corrupted — stop writes, restore from last known-good backup:
   ```bash
   bash scripts/restore_db.sh <backup-file>
   ```
7. Notify users via status page if outage > 15 minutes.

---

## Runbook: Reserve Attestation Stale (P2)

1. Check `/api/v1/reserves` — `attested_at` timestamp
2. If stale > 24 hours, run attestation refresh:
   ```bash
   # Run as protocol authority
   anchor invoke record_reserve_attestation \
     --args <attestation_hash> <reserve_ratio_bps>
   ```
3. Investigate why the attestation oracle failed to update.
4. If reserve ratio < 10,000 bps, pause new mints until reserves are reconciled.

---

## Communication Templates

### User Notification — Service Disruption

```
Subject: Membra Money — Service Interruption Notice

We are currently experiencing a service disruption affecting [feature].
No funds have been lost. [Or: We are investigating a potential issue involving user funds.]

What happened: [brief description]
What we're doing: [steps taken]
Expected resolution: [ETA or "investigating"]
What you should do: [e.g., "Do not attempt new transfers until further notice"]

We will provide updates every [30 min / 2 hr] until resolved.
— Membra Security Team
```

### User Notification — Security Incident

```
Subject: Important Security Notice from Membra Money

We are writing to inform you of a security incident that may affect your account.

[Description of incident, without operational details that could help attackers.]

Immediate actions you should take:
- [Specific user action, e.g., "Do not redeem any notes until we confirm the issue is resolved"]

We take the security of user funds extremely seriously. [Legal contacts, regulators notified if applicable.]

— Membra Security Team
```

---

## Post-Mortem Process

Every P0 and P1 incident requires a written post-mortem within 5 business days:

1. **Timeline** — minute-by-minute sequence of events
2. **Root cause** — what failed and why (5 Whys technique)
3. **Impact** — users affected, funds at risk, downtime duration
4. **Detection** — how was it found? How long before detection?
5. **Response** — what was done and by whom
6. **Action items** — specific, assigned, time-bound fixes
7. **Blameless** — focus on systems, not individuals

Post-mortems are stored in the private incident log and shared with legal/compliance.

---

## Contact Directory

> Fill in before production launch.

| Contact | Name | Method | Escalate After |
|---------|------|--------|---------------|
| On-call Engineer | TBD | PagerDuty | 15 min no ack |
| Security Lead | TBD | Signal | Immediate for P0 |
| Compliance Lead | TBD | Email + phone | 30 min for P1 |
| Legal Counsel | TBD | Phone | Immediate for P0 breach |
| Solana Foundation | security@solana.org | Email | P0 exploit |
| Anchor Team | GitHub issue | GitHub | Smart contract exploit |

---

## Testing Requirement

This plan must be tested before production launch:
- [ ] Tabletop exercise: P0 protocol pause scenario
- [ ] Tabletop exercise: key compromise scenario
- [ ] Verify all runbook commands work on staging
- [ ] Confirm on-call contacts are reachable 24/7
- [ ] Test backup restore procedure end-to-end
