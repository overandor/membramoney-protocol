import React, { useState } from "react";
import { api } from "../lib/api";

const SplitCard: React.FC = () => {
  const [claimId, setClaimId] = useState("");
  const [amount1, setAmount1] = useState<number>(500);
  const [amount2, setAmount2] = useState<number>(500);
  const [status, setStatus] = useState<{ type: "success" | "error" | "info"; msg: string } | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSplit = async () => {
    if (!claimId) {
      setStatus({ type: "error", msg: "Claim ID is required." });
      return;
    }
    setLoading(true);
    setStatus(null);
    try {
      const res = await api.splitClaim(claimId, { amounts: [amount1, amount2] });
      setStatus({
        type: "success",
        msg: res.new_claim_ids
          ? `Split successful. New claims: ${res.new_claim_ids.join(", ")}`
          : "Split successful.",
      });
    } catch (e: any) {
      setStatus({ type: "error", msg: e.message || "Split failed." });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="panel">
      <h2 className="card-title">Split Note</h2>
      <div className="form-group">
        <label>Claim ID</label>
        <input
          type="text"
          value={claimId}
          onChange={(e) => setClaimId(e.target.value)}
          placeholder="claim_..."
        />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <div className="form-group">
          <label>Amount 1 (sats)</label>
          <input
            type="number"
            value={amount1}
            onChange={(e) => setAmount1(Number(e.target.value))}
            min={1}
          />
        </div>
        <div className="form-group">
          <label>Amount 2 (sats)</label>
          <input
            type="number"
            value={amount2}
            onChange={(e) => setAmount2(Number(e.target.value))}
            min={1}
          />
        </div>
      </div>
      <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 16 }}>
        Total: {(amount1 + amount2).toLocaleString()} sats
      </div>
      <button onClick={handleSplit} disabled={loading}>
        {loading && <span className="spinner" />}
        {loading ? "Splitting..." : "Split Note"}
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

export default SplitCard;
