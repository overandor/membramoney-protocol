import React from "react";
import { useWallet } from "../lib/wallet";

const WalletConnectButton: React.FC = () => {
  const { walletAddress, isConnected, isPhantomInstalled, connect, disconnect } = useWallet();

  if (isConnected && walletAddress) {
    return (
      <div className="wallet-connected">
        <span className="wallet-address">
          {walletAddress.slice(0, 4)}...{walletAddress.slice(-4)}
        </span>
        <button onClick={disconnect} className="btn btn-secondary">
          Disconnect
        </button>
      </div>
    );
  }

  return (
    <button onClick={connect} className="btn btn-primary">
      {isPhantomInstalled ? "Connect Phantom" : "Connect Wallet (Devnet)"}
    </button>
  );
};

export default WalletConnectButton;
