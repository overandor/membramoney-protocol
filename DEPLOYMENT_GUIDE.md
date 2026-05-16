# Deployment Guide — Membra Money Protocol

**Last updated:** 2026-05-15
**Status:** DEVNET / RESEARCH PREVIEW ONLY
**Classification:** Internal Use Only

## Prerequisites

- macOS or Linux
- Solana CLI 1.17.0+
- Anchor CLI 0.30.1
- Node.js 20+ and npm
- Python 3.11+ and pip
- Docker (optional, for backend)
- Git

## 1. Local Development Setup

### 1.1 Clone Repository

```bash
git clone https://github.com/overandor/membramoney-protocol.git
cd membramoney-protocol
```

### 1.2 Install Solana & Anchor Toolchain

```bash
bash scripts/install_solana.sh
```

Verify installation:
```bash
solana --version
anchor --version
cargo --version
```

### 1.3 Configure Solana CLI

```bash
solana config set --url devnet
solana-keygen new --outfile ~/.config/solana/id.json
```

Request devnet SOL:
```bash
solana airdrop 2
```

### 1.4 Build Anchor Program

```bash
anchor build
```

**Note:** `anchor test` is blocked by `cargo-build-sbf` edition 2024 incompatibility. Use `cargo test --lib` instead.

```bash
cargo test --lib
```

### 1.5 Deploy to Devnet

```bash
anchor deploy --provider.cluster devnet
```

**Expected output:**
```
Program Id: EXNLzDxRPN81NtxZKzNBKweG93R9FWUq8gfGoFGzxYYw
Deploy success
```

### 1.6 Run Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Verify backend:
```bash
curl http://localhost:8000/health
```

### 1.7 Run UI

```bash
cd ui
npm install
npm run dev
```

Open http://localhost:5173 in browser.

---

## 2. Backend Deployment Options

### 2.1 Docker (Local / Staging)

```bash
cd backend
docker build -t membramoney-backend .
docker run -p 8000:8000 membramoney-backend
```

### 2.2 Render (Cloud)

Use the included `render.yaml`:

```bash
# Deploy via Render dashboard or CLI
render deploy
```

### 2.3 AWS / GCP / Azure

**Required Environment Variables:**
```bash
ENV=production
DEBUG=false
BACKEND_URL=https://api.membramoney.dev
HMAC_PEPPER=<generate_random_64_char_hex>
RISK_DISCLOSURE_VERSION=v1.0.0
```

**Generate HMAC pepper:**
```bash
openssl rand -hex 32
```

---

## 3. UI Deployment Options

### 3.1 Vercel (Recommended)

```bash
cd ui
npm run build
vercel --prod
```

See `ui/VERCEL_DEPLOYMENT.md` for detailed instructions.

### 3.2 Netlify

```bash
cd ui
npm run build
netlify deploy --prod --dir=dist
```

### 3.3 Static Hosting (S3, Cloudflare Pages)

```bash
cd ui
npm run build
# Upload dist/ folder to your static host
```

---

## 4. Pre-Flight Checks

Before any deployment, run:

```bash
bash scripts/pre_flight_check.sh
```

**Expected output:**
```
========================================
Membra Money Protocol — Pre-Flight Check
========================================
[1/10] Git status...                [PASS]
[2/10] Environment file check...     [PASS]
[3/10] Backend compile...            [PASS]
[4/10] Cargo check...                [PASS]
[5/10] Anchor CLI check...           [PASS]
[6/10] Solana CLI check...           [PASS]
[7/10] UI check...                   [PASS]
[8/10] Documentation...              [PASS]
[9/10] Scripts...                    [PASS]
[10/10] Secret scan...               [WARN]
========================================
Results: 17 passed, 0 failed, 1 warnings
========================================
Pre-flight PASSED. Ready for devnet deployment.
```

---

## 5. Production Deployment (NOT RECOMMENDED YET)

**WARNING:** This protocol is classified as DEVNET / RESEARCH PREVIEW ONLY. Do not deploy to mainnet without closing all P0 blockers.

