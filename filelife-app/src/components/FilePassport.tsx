import { useEffect, useState } from "react";

const LC_LABELS: Record<number,string> = {
  0:"Discovered",1:"Registered",2:"Raw Hashed",3:"Base64 Encoded",
  4:"GitHub Committed",5:"Chain Anchored",6:"Appraised",7:"Verified",8:"Amended",9:"Archived"
};

function copy(text: string) { navigator.clipboard?.writeText(text).catch(() => {}); }

export default function FilePassport({ file, onAction, loading }: { file: any; onAction: (a:string,sku:string) => void; loading: boolean }) {
  const [qr, setQr] = useState<string|null>(null);
  const [barcode, setBarcode] = useState<string|null>(null);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [appraisals, setAppraisals] = useState<any[]>([]);
  const sku = file.sku;

  useEffect(() => {
    if (!sku) return;
    window.filelife.getQR(sku).then((r:any) => setQr(r?.data?.qrDataUrl || r?.qrDataUrl || null));
    window.filelife.getBarcode(sku).then((r:any) => setBarcode(r?.data?.barcodeDataUrl || r?.barcodeDataUrl || null));
    window.filelife.getTimeline(sku).then(setTimeline);
    window.filelife.getAppraisals(sku).then(setAppraisals);
  }, [sku]);

  const lastAppraisal = appraisals[appraisals.length - 1];

  return (
    <div>
      {/* SKU Hero */}
      <div className="sku-hero">
        <div style={{fontSize:10,color:"var(--muted)",textTransform:"uppercase",letterSpacing:".1em",marginBottom:6}}>Collateral Passport · SKU</div>
        <div className="sku-value">{sku}</div>
        <div className="sku-actions">
          <button className="btn btn-ghost btn-xs" onClick={() => copy(sku)}>⎘ Copy SKU</button>
          <button className="btn btn-ghost btn-xs" onClick={() => onAction("appraise",sku)} disabled={loading}>⚡ Appraise</button>
          <button className="btn btn-ghost btn-xs" onClick={() => onAction("github",sku)} disabled={loading}>↑ GitHub</button>
          <button className="btn btn-ghost btn-xs" onClick={() => onAction("anchor",sku)} disabled={loading}>⛓ Anchor</button>
        </div>
      </div>

      {/* Identity */}
      <div className="section-card">
        <div className="section-title">Identity</div>
        <div className="info-row"><span className="info-key">Category</span><span className="info-val">{file.category} / {file.subcategory} / {file.kind}</span></div>
        <div className="info-row"><span className="info-key">Jurisdiction</span><span className="info-val">{file.jurisdiction}</span></div>
        <div className="info-row"><span className="info-key">Version</span><span className="info-val">v{file.version}</span></div>
        <div className="info-row"><span className="info-key">Lifecycle</span><span className="info-val"><span className={`badge badge-lc${file.lifecycleStage}`}>LC{file.lifecycleStage} · {LC_LABELS[file.lifecycleStage]||""}</span></span></div>
        <div className="info-row"><span className="info-key">Content Exposed</span><span className="info-val" style={{color:"var(--green)"}}>Never</span></div>
        <div className="info-row"><span className="info-key">Identity Exposed</span><span className="info-val" style={{color:"var(--green)"}}>Never</span></div>
        <div className="info-row"><span className="info-key">Registered</span><span className="info-val">{new Date(file.createdAt||file.created_at||"").toLocaleString()}</span></div>
      </div>

      {/* Hashes */}
      <div className="section-card">
        <div className="section-title">Cryptographic Hashes</div>
        <div className="hash-group">
          {[["raw_file_hash","Raw File",file.rawFileHash||file.raw_file_hash],["base64_hash","Base64",file.base64Hash||file.base64_hash],["manifest_hash","Manifest",file.manifestHash||file.manifest_hash],["sku_hash","SKU",file.skuHash||file.sku_hash]].map(([k,label,val]) => (
            <div key={k} className="hash-row">
              <span className="hash-label">{label}</span>
              <span className="hash-value" title={val as string}>{val as string}</span>
              <button className="copy-btn" onClick={() => copy(val as string)}>⎘</button>
            </div>
          ))}
        </div>
      </div>

      {/* QR + Barcode */}
      <div className="section-card">
        <div className="section-title">QR Code & Barcode</div>
        <div className="qr-barcode-row">
          {qr && <div className="qr-wrap"><img src={qr} alt="QR" /><div className="qr-label">/f/{sku?.slice(0,20)}…</div></div>}
          {barcode && <div className="barcode-wrap"><img src={barcode} alt="Barcode" style={{maxWidth:200,maxHeight:80}} /><div className="barcode-label">CODE128 · SKU</div></div>}
          {(!qr && !barcode) && <div style={{color:"var(--muted)",fontSize:11}}>Generating…</div>}
        </div>
      </div>

      {/* GitHub */}
      {file.github && (
        <div className="section-card">
          <div className="section-title">GitHub Version History</div>
          <div className="info-row"><span className="info-key">Repository</span><span className="info-val">{file.github.repo}</span></div>
          <div className="info-row"><span className="info-key">Branch</span><span className="info-val">{file.github.branch}</span></div>
          <div className="info-row"><span className="info-key">Commit</span><span className="info-val"><span style={{fontFamily:"var(--mono)"}}>{file.github.commitShort||file.github.commit_short}</span></span></div>
          <div className="info-row"><span className="info-key">Full SHA</span><span className="info-val" style={{fontFamily:"var(--mono)",fontSize:9}}>{file.github.commitSha||file.github.commit_sha}</span></div>
          {(file.github.commitUrl||file.github.commit_url) && <div style={{marginTop:8}}><a className="chain-link" href={file.github.commitUrl||file.github.commit_url} target="_blank" rel="noreferrer">↗ View on GitHub</a></div>}
        </div>
      )}

      {/* Solana */}
      {file.chain && (
        <div className="section-card">
          <div className="section-title">Blockchain Anchor · Solana Devnet</div>
          <div className="info-row"><span className="info-key">Network</span><span className="info-val"><span className="badge badge-lc5">{file.chain.networkCode||file.chain.network_code} · Devnet</span></span></div>
          <div className="info-row"><span className="info-key">Tx</span><span className="info-val" style={{fontFamily:"var(--mono)",fontSize:9}}>{(file.chain.anchorTx||file.chain.anchor_tx)?.slice(0,32)}…</span></div>
          {(file.chain.explorerUrl||file.chain.explorer_url) && <div style={{marginTop:8}}><a className="chain-link" href={file.chain.explorerUrl||file.chain.explorer_url} target="_blank" rel="noreferrer">↗ View on Explorer</a></div>}
        </div>
      )}

      {/* Appraisal */}
      {lastAppraisal && (
        <div className="section-card">
          <div className="section-title">Latest Appraisal</div>
          <div style={{textAlign:"center",padding:"8px 0"}}>
            <div style={{fontSize:28,fontWeight:700,color:"var(--accent2)"}}>${(lastAppraisal.valueUsd||lastAppraisal.appraisal_value_usd||0).toLocaleString("en-US",{minimumFractionDigits:2})}</div>
            <div style={{fontSize:10,color:"var(--muted)",marginTop:4}}>Confidence: {Math.round((lastAppraisal.confidence||0)*100)}% · {lastAppraisal.model}</div>
          </div>
          <div style={{fontSize:11,color:"var(--muted)",fontStyle:"italic",marginTop:4}}>{lastAppraisal.rationale}</div>
          {appraisals.length > 1 && <div style={{marginTop:8,fontSize:10,color:"var(--muted)"}}>{appraisals.length} appraisal(s) on record.</div>}
        </div>
      )}

      {/* Lifecycle Timeline */}
      <div className="section-card">
        <div className="section-title">Lifecycle Timeline</div>
        <div className="timeline">
          {timeline.length === 0 && <div style={{color:"var(--muted)",fontSize:11}}>No events yet.</div>}
          {timeline.map((ev, i) => (
            <div key={i} className="timeline-item">
              <div className={`timeline-dot${ev.stage>=7?" done":ev.stage>=4?" ":"pending"}`} />
              <div className="timeline-stage">LC{ev.stage} · {LC_LABELS[ev.stage]||ev.stage_label||""}</div>
              <div className="timeline-event">{ev.event_type}</div>
              <div className="timeline-time">{ev.timestamp ? new Date(ev.timestamp).toLocaleString() : ""}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
