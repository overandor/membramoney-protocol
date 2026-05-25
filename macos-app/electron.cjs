"use strict";

const { app, BrowserWindow, ipcMain, dialog, shell } = require("electron");
const path = require("path");
const fs = require("fs");
const crypto = require("crypto");
const os = require("os");

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const SNAPSHOTS_DIR = path.join(app.getPath("userData"), "appraisal_snapshots");
const SETTINGS_FILE = path.join(app.getPath("userData"), "settings.json");
const CACHE_FILE = path.join(app.getPath("userData"), "value_cache.json");

const TEXT_EXTS = new Set([
  ".py", ".rs", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
  ".toml", ".yaml", ".yml", ".json", ".md", ".txt", ".sql",
  ".sh", ".env", ".cfg", ".ini", ".html", ".css", ".scss",
  ".lock", ".gitignore", ".editorconfig",
]);

const SKIP_DIRS = new Set([
  "node_modules", ".git", "__pycache__", ".pytest_cache",
  "target", "dist", "dist-app", "build", ".venv", "venv",
  "appraisal_snapshots", ".next", ".nuxt",
]);

const MAX_FILE_BYTES = 12_000;
const MAX_FILES = 2_000;
const DEFAULT_INTERVAL_MS = 60 * 60 * 1000; // 1 hour

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------

function loadSettings() {
  try {
    return JSON.parse(fs.readFileSync(SETTINGS_FILE, "utf8"));
  } catch {
    return { apiKey: "", scanPath: os.homedir(), intervalMs: DEFAULT_INTERVAL_MS };
  }
}

function saveSettings(s) {
  fs.writeFileSync(SETTINGS_FILE, JSON.stringify(s, null, 2));
}

// ---------------------------------------------------------------------------
// Value cache (content_hash → { valueCents, rationale })
// ---------------------------------------------------------------------------

function loadCache() {
  try { return JSON.parse(fs.readFileSync(CACHE_FILE, "utf8")); }
  catch { return {}; }
}

function saveCache(cache) {
  fs.writeFileSync(CACHE_FILE, JSON.stringify(cache));
}

// ---------------------------------------------------------------------------
// Merkle tree
// ---------------------------------------------------------------------------

function sha256hex(data) {
  return crypto.createHash("sha256").update(data).digest("hex");
}

function leafHash(relPath, contentHash, valueCents) {
  return sha256hex(`${relPath}|${contentHash}|${valueCents}`);
}

function pairHash(a, b) {
  return sha256hex(a + b);
}

function buildMerkleTree(leaves) {
  if (leaves.length === 0) return { root: sha256hex("empty"), levels: [[sha256hex("empty")]] };
  let layer = [...leaves];
  const levels = [layer.slice()];
  while (layer.length > 1) {
    if (layer.length % 2 === 1) layer.push(layer[layer.length - 1]);
    const next = [];
    for (let i = 0; i < layer.length; i += 2) next.push(pairHash(layer[i], layer[i + 1]));
    levels.push(next.slice());
    layer = next;
  }
  return { root: layer[0], levels };
}

function merkleProof(leaves, index) {
  if (leaves.length === 0) return [];
  let layer = [...leaves];
  const proof = [];
  let idx = index;
  while (layer.length > 1) {
    if (layer.length % 2 === 1) layer.push(layer[layer.length - 1]);
    const sibIdx = idx ^ 1;
    proof.push({ sibling: layer[sibIdx], direction: idx % 2 === 0 ? "right" : "left" });
    layer = [];
    for (let i = 0; i < layer.length + proof.length; i += 2) {
      // re-build from original layer — simpler re-scan
    }
    // rebuild layer properly
    const orig = proof.length === 1 ? [...leaves] : (() => {
      // reconstruct previous layer from levels (not available here — simpler approach)
      return null;
    })();
    if (!orig) break;
    layer = [];
    for (let i = 0; i < orig.length; i += 2) layer.push(pairHash(orig[i], orig[i + 1] ?? orig[i]));
    idx = Math.floor(idx / 2);
  }
  return proof;
}

// ---------------------------------------------------------------------------
// File scanner
// ---------------------------------------------------------------------------

function contentHash(filePath) {
  const h = crypto.createHash("sha256");
  const buf = fs.readFileSync(filePath);
  h.update(buf);
  return h.digest("hex");
}

