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
        <div className="status success">Risk disclosure accepted for wallet {walletAddress}.</div>
      ) : (
        <>
          <div className="checkbox-row">
            <input
              id="risk-check"
              type="checkbox"
              checked={checked}
              onChange={(e) => setChecked(e.target.checked)}
            />
            <label htmlFor="risk-check" style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
              I have read and accept the risk disclosure.
            </label>
          </div>
          <button onClick={handleAccept} disabled={loading}>
            {loading ? "Accepting..." : "Accept Risk Disclosure"}
          </button>
        </>
      )}
      {error && <div className="status error" style={{ marginTop: 8 }}>{error}</div>}
    </div>
  );
};

export default RiskDisclosure;