### P0 Blockers Checklist

- [ ] External security audit
- [ ] Multi-sig upgrade authority
- [ ] Real wallet adapter (Phantom, Solflare)
- [ ] PostgreSQL persistence
- [ ] CAPTCHA + exponential backoff
- [ ] Secrets manager integration
- [ ] Dependency scanning (Snyk, Dependabot)
- [ ] Domain monitoring
- [ ] Immutable audit log
- [ ] Incident response plan
- [ ] Legal classification memo
- [ ] Compliance program (AML, sanctions)
- [ ] Insurance review
- [ ] Bug bounty program
- [ ] Formal verification

See [PRODUCTION_GAPS.md](PRODUCTION_GAPS.md) for full 880-item checklist.

---

## 6. Verification Commands

### Verify Program on Devnet

```bash
solana config set --url devnet
solana program show EXNLzDxRPN81NtxZKzNBKweG93R9FWUq8gfGoFGzxYYw
solana balance
```

### Verify Backend Health

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

### Verify UI Build

```bash
cd ui
npm run build
# Check dist/ folder exists and is not empty
ls -la dist/
```

---

## 7. Rollback Procedures

### Rollback Smart Contract

```bash
# Deploy previous version
solana program deploy target/deploy/membramoney.so \
  --program-id EXNLzDxRPN81NtxZKzNBKweG93R9FWUq8gfGoFGzxYYw
```

### Rollback Backend

```bash
# Docker
docker stop membramoney-backend
docker run -p 8000:8000 membramoney-backend:previous
```

### Rollback UI

```bash
# Vercel
vercel rollback
```

---

## 8. Monitoring & Alerting

### Backend Logs

```bash
# Local
tail -f logs/*.log

# Docker
docker logs -f membramoney-backend
```

### Audit Events

```bash
curl http://localhost:8000/api/v1/audit/events?limit=10
```

### Solana Program Monitoring

```bash
# Check program balance
solana balance EXNLzDxRPN81NtxZKzNBKweG93R9FWUq8gfGoFGzxYYw

# Check recent transactions
solana transactions EXNLzDxRPN81NtxZKzNBKweG93R9FWUq8gfGoFGzxYYw --limit 10
```

---

## 9. Troubleshooting

### Anchor Test Fails

**Error:** `lock file version 4 was found`

**Fix:**
```bash
sed -i '' 's/^version = 4$/version = 3/' Cargo.lock
cargo test --lib  # Use this instead of anchor test
```

### Insufficient Funds for Deploy

**Error:** `Account has insufficient funds for spend`

**Fix:**
```bash
solana airdrop 5
# Or use Solana Faucet: https://faucet.solana.com/
```

### Backend Port Already in Use

**Fix:**
```bash
lsof -ti:8000 | xargs kill -9
uvicorn main:app --reload --port 8000
```

### UI Build Fails

**Fix:**
```bash
cd ui
rm -rf node_modules package-lock.json
npm install
npm run build
```

---

## 10. Security Checklist

Before every deployment:

- [ ] No secrets in `.env` files (use `.env.example` as template)
- [ ] GitHub tokens rotated if exposed
- [ ] Buffer seed phrases treated as compromised
- [ ] `Cargo.lock` and `package-lock.json` committed
- [ ] Pre-flight checks passing
- [ ] README updated with current program ID
- [ ] DEVNET classification prominently displayed

---

## 11. References

- [PRODUCTION_GAPS.md](PRODUCTION_GAPS.md) — Production readiness checklist
- [ARCHITECTURE.md](ARCHITECTURE.md) — System architecture
- [DATA_FLOW.md](DATA_FLOW.md) — Data flows
- [SMART_CONTRACT_SPEC.md](SMART_CONTRACT_SPEC.md) — Contract specification
- [THREAT_MODEL.md](THREAT_MODEL.md) — Threat model
- [API_REFERENCE.md](API_REFERENCE.md) — API documentation
- [PREVIEW_STATUS.md](PREVIEW_STATUS.md) — Current status
