# Changelog — Membra Money Protocol

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Database adapter (`backend/db/adapter.py`) with dual-mode PostgreSQL / in-memory fallback
- Wire DB models into backend runtime: `main.py` endpoints now use `db.adapter` for claims, risk acceptances, audit events, idempotency keys
- Missing `__init__.py` files for `db/`, `core/`, `db/migrations/`, `tests/` packages
- `scripts/verify_clean_clone.sh` — clean-clone verification (syntax, imports, file presence, git status)
- `scripts/do_push.py` — helper to commit and push to GitHub
- `DEVNET_RELEASE_CHECKLIST.md` — staged devnet E2E release checklist with sign-off table
- `MANUAL_ACTIONS.md` — manual steps for push, test, build verification

### Added
- Production middleware: RequestIDMiddleware, AuditLoggingMiddleware, RateLimitMiddleware
- Idempotency key support for claim creation (`POST /api/v1/claims/create`)
- Structured error responses with `request_id`, `timestamp`, and `devnet` metadata
- Input sanitization helpers for wallet addresses, claim IDs, and PINs
- 24 Rust unit tests covering boundary conditions, edge cases, and negative tests
- ErrorBoundary React component for graceful UI error handling
- LoadingCard and EmptyState components with skeleton loading animations
- Enhanced DevnetBanner with dismissible state and Solana Explorer link
- Comprehensive documentation:
  - `ARCHITECTURE.md` — System architecture with component diagrams
  - `DATA_FLOW.md` — 7 data flow diagrams (mint, claim, redeem, reserve, risk, audit, pause)
  - `SMART_CONTRACT_SPEC.md` — Complete Anchor program specification
  - `THREAT_MODEL.md` — Security threat model with risk matrix
  - `API_REFERENCE.md` — Full API documentation with curl examples
  - `DEPLOYMENT_GUIDE.md` — Step-by-step deployment instructions
- GitHub Actions CI workflow (`ci.yml`) with Rust, backend, frontend, and secret scanning jobs
- Skeleton CSS animations for loading states

### Changed
- Updated `README.md` with deployed program ID and status link
- Updated `PREVIEW_STATUS.md` with new features and test counts
- Enhanced `backend/main.py` with middleware wiring and exception handlers
- ReserveStatusCard now uses LoadingCard component for consistent UX
- App.tsx wrapped with ErrorBoundary for production-grade error handling

### Security
- Added rate limiting (2 req/s per IP, burst 20)
- Added brute-force protection for claim validation (5 attempts/hour)
- Added HMAC compare_digest for timing-safe PIN comparison
- Added input sanitization to prevent injection attacks
- Structured errors hide internal details in production

### Infrastructure
- Added `nginx.conf` with security headers, gzip, and rate limiting configuration
- Added `docker-compose.override.yml` for local development with hot reload
- Added `ui/Dockerfile` multi-stage build with nginx
- Added `robots.txt` to block crawlers from devnet content
- Added `.gitattributes` for consistent line endings across OS

### Added (Session 2026-05-15T22:20)
- Enhanced health check endpoint with memory usage and store statistics
- Enhanced readiness endpoint with dependency checks
- Structured logging module (`backend/core/logging.py`) with JSON output
- Backend memory store limits and automatic cleanup (10K claims, 50K audit events)
- Integration tests with pytest fixtures (`conftest.py`, `test_api_integration.py`)
- TypeScript strict types: `ErrorResponse`, `AuditEvent`, `AuditEventsResponse`
- Added `idempotency_key` to `ClaimCreateRequest` type
- Added `getAuditEvents` API method

### Documentation
- Updated `SECURITY.md` with current security posture table and status
- GitHub issue templates: bug report, feature request
- Pull request template with checklist
- Contributing guidelines (`CONTRIBUTING.md`)
- Makefile for common development tasks
- `.pre-commit-config.yaml` with hooks for secrets, tests, and linting

### Changed
- Wire store limits enforcement into claim creation endpoint
- Wire structured logging into audit function

### Added (Session 2026-05-16)
- SQLAlchemy database models: User, Claim, RiskAcceptance, AuditLog, ReserveAttestation
- Repository pattern for database operations (User, Claim, Risk, Audit repositories)
- JWT authentication with wallet signature verification and nonce replay protection
- WalletAuthService with Redis-backed nonce storage and refresh tokens
- 50+ Rust property-based and fuzz tests
- Kubernetes manifests (9 files): namespace, deployments, services, ingress, HPA, PDB
- Terraform AWS infrastructure (8 files): VPC, RDS, ECS, ALB, secrets management
- Prometheus alerting rules and Grafana dashboard JSON
- Security headers middleware with CSP, HSTS, X-Frame-Options
- Database connection pooling with QueuePool and health checks
- Pydantic v2 validation schemas for all API endpoints
- OpenTelemetry tracing stub (ready for full OTel integration)
- Performance benchmarking suite (`scripts/benchmark.py`)
- Sequence diagrams documentation (`docs/sequence-diagrams.md`)
- Automated changelog generation script (`scripts/generate_changelog.py`)
- E2E Cypress tests for critical user flows
- TypeScript and Python API client SDKs
- Backup and disaster recovery scripts (`scripts/backup_db.sh`, `scripts/restore_db.sh`)
- Seed data script for test environments
- Deployment script (`scripts/deploy.sh`)
- Staging environment configuration (`infra/staging.env`)
- Vulnerability scanning CI workflow (`vulnerability-scan.yml`)
- Frontend components: WalletConnectButton, TransactionStatus, NetworkBadge, AuditLogViewer, MetricsDashboard
- Dependabot configuration for automated dependency updates
- Production readiness report (`PRODUCTION_READINESS.md`)

### Changed
- Updated README with production features list and new documentation links
- Updated GitHub push script with correct username (`overandor`)

## [0.1.0-devnet] — 2026-05-15

### Added
- Anchor program deployed to Solana devnet
- 7 smart contract instructions: initialize, mint_note, transfer_note, claim_note, redeem_note, attest_reserve, toggle_pause
- FastAPI backend with health, ready, risk disclosure, claims, reserves, stats, audit endpoints
- React frontend with neomorphic dark theme
- Pre-flight check script (`scripts/pre_flight_check.sh`)
- Risk disclosure flow with wallet acceptance tracking
- Claim creation and validation with PIN-based security
- In-memory audit event logging
- `PRODUCTION_GAPS.md` with 880-item production readiness checklist

### Security
- Initial risk disclosure implementation
- Basic brute-force protection
- DEVNET / RESEARCH PREVIEW ONLY classification
