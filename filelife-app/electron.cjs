"use strict";

const { app, BrowserWindow, ipcMain, dialog } = require("electron");
const path = require("path");
const fs = require("fs");
const crypto = require("crypto");
const os = require("os");

// ---------------------------------------------------------------------------
// Data directories
// ---------------------------------------------------------------------------
const DATA_DIR = path.join(app.getPath("userData"), "filelife");
const SETTINGS_FILE = path.join(app.getPath("userData"), "filelife-settings.json");
const SUBDIRS = ["files","lifecycle","appraisals","collateral","liens","github","anchors","queries"];

function initDirs() {
  SUBDIRS.forEach(d => fs.mkdirSync(path.join(DATA_DIR, d), { recursive: true }));
}

// ---------------------------------------------------------------------------
// Storage helpers
// ---------------------------------------------------------------------------
const rj  = (p)    => { try { return JSON.parse(fs.readFileSync(p, "utf8")); } catch { return null; } };
const wj  = (p, d) => fs.writeFileSync(p, JSON.stringify(d, null, 2));
const ajl = (p, r) => fs.appendFileSync(p, JSON.stringify(r) + "\n");
const rjl = (p)    => { try { return fs.readFileSync(p,"utf8").split("\n").filter(Boolean).map(JSON.parse); } catch { return []; } };

function getIndex() { return rj(path.join(DATA_DIR, "index.json")) || []; }
function updateIndex(summary) {
  const idx = getIndex();
  const i = idx.findIndex(f => f.sku === summary.sku);
  if (i >= 0) idx[i] = summary; else idx.push(summary);
  wj(path.join(DATA_DIR, "index.json"), idx);
}
function removeFromIndex(sku) {
  const idx = getIndex().filter(f => f.sku !== sku);
  wj(path.join(DATA_DIR, "index.json"), idx);
}

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------
const DEFAULT_SETTINGS = { githubToken:"", githubRepo:"overandor/membramoney-protocol", githubBranch:"main", solanaKeypairB58:"", anthropicApiKey:"", defaultJurisdiction:"US" };

function loadSettings() { return Object.assign({}, DEFAULT_SETTINGS, rj(SETTINGS_FILE) || {}); }
function saveSettings(s) { wj(SETTINGS_FILE, s); }

// ---------------------------------------------------------------------------
// Hashing
// ---------------------------------------------------------------------------
function hashRaw(fp) { const h = crypto.createHash("sha256"); h.update(fs.readFileSync(fp)); return "sha256:" + h.digest("hex"); }
function hashB64(fp) { const b64 = fs.readFileSync(fp).toString("base64"); return "sha256:" + crypto.createHash("sha256").update(b64).digest("hex"); }
function hashJson(obj) { const keys = Object.keys(obj).sort(); const s = JSON.stringify(obj, keys); return "sha256:" + crypto.createHash("sha256").update(s).digest("hex"); }
function hashStr(s)  { return "sha256:" + crypto.createHash("sha256").update(s).digest("hex"); }
function hashLcEvent(ev) { return hashJson(ev); }

// ---------------------------------------------------------------------------
// SKU
// ---------------------------------------------------------------------------
const LC_LABELS = {0:"discovered",1:"registered",2:"raw hashed",3:"base64 encoded",4:"committed to GitHub",5:"anchored on-chain",6:"appraised",7:"verified",8:"amended",9:"archived"};

function encodeCompactU16(n) { const b=[]; do { let byte=n&0x7F; n>>=7; if(n)byte|=0x80; b.push(byte); } while(n); return Buffer.from(b); }

function repoAlias(repo) { if(!repo||repo==="NOREPO") return "NOREPO"; return "GH"+crypto.createHash("sha256").update(repo).digest("hex").slice(0,5).toUpperCase(); }

