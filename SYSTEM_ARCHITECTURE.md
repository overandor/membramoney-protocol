# MEMBRA SYSTEM ARCHITECTURE

## Canonical Runtime

`membramoney-protocol`

The canonical monetary runtime responsible for:

- treasury accounting
- reserve coordination
- settlement orchestration
- validator consensus
- liquidity intelligence
- sovereign reserve federation
- governance execution
- monetary coordination

---

## Walletless Transfer Layer

Repository: `sms`

Responsibilities:

- expiring payment links
- bearer-note lifecycle
- SMS delivery
- walletless onboarding
- claim acceptance
- consumer transfer UX

Flow:

Card Purchase
→ Membra Note
→ Private Claim Link
→ SMS Delivery
→ Recipient Claim
→ Settlement

---

## Merchant Gateway

Repository: `membra-qr-gateway`

Responsibilities:

- QR redemption
- NFC ingress
- merchant settlement
- POS interactions
- checkout claims
- merchant treasury routing

---

## Treasury Intelligence

Repository: `membra_kpi`

Responsibilities:

- reserve telemetry
- governance visibility
- treasury analytics
- systemic risk monitoring
- validator observability
- liquidity metrics

---

## Ecosystem Shell

Repository: `membra`

Responsibilities:

- onboarding
- ecosystem coordination
- governance portal
- documentation
- public runtime shell
- network access layer

---

# SYSTEM FLOW

User
→ SMS
→ Merchant Gateway
→ Protocol Runtime
→ Treasury Coordination
→ KPI Intelligence

---

# CORE PRODUCT MODEL

1. User purchases fixed-value digital note.
2. Protocol reserves backing liquidity.
3. SMS runtime creates expiring bearer link.
4. Recipient claims value.
5. Merchant gateway redeems notes.
6. Treasury runtime settles balances.
7. KPI runtime monitors system health.

---

# PRINCIPLE

Users interact with:

- links
- QR codes
- SMS
- merchant claims

The protocol handles:

- reserve accounting
- settlement
- liquidity
- consensus
- governance
- treasury intelligence
