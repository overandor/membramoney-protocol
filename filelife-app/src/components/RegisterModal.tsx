import { useState } from "react";

const CATEGORIES = ["FIN","ACC","TAX","AUD","STM"];
const SUBCATEGORIES = ["ACC","BNK","PAY","LED","REV","AST"];
const KINDS = ["INV","REC","BIL","PO","PAY","TXN","TAX","CTR","VAL","RPT"];
const JURISDICTIONS = ["US","EU","UK","CA","AU","SG","JP"];

export default function RegisterModal({ onClose, onRegistered }: { onClose:()=>void; onRegistered:(sku:string)=>void }) {
  const [filePath, setFilePath] = useState("");
  const [category, setCategory] = useState("FIN");
  const [subcategory, setSubcategory] = useState("ACC");
  const [kind, setKind] = useState("INV");
  const [jurisdiction, setJurisdiction] = useState("US");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string|null>(null);

  const pick = async () => {
    const fp = await window.filelife.pickFile();
    if (fp) setFilePath(fp);
  };

  const register = async () => {
    if (!filePath) { setError("Select a file first."); return; }
    setLoading(true); setError(null);
    const r = await window.filelife.registerFile({ filePath, category, subcategory, kind, jurisdiction });
    if (r?.success === false) { setError(r.error); setLoading(false); return; }
    const sku = r?.data?.sku || r?.sku;
    onRegistered(sku);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <h2>Register Financial File</h2>
        <p style={{fontSize:11,color:"var(--muted)",marginBottom:16}}>File contents are never stored. Only cryptographic hashes and metadata.</p>
        {error && <div style={{color:"var(--red)",fontSize:11,marginBottom:10}}>{error}</div>}
        <div className="field">
          <label>File Path</label>
          <div className="field-row">
            <input value={filePath} onChange={e => setFilePath(e.target.value)} placeholder="/path/to/invoice.pdf" />
            <button className="btn btn-ghost" onClick={pick}>Browse…</button>
          </div>
        </div>
        <div className="field">
          <label>Category</label>
          <select value={category} onChange={e => setCategory(e.target.value)}>
            {CATEGORIES.map(c=><option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div className="field">
          <label>Subcategory</label>
          <select value={subcategory} onChange={e => setSubcategory(e.target.value)}>
            {SUBCATEGORIES.map(c=><option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div className="field">
          <label>Document Kind</label>
          <select value={kind} onChange={e => setKind(e.target.value)}>
            {KINDS.map(k=><option key={k} value={k}>{k}</option>)}
          </select>
        </div>
        <div className="field">
          <label>Jurisdiction</label>
          <select value={jurisdiction} onChange={e => setJurisdiction(e.target.value)}>
            {JURISDICTIONS.map(j=><option key={j} value={j}>{j}</option>)}
          </select>
        </div>
        <div className="modal-actions">
          <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={register} disabled={loading||!filePath}>{loading?"Registering…":"Register File"}</button>
        </div>
      </div>
    </div>
  );
}
