export type ProtocolNoteStatus =
  | 'created'
  | 'funded'
  | 'viewed'
  | 'claimed'
  | 'expired'
  | 'revoked'

export type ProtocolNote = {
  noteId: string
  serial: string
  amountUsd: number
  asset: 'USDC' | 'BTC' | 'SOL'
  status: ProtocolNoteStatus
  createdAt: string
  expiresAt: string
}

export function createProtocolNote(amountUsd: number, asset: ProtocolNote['asset']): ProtocolNote {
  const now = new Date()

  return {
    noteId: crypto.randomUUID(),
    serial: `MBR-${Math.floor(100000 + Math.random() * 900000)}`,
    amountUsd,
    asset,
    status: 'funded',
    createdAt: now.toISOString(),
    expiresAt: new Date(now.getTime() + 30 * 60 * 1000).toISOString()
  }
}
