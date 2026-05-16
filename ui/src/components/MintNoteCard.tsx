import React, { useState } from "react";
import { api } from "../lib/api";

interface Props {
  walletAddress: string | null;
  riskAccepted: boolean;
  onMint?: () => void;
}

const MintNoteCard: React.FC<Props> = ({ walletAddress, riskAccepted, onMint }) => {
  const [denomination, setDenomination] = useState<number>(1000);
  const [expiryMinutes, setExpiryMinutes] = useState<number>(60);
  const [recipient, setRecipient] = useState("");
  const [status, setStatus] = useState<{ type: "success" | "error" | "info"; msg: string } | null>(null);
  const [loading, setLoading] = useState(false);

  const handleMint = async () => {
    if (!walletAddress) {
      setStatus({ type: "error", msg: "Connect a wallet first." });
      return;
    }
    if (!riskAccepted) {
      setStatus({ type: "error", msg: "Accept the risk disclosure first." });
      return;
    }
    setLoading(true);
    setStatus(null);
    try {
      const res = await api.createClaim({
        wallet_address: walletAddress,
        denomination_sats: denomination,
        expires_minutes: expiryMinutes,
        risk_version: "v1.0.0-devnet",
      });
      setStatus({
        type: "success",
        msg: `Claim created: ${res.claim_id}. PIN is hidden for security.`,
      });
      onMint?.();
    } catch (e: any) {
      setStatus({ type: "error", msg: e.message || "Mint failed." });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="panel">
      <h2 className="card-title">Mint Devnet Note</h2>
      <div className="form-group">
        <label>Denomination (sats)</label>
        <input
          type="number"
          value={denomination}
          onChange={(e) => setDenomination(Number(e.target.value))}
          min={1}
        />
      </div>
      <div className="form-group">
        <label>Expiry (minutes)</label>
        <input
          type="number"
          value={expiryMinutes}
          onChange={(e) => setExpiryMinutes(Number(e.target.value))}
          min={5}
        />
      </div>
      <div className="form-group">
        <label>Recipient Wallet (optional)</label>
        <input
          type="text"
          value={recipient}
          onChange={(e) => setRecipient(e.target.value)}
          placeholder="Leave blank to mint to self"
        />
      </div>
      <button onClick={handleMint} disabled={loading}>
        {loading ? "Minting..." : "Mint Devnet Note"}
      </button>
      {status && <div className={`status ${status.type}`}>{status.msg}</div>}
    </div>
  );
};

export default MintNoteCard;
