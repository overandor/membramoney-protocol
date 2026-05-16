import React, { useEffect, useState } from "react";
import { api } from "../lib/api";

interface Props {
  accepted: boolean;
  walletAddress: string | null;
  onAccept: (v: boolean) => void;
}

const RiskDisclosure: React.FC<Props> = ({ accepted, walletAddress, onAccept }) => {
  const [text, setText] = useState<string>("Loading...");
  const [version, setVersion] = useState("");
  const [checked, setChecked] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getRiskDisclosure()
      .then((d) => {
        setText(d.text);
        setVersion(d.version);
      })
      .catch((e) => setError(e.message));
  }, []);

  const handleAccept = async () => {
    if (!walletAddress) {
      setError("Connect a wallet first.");
      return;
    }
    if (!checked) {
      setError("Check the box to accept the disclosure.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await api.acceptRiskDisclosure({
        wallet_address: walletAddress,
        accepted_version: version,
      });
      onAccept(true);
    } catch (e: any) {
      setError(e.message || "Acceptance failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2 className="card-title">Risk Disclosure</h2>
      <div className="risk-box">{text}</div>
      {accepted ? (
        <div className="status success animate-in">
          <span className="status-icon">✓</span>
          Risk disclosure accepted for wallet {walletAddress}.
        </div>
      ) : (
        <>
          <div
            className="checkbox-row"
            onClick={() => setChecked((c) => !c)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") setChecked((c) => !c); }}
          >
            <input
              id="risk-check"
              type="checkbox"
              checked={checked}
              onChange={(e) => setChecked(e.target.checked)}
              onClick={(e) => e.stopPropagation()}
            />
            <label htmlFor="risk-check">
              I have read and accept the risk disclosure.
            </label>
          </div>
          <button onClick={handleAccept} disabled={loading}>
            {loading && <span className="spinner" />}
            {loading ? "Accepting..." : "Accept Risk Disclosure"}
          </button>
        </>
      )}
      {error && (
        <div className="status error animate-in" style={{ marginTop: 12 }}>
          <span className="status-icon">✕</span>
          {error}
        </div>
      )}
    </div>
  );
};

export default RiskDisclosure;
