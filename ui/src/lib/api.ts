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

export type PaymentAsset = "SOLANA_DEVNET_USDC" | "SOLANA_DEVNET_SOL" | "BTC_LIGHTNING";
export type DeliveryChannel = "link" | "qr" | "email" | "sms" | "physical";

export interface RailsResponse {
  primary: string;
  minimum_usd_cents: number;
  rails: Record<string, Record<string, unknown>>;
  custody_disclaimer: string;
}

export interface MicropaymentCreateRequest {
  sender_wallet: string;
  usd_cents: number;
  asset: PaymentAsset;
  delivery_channel: DeliveryChannel;
  recipient_hint?: string;
  expires_minutes: number;
  risk_version: string;
  sender_signature?: string;
  escrow_tx_signature?: string;
}

export interface MicropaymentCreateResponse {
  payment_id: string;
  claim_id: string;
  claim_url: string;
  qr_payload: string;
  asset: string;
  usd_cents: number;
  status: string;
  funding_status: string;
  delivery_channel: string;
  expires_at: string;
  backend_degraded: boolean;
  devnet_warning: string;
  custody_disclaimer: string;
}

export interface MicropaymentResponse {
  payment_id: string;
  claim_id: string;
  sender_wallet: string;
  recipient_hint?: string;
  usd_cents: number;
  asset: string;
  status: string;
  funding_status: string;
  delivery_channel: string;
  expires_at: string;
  devnet_warning: string;
  custody_disclaimer: string;
}

export interface ClaimPreviewResponse {
  claim_id: string;
  payment_id?: string;
  usd_cents?: number;
  asset?: string;
  status: string;
  expired: boolean;
  message: string;
  devnet_warning: string;
}

export interface ClaimRedeemRequest {
  secret: string;
  claimant_wallet: string;
  claimant_signature?: string;
}

export interface ClaimRedeemResponse {
  redeemed: boolean;
  claim_id: string;
  payment_id?: string;
  status: string;
  message: string;
  devnet_warning: string;
}

export interface DeliveryRequest {
  channel: DeliveryChannel;
  destination?: string;
}

export interface DeliveryResponse {
  claim_id: string;
  channel: string;
  sent: boolean;
  degraded: boolean;
  message: string;
  devnet_warning: string;
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
  total_micropayments: number;
  active_micropayments: number;
  reserve_ratio_bps: number;
  devnet: boolean;
  generated_at: string;
}

export const api = {
  health: () => fetchJson<HealthResponse>("/health"),
  ready: () => fetchJson<HealthResponse>("/ready"),
  getRails: () => fetchJson<RailsResponse>("/api/v1/rails"),
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
  createMicropayment: (body: MicropaymentCreateRequest) =>
    fetchJson<MicropaymentCreateResponse>("/api/v1/micropayments", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getMicropayment: (paymentId: string) =>
    fetchJson<MicropaymentResponse>(`/api/v1/micropayments/${paymentId}`),
  previewClaim: (claimId: string) =>
    fetchJson<ClaimPreviewResponse>(`/api/v1/claims/${claimId}`),
  redeemClaim: (claimId: string, body: ClaimRedeemRequest) =>
    fetchJson<ClaimRedeemResponse>(`/api/v1/claims/${claimId}/redeem`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  deliverClaim: (claimId: string, body: DeliveryRequest) =>
    fetchJson<DeliveryResponse>(`/api/v1/claims/${claimId}/delivery`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getReserves: () => fetchJson<ReserveResponse>("/api/v1/reserves"),
  getStats: () => fetchJson<StatsResponse>("/api/v1/stats"),
};
