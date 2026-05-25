import React, { useState } from "react";
import { api, SecurityCheckResponse } from "../lib/api";

const card: React.CSSProperties = {
  background: "var(--surface)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius)",
  padding: "24px",
};

const SecurityCheckCard: React.FC = () => {
  const [userId, setUserId] = useState("");
  const [amount, setAmount] = useState<number>(100000);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SecurityCheckResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!userId) {
      setError("User ID is required.");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.securityCheck({
        user_id: userId,
        amount,
        ip_hash: "ui-placeholder",
        device_fingerprint: "ui-placeholder",
      });
      setResult(res);
    } catch (e: any) {
      setError(e.message || "Security check failed.");
    } finally {
      setLoading(false);
    }
  };

  const isAlert = result && (result.anomaly_detected || result.velocity_exceeded);

  return (
    <div style={card}>
      <h2
        style={{
          fontSize: 11,
          color: "var(--muted)",
          textTransform: "uppercase",
          letterSpacing: ".1em",
          fontWeight: 600,
          marginBottom: 20,
        }}
      >
        Security Check
      </h2>
      <div className="form-group">
        <label>User ID</label>
        <input
          type="text"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          placeholder="user_..."
        />
      </div>
      <div className="form-group">
        <label>Amount (sats)</label>
        <input
          type="number"
          value={amount}
          onChange={(e) => setAmount(Number(e.target.value))}
          min={1}
        />
      </div>
      <button onClick={handleSubmit} disabled={loading}>
        {loading && <span className="spinner" />}
        {loading ? "Checking…" : "Run Security Check"}
      </button>
      {error && (
        <div className="status error animate-in" style={{ marginTop: 12 }}>
          <span className="status-icon">✕</span>
          {error}
        </div>
      )}
      {result && (
        <div
          className="animate-in"
          style={{
            marginTop: 16,
            background: "var(--bg)",
            border: `1px solid ${isAlert ? "var(--red)" : "var(--green)"}`,
            borderRadius: "var(--radius-sm)",
            padding: "16px",
          }}
        >
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 8 }}>
            <span
              style={{
                fontSize: 12,
                fontWeight: 700,
                color: result.anomaly_detected ? "var(--red)" : "var(--green)",
              }}
            >
              Anomaly: {result.anomaly_detected ? "DETECTED" : "None"}
            </span>
            <span
              style={{
                fontSize: 12,
                fontWeight: 700,
                color: result.velocity_exceeded ? "var(--red)" : "var(--green)",
              }}
            >
              Velocity: {result.velocity_exceeded ? "EXCEEDED" : "OK"}
            </span>
            {result.risk_score !== undefined && (
              <span style={{ fontSize: 12, color: "var(--muted)" }}>
                Risk Score: {result.risk_score}
              </span>
            )}
          </div>
          {result.details && (
            <pre
              style={{
                fontSize: 11,
                color: "var(--muted)",
                fontFamily: "monospace",
                whiteSpace: "pre-wrap",
                margin: 0,
              }}
            >
              {JSON.stringify(result.details, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  );
};

export default SecurityCheckCard;