function scanFiles(root) {
  const results = [];
  function walk(dir) {
    let entries;
    try { entries = fs.readdirSync(dir, { withFileTypes: true }); }
    catch { return; }
    for (const e of entries) {
      if (results.length >= MAX_FILES) return;
      const fp = path.join(dir, e.name);
      if (e.isDirectory()) {
        if (!SKIP_DIRS.has(e.name)) walk(fp);
      } else if (e.isFile()) {
        try {
          const stat = fs.statSync(fp);
          if (stat.size > 0) results.push({ filePath: fp, size: stat.size });
        } catch { /* skip */ }
      }
    }
  }
  walk(root);
  return results;
}

// ---------------------------------------------------------------------------
// LLM appraiser
// ---------------------------------------------------------------------------

const SYSTEM_PROMPT = `You are a senior software asset appraiser specializing in open-source repositories.

Assign a fair market dollar value to individual source files, configs, and docs.

Consider:
- Intellectual property: uniqueness and non-triviality of logic
- Replacement cost: hours a skilled developer would need × $150/hr fully-loaded
- Strategic value: does it enable a core feature (crypto, API, security)?
- Data/config value: structured data, credentials hints, build config
- Documentation: well-written specs and architecture docs have real value

Output ONLY valid JSON: {"value_cents": <integer USD cents>, "rationale": "<one sentence ≤120 chars>"}

Example: {"value_cents": 4500, "rationale": "Core claim-validation logic, ~30 hrs to rebuild."}`;

async function appraiseWithLLM(apiKey, relPath, snippet) {
  const Anthropic = require("@anthropic-ai/sdk");
  const client = new Anthropic.default({ apiKey });
  const resp = await client.messages.create({
    model: "claude-haiku-4-5-20251001",
    max_tokens: 128,
    system: [{ type: "text", text: SYSTEM_PROMPT, cache_control: { type: "ephemeral" } }],
    messages: [{ role: "user", content: `File: ${relPath}\n\n\`\`\`\n${snippet}\n\`\`\`` }],
  });
  let raw = resp.content[0].text.trim();
  if (raw.startsWith("```")) { raw = raw.split("```")[1]; if (raw.startsWith("json")) raw = raw.slice(4); }
  const data = JSON.parse(raw);
  return { valueCents: Math.max(1, Math.floor(data.value_cents)), rationale: String(data.rationale ?? "").slice(0, 200) };
}

// ---------------------------------------------------------------------------
// Appraisal engine
// ---------------------------------------------------------------------------

let appraisalRunning = false;

async function runAppraisal(win, settings) {
  if (appraisalRunning) return null;
  appraisalRunning = true;

  const scanRoot = settings.scanPath;
  const apiKey = settings.apiKey;
  const cache = loadCache();

  try {
    const files = scanFiles(scanRoot);
    const total = files.length;
    const appraisals = [];

    for (let i = 0; i < files.length; i++) {
      const { filePath, size } = files[i];
      const relPath = path.relative(scanRoot, filePath);
      const ext = path.extname(filePath).toLowerCase();

      win?.webContents.send("appraisal:progress", { current: i + 1, total, file: relPath });

      let valueCents, rationale, chash;
      try {
        chash = contentHash(filePath);
      } catch {
        continue;
      }

      if (!TEXT_EXTS.has(ext)) {
        // heuristic for binary files
        valueCents = Math.max(50, Math.floor(size / 1024 * 0.1));
        rationale = `Binary/generated asset, size-based estimate (${size} bytes).`;
      } else if (cache[chash]) {
        ({ valueCents, rationale } = cache[chash]);
      } else if (apiKey) {
        try {
          let snippet = "";
          try { snippet = fs.readFileSync(filePath, "utf8").slice(0, MAX_FILE_BYTES); } catch {}
          if (!snippet.trim()) {
            valueCents = 25; rationale = "Empty or whitespace-only file.";
          } else {
            ({ valueCents, rationale } = await appraiseWithLLM(apiKey, relPath, snippet));
            cache[chash] = { valueCents, rationale };
          }
        } catch (e) {
          valueCents = 100; rationale = `LLM error: ${String(e).slice(0, 60)}.`;
        }
      } else {
        // no API key — size heuristic for text too
        const lines = Math.max(1, Math.floor(size / 40));
        valueCents = Math.min(50_000, lines * 5);
        rationale = `Size-based estimate (no API key); ~${lines} lines.`;
      }

      const lh = leafHash(relPath, chash, valueCents);
      appraisals.push({ relPath, contentHash: chash, sizeBytes: size, valueCents, rationale, leafHash: lh });
    }

    saveCache(cache);

    appraisals.sort((a, b) => a.relPath.localeCompare(b.relPath));
    const leaves = appraisals.map((a) => a.leafHash);
    const { root } = buildMerkleTree(leaves);
    const totalCents = appraisals.reduce((s, a) => s + a.valueCents, 0);

    const prev = latestSnapshot();
    const runId = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19) + "Z";
    const snap = {
      runId,
      timestamp: new Date().toISOString(),
      merkleRoot: root,
      previousRoot: prev?.merkleRoot ?? null,
      totalValueCents: totalCents,
      deltaCents: prev != null ? totalCents - prev.totalValueCents : null,
      fileCount: appraisals.length,
      scanPath: scanRoot,
      files: appraisals,
    };

    fs.mkdirSync(SNAPSHOTS_DIR, { recursive: true });
    fs.writeFileSync(path.join(SNAPSHOTS_DIR, `${runId}.json`), JSON.stringify(snap, null, 2));
    return snap;
  } finally {
    appraisalRunning = false;
  }
}

