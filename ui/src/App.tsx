import React, { useState } from "react";
import { WalletProvider } from "./lib/wallet";
import DevnetBanner from "./components/DevnetBanner";
import ErrorBoundary from "./components/ErrorBoundary";
import WalletPanel from "./components/WalletPanel";
import MintNoteCard from "./components/MintNoteCard";
import ClaimNoteCard from "./components/ClaimNoteCard";
import ReserveStatusCard from "./components/ReserveStatusCard";
import RiskDisclosure from "./components/RiskDisclosure";
import FeeSavingsCard from "./components/FeeSavingsCard";

const App: React.FC = () => {
  const [walletAddress, setWalletAddress] = useState<string | null>(null);
  const [riskAccepted, setRiskAccepted] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleRefresh = () => setRefreshKey((k: number) => k + 1);

  return (
    <WalletProvider>
      <ErrorBoundary>
        <div className="app">
        <DevnetBanner />
        <header className="app-header">
          <h1>Membra Money Protocol</h1>
          <p className="subtitle">
            BTC-denominated bearer notes · Solana speed · Near-zero fees
          </p>
        </header>
        <main className="app-main">
          <section className="panel">
            <WalletPanel
              walletAddress={walletAddress}
              onConnect={setWalletAddress}
              onDisconnect={() => setWalletAddress(null)}
            />
          </section>
          <section className="panel">
            <RiskDisclosure
              accepted={riskAccepted}
              walletAddress={walletAddress}
              onAccept={setRiskAccepted}
            />
          </section>
          <section className="grid">
            <MintNoteCard
              walletAddress={walletAddress}
              riskAccepted={riskAccepted}
              onMint={handleRefresh}
            />
            <ClaimNoteCard walletAddress={walletAddress} riskAccepted={riskAccepted} />
          </section>
          <section className="panel">
            <ReserveStatusCard key={refreshKey} />
          </section>
          <section className="panel">
            <FeeSavingsCard amountSats={100_000} />
          </section>
        </main>
        <footer className="app-footer">
          <p>EXPERIMENTAL DEVNET ONLY — NOT REAL MONEY</p>
          <p>
            <a href="/SECURITY.md">Security Policy</a> ·{" "}
            <a href="/MAINNET_READINESS.md">Mainnet Readiness</a>
          </p>
        </footer>
      </div>
      </ErrorBoundary>
    </WalletProvider>
  );
};

export default App;
