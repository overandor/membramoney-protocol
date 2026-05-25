import React, { useState } from "react";
import { useWallet } from "../lib/wallet";
import WalletPanel from "../components/WalletPanel";
import MintNoteCard from "../components/MintNoteCard";
import ClaimNoteCard from "../components/ClaimNoteCard";
import TransferCard from "../components/TransferCard";
import SplitCard from "../components/SplitCard";
import ReserveStatusCard from "../components/ReserveStatusCard";
import StatsCard from "../components/StatsCard";
import FeeSavingsCard from "../components/FeeSavingsCard";
import AuditLogViewer from "../components/AuditLogViewer";
import MetricsDashboard from "../components/MetricsDashboard";
import TreasuryCard from "../components/TreasuryCard";
import PendingBatchesCard from "../components/PendingBatchesCard";
import ComplianceCard from "../components/ComplianceCard";
import SecurityCheckCard from "../components/SecurityCheckCard";

type Tab = "protocol" | "audit" | "treasury" | "compliance";

const tabs: { id: Tab; label: string }[] = [
  { id: "protocol", label: "Protocol" },
  { id: "audit", label: "Audit Log" },
  { id: "treasury", label: "Treasury" },
  { id: "compliance", label: "Compliance" },
];

const Dashboard: React.FC = () => {
  const { walletAddress } = useWallet();
  const [tab, setTab] = useState<Tab>("protocol");
  const [refreshKey, setRefreshKey] = useState(0);

  const handleRefresh = () => setRefreshKey((k) => k + 1);

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: "0 24px 80px" }}>
      {/* Tab bar */}
      <div
        style={{
          display: "flex",
          gap: 4,
          borderBottom: "1px solid var(--border)",
          marginBottom: 32,
          marginTop: 8,
          paddingBottom: 0,
        }}
      >
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              background: "transparent",
              border: "none",
              borderBottom: tab === t.id ? "2px solid var(--accent)" : "2px solid transparent",
              padding: "12px 18px",
              fontSize: 14,
              fontWeight: tab === t.id ? 700 : 500,
              color: tab === t.id ? "var(--accent)" : "var(--muted)",
              cursor: "pointer",
              marginBottom: -1,
              transition: "color 0.15s",
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Protocol tab */}
      {tab === "protocol" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          {/* Row 1: Wallet */}
          <div
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius)",
              padding: "24px",
            }}
          >
            <WalletPanel />
          </div>

          {/* Row 2: Mint + Claim */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
            <MintNoteCard walletAddress={walletAddress} riskAccepted={true} onMint={handleRefresh} />
            <ClaimNoteCard walletAddress={walletAddress} riskAccepted={true} />
          </div>

          {/* Row 3: Transfer */}
          <TransferCard />

          {/* Row 4: Split */}
          <SplitCard />

          {/* Row 5: Reserve Status + Stats */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
            <ReserveStatusCard key={refreshKey} />
            <StatsCard />
          </div>

          {/* Row 6: Fee Savings */}
          <FeeSavingsCard amountSats={100_000} />
        </div>
      )}

      {/* Audit Log tab */}
      {tab === "audit" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <AuditLogViewer />
          <MetricsDashboard />
        </div>
      )}

      {/* Treasury tab */}
      {tab === "treasury" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <TreasuryCard />
          <PendingBatchesCard />
        </div>
      )}

      {/* Compliance tab */}
      {tab === "compliance" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
          <ComplianceCard />
          <SecurityCheckCard />
        </div>
      )}
    </div>
  );
};

export default Dashboard;
