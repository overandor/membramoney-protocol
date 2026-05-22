"use strict";

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("appraiser", {
  loadSettings: () => ipcRenderer.invoke("settings:load"),
  saveSettings: (s) => ipcRenderer.invoke("settings:save", s),

  runAppraisal: () => ipcRenderer.invoke("appraisal:run"),
  getLatest: () => ipcRenderer.invoke("appraisal:latest"),
  getHistory: () => ipcRenderer.invoke("appraisal:history"),
  getSnapshot: (runId) => ipcRenderer.invoke("appraisal:get", runId),
  getStatus: () => ipcRenderer.invoke("appraisal:status"),

  pickFolder: () => ipcRenderer.invoke("dialog:pickFolder"),

  onProgress: (cb) => {
    ipcRenderer.on("appraisal:progress", (_, data) => cb(data));
    return () => ipcRenderer.removeAllListeners("appraisal:progress");
  },
  onComplete: (cb) => {
    ipcRenderer.on("appraisal:complete", (_, snap) => cb(snap));
    return () => ipcRenderer.removeAllListeners("appraisal:complete");
  },
});
