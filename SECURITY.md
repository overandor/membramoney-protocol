# Security Policy — Membra Money Protocol

> **EXPERIMENTAL DEVNET ONLY**
>
> This is unaudited software. Do not use with real funds.

## Secret Handling

- **Never commit secrets.** All credentials live in environment variables or secret managers.
- **Rotate regularly.** API keys, JWT secrets, and HMAC peppers must be rotated before any staging or production use.
- **Use a secrets manager.** For any non-local deployment, use AWS Secrets Manager, 1Password Secrets Automation, Doppler, or HashiCorp Vault.
- **No hardcoded values.** No private keys, wallet seeds, GitHub tokens, or API keys are allowed in source code.

## Claim-Link Threat Model

Claim links are the primary user-facing attack surface:

| Threat | Mitigation |
|--------|------------|
| Brute-force PIN guessing | Rate limiting (5 attempts per PIN per hour). PINs are hashed with salt + pepper. |
| Link interception | Links are single-use and expire. HTTPS is mandatory. |
| Replay attacks | Claim codes are consumed on first valid use and marked on-chain. |
| Phishing | UI displays protocol name + devnet warning. No shortened URLs. |
| Server compromise | Minimal data stored. No real custody keys. HMAC pepper is required to forge claims. |

## Wallet Safety

- Users must verify they are connected to **Solana Devnet** before interacting.
- The UI displays the active cluster clearly.
- Never sign unexpected transactions.
- Report suspicious transactions immediately.

## Reporting Policy

If you discover a security issue:

1. **Do not open a public issue.**
2. Email `security@membra.money` (placeholder — update before use).
3. Include reproduction steps and impact assessment.
4. Allow 90 days for remediation before public disclosure.

## Devnet / Mainnet Separation

- The codebase is configured for **devnet by default**.
- No mainnet RPC endpoints are included in `.env.example`.
- `MAINNET_READINESS.md` defines the full checklist before any mainnet consideration.
- Program IDs must be manually updated and reviewed before mainnet deployment.

## Compliance Notes

- This protocol does not implement KYC/AML.
- No real money transmission occurs on devnet.
- Any move toward mainnet requires legal review and jurisdictional analysis.
