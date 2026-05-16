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
    <div className="animate-in">
      <h2 className="card-title">Reserve Status</h2>
      {error && (
        <div className="status error animate-in">
          <span className="status-icon">✕</span>
          {error}
        </div>
      )}
      {data ? (
        <div>
          <div className="stat-row">
            <span className="stat-label">Status</span>
            <span className={`stat-value ${data.status === "active" ? "success" : "warn"}`}>
              {data.status}
            </span>
          </div>
          <div className="stat-row">
            <span className="stat-label">Reserve Ratio</span>
            <span className="stat-value accent">{data.reserve_ratio_bps / 100}%</span>
          </div>
          <div className="stat-row">
            <span className="stat-label">Attested At</span>
            <span className="stat-value">{data.attested_at || "N/A"}</span>
          </div>
          <div className="stat-row">
            <span className="stat-label">Disclaimer</span>
            <span className="stat-value warn" style={{ fontSize: "0.8rem" }}>
              {data.disclaimer}
            </span>
          </div>
        </div>
      ) : (
        <div className="skeleton" style={{ height: 120 }} />
      )}
    </div>
  );
};

export default ReserveStatusCard;
