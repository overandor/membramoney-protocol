import React, { useEffect, useState } from "react";
import { api, FeeSavingsResponse } from "../lib/api";

interface Props {
  amountSats?: number;
}

const FeeSavingsCard: React.FC<Props> = ({ amountSats = 100_000 }) => {
  const [data, setData] = useState<FeeSavingsResponse | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    api.getFeeSavings(amountSats).then(setData).catch(() => setError(true));
  }, [amountSats]);

  if (error || !data) return null;

  const savings = data.savings_vs_btc;

  return (
    <div className="panel fee-savings">
      <h2 className="card-title">Why Membra?</h2>
      <p className="card-subtitle">
        BTC-denominated value · Solana speed · {data.fee_sponsored ? "Protocol-sponsored transfers" : "Near-zero fees"}
      </p>

      <div className="fee-compare">
        <div className="fee-row">
          <span className="fee-label">Direct BTC transfer (low mempool)</span>
          <span className="fee-value fee-bad">
            {data.btc_network_fees.low_congestion_sats.toLocaleString()} sats
          </span>
        </div>
        <div className="fee-row">
          <span className="fee-label">Direct BTC transfer (congested)</span>
          <span className="fee-value fee-bad">
            {data.btc_network_fees.high_congestion_sats.toLocaleString()} sats
          </span>
        </div>
        <div className="fee-row fee-highlight">
          <span className="fee-label">Membra bearer note transfer</span>
          <span className="fee-value fee-free">
            {data.fee_sponsored
              ? "FREE (fee sponsored)"
              : `${data.user_pays_sats} sats (~$0.00025)`}
          </span>
        </div>
      </div>

      <div className="speed-compare">
        <div className="speed-item">
          <div className="speed-label">BTC settlement</div>
          <div className="speed-value speed-slow">{data.settlement_time.btc_confirmations}</div>
        </div>
        <div className="speed-divider">vs</div>
        <div className="speed-item">
          <div className="speed-label">Membra / Solana</div>
          <div className="speed-value speed-fast">{data.settlement_time.membra_solana}</div>
        </div>
      </div>

      <div className="tps-row">
        <span className="tps-item">BTC: <strong>{data.btc_tps} TPS</strong></span>
        <span className="tps-item">Solana: <strong>{data.solana_tps.toLocaleString()} TPS</strong></span>
        <span className="tps-item savings-badge">
          Up to <strong>{savings.high_congestion_pct}%</strong> cheaper
        </span>
      </div>

      <div className="innovation-list">
        {Object.entries(data.innovation).map(([key, val]) => (
          <div key={key} className="innovation-item">
            <span className="innovation-icon">✦</span>
            <span>{val}</span>
          </div>
        ))}
      </div>

      <p className="fee-disclaimer">{data.disclaimer}</p>
    </div>
  );
};

export default FeeSavingsCard;
