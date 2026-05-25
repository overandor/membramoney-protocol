import React, { useState } from "react";

const API_BASE_DEFAULT =
  (import.meta as any).env?.VITE_API_BASE_URL || "http://localhost:8000";

// ── Types ──────────────────────────────────────────────────────────────────

type Method = "GET" | "POST" | "DELETE";

interface RouteDoc {
  method: Method;
  path: string;
  description: string;
  requestBody?: string;
  response?: string;
}

interface Section {
  title: string;
  routes: RouteDoc[];
}

// ── Route data ─────────────────────────────────────────────────────────────

const sections: Section[] = [
  {
    title: "Health",
    routes: [
      {
        method: "GET",
        path: "/health",
        description: "System health — returns status, env, devnet flag, and timestamp.",
        response: `{ "status": "ok", "env": "devnet", "devnet": true, "timestamp": "2024-01-01T00:00:00Z" }`,
      },
      {
        method: "GET",
        path: "/ready",
        description: "Readiness check — confirms the service is ready to accept traffic.",
        response: `{ "status": "ready" }`,
      },
      {
        method: "GET",
        path: "/api/v1/metrics",
        description: "Production metrics — Prometheus-compatible or JSON metrics snapshot.",
        response: `{ "uptime_seconds": 3600, "requests_total": 42000, "error_rate": 0.001 }`,
      },
    ],
  },
  {
    title: "Risk Disclosure",
    routes: [
      {
        method: "GET",
        path: "/api/v1/risk-disclosure",
        description: "Fetch the current risk disclosure text and version hash.",
        response: `{ "version": "v1.0", "text": "EXPERIMENTAL DEVNET ONLY...", "hash": "sha256:abc..." }`,
      },
      {
        method: "POST",
        path: "/api/v1/risk-disclosure/accept",
        description: "Record wallet acceptance of a specific risk disclosure version.",
        requestBody: `{ "wallet_address": "So1...", "risk_version": "v1.0" }`,
        response: `{ "accepted": true, "wallet_address": "So1...", "accepted_at": "2024-01-01T00:00:00Z", "version": "v1.0" }`,
      },
    ],
  },
  {
    title: "Bearer Notes (Core)",
    routes: [
      {
        method: "POST",
        path: "/api/v1/claims/create",
        description: "Mint a new BTC-denominated bearer note linked to a wallet.",
        requestBody: `{
  "wallet_address": "So1...",
  "denomination_sats": 100000,
  "expires_minutes": 60,
  "risk_version": "v1.0",
  "idempotency_key": "optional-uuid"
}`,
        response: `{
  "claim_id": "claim_abc123",
  "claim_url": "https://app.membra.money/claim/claim_abc123",
  "pin_hash": "sha256:...",
  "expires_at": "2024-01-01T01:00:00Z",
  "denomination_sats": 100000,
  "devnet_warning": "EXPERIMENTAL DEVNET ONLY"
}`,
      },
      {
        method: "POST",
        path: "/api/v1/claims/validate",
        description: "Validate a claim using its ID and PIN before redemption.",
        requestBody: `{
  "claim_id": "claim_abc123",
  "pin": "1234",
  "claimant_wallet": "So1..."
}`,
        response: `{
  "valid": true,
  "claim_id": "claim_abc123",
  "message": "Claim is valid",
  "denomination_sats": 100000
}`,
      },
      {
        method: "POST",
        path: "/api/v1/claims",
        description: "Low-level claim creation for programmatic issuers.",
        requestBody: `{
  "issuer_id": "issuer_001",
  "asset_type": "BTC",
  "denomination": 100000,
  "owner": "So1...",
  "bearer_condition": "pin:1234",
  "expiry_minutes": 60
}`,
        response: `{ "claim_id": "claim_abc123", "status": "active" }`,
      },
      {
        method: "GET",
        path: "/api/v1/claims/{claim_id}",
        description: "Fetch the current state of a bearer note by claim ID.",
        response: `{
  "claim_id": "claim_abc123",
  "status": "active",
  "denomination_sats": 100000,
  "owner": "So1...",
  "expires_at": "2024-01-01T01:00:00Z"
}`,
      },
      {
        method: "POST",
        path: "/api/v1/claims/{claim_id}/transfer",
        description: "Transfer ownership of a bearer note from one user to another.",
        requestBody: `{ "from_user": "So1...", "to_user": "So2..." }`,
        response: `{ "success": true, "claim_id": "claim_abc123", "message": "Transfer complete" }`,
      },
      {
        method: "POST",
        path: "/api/v1/claims/{claim_id}/split",
        description: "Atomically split a bearer note into two notes with given amounts.",
        requestBody: `{ "amounts": [60000, 40000] }`,
        response: `{ "success": true, "new_claim_ids": ["claim_x1", "claim_x2"] }`,
      },
      {
        method: "POST",
        path: "/api/v1/claims/{claim_id}/redeem",
        description: "Redeem a bearer note to a destination address on a target chain.",
        requestBody: `{
  "user_id": "So1...",
  "pin": "1234",
  "destination": "bc1q...",
  "chain": "bitcoin"
}`,
        response: `{ "success": true, "receipt_id": "rcpt_abc" }`,
      },
    ],
  },
  {
    title: "Reserves & Stats",
    routes: [
      {
        method: "GET",
        path: "/api/v1/reserves",
        description: "On-chain reserve status with ratio and attestation timestamp.",
        response: `{
  "status": "healthy",
  "reserve_ratio_bps": 10000,
  "attested_at": "2024-01-01T00:00:00Z",
  "disclaimer": "DEVNET",
  "devnet_only": true
}`,
      },
      {
        method: "GET",
        path: "/api/v1/stats",
        description: "Protocol statistics: total notes, active claims, redeemed notes, reserve ratio.",
        response: `{
  "total_notes": 1250,
  "redeemed_notes": 430,
  "active_claims": 820,
  "reserve_ratio_bps": 10000,
  "devnet": true,
  "generated_at": "2024-01-01T00:00:00Z"
}`,
      },
      {
        method: "GET",
        path: "/api/v1/fees/savings?amount_sats=N",
        description: "Calculate fee savings vs BTC on-chain for a given transfer amount.",
        response: `{
  "amount_transferred_sats": 100000,
  "btc_network_fees": { "low_congestion_sats": 1000, "medium_congestion_sats": 5000, "high_congestion_sats": 50000 },
  "membra_fee_sats": 0,
  "user_pays_sats": 0,
  "savings_vs_btc": { "low_congestion_pct": 100, "medium_congestion_pct": 100, "high_congestion_pct": 100 }
}`,
      },
      {
        method: "GET",
        path: "/api/v1/sponsor/status",
        description: "Check whether fee sponsoring is currently active.",
        response: `{
  "fee_sponsoring_enabled": true,
  "user_pays_fees": false,
  "solana_fee_per_tx_lamports": 5000,
  "explanation": "Protocol sponsors all Solana fees",
  "devnet": true
}`,
      },
    ],
  },
  {
    title: "Identity",
    routes: [
      {
        method: "POST",
        path: "/api/v1/identity/register",
        description: "Register a username linked to a wallet address.",
        requestBody: `{ "username": "alice", "wallet_address": "So1..." }`,
        response: `{ "username": "alice", "wallet_address": "So1...", "tag": "@alice#1234" }`,
      },
      {
        method: "GET",
        path: "/api/v1/identity/resolve/{identifier}",
        description: "Resolve a username or tag to its wallet address.",
        response: `{ "identifier": "alice", "wallet_address": "So1...", "resolved_at": "2024-01-01T00:00:00Z" }`,
      },
      {
        method: "POST",
        path: "/api/v1/identity/rotate-tag",
        description: "Rotate the discriminator tag on a username for privacy.",
        requestBody: `{ "username": "alice" }`,
        response: `{ "username": "alice", "new_tag": "@alice#5678" }`,
      },
    ],
  },
  {
    title: "Ledger",
    routes: [
      {
        method: "GET",
        path: "/api/v1/ledger/balance/{account_id}",
        description: "Fetch the current ledger balance for an account.",
        response: `{ "account_id": "acc_001", "balance_sats": 500000, "currency": "BTC" }`,
      },
      {
        method: "GET",
        path: "/api/v1/ledger/history/{account_id}?limit=N",
        description: "Paginated ledger transaction history for an account.",
        response: `{
  "account_id": "acc_001",
  "transactions": [
    { "tx_id": "tx_1", "type": "credit", "amount_sats": 100000, "timestamp": "2024-01-01T00:00:00Z" }
  ],
  "count": 1
}`,
      },
    ],
  },
  {
    title: "Settlement",
    routes: [
      {
        method: "GET",
        path: "/api/v1/settlement/quote?amount=N&chain=solana",
        description: "Get a settlement quote for a given amount and target chain.",
        response: `{ "amount_sats": 100000, "chain": "solana", "estimated_fee_sats": 0, "estimated_time_ms": 400 }`,
      },
      {
        method: "GET",
        path: "/api/v1/settlement/status/{batch_id}",
        description: "Check the status of an on-chain settlement batch.",
        response: `{ "batch_id": "batch_001", "status": "confirmed", "confirmed_at": "2024-01-01T00:00:00Z" }`,
      },
    ],
  },
  {
    title: "Treasury",
    routes: [
      {
        method: "GET",
        path: "/api/v1/treasury/reserves",
        description: "Fetch multi-asset treasury reserve balances.",
        response: `{ "btc": 1.5, "sol": 200.0, "eth": 10.0, "usdc": 50000.0, "updated_at": "2024-01-01T00:00:00Z" }`,
      },
      {
        method: "GET",
        path: "/api/v1/treasury/batches/pending",
        description: "List all pending treasury settlement batches awaiting operator signatures.",
        response: `{ "batches": [{ "batch_id": "batch_001", "status": "pending", "created_at": "2024-01-01T00:00:00Z" }], "count": 1 }`,
      },
      {
        method: "POST",
        path: "/api/v1/treasury/batches/{batch_id}/sign",
        description: "Sign a pending batch with an operator key.",
        requestBody: `{ "operator_id": "op_001", "signature_hex": "0xdeadbeef..." }`,
        response: `{ "success": true }`,
      },
      {
        method: "POST",
        path: "/api/v1/treasury/batches/{batch_id}/reject",
        description: "Reject a pending batch with a reason.",
        requestBody: `{ "operator_id": "op_001", "reason": "Suspicious transaction" }`,
        response: `{ "success": true }`,
      },
      {
        method: "POST",
        path: "/api/v1/treasury/operators",
        description: "Register a new treasury operator with their public key.",
        requestBody: `{ "operator_id": "op_001", "name": "Alice Operator", "public_key": "0x..." }`,
        response: `{ "operator_id": "op_001", "registered_at": "2024-01-01T00:00:00Z" }`,
      },
      {
        method: "GET",
        path: "/api/v1/treasury/audit",
        description: "Full treasury audit log of all operator actions.",
        response: `{ "events": [{ "event_id": "evt_1", "action": "sign", "operator_id": "op_001", "timestamp": "2024-01-01T00:00:00Z" }], "count": 1 }`,
      },
    ],
  },
  {
    title: "Redemption",
    routes: [
      {
        method: "GET",
        path: "/api/v1/redemption/queue",
        description: "List all redemption requests in the queue.",
        response: `{ "queue": [{ "receipt_id": "rcpt_001", "status": "pending", "amount_sats": 100000 }], "count": 1 }`,
      },
      {
        method: "POST",
        path: "/api/v1/redemption/{receipt_id}/approve",
        description: "Approve a redemption request.",
        requestBody: `{ "operator_id": "op_001", "required_approvals": 2 }`,
        response: `{ "success": true, "receipt_id": "rcpt_001", "status": "approved" }`,
      },
      {
        method: "POST",
        path: "/api/v1/redemption/{receipt_id}/reject",
        description: "Reject a redemption request with a reason.",
        requestBody: `{ "operator_id": "op_001", "reason": "KYC not complete" }`,
        response: `{ "success": true, "receipt_id": "rcpt_001", "status": "rejected" }`,
      },
      {
        method: "GET",
        path: "/api/v1/redemption/{receipt_id}",
        description: "Fetch the current state of a specific redemption receipt.",
        response: `{ "receipt_id": "rcpt_001", "status": "pending", "amount_sats": 100000, "destination": "bc1q..." }`,
      },
      {
        method: "GET",
        path: "/api/v1/redemption/audit/log",
        description: "Full audit log of all redemption actions.",
        response: `{ "events": [{ "action": "approve", "receipt_id": "rcpt_001", "timestamp": "2024-01-01T00:00:00Z" }] }`,
      },
      {
        method: "GET",
        path: "/api/v1/redemption/quarantine/list",
        description: "List all redemption requests currently in quarantine.",
        response: `{ "quarantined": [{ "receipt_id": "rcpt_002", "reason": "AML flag", "quarantined_at": "2024-01-01T00:00:00Z" }] }`,
      },
    ],
  },
  {
    title: "Compliance & Security",
    routes: [
      {
        method: "POST",
        path: "/api/v1/compliance/screen",
        description: "Run an AML / KYC / sanctions screening on a user ID.",
        requestBody: `{ "user_id": "So1...", "screening_type": "aml" }`,
        response: `{ "user_id": "So1...", "screening_type": "aml", "result": "clear", "flagged": false }`,
      },
      {
        method: "GET",
        path: "/api/v1/compliance/quarantine",
        description: "List all users currently in compliance quarantine.",
        response: `{ "users": [{ "user_id": "So1...", "reason": "sanctions hit", "quarantined_at": "2024-01-01T00:00:00Z" }] }`,
      },
      {
        method: "POST",
        path: "/api/v1/security/check",
        description: "Run anomaly detection and velocity checks on a transaction.",
        requestBody: `{
  "user_id": "So1...",
  "amount": 100000,
  "ip_hash": "sha256:...",
  "device_fingerprint": "fp_abc"
}`,
        response: `{ "user_id": "So1...", "anomaly_detected": false, "velocity_exceeded": false, "risk_score": 12 }`,
      },
    ],
  },
  {
    title: "FileLife (Appraisal)",
    routes: [
      {
        method: "POST",
        path: "/appraisal/run",
        description: "Trigger a new appraisal run.",
        requestBody: `{}`,
        response: `{ "run_id": "run_001", "status": "started", "started_at": "2024-01-01T00:00:00Z" }`,
      },
      {
        method: "GET",
        path: "/appraisal/latest",
        description: "Fetch the latest completed appraisal result.",
        response: `{ "run_id": "run_001", "score": 0.98, "completed_at": "2024-01-01T00:01:00Z" }`,
      },
      {
        method: "GET",
        path: "/appraisal/history",
        description: "Paginated history of all appraisal runs.",
        response: `{ "runs": [{ "run_id": "run_001", "score": 0.98, "completed_at": "2024-01-01T00:01:00Z" }], "count": 1 }`,
      },
      {
        method: "GET",
        path: "/appraisal/{run_id}",
        description: "Fetch the full result of a specific appraisal run.",
        response: `{ "run_id": "run_001", "status": "complete", "score": 0.98, "details": {} }`,
      },
      {
        method: "GET",
        path: "/appraisal/status",
        description: "Check whether the appraisal service is running.",
        response: `{ "status": "idle", "last_run": "run_001" }`,
      },
    ],
  },
];

