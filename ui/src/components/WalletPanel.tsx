import React from "react";
import { useWallet } from "../lib/wallet";
import WalletConnectButton from "./WalletConnectButton";

const WalletPanel: React.FC = () => {
  const { walletAddress, isConnected, network } = useWallet();

  return (
    <div className="animate-in">
      <h2 className="card-title">Wallet</h2>
      {isConnected && walletAddress ? (
        <div className="wallet-info">
          <div>
            <span className="wallet-label">Address</span>
            <div className="wallet-address">{walletAddress}</div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span className={`wallet-badge ${network === "mainnet-beta" ? "mainnet" : "devnet"}`}>
              {network}
            </span>
            <WalletConnectButton />
          </div>
        </div>
      ) : (
        <div className="wallet-info">
          <p style={{ color: "var(--text-muted)", marginBottom: 12 }}>
            Connect Phantom or Solflare to get started.
          </p>
          <WalletConnectButton />
        </div>
      )}
    </div>
  );
};

export default WalletPanel;
