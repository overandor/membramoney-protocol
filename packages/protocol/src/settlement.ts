export type SettlementRecord = {
  settlementId: string
  source: string
  destination: string
  amountUsd: number
  asset: 'USDC' | 'BTC' | 'SOL'
  settledAt: string
}

export function createSettlementRecord(
  source: string,
  destination: string,
  amountUsd: number,
  asset: SettlementRecord['asset']
): SettlementRecord {
  return {
    settlementId: crypto.randomUUID(),
    source,
    destination,
    amountUsd,
    asset,
    settledAt: new Date().toISOString()
  }
}