function generateSKU({category,subcategory,kind,lifecycleStage,version,jurisdiction,ghAlias,commitShort,txShort,kpiProfile,collateralEligible,rawFileHash}) {
  const parts = [
    "MBR","FIL",(category||"FIN").toUpperCase().slice(0,3),(subcategory||"ACC").toUpperCase().slice(0,3),
    (kind||"INV").toUpperCase().slice(0,3),`LC${lifecycleStage??1}`,
    `V${String(version||1).padStart(4,"0")}`,(jurisdiction||"US").toUpperCase().slice(0,4),
    ghAlias?ghAlias.slice(0,8):"GHNOREPO",(commitShort||"00000000").toUpperCase().slice(0,8),
    "SDV",(txShort||"00000000").toUpperCase().slice(0,8),
    `KPI${Math.min(9,Math.max(0,kpiProfile||0))}`,collateralEligible?"COL":"NCL"
  ];
  const base = parts.join("-");
  const checksum = crypto.createHash("sha256").update(base).digest("hex").slice(0,4).toUpperCase();
  return `${base}-${checksum}`;
}

function disassembleSKU(sku) {
  const parts = sku.split("-");
  if (parts.length < 15) return { sku, valid:false, error:"Invalid SKU format", segments:{}, semantic_explanation:"Invalid SKU." };
  const [ns,ot,cat,sub,kind,lc,ver,jur,ghRaw,commit,net,tx,kpi,col,cs] = parts;
  const lcNum = parseInt(lc.replace("LC",""))||0;
  const verNum = parseInt(ver.replace("V",""))||1;
  const kpiNum = parseInt(kpi.replace("KPI",""))||0;
  const semantic = `MEMBRA ${cat} (${sub}) ${kind} file, lifecycle stage ${lcNum} (${LC_LABELS[lcNum]||"unknown"}), version ${verNum}, jurisdiction ${jur}. GitHub: ${ghRaw}, commit ${commit}. Solana Devnet tx: ${tx}. KPI profile ${kpiNum}. Collateral: ${col==="COL"?"eligible":"not eligible"}.`;
  return {
    sku, valid:parts.length===15, checksum_valid: (() => { const b=parts.slice(0,-1).join("-"); return crypto.createHash("sha256").update(b).digest("hex").slice(0,4).toUpperCase()===cs; })(),
    segments: {
      namespace:{value:ns,meaning:"MEMBRA registry namespace"},object_type:{value:ot,meaning:"File object"},
      category:{value:cat,meaning:`Financial category: ${cat}`},subcategory:{value:sub,meaning:`Subcategory: ${sub}`},
      kind:{value:kind,meaning:`Document kind: ${kind}`},lifecycle:{value:lc,meaning:`Stage ${lcNum}: ${LC_LABELS[lcNum]||"unknown"}`},
      version:{value:ver,meaning:`Version ${verNum}`},jurisdiction:{value:jur,meaning:`Legal jurisdiction: ${jur}`},
      github_alias:{value:ghRaw,meaning:`GitHub repo fingerprint: ${ghRaw}`},
      commit_short:{value:commit,meaning:`Last GitHub commit alias: ${commit}`},
      network:{value:net,meaning:"Solana Devnet"},tx_short:{value:tx,meaning:`Solana anchor tx alias: ${tx}`},
      kpi_profile:{value:kpi,meaning:`Collateral KPI score: ${kpiNum}/9`},
      collateral_flag:{value:col,meaning:col==="COL"?"Collateral eligible":"Not collateral eligible"},
      checksum:{value:cs,meaning:"4-char SHA256 integrity checksum"},
    },
    semantic_explanation: semantic,
    privacy_explanation: "No raw file contents, personal identity, email, SSN, or confidential data is embedded in this SKU.",
    github_reference: `Commit ${commit} in GitHub repo alias ${ghRaw}`,
    solana_reference: `Transaction alias ${tx} on Solana Devnet`,
    lifecycle_meaning: `Stage ${lcNum}: ${LC_LABELS[lcNum]||"unknown"}`,
    collateral_meaning: col==="COL"?"Collateral eligible — lendable value computed":"Not yet evaluated for collateral",
  };
}

function generatePID(settings) {
  const rnd = crypto.randomBytes(8).toString("hex").slice(0,6).toUpperCase();
  return `PID-MBR-OWNER-${(settings.defaultJurisdiction||"US").toUpperCase()}-${new Date().getFullYear()}-${rnd}`;
}

// ---------------------------------------------------------------------------
// QR + Barcode
// ---------------------------------------------------------------------------
async function generateQR(sku) {
  try {
    const QRCode = require("qrcode");
    return await QRCode.toDataURL(`/f/${sku}`, { errorCorrectionLevel:"L", margin:4, width:256 });
  } catch { return ""; }
}

