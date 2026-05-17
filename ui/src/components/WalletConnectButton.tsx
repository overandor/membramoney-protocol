import React from "react";
import { WalletMultiButton } from "@solana/wallet-adapter-react-ui";

const WalletConnectButton: React.FC = () => (
  <WalletMultiButton className="btn btn-primary wallet-multi-btn" />
);

export default WalletConnectButton;
