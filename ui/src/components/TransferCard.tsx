import React, { useState } from "react";
import { api } from "../lib/api";
import { useWallet } from "../lib/wallet";

const TransferCard: React.FC = () => {
  const { walletAddress } = useWallet();
  const [claimId, setClaimId] = useState("");
  const [toWallet, setToWallet] = useState("");
  const [status, setStatus] = useState<{ type: "success" | "error" | "info"; msg: string } | null>(null);
  const [loading, setLoading] = useState(false);

  const handleTransfer = async () => {
    if (!claimId || !toWallet) {
      setStatus({ type: "error", msg: "Claim ID and destination wallet are required." });
      return;
    }
    if (!walletAddress) {
      setStatus({ type: "error", msg: "Connect a wallet first." });
      return;
    }
    setLoading(true);
    setStatus(null);
    try {
      const res = await api.transferClaim(claimId, {
        from_user: walletAddress,
        to_user: toWallet,
      });
      setStatus({ type: "success", msg: res.message || `Transfer successful for claim ${claimId}.` });
    } catch (e: any) {
      setStatus({ type: "error", msg: e.message || "Transfer failed." });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="panel">
      <h2 className="card-title">Transfer Note</h2>
      <div className="form-group">
        <label>Claim ID</label>
        <input
          type="text"
          value={claimId}
          onChange={(e) => setClaimId(e.target.value)}
          placeholder="claim_..."
        />
      </div>
      <div className="form-group">
        <label>From Wallet</label>
        <input
          type="text"
          value={walletAddress || ""}
          readOnly
          style={{ opacity: 0.6, cursor: "not-allowed" }}
          placeholder="Connect wallet"
        />
      </div>
      <div className="form-group">
        <label>To Wallet</label>
        <input
          type="text"
          value={toWallet}
          onChange={(e) => setToWallet(e.target.value)}
          placeholder="Destination wallet address"
        />
      </div>
      <button onClick={handleTransfer} disabled={loading}>
        {loading && <span className="spinner" />}
        {loading ? "Transferring..." : "Transfer Note"}
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

export default TransferCard;
