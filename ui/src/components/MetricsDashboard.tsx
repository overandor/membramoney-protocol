import React, { useState, useEffect } from "react";
import { api } from "../lib/api";
import LoadingCard from "./LoadingCard";

interface HealthData {
  status: string;
  env: string;
  devnet: boolean;
  timestamp: string;
  version: string;
  stores: {
    claims: number;
    risk_acceptances: number;
    audit_events: number;
    idempotency_keys: number;
  };
  memory_mb: number | null;
  python_version: string;
}

const MetricsDashboard: React.FC = () => {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.health()
      .then((data) => {
        setHealth(data as unknown as HealthData);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) return <LoadingCard />;
  if (!health) return <div className="panel">Failed to load metrics</div>;

  return (
    <div className="panel metrics-dashboard">
      <h3>System Metrics</h3>
      <div className="metrics-grid">
        <div className="metric-card">
          <span className="metric-label">Status</span>
          <span className={`metric-value metric-${health.status}`}>{health.status}</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Version</span>
          <span className="metric-value">{health.version}</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Environment</span>
          <span className="metric-value">{health.env}</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Memory</span>
          <span className="metric-value">{health.memory_mb ? `${health.memory_mb} MB` : "N/A"}</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Claims</span>
          <span className="metric-value">{health.stores.claims}</span>
        </div>
        <div className="metric-card">
          <span className="metric-label">Audit Events</span>
          <span className="metric-value">{health.stores.audit_events}</span>
        </div>
      </div>
    </div>
  );
};

export default MetricsDashboard;
