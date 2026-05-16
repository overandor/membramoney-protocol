# Sequence Diagrams

## Claim Creation Flow
```
User -> Frontend: Connect wallet
Frontend -> Backend: POST /claims/create
Backend -> Redis: Check idempotency key
Backend -> DB: Insert claim record
Backend -> AuditLog: Log claim_created
Backend -> Frontend: Return claim_id + pin_hash
Frontend -> User: Display claim URL + PIN
```

## Claim Redemption Flow
```
User -> Frontend: Enter claim_id + PIN
Frontend -> Backend: POST /claims/validate
Backend -> DB: Fetch claim by ID
Backend -> Crypto: Verify PIN hash
Backend -> DB: Mark claim claimed
Backend -> AuditLog: Log claim_redeemed
Backend -> Frontend: Return denomination_sats
```

## Reserve Attestation Flow
```
Authority -> Backend: POST /reserves/attest
Backend -> DB: Insert reserve attestation
Backend -> AuditLog: Log reserve_attested
Backend -> Authority: Return attestation_hash
```

## Wallet Authentication Flow
```
User -> Backend: GET /auth/nonce/{wallet}
Backend -> Redis: Store nonce (5 min TTL)
Backend -> User: Return nonce
User -> Wallet: Sign nonce
User -> Backend: POST /auth/verify
Backend -> Redis: Verify nonce
Backend -> DB: Create/update user
Backend -> User: Return JWT access + refresh tokens
```
