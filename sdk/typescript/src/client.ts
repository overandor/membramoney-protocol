const DEFAULT_BASE_URL = "https://api.membramoney.dev";

export interface ClientConfig {
  baseUrl?: string;
  apiKey?: string;
  timeout?: number;
}

export class MembraClient {
  private baseUrl: string;
  private apiKey?: string;
  private timeout: number;

  constructor(config: ClientConfig = {}) {
    this.baseUrl = config.baseUrl || DEFAULT_BASE_URL;
    this.apiKey = config.apiKey;
    this.timeout = config.timeout || 30000;
  }

  private async request<T>(path: string, opts?: RequestInit): Promise<T> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    const res = await fetch(`${this.baseUrl}${path}`, {
      ...opts,
      headers: {
        "Content-Type": "application/json",
        ...(this.apiKey ? { Authorization: `Bearer ${this.apiKey}` } : {}),
        ...opts?.headers,
      },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || res.statusText);
    }
    return res.json() as Promise<T>;
  }

  async health() {
    return this.request<{ status: string; devnet: boolean }>("/health");
  }

  async createClaim(body: {
    wallet_address: string;
    denomination_sats: number;
    expires_minutes: number;
    risk_version: string;
    idempotency_key?: string;
  }) {
    return this.request<{
      claim_id: string;
      claim_url: string;
      pin_hash: string;
      expires_at: string;
      denomination_sats: number;
    }>("/api/v1/claims/create", { method: "POST", body: JSON.stringify(body) });
  }

  async validateClaim(body: { claim_id: string; pin: string; claimant_wallet: string }) {
    return this.request<{
      valid: boolean;
      claim_id: string;
      message: string;
      denomination_sats?: number;
    }>("/api/v1/claims/validate", { method: "POST", body: JSON.stringify(body) });
  }
}
