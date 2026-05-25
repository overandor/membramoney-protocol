import { useEffect, useRef, useState } from "react";

declare global {
  interface Window {
    appraiser: {
      loadSettings: () => Promise<Settings>;
      saveSettings: (s: Settings) => Promise<boolean>;
      runAppraisal: () => Promise<Snapshot | null>;
      getLatest: () => Promise<Snapshot | null>;
      getHistory: () => Promise<SnapshotSummary[]>;
      getSnapshot: (runId: string) => Promise<Snapshot | null>;
      getStatus: () => Promise<{ running: boolean }>;
      pickFolder: () => Promise<string | null>;
      onProgress: (cb: (p: Progress) => void) => () => void;
      onComplete: (cb: (s: Snapshot) => void) => () => void;
    };
  }
}

interface Settings { apiKey: string; scanPath: string; intervalMs: number; }
interface FileAppraisal { relPath: string; contentHash: string; sizeBytes: number; valueCents: number; rationale: string; leafHash: string; }
interface Snapshot { runId: string; timestamp: string; merkleRoot: string; previousRoot: string | null; totalValueCents: number; deltaCents: number | null; fileCount: number; scanPath: string; files: FileAppraisal[]; }
interface SnapshotSummary { runId: string; timestamp: string; merkleRoot: string; previousRoot: string | null; totalValueCents: number; deltaCents: number | null; fileCount: number; }
interface Progress { current: number; total: number; file: string; }

