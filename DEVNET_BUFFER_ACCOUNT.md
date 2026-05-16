# Devnet Buffer Account Recovery Info

**Date:** $(date)
**Status:** Deploy attempt failed — insufficient funds (0 SOL)

## Buffer Account Seed Phrase
```
lyrics have liberty easy tag version melody armor phone jar disagree genuine
```

## How to recover the buffer account's lamports

1. Recover the keypair:
   ```bash
   solana-keygen recover --outfile /tmp/buffer-keypair.json
   # Enter seed phrase above when prompted
   ```

2. Close the buffer account and reclaim SOL:
   ```bash
   solana program close <BUFFER_ACCOUNT_ADDRESS> --buffer-authority /tmp/buffer-keypair.json
   ```

## Wallet needing funds
- Address: `CFvvtuX8JMia5MY4m3tkjJ6uG45Xwbm7swS7qgDXsStL`
- Required: ~3.5 SOL for program deploy + 0.001265 SOL fee
- Current: 0 SOL

## Funding options
- Solana Devnet Faucet: https://faucet.solana.com/
- Discord `#devnet-faucet` channel
- Request from another devnet wallet
