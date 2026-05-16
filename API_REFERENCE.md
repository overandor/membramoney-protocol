# API Reference — Membra Money Protocol

**Last updated:** 2026-05-15
**Base URL:** `http://localhost:8000`
**Version:** `0.1.0-devnet`
**Status:** DEVNET / RESEARCH PREVIEW ONLY

## Authentication

No authentication required for devnet. All endpoints are public.

**Headers:**
```
Content-Type: application/json
X-Request-ID: <uuid>  (optional, auto-generated if absent)
```

## Common Response Format

All responses follow this structure:

```json
{
  "error": {
    "code": "HTTP_403",
    "message": "Risk disclosure not accepted for this wallet.",
    "status_code": 403
  },
  "meta": {
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2026-05-15T10:00:00Z",
    "devnet": true,
    "production_ready": false
  }
}
```

For successful responses, `error` is omitted.

## Endpoints

### Health & Readiness

#### GET `/health`

Liveness probe.

**Response:**
```json
{
  "status": "healthy",
  "env": "devnet",
  "devnet": true,
  "timestamp": "2026-05-15T10:00:00Z"
}
```

#### GET `/ready`

Readiness probe.

**Response:**
```json
{
  "status": "ready",
  "env": "devnet",
  "devnet": true,
  "timestamp": "2026-05-15T10:00:00Z"
}
```

---

### Risk Disclosure

#### GET `/api/v1/risk-disclosure`

Returns current risk disclosure text and version hash.

**Response:**
```json
{
  "version": "v1.0.0-devnet",
  "text": "This is an experimental devnet protocol...",
  "hash": "a3f5c8..."
}
```

#### POST `/api/v1/risk-disclosure/accept`

Records wallet acceptance of risk disclosure.

**Request:**
```json
{
  "wallet_address": "CFvvtuX8JMia5MY4m3tkjJ6uG45Xwbm7swS7qgDXsStL",
  "accepted_version": "v1.0.0-devnet",
  "signature": null
}
```

**Validation:**
- `wallet_address`: 32-44 chars
- `accepted_version`: must match current version

**Response (success):**
```json
{
  "accepted": true,
  "wallet_address": "CFvvtu...",
  "accepted_at": "2026-05-15T10:00:00Z",
  "version": "v1.0.0-devnet"
}
```

**Response (error):**
```json
{
  "error": {
    "code": "HTTP_400",
    "message": "Risk disclosure version mismatch. Expected v1.0.0-devnet, got v1.0.0",
    "status_code": 400
  },
  "meta": { ... }
}
```

---

### Claims

#### POST `/api/v1/claims/create`

Creates a new claim link with PIN. Requires risk acceptance.

**Request:**
```json
{
  "wallet_address": "CFvvtuX8JMia5MY4m3tkjJ6uG45Xwbm7swS7qgDXsStL",
  "denomination_sats": 1000000,
  "expires_minutes": 60,
  "risk_version": "v1.0.0-devnet",
  "idempotency_key": "unique-key-123"
}
```

**Validation:**
- `wallet_address`: 32-44 chars, must have accepted risk disclosure
- `denomination_sats`: >= 1
- `expires_minutes`: 1-129,600 (90 days)
- `risk_version`: must match current version
- `idempotency_key`: optional, max 64 chars

**Response (success):**
```json
{
  "claim_id": "550e8400-e29b-41d4-a716-446655440000",
  "claim_url": "http://localhost:8000/claim/550e8400-e29b-41d4-a716-446655440000",
  "pin_hash": "a3f5c8...",
  "expires_at": "2026-05-15T11:00:00Z",
  "denomination_sats": 1000000,
  "devnet_warning": "EXPERIMENTAL DEVNET ONLY — NOT REAL MONEY"
}
```

**Idempotency:**
If `idempotency_key` is provided and already used, returns the original claim without creating a new one.

**Response (idempotent replay):**
```json
{
  "claim_id": "550e8400-e29b-41d4-a716-446655440000",
  "claim_url": "...",
  "pin_hash": "a3f5c8...",
  "expires_at": "...",
  "denomination_sats": 1000000,
  "devnet_warning": "EXPERIMENTAL DEVNET ONLY — NOT REAL MONEY (idempotent replay)"
}
```

**Response (error - risk not accepted):**
```json
{
  "error": {
    "code": "HTTP_403",
    "message": "Risk disclosure not accepted for this wallet.",
    "status_code": 403
  },
  "meta": { ... }
}
```

#### POST `/api/v1/claims/validate`

Validates a claim ID + PIN. Brute-force protected.

**Request:**
```json
{
  "claim_id": "550e8400-e29b-41d4-a716-446655440000",
  "pin": "ABCD1234",
  "claimant_wallet": "CFvvtuX8JMia5MY4m3tkjJ6uG45Xwbm7swS7qgDXsStL"
}
```

