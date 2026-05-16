import React, { useEffect, useState } from "react";
import { api, ReserveResponse } from "../lib/api";

const ReserveStatusCard: React.FC = () => {
  const [data, setData] = useState<ReserveResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    api
      .getReserves()
      .then((d) => {
        if (mounted) setData(d);
      })
      .catch((e) => {
        if (mounted) setError(e.message || "Failed to load reserves.");
      });
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div>
      <h2 className="card-title">Reserve Status</h2>
      {error && <div className="status error">{error}</div>}
      {data ? (
        <div style={{ display: "grid", gap: 8 }}>
          <p style={{ margin: 0, color: "var(--text)" }}>
            <strong>Status:</strong> {data.status}
          </p>
          <p style={{ margin: 0, color: "var(--text)" }}>
            <strong>Reserve Ratio:</strong> {data.reserve_ratio_bps / 100}%
          </p>
          <p style={{ margin: 0, color: "var(--text)" }}>
            <strong>Attested At:</strong> {data.attested_at || "N/A"}
          </p>
          <p style={{ margin: 0, color: "var(--warn)", fontSize: "0.85rem" }}>
            {data.disclaimer}
          </p>
        </div>
      ) : (
        <p style={{ color: "var(--text-muted)" }}>Loading...</p>
      )}
    </div>
  );
};

export default ReserveStatusCard;
