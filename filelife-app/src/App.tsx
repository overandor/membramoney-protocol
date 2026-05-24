import { useCallback, useEffect, useState } from "react";
import FilePassport from "./components/FilePassport";
import CollateralPanel from "./components/CollateralPanel";
import LLMChat from "./components/LLMChat";
import SettingsPanel from "./components/SettingsPanel";
import RegisterModal from "./components/RegisterModal";

declare global {
  interface Window {
    filelife: any;
  }
}

const LC_LABELS: Record<number,string> = {
  0:"Discovered",1:"Registered",2:"Raw Hashed",3:"Base64 Encoded",
  4:"GitHub Committed",5:"Chain Anchored",6:"Appraised",7:"Verified",8:"Amended",9:"Archived"
};

export default function App() {
  const [files, setFiles] = useState<any[]>([]);
  const [selectedSku, setSelectedSku] = useState<string|null>(null);
  const [selectedFile, setSelectedFile] = useState<any>(null);
  const [rightTab, setRightTab] = useState<"passport"|"collateral"|"qa"|"settings">("passport");
  const [search, setSearch] = useState("");
  const [showRegister, setShowRegister] = useState(false);
  const [loading, setLoading] = useState(false);
  const [actionMsg, setActionMsg] = useState<string|null>(null);

  const loadFiles = useCallback(async () => {
    const list = await window.filelife.listFiles();
    setFiles(list || []);
  }, []);

  const loadFile = useCallback(async (sku: string) => {
    setLoading(true);
    const f = await window.filelife.getManifest(sku);
    setSelectedFile(f);
    setSelectedSku(sku);
    setLoading(false);
  }, []);

  useEffect(() => { loadFiles(); }, [loadFiles]);

  const toast = (msg: string) => { setActionMsg(msg); setTimeout(() => setActionMsg(null), 3000); };

  const handleAction = async (action: string, sku: string) => {
    setLoading(true);
    try {
      let result: any;
      if (action === "appraise")   result = await window.filelife.appraise(sku);
      if (action === "github")     result = await window.filelife.commitToGitHub(sku);
      if (action === "anchor")     result = await window.filelife.anchorOnChain(sku);
      if (result?.success === false) { toast(`Error: ${result.error}`); return; }
      const newSku = result?.data?.sku || sku;
      toast(`✓ Action complete`);
      await loadFiles();
      await loadFile(newSku);
    } finally { setLoading(false); }
  };

  const filtered = files.filter(f =>
    !search || f.sku?.toLowerCase().includes(search.toLowerCase()) ||
    f.category?.toLowerCase().includes(search.toLowerCase()) ||
    f.kind?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="layout">
      {/* Titlebar */}
      <div className="titlebar">
        <div className="titlebar-left">
          <span className="app-name">MEMBRA FileLife Registry</span>
          {actionMsg && <span style={{fontSize:11,color:"var(--green)"}}>{actionMsg}</span>}
        </div>
        <div className="titlebar-right">
          <button className="btn btn-primary btn-sm" onClick={() => setShowRegister(true)}>+ Register File</button>
          <button className="btn btn-ghost btn-sm" onClick={() => { setRightTab("settings"); setSelectedSku(null); }}>⚙ Settings</button>
        </div>
      </div>

      {/* Sidebar */}
      <div className="sidebar">
        <div className="sidebar-search">
          <input placeholder="Search files…" value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        <div className="sidebar-section">Files ({filtered.length})</div>
        {filtered.length === 0 && (
          <div style={{padding:"20px 12px",color:"var(--muted)",fontSize:11,textAlign:"center"}}>
            {files.length === 0 ? "No files registered yet." : "No matches."}
          </div>
        )}
        {filtered.map(f => (
          <div key={f.sku} className={`file-item${selectedSku===f.sku?" active":""}`} onClick={() => loadFile(f.sku)}>
            <div className="file-item-name">{f.kind} · {f.subcategory} · {f.category}</div>
            <div className="file-item-sku">{f.sku?.slice(0,40)}…</div>
            <div className="file-item-meta">
              <span className={`badge badge-lc${f.lifecycleStage}`}>LC{f.lifecycleStage} {LC_LABELS[f.lifecycleStage]||""}</span>
              <span style={{fontSize:10,color:"var(--muted)"}}>v{f.version}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Main passport area */}
      <div className="passport-area" style={{padding:16}}>
        {loading && <div className="loading">Loading…</div>}
        {!loading && !selectedFile && rightTab !== "settings" && (
          <div className="empty-state">
            <h3>No file selected</h3>
            <p>Register a financial file to create its MEMBRA Collateral Passport — SKU, QR, barcode, blockchain anchor, and bank-grade collateral certificate.</p>
            <button className="btn btn-primary" onClick={() => setShowRegister(true)}>+ Register First File</button>
          </div>
        )}
        {!loading && selectedFile && (
          <FilePassport file={selectedFile} onAction={handleAction} loading={loading} />
        )}
        {rightTab === "settings" && !selectedFile && (
          <div style={{padding:8}}><SettingsPanel /></div>
        )}
      </div>

      {/* Right panel */}
      <div className="right-panel">
        <div className="tabs">
          {selectedFile && <>
            <button className={`tab-btn${rightTab==="passport"?" active":""}`} onClick={() => setRightTab("passport")}>Passport</button>
            <button className={`tab-btn${rightTab==="collateral"?" active":""}`} onClick={() => setRightTab("collateral")}>Collateral</button>
            <button className={`tab-btn${rightTab==="qa"?" active":""}`} onClick={() => setRightTab("qa")}>Q&A</button>
          </>}
          <button className={`tab-btn${rightTab==="settings"?" active":""}`} onClick={() => setRightTab("settings")}>Settings</button>
        </div>
        <div style={{flex:1,overflow:"hidden",display:"flex",flexDirection:"column"}}>
          {rightTab === "collateral" && selectedFile && <CollateralPanel sku={selectedSku!} file={selectedFile} />}
          {rightTab === "qa" && selectedFile && <LLMChat sku={selectedSku!} />}
          {rightTab === "settings" && <div style={{overflow:"auto",flex:1}}><SettingsPanel /></div>}
          {rightTab === "passport" && selectedFile && (
            <div style={{padding:12,overflow:"auto",flex:1}}>
              <div className="section-title">SKU Explained</div>
              <SKUExplain sku={selectedSku!} />
            </div>
          )}
        </div>
      </div>

      {showRegister && (
        <RegisterModal
          onClose={() => setShowRegister(false)}
          onRegistered={async (sku) => { setShowRegister(false); await loadFiles(); await loadFile(sku); }}
        />
      )}
    </div>
  );
}

function SKUExplain({ sku }: { sku: string }) {
  const [expl, setExpl] = useState<any>(null);
  useEffect(() => {
    window.filelife.explainSKU(sku).then(setExpl);
  }, [sku]);
  if (!expl) return <div className="loading">Loading explanation…</div>;
  return (
    <div>
      <div style={{fontSize:11,color:"var(--text)",marginBottom:12,lineHeight:1.6}}>{expl.semantic_explanation}</div>
      <div style={{fontSize:10,color:"var(--muted)",marginBottom:12,fontStyle:"italic"}}>{expl.privacy_explanation}</div>
      {Object.entries(expl.segments||{}).map(([k,v]: any) => (
        <div key={k} className="info-row">
          <span className="info-key" style={{fontFamily:"var(--mono)"}}>{v.value}</span>
          <span className="info-val" style={{color:"var(--muted)"}}>{v.meaning}</span>
        </div>
      ))}
    </div>
  );
}
