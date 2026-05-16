# Membra Money Protocol — Staged Devnet E2E Release Checklist

**Status:** DEVNET / RESEARCH PREVIEW / ENGINEERING CANDIDATE  
**Not production ready.**

---

## Pre-Release (Code Freeze)

- [ ] All features merged to `main`
- [ ] `scripts/verify_clean_clone.sh` passes (0 failures)
- [ ] `cargo test --lib` passes (programs/membramoney)
- [ ] `pytest backend/tests` passes (mock DB if needed)
- [ ] `npm run build` passes in `ui/`
- [ ] No `.env` files committed (only `.env.example`)
- [ ] Secrets rotated (JWT secret, pepper, Redis)
- [ ] CHANGELOG.md updated with release notes
- [ ] Version bumped in `backend/main.py` and `ui/package.json`

---

## Devnet Deployment

### Smart Contract
- [ ] `anchor build` succeeds with zero warnings
- [ ] `anchor deploy --provider.cluster devnet` succeeds
- [ ] Program ID updated in `.env.example` and docs
- [ ] `anchor test` passes on devnet
- [ ] Contract verified on SolanaFM / Solscan (optional)

### Backend
- [ ] Docker image builds: `docker build -t membramoney-backend backend/`
- [ ] Health check `/health` returns `status: healthy`
- [ ] Ready check `/ready` returns `status: ready`
- [ ] Metrics endpoint `/metrics` returns Prometheus metrics
- [ ] Database migrations applied (`alembic upgrade head`)
- [ ] Seed data script runs without error
- [ ] JWT auth flow tested (nonce → sign → token)
- [ ] CORS headers correct for devnet frontend origin
- [ ] Security headers present (CSP, HSTS, X-Frame-Options)
- [ ] Rate limiting functional (5/min auth, 100/min API)

### Frontend
- [ ] `npm run build` produces valid static assets
- [ ] Wallet connection works (Phantom / Solflare)
- [ ] Risk disclosure modal displays and records acceptance
- [ ] Claim creation flow end-to-end (create → share → validate)
- [ ] Reserve status card displays with disclaimer
- [ ] Devnet banner visible on all pages
- [ ] No console errors in browser

### Integration
- [ ] Frontend → Backend API calls succeed (CORS OK)
- [ ] Backend → Solana devnet RPC calls succeed
- [ ] End-to-end claim lifecycle tested manually
- [ ] Idempotency keys prevent duplicate claims
- [ ] Audit events logged for every major action

---

## Infrastructure

- [ ] Kubernetes namespace created (`kubectl apply -f k8s/namespace.yaml`)
- [ ] Backend deployment rolled out (`kubectl apply -f k8s/backend-deployment.yaml`)
- [ ] Ingress configured with TLS (devnet cert)
- [ ] Prometheus scraping `/metrics` successfully
- [ ] Grafana dashboard imported and visible
- [ ] Alert rules loaded (Slack/Discord webhook tested)
- [ ] Terraform plan reviewed and applied (staging environment)

---

## Security & Compliance

- [ ] No hardcoded secrets in source code
- [ ] `.env.example` complete and up-to-date
- [ ] Dependabot alerts reviewed (0 critical)
- [ ] Snyk / Trivy scan passes
- [ ] OWASP ZAP baseline scan (no high/critical findings)
- [ ] Backup script tested (`scripts/backup.sh`)
- [ ] Disaster recovery runbook written

---

## Documentation

- [ ] `README.md` reflects current architecture and setup steps
- [ ] `PRODUCTION_READINESS.md` updated with known gaps
- [ ] API documentation generated (`/docs` FastAPI OpenAPI)
- [ ] Sequence diagrams reviewed for accuracy
- [ ] On-call runbook created
- [ ] Post-mortem template ready

---

## Post-Release Validation

- [ ] Staged devnet E2E performed by 2+ team members
- [ ] Bug tracker triaged (all P0/P1 resolved or accepted)
- [ ] Performance baseline recorded (latency, throughput)
- [ ] Community announcement drafted (if applicable)
- [ ] Next milestone defined and ticketed

---

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Tech Lead | | | |
| Security Reviewer | | | |
| QA Lead | | | |
| Product Owner | | | |

---

*This checklist is a living document. Update it as the protocol matures toward mainnet.*
