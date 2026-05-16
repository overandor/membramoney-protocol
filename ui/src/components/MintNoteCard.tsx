import React, { useMemo, useState } from "react";
import { api, DeliveryChannel, PaymentAsset } from "../lib/api";

interface Props {
  walletAddress: string | null;
  riskAccepted: boolean;
  onMint?: () => void;
}

const assetLabels: Record<PaymentAsset, string> = {
  SOLANA_DEVNET_USDC: "Solana Devnet USDC",
  SOLANA_DEVNET_SOL: "Solana Devnet SOL",
  BTC_LIGHTNING: "BTC Lightning (disabled unless configured)",
};

const MintNoteCard: React.FC<Props> = ({ walletAddress, riskAccepted, onMint }) => {
  const [usdCents, setUsdCents] = useState<number>(1);
  const [expiryMinutes, setExpiryMinutes] = useState<number>(60);
  const [asset, setAsset] = useState<PaymentAsset>("SOLANA_DEVNET_USDC");
  const [deliveryChannel, setDeliveryChannel] = useState<DeliveryChannel>("qr");
  const [recipient, setRecipient] = useState("");
  const [claimUrl, setClaimUrl] = useState("");
  const [qrPayload, setQrPayload] = useState("");
  const [status, setStatus] = useState<{ type: "success" | "error" | "info"; msg: string } | null>(null);
  const [loading, setLoading] = useState(false);

  const usdLabel = useMemo(() => `$${(usdCents / 100).toFixed(2)}`, [usdCents]);

  const handleCreate = async () => {
    if (!walletAddress) {
      setStatus({ type: "error", msg: "Connect a wallet first." });
      return;
    }
    if (!riskAccepted) {
      setStatus({ type: "error", msg: "Accept the risk disclosure first." });
      return;
    }
    if (usdCents < 1) {
      setStatus({ type: "error", msg: "Minimum micropayment is $0.01." });
      return;
    }
    setLoading(true);
    setStatus(null);
    setClaimUrl("");
    setQrPayload("");
    try {
      const res = await api.createMicropayment({
        sender_wallet: walletAddress,
        usd_cents: usdCents,
        asset,
        delivery_channel: deliveryChannel,
        recipient_hint: recipient || undefined,
        expires_minutes: expiryMinutes,
        risk_version: "v1.0.0-devnet",
      });
      setClaimUrl(res.claim_url);
      setQrPayload(res.qr_payload);
      setStatus({
        type: res.backend_degraded ? "info" : "success",
        msg: `${usdLabel} claim link created. Status: ${res.status}; funding: ${res.funding_status}.`,
      });
      onMint?.();
    } catch (e: any) {
      setStatus({ type: "error", msg: e.message || "Micropayment creation failed." });
    } finally {
      setLoading(false);
    }
  };

  const copyClaim = async () => {
    if (!claimUrl) return;
    await navigator.clipboard.writeText(claimUrl);
    setStatus({ type: "success", msg: "Claim link copied. Deliver it only to the intended recipient." });
  };

  return (
    <div className="panel">
      <h2 className="card-title">Create Micropayment</h2>
      <p className="muted">
        Minimum $0.01. This creates a one-time claim secret and QR/link payload; it does not send private keys or claim confirmed funding.
      </p>
      <div className="form-group">
        <label>Amount (USD cents)</label>
        <input
          type="number"
          value={usdCents}
          onChange={(e) => setUsdCents(Number(e.target.value))}
          min={1}
        />
        <small className="muted">Current amount: {usdLabel}</small>
      </div>
      <div className="form-group">
        <label>Asset Rail</label>
        <select value={asset} onChange={(e) => setAsset(e.target.value as PaymentAsset)}>
          {Object.entries(assetLabels).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
      </div>
      <div className="form-group">
        <label>Delivery Mode</label>
        <select value={deliveryChannel} onChange={(e) => setDeliveryChannel(e.target.value as DeliveryChannel)}>
          <option value="qr">QR payload</option>
          <option value="link">Direct link</option>
          <option value="physical">Printable physical voucher</option>
          <option value="email">Email degraded mode</option>
          <option value="sms">SMS degraded mode</option>
        </select>
      </div>
      <div className="form-group">
        <label>Expiry (minutes)</label>
        <input
          type="number"
          value={expiryMinutes}
          onChange={(e) => setExpiryMinutes(Number(e.target.value))}
          min={1}
        />
      </div>
      <div className="form-group">
        <label>Recipient hint (optional)</label>
        <input
          type="text"
          value={recipient}
          onChange={(e) => setRecipient(e.target.value)}
          placeholder="Email, phone, wallet, or voucher label"
        />
      </div>
      <button onClick={handleCreate} disabled={loading}>
        {loading && <span className="spinner" />}
        {loading ? "Creating..." : "Create $0.01+ Claim Link"}
      </button>
      {claimUrl && (
        <div className="status info animate-in">
          <span className="status-icon">ℹ</span>
          <div>
            <strong>Claim URL</strong>
            <p className="wallet-address">{claimUrl}</p>
            <button type="button" onClick={copyClaim}>Copy claim link</button>
            <p className="muted">QR payload matches the claim URL. Escrow redemption remains blocked until funding is confirmed.</p>
          </div>
        </div>
      )}
      {qrPayload && (
        <div className="risk-box">
          <strong>Printable / QR Payload</strong>
          <p className="wallet-address">{qrPayload}</p>
        </div>
      )}
      {status && (
        <div className={`status ${status.type} animate-in`}>
          <span className="status-icon">
            {status.type === "success" ? "✓" : status.type === "error" ? "✕" : "ℹ"}
          </span>
          {status.msg}
        </div>
      )}
    </div>
  );
};

export default MintNoteCard;