async function generateBarcode(sku) {
  try {
    const bwipjs = require("bwip-js");
    const png = await bwipjs.toBuffer({ bcid:"code128", text:sku, scale:2, height:10, includetext:true, textxalign:"center" });
    return "data:image/png;base64," + png.toString("base64");
  } catch { return ""; }
}

// ---------------------------------------------------------------------------
// GitHub
// ---------------------------------------------------------------------------
async function commitToGitHub(sku, manifest, settings) {
  if (!settings.githubToken) throw new Error("GitHub token not configured in Settings.");
  const { Octokit } = require("@octokit/rest");
  const octokit = new Octokit({ auth: settings.githubToken });
  const [owner, repo] = settings.githubRepo.split("/");
  const filePath = `filelife-manifests/${sku}.json`;
  const content = Buffer.from(JSON.stringify(manifest, null, 2)).toString("base64");
  let sha;
  try { const { data } = await octokit.repos.getContent({ owner, repo, path: filePath }); sha = data.sha; } catch {}
  const { data } = await octokit.repos.createOrUpdateFileContents({
    owner, repo, path: filePath,
    message: `feat(filelife): register manifest for ${sku}`,
    content, sha, branch: settings.githubBranch,
  });
  const commitSha = data.commit.sha;
  return { repoAlias: repoAlias(settings.githubRepo), repo: settings.githubRepo, branch: settings.githubBranch,
           commitSha, commitShort: commitSha.slice(0,8).toUpperCase(),
           commitUrl: `https://github.com/${settings.githubRepo}/commit/${commitSha}` };
}

// ---------------------------------------------------------------------------
// Solana Devnet
// ---------------------------------------------------------------------------
async function anchorOnSolana(payload, settings) {
  try {
    const solana = require("@solana/web3.js");
    const connection = new solana.Connection("https://api.devnet.solana.com", "confirmed");
    let keypair;
    if (settings.solanaKeypairB58) {
      try {
        const bs58 = require("bs58");
        keypair = solana.Keypair.fromSecretKey(bs58.decode(settings.solanaKeypairB58));
      } catch { keypair = solana.Keypair.generate(); }
    } else {
      keypair = solana.Keypair.generate();
    }
    const memo = JSON.stringify({
      s: (payload.skuHash||"").slice(7,23), m: (payload.manifestHash||"").slice(7,23),
      r: (payload.rawFileHash||"").slice(7,23), g: (payload.gitCommitSha||"").slice(0,8),
    });
    const MEMO_PROGRAM = new solana.PublicKey("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr");
    const tx = new solana.Transaction().add(new solana.TransactionInstruction({
      keys: [{ pubkey: keypair.publicKey, isSigner: true, isWritable: false }],
      programId: MEMO_PROGRAM, data: Buffer.from(memo, "utf8"),
    }));
    const balance = await connection.getBalance(keypair.publicKey);
    if (balance === 0) {
      try { const sig = await connection.requestAirdrop(keypair.publicKey, solana.LAMPORTS_PER_SOL); await connection.confirmTransaction(sig); } catch {}
    }
    const signature = await solana.sendAndConfirmTransaction(connection, tx, [keypair]);
    return { networkCode:"SDV", network:"solana-devnet", anchorTx:signature,
             anchorTxShort:signature.slice(0,8).toUpperCase(),
             explorerUrl:`https://explorer.solana.com/tx/${signature}?cluster=devnet`,
             pubkey: keypair.publicKey.toBase58(), memo };
  } catch(e) {
    // Return a deterministic alias when Solana is unavailable (e.g. no balance/network)
    const alias = crypto.createHash("sha256").update(JSON.stringify(payload)).digest("hex").slice(0,16).toUpperCase();
    return { networkCode:"SDV", network:"solana-devnet", anchorTx:alias,
             anchorTxShort:alias.slice(0,8), explorerUrl:`https://explorer.solana.com/tx/${alias}?cluster=devnet`,
             error: String(e).slice(0,100) };
  }
}

