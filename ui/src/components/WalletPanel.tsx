import React from "react";
import { connectWallet, disconnectWallet } from "../lib/solana";

interface Props {
  walletAddress: string | null;
  onConnect: (addr: string) => void;
  onDisconnect: () => void;
}

const WalletPanel: React.FC<Props> = ({ walletAddress, onConnect, onDisconnect }) => {
  const handleConnect = async () => {
    try {
      const conn = await connectWallet();
      if (conn.connected && conn.address) {
        onConnect(conn.address);
      }
    } catch (e) {
      console.error("Wallet connect error:", e);
    }
  };

  const handleDisconnect = () => {
    disconnectWallet();
    onDisconnect();
  };

  return (
    <div className="animate-in">
      <h2 className="card-title">Wallet</h2>
      {walletAddress ? (
        <div className="wallet-info">
          <div>
            <span className="wallet-label">Address</span>
            <div className="wallet-address">{walletAddress}</div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span className="wallet-badge devnet">devnet</span>
            <button className="btn-secondary" onClick={handleDisconnect}>
              Disconnect
            </button>
          </div>
        </div>
      ) : (
        <div className="wallet-info">
          <p style={{ color: "var(--text-muted)", marginBottom: 4 }}>
            No wallet connected.
          </p>
          <button onClick={handleConnect}>Connect Wallet</button>
          <p style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>
            Devnet placeholder — paste a test address or leave blank.
          </p>
        </div>
      )}
    </div>
  );
};

export default WalletPanel;
