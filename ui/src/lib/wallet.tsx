import React, { createContext, useContext, useState, useCallback, useEffect } from "react";

interface WalletContextType {
  walletAddress: string | null;
  isConnected: boolean;
  isPhantomInstalled: boolean;
  connect: () => Promise<void>;
  disconnect: () => void;
  network: string;
}

const WalletContext = createContext<WalletContextType>({
  walletAddress: null,
  isConnected: false,
  isPhantomInstalled: false,
  connect: async () => {},
  disconnect: () => {},
  network: "devnet",
});

export const useWallet = () => useContext(WalletContext);

/**
 * Solana Wallet Provider — currently simulates connection for devnet.
 * In production, this would integrate with @solana/wallet-adapter-react.
 */
export const WalletProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [walletAddress, setWalletAddress] = useState<string | null>(null);
  const [isPhantomInstalled, setIsPhantomInstalled] = useState(false);
  const network = "devnet";

  useEffect(() => {
    // Check if Phantom wallet extension is installed
    const phantom = (window as any).solana;
    if (phantom?.isPhantom) {
      setIsPhantomInstalled(true);
      // Auto-connect if previously authorized
      if (phantom.isConnected && phantom.publicKey) {
        setWalletAddress(phantom.publicKey.toString());
      }
    }
  }, []);

  const connect = useCallback(async () => {
    try {
      const phantom = (window as any).solana;
      if (phantom?.isPhantom) {
        const response = await phantom.connect();
        setWalletAddress(response.publicKey.toString());
      } else {
        // Fallback: simulate connection for devnet testing
        const simulatedAddress = "CFvvtuX8JMia5MY4m3tkjJ6uG45Xwbm7swS7qgDXsStL";
        setWalletAddress(simulatedAddress);
        console.warn("Phantom wallet not detected. Using simulated devnet wallet.", simulatedAddress);
      }
    } catch (err) {
      console.error("Wallet connection failed:", err);
      throw err;
    }
  }, []);

  const disconnect = useCallback(() => {
    const phantom = (window as any).solana;
    if (phantom?.isPhantom && phantom.isConnected) {
      phantom.disconnect();
    }
    setWalletAddress(null);
  }, []);

  return (
    <WalletContext.Provider
      value={{
        walletAddress,
        isConnected: !!walletAddress,
        isPhantomInstalled,
        connect,
        disconnect,
        network,
      }}
    >
      {children}
    </WalletContext.Provider>
  );
};