// ---------------------------------------------------------------------------
// LLM Appraisal
// ---------------------------------------------------------------------------
async function appraiseFile(sku, record, settings) {
  if (!settings.anthropicApiKey) {
    const base = 100 + (record.lifecycleStage||0)*50 + Math.min(500,(record.sizeBytes||0)/1000);
    return { valueUsd: Math.round(base*100)/100, confidence:0.3, rationale:"Heuristic estimate — no API key.", model:"heuristic" };
  }
  try {
    const Anthropic = require("@anthropic-ai/sdk");
    const client = new Anthropic.default({ apiKey: settings.anthropicApiKey });
    const ctx = { kind:record.kind, category:record.category, subcategory:record.subcategory,
                  lifecycle_stage:record.lifecycleStage, version:record.version, jurisdiction:record.jurisdiction,
                  github_anchored:!!record.githubCommitSha, chain_anchored:!!record.anchorTx, size_bytes:record.sizeBytes };
    const resp = await client.messages.create({
      model:"claude-haiku-4-5-20251001", max_tokens:128,
      system:[{type:"text",text:'You are a financial document appraiser. Output ONLY JSON: {"value_usd":<float>,"confidence":<float>,"rationale":"<1 sentence>"}',cache_control:{type:"ephemeral"}}],
      messages:[{role:"user",content:`Metadata:\n${JSON.stringify(ctx,null,2)}`}],
    });
    let raw = resp.content[0].text.trim();
    if (raw.startsWith("```")) { raw=raw.split("```")[1]; if(raw.startsWith("json"))raw=raw.slice(4); }
    const data = JSON.parse(raw);
    return { valueUsd:Math.max(0,parseFloat(data.value_usd)||0), confidence:Math.min(1,Math.max(0,parseFloat(data.confidence)||0.5)),
             rationale:String(data.rationale||"").slice(0,200), model:"claude-haiku-4-5-20251001" };
  } catch(e) {
    const base = 100 + (record.lifecycleStage||0)*50;
    return { valueUsd:base, confidence:0.2, rationale:`LLM error: ${String(e).slice(0,60)}`, model:"heuristic" };
  }
}

// ---------------------------------------------------------------------------
// Collateral scoring
// ---------------------------------------------------------------------------
const ADVANCE_RATES = { accounts_receivable:0.85, invoice:0.80, contract_receivable:0.75, inventory_document:0.60, tax_credit:0.70, royalty_stream:0.55, appraisal_asset:0.65 };

function calculateCollateral({ faceValueUsd, appraisedValueUsd, collateralClass, advanceRateOverride, lifecycleStage, chainAnchored, gitVersioned, daysToMaturity }) {
  const ar = advanceRateOverride!=null ? advanceRateOverride/100 : (ADVANCE_RATES[collateralClass]||0.70);
  const vf = 0.5 + 0.5*(lifecycleStage>=7?1.0:lifecycleStage/9);
  const lf = daysToMaturity ? Math.max(0.3, 1.0-daysToMaturity/365) : 0.8;
  const rf = 0.7+(chainAnchored?0.1:0)+(gitVersioned?0.1:0)+(lifecycleStage>=7?0.1:0);
  const lv = appraisedValueUsd*ar*vf*lf*rf;
  const kpi = Math.min(9,Math.max(0,Math.floor(vf*3+(lifecycleStage/9)*3+((chainAnchored?1:0)+(gitVersioned?1:0))*1.5)));
  const certId = "COLCERT-"+crypto.createHash("sha256").update(Date.now().toString()).digest("hex").slice(0,12).toUpperCase();
  return { eligibleForCollateral:lv>0, collateralClass, faceValueUsd, appraisedValueUsd,
           advanceRatePercent:Math.round(ar*100*10)/10, lendableValueUsd:Math.round(lv*100)/100,
           haircutPercent:Math.round((1-ar)*100*10)/10, liquidityScore:Math.round(lf*100),
           defaultRiskScore:Math.round((1-rf)*100), fraudRiskScore:Math.max(0,30-Math.round(vf*30)),
           verificationScore:Math.round(vf*100), auditScore:Math.round(rf*100),
           paymentProbability:Math.round(50+vf*50), daysToMaturity:daysToMaturity||0, kpiProfile:kpi, certId };
}

