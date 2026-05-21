export type TreasuryAccount = {
  treasuryId: string
  jurisdiction: string
  operatingReserveUsd: number
  issuedLiabilitiesUsd: number
  reserveRatio: number
  updatedAt: string
}

export function createTreasuryAccount(
  jurisdiction: string,
  operatingReserveUsd: number,
  issuedLiabilitiesUsd: number
): TreasuryAccount {
  const reserveRatio = issuedLiabilitiesUsd === 0
    ? 0
    : Number((operatingReserveUsd / issuedLiabilitiesUsd).toFixed(4))

  return {
    treasuryId: crypto.randomUUID(),
    jurisdiction,
    operatingReserveUsd,
    issuedLiabilitiesUsd,
    reserveRatio,
    updatedAt: new Date().toISOString()
  }
}

export function isTreasuryHealthy(account: TreasuryAccount, minimumRatio = 1.0) {
  return account.reserveRatio >= minimumRatio
}
