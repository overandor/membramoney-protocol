# Devnet Deployment Guide

## Prerequisites

- macOS or Linux (ARM64 or x86_64)
- Git
- Python 3.11+
- Node.js 20+

## 1. Install Solana CLI

```bash
bash scripts/install_solana.sh
```

This installs:
- Solana CLI
- Anchor CLI
- Devnet configuration

## 2. Build Anchor Program

```bash
anchor build
```

Expected output:
```
Compiling membramoney v0.1.0
    Finished release [optimized] target(s) in XXs
```

## 3. Run Anchor Tests

```bash
anchor test
```

This starts a local validator, deploys the program, and runs the TS test suite.

## 4. Deploy to Devnet

```bash
solana config set --url devnet
solana airdrop 2  # get devnet SOL
anchor deploy --provider.cluster devnet
```

After deployment, update the program ID in:
- `Anchor.toml`
- `programs/membramoney/src/lib.rs` (declare_id!)
- Backend `.env` (if referencing program ID)

## 5. Update Program ID

```bash
# Get the new program ID
solana address -k target/deploy/membramoney-keypair.json

# Replace in Anchor.toml and lib.rs
# (Manual step — future versions may automate)
```

## 6. Run Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and set DEVNET=true, ANCHOR_PROGRAM_ID=<your program id>

uvicorn main:app --reload --port 8000
```

Health check:
```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

## 7. Run UI

```bash
cd ui
npm install

cp .env.example .env.local
# Edit .env.local and set VITE_API_BASE_URL=http://localhost:8000

npm run dev
```

Open `http://localhost:5173` (or whichever port Vite uses).

## 8. Run Smoke Test

```bash
bash scripts/pre_flight_check.sh
npx ts-node scripts/devnet_smoke_test.ts
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `solana` not found | Re-run `scripts/install_solana.sh` |
| `anchor` not found | Ensure `~/.cargo/bin` is in PATH |
| Build fails | Run `anchor clean` then `anchor build` |
| Tests fail | Check local validator is not already running on port 8899 |
| Devnet deploy fails | Ensure wallet has devnet SOL (`solana airdrop 2`) |
| UI build fails | Delete `node_modules` and `package-lock.json`, re-run `npm install` |

## Docker (Optional)

```bash
docker-compose up --build
```

This starts the backend + PostgreSQL locally.
