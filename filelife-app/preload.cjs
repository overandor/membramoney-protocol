"use strict";
const { contextBridge, ipcRenderer } = require("electron");

const invoke = (ch, ...args) => ipcRenderer.invoke(ch, ...args);

contextBridge.exposeInMainWorld("filelife", {
  loadSettings:      ()           => invoke("settings:load"),
  saveSettings:      (s)          => invoke("settings:save", s),
  pickFile:          ()           => invoke("dialog:pickFile"),
  registerFile:      (req)        => invoke("file:register", req),
  listFiles:         ()           => invoke("file:list"),
  getFile:           (sku)        => invoke("file:get", sku),
  getManifest:       (sku)        => invoke("file:manifest", sku),
  getTimeline:       (sku)        => invoke("file:timeline", sku),
  appraise:          (sku)        => invoke("file:appraise", sku),
  commitToGitHub:    (sku)        => invoke("file:github", sku),
  anchorOnChain:     (sku)        => invoke("file:anchor", sku),
  verify:            (sku, fp)    => invoke("file:verify", sku, fp),
  getQR:             (sku)        => invoke("file:qr", sku),
  getBarcode:        (sku)        => invoke("file:barcode", sku),
  explainSKU:        (sku)        => invoke("sku:explain", sku),
  getAppraisals:     (sku)        => invoke("file:appraisals", sku),
  evaluateCollateral:(sku, req)   => invoke("collateral:evaluate", sku, req),
  pledgeCollateral:  (sku, req)   => invoke("collateral:pledge", sku, req),
  releaseCollateral: (sku)        => invoke("collateral:release", sku),
  getCollateral:     (sku)        => invoke("collateral:get", sku),
  getLienStatus:     (sku)        => invoke("collateral:lien", sku),
  askQuestion:       (sku, q)     => invoke("file:ask", sku, q),
  onProgress: (cb) => {
    ipcRenderer.on("progress", (_, d) => cb(d));
    return () => ipcRenderer.removeAllListeners("progress");
  },
});
