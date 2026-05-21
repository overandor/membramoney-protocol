export type GovernanceProposal = {
  proposalId: string
  title: string
  approvals: number
  rejections: number
  status: 'pending' | 'approved' | 'rejected'
  finalizedAt?: string
}

export function createGovernanceProposal(title: string): GovernanceProposal {
  return {
    proposalId: crypto.randomUUID(),
    title,
    approvals: 0,
    rejections: 0,
    status: 'pending'
  }
}

export function finalizeGovernanceProposal(
  proposal: GovernanceProposal,
  threshold = 3
) {
  proposal.status = proposal.approvals >= threshold
    ? 'approved'
    : 'rejected'

  proposal.finalizedAt = new Date().toISOString()

  return proposal
}
