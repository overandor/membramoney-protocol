import { useState, useRef, useEffect } from "react";

const SUGGESTED = [
  "Is this file verified?","What is its collateral value?",
  "What changed since version 1?","Is the blockchain anchor valid?",
  "What is the estimated lendable value?","Is this file eligible as collateral?",
  "What lifecycle stage is this file at?","Who holds the lien on this file?"
];

interface Msg { role:"user"|"assistant"; text:string; sources?:string[]; confidence?:number; }

export default function LLMChat({ sku }: { sku: string }) {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior:"smooth" }); }, [msgs]);

  const send = async (q: string) => {
    if (!q.trim() || loading) return;
    const question = q.trim();
    setInput("");
    setMsgs(prev => [...prev, { role:"user", text:question }]);
    setLoading(true);
    const r = await window.filelife.askQuestion(sku, question);
    const data = r?.data || r;
    setMsgs(prev => [...prev, { role:"assistant", text:data?.answer||"No response.", sources:data?.sources||[], confidence:data?.confidence }]);
    setLoading(false);
  };

  return (
    <div className="chat-wrap">
      <div className="suggested-qs">
        {SUGGESTED.map(q => <button key={q} className="suggested-q" onClick={() => send(q)}>{q}</button>)}
      </div>
      <div className="chat-messages">
        {msgs.length === 0 && <div style={{color:"var(--muted)",fontSize:11,textAlign:"center",marginTop:20}}>Ask anything about this file's metadata, history, or collateral status. Raw contents are never exposed.</div>}
        {msgs.map((m, i) => (
          <div key={i} className={m.role === "user" ? "msg-user" : "msg-assistant"}>
            {m.text}
            {m.role==="assistant" && m.sources && m.sources.length > 0 && (
              <div className="msg-sources">
                {m.sources.map(s => <span key={s} className="msg-source-tag">{s}</span>)}
              </div>
            )}
            {m.role==="assistant" && m.confidence!=null && (
              <div className="msg-confidence">Confidence: {Math.round(m.confidence*100)}%</div>
            )}
          </div>
        ))}
        {loading && <div className="msg-assistant" style={{color:"var(--muted)"}}>Thinking…</div>}
        <div ref={bottomRef} />
      </div>
      <div className="chat-input-row">
        <textarea className="chat-input" rows={2} value={input} onChange={e => setInput(e.target.value)}
          placeholder="Ask about this file's lifecycle, hashes, GitHub history, Solana anchor, collateral status…"
          onKeyDown={e => { if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();send(input);} }} />
        <button className="btn btn-primary" onClick={() => send(input)} disabled={loading||!input.trim()}>Send</button>
      </div>
    </div>
  );
}
