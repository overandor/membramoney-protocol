import React, { useState } from "react";
import { api, ComplianceScreenResponse } from "../lib/api";

const card: React.CSSProperties = {
  background: "var(--surface)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius)",
  padding: "24px",
};

const ComplianceCard: React.FC = () => {
  const [userId, setUserId] = useState("");
  const [screeningType, setScreeningType] = useState("aml");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ComplianceScreenResponse | null>(null);
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
      const res = await api.screenCompliance({ user_id: userId, screening_type: screeningType });
      setResult(res);
    } catch (e: any) {
      setError(e.message || "Screening failed.");
    } finally {
      setLoading(false);
    }
  };

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
        Compliance Screening
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
        <label>Screening Type</label>
        <select
          value={screeningType}
          onChange={(e) => setScreeningType(e.target.value)}
          style={{
            width: "100%",
            background: "var(--bg)",
            border: "1px solid var(--border2)",
            borderRadius: "var(--radius-sm)",
            padding: "10px 12px",
            color: "var(--text)",
            fontSize: 14,
          }}
        >
          <option value="aml">AML</option>
          <option value="kyc">KYC</option>
          <option value="sanctions">Sanctions</option>
        </select>
      </div>
      <button onClick={handleSubmit} disabled={loading}>
        {loading && <span className="spinner" />}
        {loading ? "Screening…" : "Run Screening"}
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
            border: `1px solid ${result.flagged ? "var(--red)" : "var(--green)"}`,
            borderRadius: "var(--radius-sm)",
            padding: "16px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
            <span
              style={{
                fontWeight: 700,
                fontSize: 13,
                color: result.flagged ? "var(--red)" : "var(--green)",
              }}
            >
              {result.flagged ? "FLAGGED" : "CLEAR"}
            </span>
            <span style={{ fontSize: 12, color: "var(--muted)" }}>
              {result.screening_type.toUpperCase()} · {result.result}
            </span>
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

export default ComplianceCard;
