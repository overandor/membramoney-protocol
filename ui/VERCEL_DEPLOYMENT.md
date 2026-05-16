# UI Deployment — Vercel

## Prerequisites

- Vercel account (free tier works)
- Vercel CLI: `npm i -g vercel`

## Deploy

```bash
cd ui
vercel
```

## Environment Variables

In the Vercel dashboard, add:

- `VITE_API_BASE_URL` — URL of your deployed backend (e.g., `https://membramoney-backend.onrender.com`)
- `VITE_SOLANA_NETWORK` = `devnet`
- `VITE_ANCHOR_PROGRAM_ID` — Your deployed program ID

## Build Settings

Vercel auto-detects Vite. If not:

- **Framework Preset:** Vite
- **Build Command:** `npm run build`
- **Output Directory:** `dist`
- **Install Command:** `npm install`

## Important

- The UI is **devnet only**. Ensure `VITE_SOLANA_NETWORK=devnet`.
- Do not deploy with production API keys or secrets.
- All API calls go to `VITE_API_BASE_URL`.
