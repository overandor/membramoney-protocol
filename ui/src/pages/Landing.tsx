import React from "react";

interface Props {
  onLaunchApp: () => void;
  onViewDocs: () => void;
}

const features = [
  {
    icon: "₿",
    title: "No Bridge Required",
    desc: "BTC-denominated value moves on Solana without wrapping or custodial bridges. Notes carry denomination in satoshis.",
  },
  {
    icon: "🔗",
    title: "No Wallet to Receive",
    desc: "Recipients claim via PIN from a URL link. No wallet setup needed — just a browser and the claim code.",
  },
  {
    icon: "⚡",
    title: "Gasless Transfers",
    desc: "The protocol sponsors the ~$0.00025 Solana fee for users. Send BTC-denominated value with zero user-side gas.",
  },
  {
    icon: "✂",
    title: "Atomic Split & Merge",
    desc: "One note splits into exact change atomically. Two notes merge in a single transaction. No partial state.",
  },
  {
    icon: "⏱",
    title: "Programmable Expiry",
    desc: "Notes carry expiry, redemption policy, and compliance state. Expired notes auto-return to issuer treasury.",
  },
  {
    icon: "🔍",
    title: "Full Audit Trail",
    desc: "Every state transition — mint, transfer, split, merge, redeem — is verifiable on-chain with a full event log.",
  },
];

const comparisonRows = [
  { label: "Fee (low congestion)", btc: "~1,000 sats", lightning: "~1 sat", membra: "0 sats" },
  { label: "Fee (high congestion)", btc: "~50,000 sats", lightning: "~10 sats", membra: "0 sats" },
  { label: "Settlement time", btc: "10–60 min", lightning: "1–5 sec", membra: "~400ms" },
  { label: "Receiver needs wallet", btc: "Yes", lightning: "Yes", membra: "No" },
  { label: "Programmable expiry", btc: "No", lightning: "No", membra: "Yes" },
  { label: "TPS capacity", btc: "~7", lightning: "~1,000", membra: "65,000+" },
];

const card: React.CSSProperties = {
  background: "var(--surface)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius)",
  padding: "24px",
};

