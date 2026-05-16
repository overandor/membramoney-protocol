import React from "react";
import { useWallet } from "../lib/wallet";

const NetworkBadge: React.FC = () => {
  const { network } = useWallet();

  return (
    <div className={`network-badge network-${network}`}>
      <span className="network-indicator" />
      <span className="network-name">{network.toUpperCase()}</span>
    </div>
  );
};

export default NetworkBadge;
