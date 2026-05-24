import { useState } from "react";

const CLASSES = ["invoice","accounts_receivable","contract_receivable","inventory_document","tax_credit","royalty_stream","appraisal_asset"];

export default function CollateralPanel({ sku, file }: { sku: string; file: any }) {
  const [faceValue, setFaceValue] = useState("10000");
  const [collClass, setCollClass] = useState("invoice");
  const [daysToMaturity, setDaysToMaturity] = useState("30");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [lienPid, setLienPid] = useState("");
  const [lienStatus, setLienStatus] = useState<any>(null);
  const [msg, setMsg] = useState<string|null>(null);

  const toast = (m: string) => { setMsg(m); setTimeout(() => setMsg(null), 3000); };

  const evaluate = async () => {
    setLoading(true);
    const r = await window.filelife.evaluateCollateral(sku, {
      faceValueUsd: parseFloat(faceValue)||0, collateralClass: collClass,
      daysToMaturity: parseInt(daysToMaturity)||0
    });
    setResult(r?.data || r);
    setLoading(false);
  };

  const pledge = async () => {
    if (!lienPid) return;
    const r = await window.filelife.pledgeCollateral(sku, { lienHolderPid: lienPid });
    toast("Collateral pledged.");
    setLienStatus(r?.data || r);
  };

  const release = async () => {
    const r = await window.filelife.releaseCollateral(sku);
    toast("Lien released.");
    setLienStatus(r?.data || r);
  };

  const col = result;

  return (
    <div style={{padding:12,overflow:"auto",flex:1}}>
      {msg && <div style={{color:"var(--green)",fontSize:11,marginBottom:8}}>{msg}</div>}

      <div className="section-card">
        <div className="section-title">Evaluate Collateral</div>
        <div className="field">
          <label>Face Value (USD)</label>
          <input type="number" value={faceValue} onChange={e => setFaceValue(e.target.value)} />
        </div>
        <div className="field">
          <label>Collateral Class</label>
          <select value={collClass} onChange={e => setCollClass(e.target.value)}>
            {CLASSES.map(c => <option key={c} value={c}>{c.replace(/_/g," ")}</option>)}
          </select>
        </div>
        <div className="field">
          <label>Days to Maturity</label>
          <input type="number" value={daysToMaturity} onChange={e => setDaysToMaturity(e.target.value)} />
        </div>
        <button className="btn btn-primary" onClick={evaluate} disabled={loading}>{loading?"Calculating…":"Calculate"}</button>
      </div>

      {col && (
        <>
          <div className="section-card">
            <div className="lendable-hero">
              <div className="lendable-amount">${(col.lendableValueUsd||0).toLocaleString("en-US",{minimumFractionDigits:2})}</div>
              <div className="lendable-label">Estimated Lendable Value</div>
              <div style={{fontSize:10,color:"var(--muted)",marginTop:4}}>KPI Profile: {col.kpiProfile}/9 · Advance Rate: {col.advanceRatePercent}% · Haircut: {col.haircutPercent}%</div>
            </div>
            <div className="advance-bar-wrap">
              <div style={{display:"flex",justifyContent:"space-between",fontSize:10,color:"var(--muted)",marginBottom:4}}>
                <span>$0</span><span>Lendable</span><span>${(col.faceValueUsd||0).toLocaleString()}</span>
              </div>
              <div className="advance-bar">
                <div className="advance-fill" style={{width:`${col.advanceRatePercent||0}%`}} />
              </div>
            </div>
            <div className="score-grid">
              <ScoreItem num={col.liquidityScore} label="Liquidity" color="var(--accent2)" />
              <ScoreItem num={100-(col.defaultRiskScore||0)} label="Credit Score" color="var(--green)" />
              <ScoreItem num={100-(col.fraudRiskScore||0)} label="Fraud Score" color="var(--yellow)" />
              <ScoreItem num={col.verificationScore} label="Verification" color="var(--accent3)" />
              <ScoreItem num={col.auditScore} label="Audit" color="var(--green)" />
              <ScoreItem num={col.paymentProbability} label="Payment Prob" color="var(--accent2)" />
            </div>
          </div>

          <div className="section-card">
            <div className="section-title">Collateral Certificate</div>
            <div className="info-row"><span className="info-key">Cert ID</span><span className="info-val" style={{fontFamily:"var(--mono)",fontSize:10}}>{col.certId}</span></div>
            <div className="info-row"><span className="info-key">Eligible</span><span className="info-val"><span className={`badge ${col.eligibleForCollateral?"badge-col":"badge-ncl"}`}>{col.eligibleForCollateral?"Eligible":"Not Eligible"}</span></span></div>
            <div className="info-row"><span className="info-key">Class</span><span className="info-val">{col.collateralClass}</span></div>
            <div className="info-row"><span className="info-key">Appraised Value</span><span className="info-val">${(col.appraisedValueUsd||0).toFixed(2)}</span></div>
            <p style={{fontSize:10,color:"var(--muted)",marginTop:8,fontStyle:"italic"}}>Disclaimer: This is a collateral-eligible estimate. Not a guarantee of value. Subject to independent audit.</p>
          </div>

          <div className="section-card">
            <div className="section-title">Lien Management</div>
            {!lienStatus && <div className="info-row"><span className="info-key">Status</span><span className="info-val"><span className="badge badge-none">No Active Lien</span></span></div>}
            {lienStatus && <div className="info-row"><span className="info-key">Status</span><span className="info-val"><span className={`badge badge-${lienStatus.lienStatus||"none"}`}>{lienStatus.lienStatus}</span></span></div>}
            <div className="field" style={{marginTop:10}}>
              <label>Lien Holder PID</label>
              <input placeholder="PID-MBR-BANK-US-2026-XXXXXX" value={lienPid} onChange={e => setLienPid(e.target.value)} />
            </div>
            <div style={{display:"flex",gap:8}}>
              <button className="btn btn-success btn-sm" onClick={pledge} disabled={!lienPid}>Pledge</button>
              <button className="btn btn-danger btn-sm" onClick={release}>Release Lien</button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function ScoreItem({ num, label, color }: { num: number; label: string; color: string }) {
  return (
    <div className="score-item">
      <div className="score-num" style={{color}}>{num??0}</div>
      <div className="score-lbl">{label}</div>
    </div>
  );
}
