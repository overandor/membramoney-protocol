const API_BASE = (import.meta as any).env?.VITE_API_BASE_URL || "http://localhost:8000";

async function fetchJson<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...opts?.headers },
    ...opts,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json() as Promise<T>;
}

export interface HealthResponse {
  status: string;
  env: string;
  devnet: boolean;
  timestamp: string;
}

export interface RiskDisclosureResponse {
  version: string;
  text: string;
  hash: string;
}

export interface RiskAcceptRequest {
  wallet_address: string;
  accepted_version: string;
  signature?: string;
}

export interface RiskAcceptResponse {
  accepted: boolean;
  wallet_address: string;
  accepted_at: string;
  version: string;
}

export interface ClaimCreateRequest {
  wallet_address: string;
  denomination_sats: number;
  expires_minutes: number;
  risk_version: string;
  idempotency_key?: string;
}

export interface ClaimCreateResponse {
  claim_id: string;
  claim_url: string;
  pin_hash: string;
  expires_at: string;
  denomination_sats: number;
  devnet_warning: string;
}

export interface ClaimValidateRequest {
  claim_id: string;
  pin: string;
  claimant_wallet: string;
}

export interface ClaimValidateResponse {
  valid: boolean;
  claim_id: string;
  message: string;
  denomination_sats?: number;
}

export interface ReserveResponse {
  status: string;
  reserve_ratio_bps: number;
  attested_at?: string;
  disclaimer: string;
  devnet_only: boolean;
}

export interface StatsResponse {
  total_notes: number;
  redeemed_notes: number;
  active_claims: number;
  reserve_ratio_bps: number;
  devnet: boolean;
  generated_at: string;
}

export interface ErrorResponse {
  error: {
    code: string;
    message: string;
    status_code: number;
  };
  meta: {
    request_id: string;
    timestamp: string;
    devnet: boolean;
    production_ready: boolean;
  };
}

export interface AuditEvent {
  event_id: string;
  event_type: string;
  timestamp: string;
  details: Record<string, unknown>;
}

export interface AuditEventsResponse {
  events: AuditEvent[];
  count: number;
}

export interface FeeSavingsResponse {
  amount_transferred_sats: number;
  btc_network_fees: {
    low_congestion_sats: number;
    medium_congestion_sats: number;
    high_congestion_sats: number;
  };
  membra_fee_sats: number;
  fee_sponsored: boolean;
  user_pays_sats: number;
  savings_vs_btc: {
    low_congestion_pct: number;
    medium_congestion_pct: number;
    high_congestion_pct: number;
  };
  settlement_time: {
    btc_confirmations: string;
    membra_solana: string;
  };
  btc_tps: number;
  solana_tps: number;
  innovation: Record<string, string>;
  disclaimer: string;
  devnet: boolean;
}

export interface SponsorStatusResponse {
  fee_sponsoring_enabled: boolean;
  user_pays_fees: boolean;
  solana_fee_per_tx_lamports: number;
  explanation: string;
  devnet: boolean;
}

export interface TransferResponse {
  success: boolean;
  claim_id: string;
  message?: string;
}

export interface SplitResponse {
  success: boolean;
  new_claim_ids: string[];
  message?: string;
}

export interface RedeemResponse {
  success: boolean;
  receipt_id?: string;
  message?: string;
}

export interface TreasuryReservesResponse {
  btc?: number;
  sol?: number;
  eth?: number;
  usdc?: number;
  updated_at?: string;
  [key: string]: unknown;
}

export interface PendingBatch {
  batch_id: string;
  created_at: string;
  amount?: number;
  status: string;
  [key: string]: unknown;
}

export interface PendingBatchesResponse {
  batches: PendingBatch[];
  count: number;
}

export interface ComplianceScreenResponse {
  user_id: string;
  screening_type: string;
  result: string;
  flagged: boolean;
  details?: Record<string, unknown>;
}

export interface SecurityCheckResponse {
  user_id: string;
  anomaly_detected: boolean;
  velocity_exceeded: boolean;
  risk_score?: number;
  details?: Record<string, unknown>;
}

export const api = {
  health: () => fetchJson<HealthResponse>("/health"),
  ready: () => fetchJson<HealthResponse>("/ready"),
  getRiskDisclosure: () => fetchJson<RiskDisclosureResponse>("/api/v1/risk-disclosure"),
  acceptRiskDisclosure: (body: RiskAcceptRequest) =>
    fetchJson<RiskAcceptResponse>("/api/v1/risk-disclosure/accept", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  createClaim: (body: ClaimCreateRequest) =>
    fetchJson<ClaimCreateResponse>("/api/v1/claims/create", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  validateClaim: (body: ClaimValidateRequest) =>
    fetchJson<ClaimValidateResponse>("/api/v1/claims/validate", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getReserves: () => fetchJson<ReserveResponse>("/api/v1/reserves"),
  getStats: () => fetchJson<StatsResponse>("/api/v1/stats"),
  getAuditEvents: (limit?: number) =>
    fetchJson<AuditEventsResponse>(`/api/v1/audit/events?limit=${limit || 100}`),
  getFeeSavings: (amountSats?: number) =>
    fetchJson<FeeSavingsResponse>(`/api/v1/fees/savings?amount_sats=${amountSats || 100000}`),
  getSponsorStatus: () => fetchJson<SponsorStatusResponse>("/api/v1/sponsor/status"),

  // Transfer, Split, Redeem
  transferClaim: (claimId: string, body: { from_user: string; to_user: string }) =>
    fetchJson<TransferResponse>(`/api/v1/claims/${claimId}/transfer`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  splitClaim: (claimId: string, body: { amounts: number[] }) =>
    fetchJson<SplitResponse>(`/api/v1/claims/${claimId}/split`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  redeemClaim: (claimId: string, body: { user_id: string; pin: string; destination: string; chain: string }) =>
    fetchJson<RedeemResponse>(`/api/v1/claims/${claimId}/redeem`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  // Treasury
  getTreasuryReserves: () => fetchJson<TreasuryReservesResponse>("/api/v1/treasury/reserves"),
  getPendingBatches: () => fetchJson<PendingBatchesResponse>("/api/v1/treasury/batches/pending"),
  signBatch: (batchId: string, body: { operator_id: string; signature_hex: string }) =>
    fetchJson<{ success: boolean }>(`/api/v1/treasury/batches/${batchId}/sign`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  rejectBatch: (batchId: string, body: { operator_id: string; reason: string }) =>
    fetchJson<{ success: boolean }>(`/api/v1/treasury/batches/${batchId}/reject`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  // Compliance & Security
  screenCompliance: (body: { user_id: string; screening_type: string }) =>
    fetchJson<ComplianceScreenResponse>("/api/v1/compliance/screen", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  securityCheck: (body: { user_id: string; amount: number; ip_hash: string; device_fingerprint: string }) =>
    fetchJson<SecurityCheckResponse>("/api/v1/security/check", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};
