# Devnet Build & Deploy Guide

> Run these commands locally after cloning the repo.
> Requires: macOS or Linux, Rust (stable), Node.js 20+, Python 3.11+.

---

## Step 1 — Install Toolchain

```bash
# Install Solana CLI (1.18.x)
sh -c "$(curl -sSfL https://release.solana.com/stable/install)"
export PATH="$HOME/.local/share/solana/install/active_release/bin:$PATH"

# Install Anchor CLI via avm (Anchor Version Manager)
cargo install --git https://github.com/coral-xyz/anchor avm --locked
avm install 0.29.0
avm use 0.29.0

# Verify
solana --version   # expect: solana-cli 1.18.x
anchor --version   # expect: anchor-cli 0.29.0
```

## Step 2 — Generate a Devnet Wallet

```bash
# Create a new keypair (skip if you already have one)
solana-keygen new --no-passphrase --outfile ~/.config/solana/id.json

# Point CLI at devnet
solana config set --url devnet

# Check your address
solana address

# Airdrop 2 SOL for deploy fees (devnet only)
solana airdrop 2
solana balance
```

## Step 3 — Build the Anchor Program

```bash
cd programs/membramoney

# Known issue: Cargo.lock v4 incompatibility with older cargo-build-sbf.
# If `anchor build` fails, use the --no-idl workaround:
anchor build -- --no-idl

# Or upgrade to latest Solana toolchain first:
solana-install update
```

Expected output:
```
BPF SDK: ...
Compiling membramoney v0.1.0-devnet
    Finished release [optimized] target(s) in Xs
```

The compiled `.so` is at:
```
target/deploy/membramoney.so
```

## Step 4 — Deploy to Devnet

```bash
# Deploy (takes ~30 seconds)
anchor deploy --provider.cluster devnet

# Note the deployed Program ID — update declare_id! in lib.rs and Anchor.toml
# if this is a fresh deployment (not the same keypair as the existing devnet ID).
```

Expected output:
```
Deploying workspace: https://api.devnet.solana.com
Upgrade authority: <your-wallet-address>
Deploying program "membramoney"...
Program path: target/deploy/membramoney.so...
Program Id: EXNLzDxRPN81NtxZKzNBKweG93R9FWUq8gfGoFGzxYYw
Deploy success
```

## Step 5 — Smoke Test

```bash
# Run the pre-flight check
bash scripts/pre_flight_check.sh

# Run devnet smoke test
npx ts-node scripts/devnet_smoke_test.ts
```

## Step 6 — Run the Full Stack Locally

```bash
# Backend (from repo root)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # edit .env with real values
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd ui
npm install --legacy-peer-deps
cp .env.example .env    # set VITE_API_BASE_URL=http://localhost:8000
npm run dev
# → open http://localhost:5173
```

## Step 7 — Connect Wallet and Test

1. Open http://localhost:5173 in a browser with Phantom or Solflare installed.
2. Switch the extension to **Devnet** network.
3. Click **Connect Wallet** — the WalletMultiButton shows a wallet selection modal.
4. Accept the risk disclosure.
5. Mint a devnet note (denomination in sats, expiry in minutes).
6. Copy the claim URL and open in a new tab to claim.

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `Cargo.lock version 4` | `cargo-build-sbf` too old | Run `solana-install update` or use `-- --no-idl` flag |
| `insufficient funds` | Wallet has no devnet SOL | Run `solana airdrop 2` |
| `Program already deployed` | Previous deploy exists | Use `anchor upgrade` instead of `anchor deploy` |
| `Wallet not detected` | Extension not installed | Install Phantom from phantom.app |
| CORS error in browser | Backend not running | Start `uvicorn main:app --port 8000` |

## Environment Variables for Mainnet (Future)

```env
# .env (backend)
ENV=production
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
ANCHOR_PROGRAM_ID=<mainnet-program-id>
FEE_SPONSORING_ENABLED=true
FEE_SPONSOR_WALLET=<funded-pubkey>

# ui/.env
VITE_SOLANA_NETWORK=mainnet-beta
VITE_SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
```