const Landing: React.FC<Props> = ({ onLaunchApp, onViewDocs }) => {
  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: "0 24px 80px" }}>
      {/* Hero */}
      <section
        style={{
          textAlign: "center",
          padding: "100px 0 72px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 24,
        }}
      >
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            background: "rgba(124,106,247,0.12)",
            border: "1px solid rgba(124,106,247,0.3)",
            borderRadius: 20,
            padding: "6px 16px",
            fontSize: 12,
            fontWeight: 700,
            color: "var(--accent)",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
          }}
        >
          <span
            style={{
              width: 7,
              height: 7,
              borderRadius: "50%",
              background: "var(--green)",
              boxShadow: "0 0 6px var(--green)",
              display: "inline-block",
            }}
          />
          Devnet Live
        </div>

        <h1
          style={{
            fontSize: "clamp(2.4rem, 6vw, 4rem)",
            fontWeight: 900,
            lineHeight: 1.1,
            letterSpacing: "-0.03em",
            background: "linear-gradient(135deg, var(--accent), var(--accent2))",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
            margin: 0,
          }}
        >
          BTC value at Solana speed
        </h1>

        <p
          style={{
            fontSize: "clamp(1rem, 2.5vw, 1.2rem)",
            color: "var(--muted)",
            maxWidth: 640,
            lineHeight: 1.7,
            margin: 0,
          }}
        >
          Membra is an experimental devnet protocol for Bitcoin-denominated bearer
          notes — transferred in 400ms, at near-zero cost, no bridge required.
        </p>

        <div style={{ display: "flex", gap: 16, flexWrap: "wrap", justifyContent: "center" }}>
          <button
            onClick={onLaunchApp}
            style={{
              background: "linear-gradient(135deg, var(--accent), var(--accent2))",
              border: "none",
              borderRadius: "var(--radius-sm)",
              padding: "14px 32px",
              color: "#0b0c15",
              fontWeight: 700,
              fontSize: 15,
              cursor: "pointer",
              letterSpacing: "0.01em",
            }}
          >
            Launch App →
          </button>
          <button
            onClick={onViewDocs}
            style={{
              background: "transparent",
              border: "1px solid var(--border2)",
              borderRadius: "var(--radius-sm)",
              padding: "14px 32px",
              color: "var(--text)",
              fontWeight: 600,
              fontSize: 15,
              cursor: "pointer",
            }}
          >
            View API Docs
          </button>
        </div>
      </section>

      {/* Stats bar */}
      <section
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 1,
          background: "var(--border)",
          borderRadius: "var(--radius)",
          overflow: "hidden",
          marginBottom: 64,
        }}
      >
        {[
          { value: "~400ms", label: "Settlement" },
          { value: "~$0.00025", label: "Per Transfer" },
          { value: "65,000+", label: "TPS Capacity" },
        ].map((stat) => (
          <div
            key={stat.label}
            style={{
              background: "var(--surface)",
              padding: "32px 24px",
              textAlign: "center",
            }}
          >
            <div
              style={{
                fontSize: "clamp(1.8rem, 4vw, 2.6rem)",
                fontWeight: 900,
                letterSpacing: "-0.02em",
                background: "linear-gradient(135deg, var(--accent), var(--accent2))",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
                lineHeight: 1.1,
                marginBottom: 8,
              }}
            >
              {stat.value}
            </div>
            <div
              style={{
                fontSize: 12,
                color: "var(--muted)",
                textTransform: "uppercase",
                letterSpacing: "0.1em",
                fontWeight: 600,
              }}
            >
              {stat.label}
            </div>
          </div>
        ))}
      </section>

      {/* Feature grid */}
      <section style={{ marginBottom: 72 }}>
        <h2
          style={{
            textAlign: "center",
            fontSize: 11,
            color: "var(--muted)",
            textTransform: "uppercase",
            letterSpacing: "0.1em",
            fontWeight: 600,
            marginBottom: 32,
          }}
        >
          Protocol Features
        </h2>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
            gap: 16,
          }}
        >
          {features.map((f) => (
            <div key={f.title} style={{ ...card }}>
              <div style={{ fontSize: 28, marginBottom: 14 }}>{f.icon}</div>
              <h3
                style={{
                  fontSize: 15,
                  fontWeight: 700,
                  color: "var(--text)",
                  marginBottom: 8,
                }}
              >
                {f.title}
              </h3>
              <p style={{ fontSize: 13.5, color: "var(--muted)", lineHeight: 1.65, margin: 0 }}>
                {f.desc}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Comparison table */}
      <section style={{ marginBottom: 72 }}>
        <h2
          style={{
            textAlign: "center",
            fontSize: 11,
            color: "var(--muted)",
            textTransform: "uppercase",
            letterSpacing: "0.1em",
            fontWeight: 600,
            marginBottom: 32,
          }}
        >
          How Membra Compares
        </h2>
        <div
          style={{
            ...card,
            padding: 0,
            overflow: "hidden",
          }}
        >
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              fontSize: 14,
            }}
          >
            <thead>
              <tr style={{ background: "var(--surface2)" }}>
                <th
                  style={{
                    padding: "16px 20px",
                    textAlign: "left",
                    fontSize: 11,
                    color: "var(--muted)",
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    fontWeight: 600,
                    borderBottom: "1px solid var(--border)",
                  }}
                >
                  Feature
                </th>
                {["BTC On-Chain", "Lightning", "Membra"].map((col) => (
                  <th
                    key={col}
                    style={{
                      padding: "16px 20px",
                      textAlign: "center",
                      fontSize: 11,
                      color: col === "Membra" ? "var(--accent)" : "var(--muted)",
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                      fontWeight: 700,
                      borderBottom: "1px solid var(--border)",
                    }}
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {comparisonRows.map((row, i) => (
                <tr
                  key={row.label}
                  style={{
                    background: i % 2 === 0 ? "var(--surface)" : "var(--surface2)",
                  }}
                >
                  <td
                    style={{
                      padding: "14px 20px",
                      color: "var(--muted)",
                      fontSize: 13,
                      fontWeight: 500,
                    }}
                  >
                    {row.label}
                  </td>
                  <td
                    style={{
                      padding: "14px 20px",
                      textAlign: "center",
                      color: "var(--text)",
                      fontSize: 13,
                      fontFamily: "monospace",
                    }}
                  >
                    {row.btc}
                  </td>
                  <td
                    style={{
                      padding: "14px 20px",
                      textAlign: "center",
                      color: "var(--text)",
                      fontSize: 13,
                      fontFamily: "monospace",
                    }}
                  >
                    {row.lightning}
                  </td>
                  <td
                    style={{
                      padding: "14px 20px",
                      textAlign: "center",
                      color: "var(--accent2)",
                      fontSize: 13,
                      fontFamily: "monospace",
                      fontWeight: 700,
                    }}
                  >
                    {row.membra}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* CTA */}
      <section
        style={{
          textAlign: "center",
          padding: "48px 32px",
          background: "linear-gradient(135deg, rgba(124,106,247,0.08), rgba(79,209,197,0.08))",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius-lg)",
          marginBottom: 48,
        }}
      >
        <h2
          style={{
            fontSize: "clamp(1.4rem, 3vw, 2rem)",
            fontWeight: 800,
            color: "var(--text)",
            marginBottom: 12,
          }}
        >
          Ready to explore the protocol?
        </h2>
        <p style={{ color: "var(--muted)", marginBottom: 28, fontSize: 15 }}>
          Connect a Solana devnet wallet and mint your first bearer note in seconds.
        </p>
        <button
          onClick={onLaunchApp}
          style={{
            background: "linear-gradient(135deg, var(--accent), var(--accent2))",
            border: "none",
            borderRadius: "var(--radius-sm)",
            padding: "14px 36px",
            color: "#0b0c15",
            fontWeight: 700,
            fontSize: 15,
            cursor: "pointer",
          }}
        >
          Launch App →
        </button>
      </section>

      {/* Devnet disclaimer */}
      <div
        style={{
          textAlign: "center",
          padding: "16px",
          background: "rgba(252,129,129,0.06)",
          border: "1px solid rgba(252,129,129,0.2)",
          borderRadius: "var(--radius-sm)",
          color: "var(--red)",
          fontSize: 12,
          fontWeight: 700,
          letterSpacing: "0.06em",
          textTransform: "uppercase",
        }}
      >
        EXPERIMENTAL DEVNET ONLY — NOT REAL MONEY
      </div>
    </div>
  );
};

export default Landing;