**Validation:**
- `claim_id`: must exist
- `pin`: 4-32 chars
- `claimant_wallet`: 32-44 chars

**Response (success):**
```json
{
  "valid": true,
  "claim_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Claim validated successfully.",
  "denomination_sats": 1000000
}
```

**Response (invalid PIN):**
```json
{
  "valid": false,
  "claim_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Invalid PIN."
}
```

**Response (rate limited):**
```json
{
  "error": {
    "code": "HTTP_429",
    "message": "Too many attempts. Try again later.",
    "status_code": 429
  },
  "meta": { ... }
}
```

**Rate Limits:**
- Per IP: 2 requests/second, burst 20
- Per claim + wallet: 5 attempts per hour

---

### Reserves

#### GET `/api/v1/reserves`

Returns illustrative reserve status.

**Response:**
```json
{
  "status": "active",
  "reserve_ratio_bps": 10000,
  "attested_at": "2026-05-15T10:00:00Z",
  "disclaimer": "Reserve data is illustrative only. No real BTC custody exists.",
  "devnet_only": true
}
```

---

### Stats

#### GET `/api/v1/stats`

Returns protocol statistics.

**Response:**
```json
{
  "total_notes": 42,
  "redeemed_notes": 10,
  "active_claims": 32,
  "reserve_ratio_bps": 10000,
  "devnet": true,
  "generated_at": "2026-05-15T10:00:00Z"
}
```

---

### Audit

#### GET `/api/v1/audit/events`

Returns recent audit events.

**Query Parameters:**
- `limit`: int, default 100, max 1000

**Response:**
```json
{
  "events": [
    {
      "event_id": "...",
      "event_type": "claim_created",
      "timestamp": "2026-05-15T10:00:00Z",
      "details": {
        "claim_id": "...",
        "issuer": "...",
        "denomination_sats": 1000000
      }
    }
  ],
  "count": 1
}
```

---

## Rate Limiting

All endpoints are rate-limited per client IP:

- **Rate:** 2 requests/second
- **Burst:** 20 requests
- **Window:** 60 seconds

Exceeding the limit returns:
```json
{
  "detail": "Rate limit exceeded. Slow down.",
  "retry_after": 1,
  "devnet_warning": "EXPERIMENTAL DEVNET ONLY"
}
```

## Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| `HTTP_400` | 400 | Bad request (validation error) |
| `HTTP_403` | 403 | Forbidden (risk not accepted) |
| `HTTP_404` | 404 | Not found (claim doesn't exist) |
| `HTTP_429` | 429 | Too many requests (rate limited) |
| `HTTP_500` | 500 | Internal server error |
| `INTERNAL_ERROR` | 500 | Unexpected error |

## Middleware

Every request is processed through:

1. **RequestIDMiddleware** — injects `X-Request-ID`
2. **AuditLoggingMiddleware** — logs to stderr (JSON)
3. **RateLimitMiddleware** — token-bucket per IP
4. **CORSMiddleware** — CORS headers

## SDK Generation

The API conforms to OpenAPI 3.0. To generate an SDK:

```bash
# Generate OpenAPI spec from FastAPI
cd backend
python -c "from main import app; import json; print(json.dumps(app.openapi()))" > openapi.json

# Generate TypeScript client
npx openapi-typescript-codegen --input openapi.json --output sdk/
```

## curl Examples

### Health check
```bash
curl http://localhost:8000/health
```

### Get risk disclosure
```bash
curl http://localhost:8000/api/v1/risk-disclosure
```

### Accept risk disclosure
```bash
curl -X POST http://localhost:8000/api/v1/risk-disclosure/accept \
  -H "Content-Type: application/json" \
  -d '{"wallet_address": "CFvvtu...", "accepted_version": "v1.0.0-devnet"}'
```

### Create claim
```bash
curl -X POST http://localhost:8000/api/v1/claims/create \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: unique-key-123" \
  -d '{
    "wallet_address": "CFvvtu...",
    "denomination_sats": 1000000,
    "expires_minutes": 60,
    "risk_version": "v1.0.0-devnet"
  }'
```

### Validate claim
```bash
curl -X POST http://localhost:8000/api/v1/claims/validate \
  -H "Content-Type: application/json" \
  -d '{
    "claim_id": "...",
    "pin": "ABCD1234",
    "claimant_wallet": "CFvvtu..."
  }'
```

## Changelog

| Date | Change |
|------|--------|
| 2026-05-15 | Added idempotency keys, structured errors, rate limiting, audit logging |
| 2026-05-15 | Initial API with claims, reserves, risk disclosure |
