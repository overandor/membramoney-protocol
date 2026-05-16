# Membra Money Protocol

> **EXPERIMENTAL DEVNET ONLY — NOT REAL MONEY**
>
> This repository contains unaudited, experimental software intended for Solana devnet. No mainnet deployment path is enabled by default. There is no real BTC custody, no real money claims, and no guarantee of correctness.

## What is Membra Money?

Membra Money is an experimental devnet-first Solana protocol for Bitcoin-denominated bearer-note style claims. It allows:

- **Minting** devnet notes denominated in satoshis.
- **Transferring** notes between wallets.
- **Claiming** notes via PIN/code entry.
- **Redeeming** notes back to the issuer.
- **Auditing** note state and reserve attestations on-chain.

The protocol is intentionally simple to minimize attack surface. It does **not** implement real BTC bridges, real custody, or real money settlement. All values are simulated on devnet.

## Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                        User Browser                         │
│  ┌─────────────┐ ┌─────────────┐ ┌───────────────────────┐  │
│  │ WalletPanel │ │ MintNoteCard│ │   ClaimNoteCard       │  │
│  └─────────────┘ └─────────────┘ └───────────────────────┘  │
│  ┌─────────────┐ ┌─────────────┐ ┌───────────────────────┐  │
│  │ReserveStatus│ │ RiskDiscl.  │ │   DevnetBanner        │  │
│  └─────────────┘ └─────────────┘ └───────────────────────┘  │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP / WebSocket
┌─────────────────────────▼───────────────────────────────────┐
│                      FastAPI Backend                        │
│  ┌─────────────┐ ┌─────────────┐ ┌───────────────────────┐  │
│  │  /health    │ │ /api/v1/... │ │  Risk Disclosure      │  │
│  │  /ready     │ │  Claims     │ │  Reserve Metadata     │  │
│  └─────────────┘ └─────────────┘ └───────────────────────┘  │
└─────────────────────────┬───────────────────────────────────┘
                          │ RPC (devnet)
┌─────────────────────────▼───────────────────────────────────┐
│                Solana Devnet / Anchor Program                 │
│  ┌─────────────┐ ┌─────────────┐ ┌───────────────────────┐  │
│  │ ProtocolState│ │   Note     │ │ ReserveAttestation    │  │
│  └─────────────┘ └─────────────┘ └───────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Quickstart

### Prerequisites

- Solana CLI
- Anchor CLI
- Node.js 20+ and npm
- Python 3.11+ and pip
- Docker (optional, for local backend)

### 1. Clone and setup

```bash
git clone https://github.com/overandor/membramoney-protocol.git
cd membramoney-protocol
```

### 2. Install toolchain

```bash
bash scripts/install_solana.sh
```

### 3. Build and test Anchor program

```bash
anchor build
anchor test
```

### 4. Run backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 5. Run UI

```bash
cd ui
npm install
npm run dev
```

### 6. Smoke test

```bash
bash scripts/pre_flight_check.sh
```

## Build / Test / Deploy Sequence

1. `anchor build` — compile program.
2. `anchor test` — run local validator + TS tests.
3. `pytest backend/tests/` — run backend tests.
4. `bash scripts/validate.sh` — run full validation suite.
5. `anchor deploy --provider.cluster devnet` — deploy to devnet.
6. `bash scripts/devnet_smoke_test.ts` — verify devnet deployment.

## Safety and Compliance Boundaries

- **Devnet only.** No mainnet deployment path is enabled.
- **No real BTC custody.** Reserve metadata is illustrative only.
- **No real money claims.** Notes have no off-chain value.
- **All secrets via environment variables.** No hardcoded keys.
- **Every UI screen shows `EXPERIMENTAL DEVNET ONLY`.**
- **No guaranteed returns, no risk-free language.**

See `SECURITY.md` and `MAINNET_READINESS.md` for full details.

## Repository Layout

```text
membramoney-protocol/
  README.md
  SECURITY.md
  MAINNET_READINESS.md
  DEVNET_DEPLOYMENT.md
  .gitignore
  .env.example
  Anchor.toml
  Cargo.toml
  package.json
  tsconfig.json
  programs/membramoney/
  backend/
  ui/
  scripts/
  tests/
```

## License

MIT — See LICENSE for details. Use at your own risk.