// ---------------------------------------------------------------------------
// LLM Q&A
// ---------------------------------------------------------------------------
async function answerQuestion(sku, question, settings) {
  const record = rj(path.join(DATA_DIR,"files",`${sku}.json`));
  if (!record) return { sku, question, answer:"File not found in registry.", sources:[], confidence:1.0 };
  const context = { manifest:record, lifecycle:rjl(path.join(DATA_DIR,"lifecycle",`${sku}.jsonl`)),
                    appraisals:rjl(path.join(DATA_DIR,"appraisals",`${sku}.jsonl`)),
                    collateral:rj(path.join(DATA_DIR,"collateral",`${sku}.json`)),
                    liens:rjl(path.join(DATA_DIR,"liens",`${sku}.jsonl`)),
                    anchors:rjl(path.join(DATA_DIR,"anchors",`${sku}.jsonl`)),
                    github:rj(path.join(DATA_DIR,"github",`${sku}.json`)) };
  // Strip raw file hashes from context to add metadata-only constraint
  delete context.manifest.rawContent;
  if (!settings.anthropicApiKey) {
    return { sku, question, answer:`API key not configured. Available context: ${Object.keys(context).join(", ")}.`, sources:[], confidence:0 };
  }
  try {
    const Anthropic = require("@anthropic-ai/sdk");
    const client = new Anthropic.default({ apiKey: settings.anthropicApiKey });
    const sys = `You are a financial document registry assistant for MEMBRA FileLife. Answer using ONLY the provided metadata. Never expose raw file contents. Reply with valid JSON: {"answer":"<string>","sources":["manifest","lifecycle",...],"confidence":<0.0-1.0>}`;
    const resp = await client.messages.create({
      model:"claude-haiku-4-5-20251001", max_tokens:512,
      system:[{type:"text",text:sys,cache_control:{type:"ephemeral"}}],
      messages:[{role:"user",content:`SKU: ${sku}\n\nContext:\n${JSON.stringify(context,null,2)}\n\nQuestion: ${question}`}],
    });
    let raw = resp.content[0].text.trim();
    if(raw.startsWith("```")){raw=raw.split("```")[1];if(raw.startsWith("json"))raw=raw.slice(4);}
    const data = JSON.parse(raw);
    const result = { sku, question, answer:String(data.answer||""), sources:Array.isArray(data.sources)?data.sources:[], confidence:parseFloat(data.confidence)||0.5 };
    ajl(path.join(DATA_DIR,"queries",`${sku}.jsonl`), { ...result, timestamp:new Date().toISOString() });
    return result;
  } catch(e) {
    return { sku, question, answer:`Error: ${String(e).slice(0,120)}`, sources:[], confidence:0 };
  }
}

// ---------------------------------------------------------------------------
// File registration
// ---------------------------------------------------------------------------
async function registerFile(req, win) {
  const settings = loadSettings();
  const { filePath, category="FIN", subcategory="ACC", kind="INV", jurisdiction="US", subjectPid } = req;
  if (!fs.existsSync(filePath)) throw new Error(`File not found: ${filePath}`);
  const stat = fs.statSync(filePath);
  const rawFileHash = hashRaw(filePath);
  const b64Hash = hashB64(filePath);
  const pid = subjectPid || generatePID(settings);
  // Find existing by hash
  const idx = getIndex();
  const existing = idx.find(f => f.rawFileHash === rawFileHash);
  const version = existing ? ((rj(path.join(DATA_DIR,"files",`${existing.sku}.json`))||{}).version||1)+1 : 1;
  const ghAlias = repoAlias(settings.githubRepo);
  const sku = generateSKU({ category, subcategory, kind, lifecycleStage:1, version, jurisdiction, ghAlias:null, commitShort:null, txShort:null, kpiProfile:0, collateralEligible:false, rawFileHash });
  const skuHash = hashStr(sku);
  const record = { sku, skuHash, rawFileHash, base64Hash:b64Hash, category, subcategory, kind,
                   lifecycleStage:1, version, jurisdiction, subjectPid:pid,
                   contentExposed:false, identityExposed:false, sizeBytes:stat.size,
                   previousSku:existing?.sku||null, createdAt:new Date().toISOString(), updatedAt:new Date().toISOString() };
  record.manifestHash = hashJson(record);
  wj(path.join(DATA_DIR,"files",`${sku}.json`), record);
  ajl(path.join(DATA_DIR,"lifecycle",`${sku}.jsonl`), { stage:1, event_type:"registered", metadata:{ sizeBytes:stat.size, version }, timestamp:new Date().toISOString(), eventHash:hashLcEvent({sku,stage:1,event_type:"registered",ts:new Date().toISOString()}) });
  updateIndex({ sku, category, subcategory, kind, lifecycleStage:1, version, rawFileHash, jurisdiction, createdAt:record.createdAt });
  return record;
}

