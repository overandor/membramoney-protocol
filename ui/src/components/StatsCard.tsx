import React, { useEffect, useState } from "react";
import { api, StatsResponse } from "../lib/api";

const StatsCard: React.FC = () => {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .getStats()
      .then(setStats)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const metrics = stats
    ? [
        { label: "Total Notes", value: stats.total_notes.toLocaleString() },
        { label: "Active Claims", value: stats.active_claims.toLocaleString() },
        { label: "Redeemed Notes", value: stats.redeemed_notes.toLocaleString() },
        { label: "Reserve Ratio", value: `${(stats.reserve_ratio_bps / 100).toFixed(2)}%` },
      ]
    : [];

  return (
    <div className="panel">
      <h2 className="card-title">Protocol Stats</h2>
      {loading && (
        <div style={{ textAlign: "center", padding: 24, color: "var(--muted)" }}>
          <span className="spinner" /> Loading stats…
        </div>
      )}
      {error && (
        <div className="status error">
          <span className="status-icon">✕</span>
          {error}
        </div>
      )}
      {stats && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 12,
          }}
        >
          {metrics.map((m) => (
            <div
              key={m.label}
              style={{
                background: "var(--bg)",
                borderRadius: "var(--radius-sm)",
                padding: "16px",
                textAlign: "center",
              }}
            >
              <div
                style={{
                  fontSize: "1.5rem",
                  fontWeight: 800,
                  color: "var(--accent)",
                  fontFamily: "monospace",
                  marginBottom: 4,
                }}
              >
                {m.value}
              </div>
              <div
                style={{
                  fontSize: 11,
                  color: "var(--muted)",
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                  fontWeight: 600,
                }}
              >
                {m.label}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default StatsCard;
