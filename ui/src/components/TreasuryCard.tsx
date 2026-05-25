import React, { useEffect, useState } from "react";
import { api, TreasuryReservesResponse } from "../lib/api";

const card: React.CSSProperties = {
  background: "var(--surface)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius)",
  padding: "24px",
};

const TreasuryCard: React.FC = () => {
  const [reserves, setReserves] = useState<TreasuryReservesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getTreasuryReserves()
      .then(setReserves)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const assets = reserves
    ? [
        { label: "BTC", value: reserves.btc ?? "—", color: "var(--accent3)" },
        { label: "SOL", value: reserves.sol ?? "—", color: "var(--accent)" },
        { label: "ETH", value: reserves.eth ?? "—", color: "var(--blue)" },
        { label: "USDC", value: reserves.usdc ?? "—", color: "var(--green)" },
      ]
    : [];

  return (
    <div style={card}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <h2
          style={{
            fontSize: 11,
            color: "var(--muted)",
            textTransform: "uppercase",
            letterSpacing: ".1em",
            fontWeight: 600,
            margin: 0,
          }}
        >
          Treasury Reserves
        </h2>
        {reserves?.updated_at && (
          <span style={{ fontSize: 11, color: "var(--muted2)" }}>
            Updated {new Date(reserves.updated_at).toLocaleTimeString()}
          </span>
        )}
      </div>
      {loading && (
        <div style={{ textAlign: "center", padding: 32, color: "var(--muted)" }}>
          <span className="spinner" /> Loading reserves…
        </div>
      )}
      {error && (
        <div className="status error">
          <span className="status-icon">✕</span>
          {error}
        </div>
      )}
      {reserves && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          {assets.map((a) => (
            <div
              key={a.label}
              style={{
                background: "var(--bg)",
                borderRadius: "var(--radius-sm)",
                padding: "16px",
                textAlign: "center",
                border: "1px solid var(--border)",
              }}
            >
              <div
                style={{
                  fontSize: "1.4rem",
                  fontWeight: 800,
                  color: a.color,
                  fontFamily: "monospace",
                  marginBottom: 4,
                }}
              >
                {typeof a.value === "number" ? a.value.toLocaleString() : String(a.value)}
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
                {a.label}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default TreasuryCard;