function fmt$(cents: number) {
  return "$" + (cents / 100).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtDelta(cents: number | null) {
  if (cents === null) return null;
  const abs = fmt$(Math.abs(cents));
  if (cents > 0) return { label: `+${abs}`, cls: "pos" };
  if (cents < 0) return { label: `-${abs}`, cls: "neg" };
  return { label: "±$0.00", cls: "flat" };
}

function shortDate(ts: string) {
  const d = new Date(ts);
  return d.toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

// ---------------------------------------------------------------------------
// Components
// ---------------------------------------------------------------------------

function Hero({ snap, running, progress }: { snap: Snapshot | null; running: boolean; progress: Progress | null }) {
  const delta = fmtDelta(snap?.deltaCents ?? null);
  return (
    <div className="hero">
      <div>
        <div className="hero-label">Machine Net Worth</div>
        <div className="hero-value" style={{ color: snap ? "#e2e8f0" : "#4a5568" }}>
          {snap ? fmt$(snap.totalValueCents) : "$—"}
        </div>
        <div className="hero-meta">
          {snap && <span>{snap.fileCount.toLocaleString()} files appraised</span>}
          {snap && <span>{shortDate(snap.timestamp)}</span>}
          {delta && <span className={`delta ${delta.cls}`}>{delta.label} vs prev run</span>}
        </div>
        {running && progress && (
          <div className="progress-wrap" style={{ marginTop: 16, marginBottom: 0 }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "var(--muted)" }}>
              <span>Appraising files…</span>
              <span>{progress.current} / {progress.total}</span>
            </div>
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${progress.total ? (progress.current / progress.total) * 100 : 0}%` }} />
            </div>
            <div className="progress-file">{progress.file}</div>
          </div>
        )}
      </div>
      {snap && (
        <div>
          <div className="merkle-chip">
            <div className="label">Merkle Root</div>
            {snap.merkleRoot}
          </div>
          {snap.previousRoot && (
            <div className="merkle-chip" style={{ marginTop: 8 }}>
              <div className="label">Previous Root</div>
              {snap.previousRoot}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

type SortKey = "value" | "path" | "size";

function FileTable({ files }: { files: FileAppraisal[] }) {
  const [sort, setSort] = useState<SortKey>("value");
  const [asc, setAsc] = useState(false);
  const [filter, setFilter] = useState("");

  const toggleSort = (k: SortKey) => {
    if (sort === k) setAsc((a) => !a);
    else { setSort(k); setAsc(k === "path"); }
  };

  const sorted = [...files]
    .filter((f) => !filter || f.relPath.toLowerCase().includes(filter.toLowerCase()))
    .sort((a, b) => {
      let cmp = 0;
      if (sort === "value") cmp = a.valueCents - b.valueCents;
      else if (sort === "path") cmp = a.relPath.localeCompare(b.relPath);
      else cmp = a.sizeBytes - b.sizeBytes;
      return asc ? cmp : -cmp;
    });

  const col = (k: SortKey, label: string) => (
    <button className={`sort-btn${sort === k ? " active" : ""}`} onClick={() => toggleSort(k)}>
      {label} {sort === k ? (asc ? "↑" : "↓") : ""}
    </button>
  );

  return (
    <>
      <div style={{ marginBottom: 10 }}>
        <input
          style={{ background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: 6, padding: "6px 10px", color: "var(--text)", fontSize: 12, width: 280, outline: "none" }}
          placeholder="Filter files…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
        <span style={{ marginLeft: 12, fontSize: 11, color: "var(--muted)" }}>{sorted.length.toLocaleString()} files</span>
      </div>
      <div className="table-wrap">
        <div className="table-header">
          <span>{col("path", "File")}</span>
          <span style={{ textAlign: "right" }}>{col("value", "Value")}</span>
          <span style={{ paddingLeft: 12 }}>Rationale</span>
        </div>
        <div style={{ maxHeight: 480, overflowY: "auto" }}>
          {sorted.map((f) => (
            <div className="table-row" key={f.leafHash}>
              <span className="file-path" title={f.relPath}>{f.relPath}</span>
              <span className="file-value">{fmt$(f.valueCents)}</span>
              <span className="file-rationale" title={f.rationale}>{f.rationale}</span>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

function Sidebar({ history, selectedId, onSelect }: { history: SnapshotSummary[]; selectedId: string | null; onSelect: (id: string) => void; }) {
  return (
    <div className="sidebar">
      <div className="sidebar-section">Run History</div>
      {history.length === 0 && <div style={{ padding: "12px 16px", color: "var(--muted)", fontSize: 12 }}>No runs yet</div>}
      {history.map((s) => {
        const d = fmtDelta(s.deltaCents);
        return (
          <div key={s.runId} className={`history-item${selectedId === s.runId ? " active" : ""}`} onClick={() => onSelect(s.runId)}>
            <div className="history-val">{fmt$(s.totalValueCents)}</div>
            <div className="history-date">{shortDate(s.timestamp)}</div>
            {d && <div className={`history-delta delta ${d.cls}`}>{d.label}</div>}
            <div style={{ fontSize: 10, color: "var(--muted)", marginTop: 2 }}>{s.fileCount} files · {s.merkleRoot.slice(0, 12)}…</div>
          </div>
        );
      })}
    </div>
  );
}

function SettingsPanel({ onSave }: { onSave: () => void }) {
  const [s, setS] = useState<Settings>({ apiKey: "", scanPath: "", intervalMs: 3_600_000 });
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    window.appraiser.loadSettings().then(setS);
  }, []);

  const pickFolder = async () => {
    const p = await window.appraiser.pickFolder();
    if (p) setS((prev) => ({ ...prev, scanPath: p }));
  };

  const save = async () => {
    await window.appraiser.saveSettings(s);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
    onSave();
  };

  return (
    <div className="settings">
      <h2>Settings</h2>
      <div className="field">
        <label>Anthropic API Key</label>
        <input type="password" value={s.apiKey} placeholder="sk-ant-…" onChange={(e) => setS((p) => ({ ...p, apiKey: e.target.value }))} />
      </div>
      <div className="field">
        <label>Scan Directory</label>
        <div className="field-row">
          <input type="text" value={s.scanPath} onChange={(e) => setS((p) => ({ ...p, scanPath: e.target.value }))} />
          <button className="btn btn-ghost" onClick={pickFolder}>Browse…</button>
        </div>
      </div>
      <div className="field">
        <label>Appraisal Interval</label>
        <select
          style={{ background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: 6, padding: "7px 10px", color: "var(--text)", fontSize: 13 }}
          value={s.intervalMs}
          onChange={(e) => setS((p) => ({ ...p, intervalMs: Number(e.target.value) }))}
        >
          <option value={600_000}>Every 10 minutes</option>
          <option value={1_800_000}>Every 30 minutes</option>
          <option value={3_600_000}>Every hour</option>
          <option value={14_400_000}>Every 4 hours</option>
          <option value={86_400_000}>Every 24 hours</option>
        </select>
      </div>
      <button className="btn btn-primary" onClick={save}>{saved ? "✓ Saved" : "Save Settings"}</button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------

export default function App() {
  const [tab, setTab] = useState<"dashboard" | "settings">("dashboard");
  const [snap, setSnap] = useState<Snapshot | null>(null);
  const [history, setHistory] = useState<SnapshotSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<Progress | null>(null);

  const loadHistory = async () => {
    const h = await window.appraiser.getHistory();
    setHistory(h);
  };

  const loadLatest = async () => {
    const s = await window.appraiser.getLatest();
    setSnap(s);
    if (s) setSelectedId(s.runId);
  };

  useEffect(() => {
    loadLatest();
    loadHistory();

    const offProgress = window.appraiser.onProgress((p) => {
      setRunning(true);
      setProgress(p);
    });
    const offComplete = window.appraiser.onComplete((s) => {
      setSnap(s);
      setSelectedId(s.runId);
      setRunning(false);
      setProgress(null);
      loadHistory();
    });
    return () => { offProgress(); offComplete(); };
  }, []);

  const selectRun = async (id: string) => {
    setSelectedId(id);
    const s = await window.appraiser.getSnapshot(id);
    if (s) setSnap(s);
  };

  const triggerRun = async () => {
    if (running) return;
    setRunning(true);
    setProgress(null);
    const s = await window.appraiser.runAppraisal();
    if (s) {
      setSnap(s);
      setSelectedId(s.runId);
      loadHistory();
    }
    setRunning(false);
    setProgress(null);
  };

  return (
    <div className="layout">
      <div className="titlebar" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <h1>MEMBRA APPRAISER</h1>
        <div style={{ display: "flex", gap: 8, WebkitAppRegion: "no-drag" } as React.CSSProperties}>
          <div className="tabs" style={{ marginBottom: 0 }}>
            <button className={`tab${tab === "dashboard" ? " active" : ""}`} onClick={() => setTab("dashboard")}>Dashboard</button>
            <button className={`tab${tab === "settings" ? " active" : ""}`} onClick={() => setTab("settings")}>Settings</button>
          </div>
          <button className="btn btn-primary" onClick={triggerRun} disabled={running} style={{ padding: "5px 14px", fontSize: 12 }}>
            {running ? "Running…" : "⚡ Appraise Now"}
          </button>
        </div>
      </div>

      <Sidebar history={history} selectedId={selectedId} onSelect={selectRun} />

      <div className="main">
        {tab === "settings" ? (
          <SettingsPanel onSave={() => {}} />
        ) : (
          <>
            <Hero snap={snap} running={running} progress={progress} />
            {snap ? (
              <FileTable files={snap.files} />
            ) : (
              <div className="empty">
                <h3>No appraisals yet</h3>
                <p>Click "⚡ Appraise Now" or set an interval in Settings to begin.</p>
                <p style={{ marginTop: 8, fontSize: 12 }}>Without an API key, values are estimated from file size. Add a key in Settings for LLM-powered appraisals.</p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
