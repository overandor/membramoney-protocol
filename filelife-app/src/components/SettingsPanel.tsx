import { useEffect, useState } from "react";

export default function SettingsPanel() {
  const [s, setS] = useState({ githubToken:"", githubRepo:"overandor/membramoney-protocol", githubBranch:"main", solanaKeypairB58:"", anthropicApiKey:"", defaultJurisdiction:"US" });
  const [saved, setSaved] = useState(false);

  useEffect(() => { window.filelife.loadSettings().then(setS); }, []);

  const save = async () => {
    await window.filelife.saveSettings(s);
    setSaved(true); setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="settings-form">
      <div className="section-title" style={{marginBottom:16}}>Configuration</div>
      <div className="field"><label>Anthropic API Key</label><input type="password" value={s.anthropicApiKey} placeholder="sk-ant-…" onChange={e => setS(p=>({...p,anthropicApiKey:e.target.value}))} /></div>
      <div className="field"><label>GitHub Personal Access Token</label><input type="password" value={s.githubToken} placeholder="ghp_…" onChange={e => setS(p=>({...p,githubToken:e.target.value}))} /></div>
      <div className="field"><label>GitHub Repository</label><input value={s.githubRepo} onChange={e => setS(p=>({...p,githubRepo:e.target.value}))} /></div>
      <div className="field"><label>GitHub Branch</label><input value={s.githubBranch} onChange={e => setS(p=>({...p,githubBranch:e.target.value}))} /></div>
      <div className="field"><label>Solana Keypair (base58, optional)</label><input type="password" value={s.solanaKeypairB58} placeholder="Leave blank for auto-generated ephemeral keypair" onChange={e => setS(p=>({...p,solanaKeypairB58:e.target.value}))} /></div>
      <div className="field">
        <label>Default Jurisdiction</label>
        <select value={s.defaultJurisdiction} onChange={e => setS(p=>({...p,defaultJurisdiction:e.target.value}))}>
          {["US","EU","UK","CA","AU","SG","JP"].map(j=><option key={j} value={j}>{j}</option>)}
        </select>
      </div>
      <button className="btn btn-primary" onClick={save}>{saved?"✓ Saved":"Save Settings"}</button>
      <p style={{fontSize:10,color:"var(--muted)",marginTop:12}}>API keys are stored locally in your app data directory. They are never uploaded or shared.</p>
    </div>
  );
}
