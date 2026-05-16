/**
 * Solana wallet helpers
 *
 * This module provides a clean wallet placeholder.
 * TODO: Integrate @solana/wallet-adapter-react for real wallet connection.
 */

export const DEVNET_RPC = "https://api.devnet.solana.com";
export const DEVNET_CLUSTER = "devnet";

export interface WalletConnection {
  address: string;
  connected: boolean;
  network: string;
}

export function isValidSolanaAddress(address: string): boolean {
  return /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(address);
}

export async function connectWallet(): Promise<WalletConnection> {
  // TODO: Replace with real wallet adapter integration.
  // Example using @solana/wallet-adapter-react:
  // const { publicKey } = useWallet();
  // return { address: publicKey?.toBase58() || "", connected: !!publicKey, network: DEVNET_CLUSTER };

  // For devnet smoke-testing, simulate a connection after user confirmation.
  const simulated = window.prompt(
    "Paste a devnet wallet address (or leave blank for simulated):"
  );
  const address = simulated?.trim() || "SimulatedDevnetWallet111111111111111111111";
  return { address, connected: true, network: DEVNET_CLUSTER };
}

export function disconnectWallet(): WalletConnection {
  return { address: "", connected: false, network: DEVNET_CLUSTER };
}