// ── Helpers ────────────────────────────────────────────────────────────────

const methodColors: Record<Method, { bg: string; color: string }> = {
  GET: { bg: "rgba(79,209,197,0.15)", color: "var(--accent2)" },
  POST: { bg: "rgba(124,106,247,0.15)", color: "var(--accent)" },
  DELETE: { bg: "rgba(252,129,129,0.15)", color: "var(--red)" },
};

const MethodBadge: React.FC<{ method: Method }> = ({ method }) => {
  const { bg, color } = methodColors[method];
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "6px 10px",
        borderRadius: 4,
        background: bg,
        color,
        fontWeight: 600,
        fontSize: 11,
        fontFamily: "monospace",
        letterSpacing: "0.04em",
        flexShrink: 0,
      }}
    >
      {method}
    </span>
  );
};

const CodeBlock: React.FC<{ code: string }> = ({ code }) => (
  <pre
    style={{
      background: "var(--bg)",
      border: "1px solid var(--border)",
      borderRadius: "var(--radius-sm)",
      padding: "14px 16px",
      fontSize: 12,
      fontFamily: "monospace",
      color: "var(--text)",
      overflowX: "auto",
      margin: 0,
      lineHeight: 1.6,
      whiteSpace: "pre-wrap",
      wordBreak: "break-word",
    }}
  >
    {code}
  </pre>
);

