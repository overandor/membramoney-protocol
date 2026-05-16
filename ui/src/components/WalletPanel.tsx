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
    <div>
      <h2 className="card-title">Wallet</h2>
      {walletAddress ? (
        <div>
          <p style={{ wordBreak: "break-all", color: "var(--text)" }}>
            <strong>Address:</strong> {walletAddress}
          </p>
          <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
            Network: devnet
          </p>
          <button onClick={handleDisconnect} style={{ marginTop: 8 }}>
            Disconnect
          </button>
        </div>
      ) : (
        <div>
          <p style={{ color: "var(--text-muted)" }}>No wallet connected.</p>
          <button onClick={handleConnect} style={{ marginTop: 8 }}>
            Connect Wallet
          </button>
          <p style={{ color: "var(--text-muted)", fontSize: "0.75rem", marginTop: 6 }}>
            Devnet placeholder: paste a test address or leave blank.
          </p>
        </div>
      )}
    </div>
  );
};

export default WalletPanel;
