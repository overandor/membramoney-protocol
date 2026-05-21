export type ReserveState = {
  reserveId: string
  asset: 'USD' | 'USDC' | 'BTC' | 'SOL'
  totalLocked: number
  totalIssued: number
  updatedAt: string
}

export function createReserveState(
  asset: ReserveState['asset'],
  totalLocked: number,
  totalIssued: number
): ReserveState {
  return {
    reserveId: crypto.randomUUID(),
    asset,
    totalLocked,
    totalIssued,
    updatedAt: new Date().toISOString()
  }
}
