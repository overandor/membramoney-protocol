import React, { useEffect, useState } from "react";
import { api, PendingBatch } from "../lib/api";

const card: React.CSSProperties = {
  background: "var(--surface)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius)",
  padding: "24px",
};

const PendingBatchesCard: React.FC = () => {
  const [batches, setBatches] = useState<PendingBatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionStatus, setActionStatus] = useState<Record<string, string>>({});

  const load = () => {
    setLoading(true);
    setError(null);
    api
      .getPendingBatches()
      .then((r) => setBatches(r.batches || []))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const handleSign = async (batchId: string) => {
    setActionStatus((s) => ({ ...s, [batchId]: "signing…" }));
    try {
      await api.signBatch(batchId, { operator_id: "ui-operator", signature_hex: "0x" });
      setActionStatus((s) => ({ ...s, [batchId]: "signed" }));
      load();
    } catch (e: any) {
      setActionStatus((s) => ({ ...s, [batchId]: `Error: ${e.message}` }));
    }
  };

  const handleReject = async (batchId: string) => {
    setActionStatus((s) => ({ ...s, [batchId]: "rejecting…" }));
    try {
      await api.rejectBatch(batchId, { operator_id: "ui-operator", reason: "Rejected via UI" });
      setActionStatus((s) => ({ ...s, [batchId]: "rejected" }));
      load();
    } catch (e: any) {
      setActionStatus((s) => ({ ...s, [batchId]: `Error: ${e.message}` }));
    }
  };

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
          Pending Batches
        </h2>
        <button
          onClick={load}
          style={{
            background: "transparent",
            border: "1px solid var(--border2)",
            borderRadius: "var(--radius-sm)",
            padding: "4px 12px",
            fontSize: 12,
            color: "var(--muted)",
            cursor: "pointer",
          }}
        >
          Refresh
        </button>
      </div>
      {loading && (
        <div style={{ textAlign: "center", padding: 24, color: "var(--muted)" }}>
          <span className="spinner" /> Loading…
        </div>
      )}
      {error && (
        <div className="status error">
          <span className="status-icon">✕</span>
          {error}
        </div>
      )}
      {!loading && !error && batches.length === 0 && (
        <div style={{ textAlign: "center", padding: 24, color: "var(--muted)", fontSize: 13 }}>
          No pending batches.
        </div>
      )}
      {batches.map((b) => (
        <div
          key={b.batch_id}
          style={{
            background: "var(--bg)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-sm)",
            padding: "14px 16px",
            marginBottom: 10,
            display: "flex",
            alignItems: "center",
            gap: 12,
            flexWrap: "wrap",
          }}
        >
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontFamily: "monospace", fontSize: 12, color: "var(--text)", marginBottom: 2 }}>
              {b.batch_id}
            </div>
            <div style={{ fontSize: 11, color: "var(--muted)" }}>
              {b.status} · {b.created_at ? new Date(b.created_at).toLocaleString() : ""}
              {b.amount !== undefined ? ` · ${b.amount} sats` : ""}
            </div>
          </div>
          {actionStatus[b.batch_id] ? (
            <span style={{ fontSize: 12, color: "var(--muted)" }}>{actionStatus[b.batch_id]}</span>
          ) : (
            <div style={{ display: "flex", gap: 8 }}>
              <button
                onClick={() => handleSign(b.batch_id)}
                style={{
                  background: "var(--green)",
                  border: "none",
                  borderRadius: 6,
                  padding: "6px 14px",
                  fontSize: 12,
                  fontWeight: 600,
                  color: "#0b0c15",
                  cursor: "pointer",
                }}
              >
                Sign
              </button>
              <button
                onClick={() => handleReject(b.batch_id)}
                style={{
                  background: "var(--red)",
                  border: "none",
                  borderRadius: 6,
                  padding: "6px 14px",
                  fontSize: 12,
                  fontWeight: 600,
                  color: "#0b0c15",
                  cursor: "pointer",
                }}
              >
                Reject
              </button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
};

export default PendingBatchesCard;