const RouteRow: React.FC<{ route: RouteDoc; baseUrl: string }> = ({ route, baseUrl }) => {
  const [open, setOpen] = useState(false);

  return (
    <div
      style={{
        borderBottom: "1px solid var(--border)",
      }}
    >
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          width: "100%",
          background: "transparent",
          border: "none",
          padding: "14px 20px",
          display: "flex",
          alignItems: "center",
          gap: 14,
          cursor: "pointer",
          textAlign: "left",
        }}
      >
        <MethodBadge method={route.method} />
        <code
          style={{
            fontSize: 13,
            fontFamily: "monospace",
            color: "var(--text)",
            fontWeight: 500,
          }}
        >
          {route.path}
        </code>
        <span style={{ flex: 1, fontSize: 13, color: "var(--muted)", marginLeft: 8 }}>
          {route.description}
        </span>
        <span style={{ color: "var(--muted)", fontSize: 14, marginLeft: 8 }}>
          {open ? "▲" : "▼"}
        </span>
      </button>
      {open && (
        <div style={{ padding: "0 20px 20px", display: "flex", flexDirection: "column", gap: 14 }}>
          <div>
            <div
              style={{
                fontSize: 11,
                color: "var(--muted)",
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                fontWeight: 600,
                marginBottom: 6,
              }}
            >
              Full URL
            </div>
            <CodeBlock code={`${baseUrl}${route.path}`} />
          </div>
          {route.requestBody && (
            <div>
              <div
                style={{
                  fontSize: 11,
                  color: "var(--muted)",
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                  fontWeight: 600,
                  marginBottom: 6,
                }}
              >
                Request Body
              </div>
              <CodeBlock code={route.requestBody} />
            </div>
          )}
          {route.response && (
            <div>
              <div
                style={{
                  fontSize: 11,
                  color: "var(--muted)",
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                  fontWeight: 600,
                  marginBottom: 6,
                }}
              >
                Response Schema
              </div>
              <CodeBlock code={route.response} />
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const SectionBlock: React.FC<{ section: Section; baseUrl: string }> = ({ section, baseUrl }) => {
  const [expanded, setExpanded] = useState(true);

  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius)",
        overflow: "hidden",
        marginBottom: 16,
      }}
    >
      <button
        onClick={() => setExpanded((e) => !e)}
        style={{
          width: "100%",
          background: "var(--surface2)",
          border: "none",
          borderBottom: expanded ? "1px solid var(--border)" : "none",
          padding: "14px 20px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          cursor: "pointer",
          textAlign: "left",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span
            style={{
              fontSize: 13,
              fontWeight: 700,
              color: "var(--text)",
              letterSpacing: "0.01em",
            }}
          >
            {section.title}
          </span>
          <span
            style={{
              fontSize: 11,
              color: "var(--muted)",
              background: "var(--surface3)",
              border: "1px solid var(--border)",
              borderRadius: 10,
              padding: "2px 8px",
            }}
          >
            {section.routes.length} route{section.routes.length !== 1 ? "s" : ""}
          </span>
        </div>
        <span style={{ color: "var(--muted)", fontSize: 14 }}>{expanded ? "▲" : "▼"}</span>
      </button>
      {expanded &&
        section.routes.map((route) => (
          <RouteRow key={`${route.method}:${route.path}`} route={route} baseUrl={baseUrl} />
        ))}
    </div>
  );
};

// ── Page ───────────────────────────────────────────────────────────────────

const ApiDocs: React.FC = () => {
  const [baseUrl, setBaseUrl] = useState(API_BASE_DEFAULT);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(baseUrl).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  const totalRoutes = sections.reduce((n, s) => n + s.routes.length, 0);

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: "0 24px 80px" }}>
      {/* Header */}
      <div style={{ padding: "48px 0 36px" }}>
        <div
          style={{
            fontSize: 11,
            color: "var(--muted)",
            textTransform: "uppercase",
            letterSpacing: "0.1em",
            fontWeight: 600,
            marginBottom: 12,
          }}
        >
          Reference
        </div>
        <h1
          style={{
            fontSize: "clamp(1.8rem, 4vw, 2.8rem)",
            fontWeight: 900,
            letterSpacing: "-0.02em",
            background: "linear-gradient(135deg, var(--accent), var(--accent2))",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
            marginBottom: 12,
          }}
        >
          API Documentation
        </h1>
        <p style={{ color: "var(--muted)", fontSize: 15 }}>
          {sections.length} sections · {totalRoutes} routes · REST/JSON
        </p>
      </div>

      {/* Base URL bar */}
      <div
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius)",
          padding: "16px 20px",
          display: "flex",
          alignItems: "center",
          gap: 12,
          marginBottom: 32,
          flexWrap: "wrap",
        }}
      >
        <span
          style={{
            fontSize: 11,
            color: "var(--muted)",
            textTransform: "uppercase",
            letterSpacing: "0.1em",
            fontWeight: 600,
            flexShrink: 0,
          }}
        >
          Base URL
        </span>
        <input
          type="text"
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          style={{
            flex: 1,
            minWidth: 200,
            background: "var(--bg)",
            border: "1px solid var(--border2)",
            borderRadius: "var(--radius-sm)",
            padding: "8px 12px",
            color: "var(--text)",
            fontFamily: "monospace",
            fontSize: 13,
          }}
        />
        <button
          onClick={handleCopy}
          style={{
            background: copied ? "var(--green)" : "var(--surface2)",
            border: "1px solid var(--border2)",
            borderRadius: "var(--radius-sm)",
            padding: "8px 16px",
            fontSize: 12,
            fontWeight: 600,
            color: copied ? "#0b0c15" : "var(--text)",
            cursor: "pointer",
            transition: "all 0.15s",
            flexShrink: 0,
          }}
        >
          {copied ? "Copied!" : "Copy Base URL"}
        </button>
      </div>

      {/* Sections */}
      {sections.map((section) => (
        <SectionBlock key={section.title} section={section} baseUrl={baseUrl} />
      ))}
    </div>
  );
};

export default ApiDocs;
