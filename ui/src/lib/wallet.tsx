/**
 * Solana Wallet Provider — production integration via @solana/wallet-adapter-react.
 * Supports Phantom, Solflare. Falls back gracefully when extensions are absent.
 *
 * Network is driven by VITE_SOLANA_NETWORK (devnet | mainnet-beta).
 * RPC is driven by VITE_SOLANA_RPC_URL (optional custom endpoint).
 */

import React, { createContext, useContext, useMemo } from "react";
import {
  ConnectionProvider,
  WalletProvider as AdapterWalletProvider,
  useWallet as useAdapterWallet,
} from "@solana/wallet-adapter-react";
import { WalletModalProvider } from "@solana/wallet-adapter-react-ui";
import { PhantomWalletAdapter } from "@solana/wallet-adapter-phantom";
import { SolflareWalletAdapter } from "@solana/wallet-adapter-solflare";
import "@solana/wallet-adapter-react-ui/styles.css";

const NETWORK: string =
  (import.meta as any).env?.VITE_SOLANA_NETWORK || "devnet";

const RPC_URL: string =
  (import.meta as any).env?.VITE_SOLANA_RPC_URL ||
  (NETWORK === "mainnet-beta"
    ? "https://api.mainnet-beta.solana.com"
    : "https://api.devnet.solana.com");

// ---------------------------------------------------------------------------
// Public context shape — identical to previous API so all components compile.
// ---------------------------------------------------------------------------

export interface WalletContextType {
  walletAddress: string | null;
  isConnected: boolean;
  isPhantomInstalled: boolean;
  connect: () => Promise<void>;
  disconnect: () => void;
  network: string;
}

const WalletCompatContext = createContext<WalletContextType>({
  walletAddress: null,
  isConnected: false,
  isPhantomInstalled: false,
  connect: async () => {},
  disconnect: () => {},
  network: NETWORK,
});

export const useWallet = (): WalletContextType =>
  useContext(WalletCompatContext);

// ---------------------------------------------------------------------------
// Bridge: reads from the real adapter and exposes the compat interface.
// ---------------------------------------------------------------------------

const WalletCompatBridge: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const {
    publicKey,
    connected,
    connect,
    disconnect,
  } = useAdapterWallet();

  const isPhantomInstalled =
    typeof window !== "undefined" && !!(window as any).phantom?.solana?.isPhantom;

  return (
    <WalletCompatContext.Provider
      value={{
        walletAddress: publicKey?.toString() ?? null,
        isConnected: connected && !!publicKey,
        isPhantomInstalled,
        connect,
        disconnect,
        network: NETWORK,
      }}
    >
      {children}
    </WalletCompatContext.Provider>
  );
};

// ---------------------------------------------------------------------------
// WalletProvider — wrap your app root with this.
// ---------------------------------------------------------------------------

export const WalletProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const adapters = useMemo(
    () => [new PhantomWalletAdapter(), new SolflareWalletAdapter()],
    []
  );

  return (
    <ConnectionProvider endpoint={RPC_URL}>
      <AdapterWalletProvider wallets={adapters} autoConnect>
        <WalletModalProvider>
          <WalletCompatBridge>{children}</WalletCompatBridge>
        </WalletModalProvider>
      </AdapterWalletProvider>
    </ConnectionProvider>
  );
};
