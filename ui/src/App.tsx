import React, { useState } from "react";
import { WalletProvider, useWallet } from "./lib/wallet";
import DevnetBanner from "./components/DevnetBanner";
import ErrorBoundary from "./components/ErrorBoundary";
import RiskDisclosure from "./components/RiskDisclosure";
import Landing from "./pages/Landing";
import Dashboard from "./pages/Dashboard";
import ApiDocs from "./pages/ApiDocs";

type Page = "landing" | "app" | "docs";

// ── Navbar ─────────────────────────────────────────────────────────────────

interface NavbarProps {
  page: Page;
  onNav: (p: Page) => void;
}

const Navbar: React.FC<NavbarProps> = ({ page, onNav }) => {
  const navItems: { id: Page; label: string }[] = [
    { id: "landing", label: "Landing" },
    { id: "app", label: "App" },
    { id: "docs", label: "API Docs" },
  ];

  return (
    <nav
      style={{
        position: "sticky",
        top: 0,
        zIndex: 100,
        background: "rgba(23, 25, 35, 0.92)",
        backdropFilter: "blur(12px)",
        borderBottom: "1px solid var(--border)",
        display: "flex",
        alignItems: "center",
        padding: "0 24px",
        height: 56,
        gap: 4,
      }}
    >
      {/* Logo */}
      <button
        onClick={() => onNav("landing")}
        style={{
          border: "none",
          cursor: "pointer",
          padding: "0 16px 0 0",
          marginRight: 8,
          fontWeight: 900,
          fontSize: 16,
          letterSpacing: "0.04em",
          background: "linear-gradient(135deg, var(--accent), var(--accent2))",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
          backgroundClip: "text",
        } as React.CSSProperties}
      >
        MEMBRA
      </button>

      {/* Nav links */}
      {navItems.map((item) => (
        <button
          key={item.id}
          onClick={() => onNav(item.id)}
          style={{
            border: "none",
            padding: "6px 14px",
            fontSize: 13,
            fontWeight: page === item.id ? 700 : 500,
            color: page === item.id ? "var(--text)" : "var(--muted)",
            cursor: "pointer",
            borderRadius: "var(--radius-sm)",
            background: page === item.id ? "var(--surface2)" : "transparent",
            transition: "all 0.15s",
          } as React.CSSProperties}
        >
          {item.label}
        </button>
      ))}

      {/* Spacer */}
      <div style={{ flex: 1 }} />

      {/* Devnet badge */}
      <div
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 6,
          background: "rgba(252,129,129,0.1)",
          border: "1px solid rgba(252,129,129,0.3)",
          borderRadius: 20,
          padding: "4px 12px",
          fontSize: 11,
          fontWeight: 700,
          color: "var(--red)",
          letterSpacing: "0.06em",
          textTransform: "uppercase",
        }}
      >
        <span
          style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: "var(--red)",
            display: "inline-block",
          }}
        />
        devnet
      </div>
    </nav>
  );
};

// ── App content (inside WalletProvider) ────────────────────────────────────

const AppContent: React.FC = () => {
  const { walletAddress } = useWallet();
  const [page, setPage] = useState<Page>("landing");
  const [riskAccepted, setRiskAccepted] = useState(false);

  return (
    <ErrorBoundary>
      <div style={{ minHeight: "100vh", background: "var(--bg)", color: "var(--text)" }}>
        <DevnetBanner />
        <Navbar page={page} onNav={setPage} />

        {page === "landing" && (
          <Landing onLaunchApp={() => setPage("app")} onViewDocs={() => setPage("docs")} />
        )}

        {page === "app" && (
          <>
            {!riskAccepted ? (
              <div style={{ maxWidth: 680, margin: "0 auto", padding: "48px 24px" }}>
                <div
                  style={{
                    background: "var(--surface)",
                    border: "1px solid var(--border)",
                    borderRadius: "var(--radius)",
                    padding: "32px",
                  }}
                >
                  <RiskDisclosure
                    accepted={riskAccepted}
                    walletAddress={walletAddress}
                    onAccept={setRiskAccepted}
                  />
                </div>
              </div>
            ) : (
              <Dashboard />
            )}
          </>
        )}

        {page === "docs" && <ApiDocs />}

        <footer
          style={{
            textAlign: "center",
            padding: "24px",
            borderTop: "1px solid var(--border)",
            color: "var(--muted2)",
            fontSize: 12,
          }}
        >
          <p style={{ marginBottom: 4, fontWeight: 700, color: "var(--red)", letterSpacing: "0.06em", textTransform: "uppercase" }}>
            EXPERIMENTAL DEVNET ONLY — NOT REAL MONEY
          </p>
          <p>
            <a href="/SECURITY.md" style={{ color: "var(--muted)", textDecoration: "none" }}>Security Policy</a>
            {" · "}
            <a href="/MAINNET_READINESS.md" style={{ color: "var(--muted)", textDecoration: "none" }}>Mainnet Readiness</a>
          </p>
        </footer>
      </div>
    </ErrorBoundary>
  );
};

// ── Root ───────────────────────────────────────────────────────────────────

const App: React.FC = () => (
  <WalletProvider>
    <AppContent />
  </WalletProvider>
);

export default App;