function listSnapshotIds() {
  try {
    return fs.readdirSync(SNAPSHOTS_DIR)
      .filter((f) => f.endsWith(".json"))
      .map((f) => f.slice(0, -5))
      .sort();
  } catch { return []; }
}

function loadSnapshot(runId) {
  try { return JSON.parse(fs.readFileSync(path.join(SNAPSHOTS_DIR, `${runId}.json`), "utf8")); }
  catch { return null; }
}

function latestSnapshot() {
  const ids = listSnapshotIds();
  return ids.length ? loadSnapshot(ids[ids.length - 1]) : null;
}

// ---------------------------------------------------------------------------
// IPC handlers
// ---------------------------------------------------------------------------

function registerIPC(win) {
  ipcMain.handle("settings:load", () => loadSettings());
  ipcMain.handle("settings:save", (_, s) => { saveSettings(s); return true; });

  ipcMain.handle("appraisal:run", async () => {
    const s = loadSettings();
    const snap = await runAppraisal(win, s);
    return snap;
  });

  ipcMain.handle("appraisal:latest", () => latestSnapshot());

  ipcMain.handle("appraisal:history", () => {
    return listSnapshotIds()
      .reverse()
      .slice(0, 50)
      .map((id) => {
        const s = loadSnapshot(id);
        if (!s) return null;
        return {
          runId: s.runId, timestamp: s.timestamp, merkleRoot: s.merkleRoot,
          previousRoot: s.previousRoot, totalValueCents: s.totalValueCents,
          deltaCents: s.deltaCents, fileCount: s.fileCount,
        };
      })
      .filter(Boolean);
  });

  ipcMain.handle("appraisal:get", (_, runId) => loadSnapshot(runId));

  ipcMain.handle("appraisal:status", () => ({ running: appraisalRunning }));

  ipcMain.handle("dialog:pickFolder", async () => {
    const { canceled, filePaths } = await dialog.showOpenDialog(win, {
      properties: ["openDirectory"],
    });
    return canceled ? null : filePaths[0];
  });
}

// ---------------------------------------------------------------------------
// Hourly scheduler
// ---------------------------------------------------------------------------

let schedulerTimer = null;

function startScheduler(win) {
  if (schedulerTimer) clearInterval(schedulerTimer);
  const s = loadSettings();
  const interval = s.intervalMs ?? DEFAULT_INTERVAL_MS;
  schedulerTimer = setInterval(async () => {
    const settings = loadSettings();
    const snap = await runAppraisal(win, settings);
    if (snap) win?.webContents.send("appraisal:complete", snap);
  }, interval);
}

// ---------------------------------------------------------------------------
// Window
// ---------------------------------------------------------------------------

let mainWin = null;

function createWindow() {
  mainWin = new BrowserWindow({
    width: 1200,
    height: 820,
    minWidth: 900,
    minHeight: 600,
    titleBarStyle: "hiddenInset",
    backgroundColor: "#0f0f13",
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  const isDev = !app.isPackaged;
  if (isDev) {
    mainWin.loadURL("http://localhost:5174");
    mainWin.webContents.openDevTools();
  } else {
    mainWin.loadFile(path.join(__dirname, "dist", "index.html"));
  }

  registerIPC(mainWin);
  startScheduler(mainWin);
}

app.whenReady().then(createWindow);
app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit(); });
app.on("activate", () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
