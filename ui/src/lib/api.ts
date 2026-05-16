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
};