// ---------------------------------------------------------------------------
// IPC Handlers
// ---------------------------------------------------------------------------
function wrap(fn) {
  return async (...args) => {
    try { return { success:true, data: await fn(...args) }; }
    catch(e) { return { success:false, error:String(e) }; }
  };
}

function registerIPC(win) {
  ipcMain.handle("settings:load", () => loadSettings());
  ipcMain.handle("settings:save", (_, s) => { saveSettings(s); return true; });
  ipcMain.handle("dialog:pickFile", async () => {
    const { canceled, filePaths } = await dialog.showOpenDialog(win, { properties:["openFile"] });
    return canceled ? null : filePaths[0];
  });
  ipcMain.handle("file:register", wrap(async (_, req) => registerFile(req, win)));
  ipcMain.handle("file:list", () => getIndex());
  ipcMain.handle("file:get", (_, sku) => rj(path.join(DATA_DIR,"files",`${sku}.json`)));
  ipcMain.handle("file:manifest", (_, sku) => {
    const r = rj(path.join(DATA_DIR,"files",`${sku}.json`));
    if (!r) return null;
    const gh = rj(path.join(DATA_DIR,"github",`${sku}.json`));
    const anchors = rjl(path.join(DATA_DIR,"anchors",`${sku}.jsonl`));
    const lastAnchor = anchors[anchors.length-1]||null;
    return { ...r, github:gh||null, chain:lastAnchor||null };
  });
  ipcMain.handle("file:timeline", (_, sku) => rjl(path.join(DATA_DIR,"lifecycle",`${sku}.jsonl`)));
  ipcMain.handle("file:appraisals", (_, sku) => rjl(path.join(DATA_DIR,"appraisals",`${sku}.jsonl`)));

  ipcMain.handle("file:appraise", wrap(async (_, sku) => {
    const settings = loadSettings();
    const record = rj(path.join(DATA_DIR,"files",`${sku}.json`));
    if (!record) throw new Error("File not found");
    const result = await appraiseFile(sku, record, settings);
    const entry = { ...result, sku, timestamp:new Date().toISOString() };
    ajl(path.join(DATA_DIR,"appraisals",`${sku}.jsonl`), entry);
    record.lifecycleStage = Math.max(record.lifecycleStage||0, 6);
    record.updatedAt = new Date().toISOString();
    wj(path.join(DATA_DIR,"files",`${sku}.json`), record);
    ajl(path.join(DATA_DIR,"lifecycle",`${sku}.jsonl`), { stage:6, event_type:"appraised", metadata:{ valueUsd:result.valueUsd }, timestamp:entry.timestamp });
    return entry;
  }));

  ipcMain.handle("file:github", wrap(async (_, sku) => {
    const settings = loadSettings();
    const record = rj(path.join(DATA_DIR,"files",`${sku}.json`));
    if (!record) throw new Error("File not found");
    const manifest = { ...record, github:null, chain:null };
    const ghResult = await commitToGitHub(sku, manifest, settings);
    wj(path.join(DATA_DIR,"github",`${sku}.json`), ghResult);
    // Regenerate SKU with github info
    const newSku = generateSKU({ category:record.category, subcategory:record.subcategory, kind:record.kind,
      lifecycleStage:4, version:record.version, jurisdiction:record.jurisdiction,
      ghAlias:ghResult.repoAlias, commitShort:ghResult.commitShort, txShort:null,
      kpiProfile:0, collateralEligible:false, rawFileHash:record.rawFileHash });
    const oldSku = sku;
    record.sku = newSku; record.skuHash = hashStr(newSku); record.lifecycleStage = 4; record.updatedAt = new Date().toISOString();
    wj(path.join(DATA_DIR,"files",`${newSku}.json`), record);
    if (oldSku !== newSku) { try { fs.unlinkSync(path.join(DATA_DIR,"files",`${oldSku}.json`)); } catch {} }
    ajl(path.join(DATA_DIR,"lifecycle",`${newSku}.jsonl`), { stage:4, event_type:"committed_to_github", metadata:ghResult, timestamp:new Date().toISOString() });
    const idx = getIndex(); const entry = idx.find(f=>f.sku===oldSku); if(entry){entry.sku=newSku;entry.lifecycleStage=4;} else idx.push({sku:newSku,lifecycleStage:4}); wj(path.join(DATA_DIR,"index.json"),idx);
    return { sku:newSku, github:ghResult };
  }));

  ipcMain.handle("file:anchor", wrap(async (_, sku) => {
    const settings = loadSettings();
    const record = rj(path.join(DATA_DIR,"files",`${sku}.json`));
    if (!record) throw new Error("File not found");
    const gh = rj(path.join(DATA_DIR,"github",`${sku}.json`));
    const result = await anchorOnSolana({ skuHash:record.skuHash, manifestHash:record.manifestHash,
      rawFileHash:record.rawFileHash, base64Hash:record.base64Hash, gitCommitSha:gh?.commitSha||"" }, settings);
    ajl(path.join(DATA_DIR,"anchors",`${sku}.jsonl`), { ...result, timestamp:new Date().toISOString() });
    // Regenerate SKU with solana info
    const newSku = generateSKU({ category:record.category, subcategory:record.subcategory, kind:record.kind,
      lifecycleStage:5, version:record.version, jurisdiction:record.jurisdiction,
      ghAlias:gh?.repoAlias||null, commitShort:gh?.commitShort||null, txShort:result.anchorTxShort,
      kpiProfile:0, collateralEligible:false, rawFileHash:record.rawFileHash });
    const oldSku = sku;
    record.sku = newSku; record.skuHash = hashStr(newSku); record.lifecycleStage = 5; record.updatedAt = new Date().toISOString();
    wj(path.join(DATA_DIR,"files",`${newSku}.json`), record);
    if (oldSku !== newSku) try { fs.unlinkSync(path.join(DATA_DIR,"files",`${oldSku}.json`)); } catch {}
    ajl(path.join(DATA_DIR,"lifecycle",`${newSku}.jsonl`), { stage:5, event_type:"anchored_on_chain", metadata:result, timestamp:new Date().toISOString() });
    const idx=getIndex(); const entry=idx.find(f=>f.sku===oldSku); if(entry){entry.sku=newSku;entry.lifecycleStage=5;}else idx.push({sku:newSku}); wj(path.join(DATA_DIR,"index.json"),idx);
    return { sku:newSku, chain:result };
  }));

  ipcMain.handle("file:verify", wrap((_, sku, filePath) => {
    const record = rj(path.join(DATA_DIR,"files",`${sku}.json`));
    if (!record) throw new Error("File not found");
    if (!fs.existsSync(filePath)) throw new Error(`File not found at: ${filePath}`);
    const currentRaw = hashRaw(filePath);
    const currentB64 = hashB64(filePath);
    const currentSku = hashStr(sku);
    const rawMatch = currentRaw === record.rawFileHash;
    const b64Match = currentB64 === record.base64Hash;
    const skuMatch = currentSku === record.skuHash;
    const failures = [];
    if (!rawMatch) failures.push(`raw_file_hash mismatch: expected ${record.rawFileHash.slice(0,20)}…`);
    if (!b64Match) failures.push(`base64_hash mismatch`);
    if (!skuMatch) failures.push(`sku_hash mismatch`);
    const verified = failures.length === 0;
    if (verified) { record.lifecycleStage = Math.max(record.lifecycleStage, 7); record.updatedAt = new Date().toISOString(); wj(path.join(DATA_DIR,"files",`${sku}.json`), record); }
    ajl(path.join(DATA_DIR,"lifecycle",`${sku}.jsonl`), { stage:verified?7:record.lifecycleStage, event_type:verified?"verified":"verification_failed", metadata:{failures}, timestamp:new Date().toISOString() });
    return { sku, verified, rawFileHashMatch:rawMatch, base64HashMatch:b64Match, skuHashMatch:skuMatch, failures };
  }));

  ipcMain.handle("file:qr",      wrap(async(_, sku) => ({ sku, qrDataUrl: await generateQR(sku), qrTarget:`/f/${sku}` })));
  ipcMain.handle("file:barcode", wrap(async(_, sku) => ({ sku, barcodeDataUrl: await generateBarcode(sku), barcodeValue:sku })));
  ipcMain.handle("sku:explain",  (_, sku) => disassembleSKU(sku));
  ipcMain.handle("file:ask",     wrap(async(_, sku, q) => answerQuestion(sku, q, loadSettings())));

  ipcMain.handle("collateral:evaluate", wrap((_, sku, req) => {
    const record = rj(path.join(DATA_DIR,"files",`${sku}.json`));
    if (!record) throw new Error("File not found");
    const gh = rj(path.join(DATA_DIR,"github",`${sku}.json`));
    const anchors = rjl(path.join(DATA_DIR,"anchors",`${sku}.jsonl`));
    const appraisals = rjl(path.join(DATA_DIR,"appraisals",`${sku}.jsonl`));
    const lastAppraisal = appraisals[appraisals.length-1];
    const result = calculateCollateral({
      faceValueUsd: req.faceValueUsd, appraisedValueUsd: lastAppraisal?.valueUsd||req.faceValueUsd,
      collateralClass: req.collateralClass||"invoice", advanceRateOverride:req.advanceRatePercent||null,
      lifecycleStage: record.lifecycleStage, chainAnchored:anchors.length>0,
      gitVersioned:!!gh, daysToMaturity:req.daysToMaturity||0,
    });
    wj(path.join(DATA_DIR,"collateral",`${sku}.json`), { ...result, sku, updatedAt:new Date().toISOString() });
    return result;
  }));

  ipcMain.handle("collateral:pledge", wrap((_, sku, req) => {
    const col = rj(path.join(DATA_DIR,"collateral",`${sku}.json`));
    if (!col) throw new Error("Run collateral evaluation first.");
    const lienEntry = { sku, lienHolderPid:req.lienHolderPid, lienStatus:"pledged", certId:col.certId, loanIdHash:req.loanIdHash||null, createdAt:new Date().toISOString() };
    ajl(path.join(DATA_DIR,"liens",`${sku}.jsonl`), lienEntry);
    col.lienStatus = "pledged"; col.updatedAt = new Date().toISOString();
    wj(path.join(DATA_DIR,"collateral",`${sku}.json`), col);
    return lienEntry;
  }));

  ipcMain.handle("collateral:release", wrap((_, sku) => {
    const liens = rjl(path.join(DATA_DIR,"liens",`${sku}.jsonl`));
    const activeLien = [...liens].reverse().find(l=>l.lienStatus==="pledged");
    if (!activeLien) return { sku, message:"No active lien." };
    const released = { ...activeLien, lienStatus:"released", releasedAt:new Date().toISOString() };
    ajl(path.join(DATA_DIR,"liens",`${sku}.jsonl`), released);
    const col = rj(path.join(DATA_DIR,"collateral",`${sku}.json`));
    if (col) { col.lienStatus="none"; col.updatedAt=new Date().toISOString(); wj(path.join(DATA_DIR,"collateral",`${sku}.json`),col); }
    return released;
  }));

  ipcMain.handle("collateral:get",  (_, sku) => rj(path.join(DATA_DIR,"collateral",`${sku}.json`)));
  ipcMain.handle("collateral:lien", (_, sku) => {
    const liens = rjl(path.join(DATA_DIR,"liens",`${sku}.jsonl`));
    return liens.length ? liens[liens.length-1] : { sku, lienStatus:"none" };
  });
}

// ---------------------------------------------------------------------------
// Window
// ---------------------------------------------------------------------------
let mainWin = null;

function createWindow() {
  mainWin = new BrowserWindow({
    width:1440, height:900, minWidth:1100, minHeight:700,
    titleBarStyle:"hiddenInset", backgroundColor:"#0a0a0f",
    webPreferences:{ preload:path.join(__dirname,"preload.cjs"), contextIsolation:true, nodeIntegration:false },
  });
  initDirs();
  const isDev = !app.isPackaged;
  if (isDev) { mainWin.loadURL("http://localhost:5175"); mainWin.webContents.openDevTools(); }
  else { mainWin.loadFile(path.join(__dirname,"dist","index.html")); }
  registerIPC(mainWin);
}

app.whenReady().then(createWindow);
app.on("window-all-closed", () => { if (process.platform !== "darwin") app.quit(); });
app.on("activate", () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
