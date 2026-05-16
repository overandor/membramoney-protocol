import React, { useState } from "react";
import { api } from "../lib/api";

interface Props {
  walletAddress: string | null;
  riskAccepted: boolean;
}

const ClaimNoteCard: React.FC<Props> = ({ walletAddress, riskAccepted }) => {
  const [claimId, setClaimId] = useState("");
  const [pin, setPin] = useState("");
  const [status, setStatus] = useState<{ type: "success" | "error" | "info"; msg: string } | null>(null);
  const [loading, setLoading] = useState(false);

  const handleValidate = async () => {
    if (!walletAddress) {
      setStatus({ type: "error", msg: "Connect a wallet first." });
      return;
    }
    if (!riskAccepted) {
      setStatus({ type: "error", msg: "Accept the risk disclosure first." });
      return;
    }
    if (!claimId.trim() || !pin.trim()) {
      setStatus({ type: "error", msg: "Enter claim ID and PIN." });
      return;
    }
    setLoading(true);
    setStatus(null);
    try {
      const res = await api.validateClaim({
        claim_id: claimId.trim(),
        pin: pin.trim(),
        claimant_wallet: walletAddress,
      });
      setStatus({
        type: res.valid ? "success" : "error",
        msg: res.message,
      });
    } catch (e: any) {
      setStatus({ type: "error", msg: e.message || "Validation failed." });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="panel">
      <h2 className="card-title">Validate Claim</h2>
      <div className="form-group">
        <label>Claim ID</label>
        <input
          type="text"
          value={claimId}
          onChange={(e) => setClaimId(e.target.value)}
          placeholder="Paste claim ID"
        />
      </div>
      <div className="form-group">
        <label>PIN</label>
        <input
          type="password"
          value={pin}
          onChange={(e) => setPin(e.target.value)}
          placeholder="Enter PIN"
        />
      </div>
      <button onClick={handleValidate} disabled={loading}>
        {loading && <span className="spinner" />}
        {loading ? "Validating..." : "Validate Claim"}
      </button>
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

export default ClaimNoteCard;
