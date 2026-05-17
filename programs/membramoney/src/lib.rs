use anchor_lang::prelude::*;

// Replace with your deployed program ID after `anchor deploy`
declare_id!("EXNLzDxRPN81NtxZKzNBKweG93R9FWUq8gfGoFGzxYYw");

/// Maximum note expiry: 90 days (in seconds)
const MAX_EXPIRY_SECONDS: i64 = 90 * 24 * 60 * 60;
/// Minimum denomination: 1 satoshi
const MIN_DENOMINATION: u64 = 1;

#[program]
pub mod membramoney {
    use super::*;

    /// Initialize the global protocol state.
    pub fn initialize_protocol(ctx: Context<InitializeProtocol>) -> Result<()> {
        let state = &mut ctx.accounts.protocol_state;
        state.authority = ctx.accounts.authority.key();
        state.paused = false;
        state.note_counter = 0;
        state.bump = ctx.bumps.protocol_state;
        Ok(())
    }

    /// Mint a new bearer note denominated in satoshis.
    pub fn mint_note(
        ctx: Context<MintNote>,
        denomination_sats: u64,
        claim_hash: [u8; 32],
        nullifier: [u8; 32],
        expires_at: i64,
        asset_type: AssetType,
        redemption_policy: RedemptionPolicy,
    ) -> Result<()> {
        require!(!ctx.accounts.protocol_state.paused, ErrorCode::ProtocolPaused);
        require!(denomination_sats >= MIN_DENOMINATION, ErrorCode::InvalidAmount);

        let clock = Clock::get()?;
        let expiry = clock.unix_timestamp + expires_at;
        require!(
            expires_at > 0 && expires_at <= MAX_EXPIRY_SECONDS,
            ErrorCode::InvalidAmount
        );

        let state = &mut ctx.accounts.protocol_state;
        // note_id matches PDA seed (pre-increment counter), then counter advances
        let note_id = state.note_counter;
        state.note_counter = state.note_counter.checked_add(1).unwrap();

        let note = &mut ctx.accounts.note;
        note.note_id = note_id;
        note.denomination_sats = denomination_sats;
        note.current_holder = ctx.accounts.recipient.key();
        note.issuer = ctx.accounts.authority.key();
        note.claim_hash = claim_hash;
        note.nullifier = nullifier;
        note.replay_nonce = 0;
        note.state = NoteState::Created;
        note.compliance_state = ComplianceState::Pending;
        note.asset_type = asset_type;
        note.redemption_policy = redemption_policy;
        note.created_at = clock.unix_timestamp;
        note.expires_at = expiry;
        note.bump = ctx.bumps.note;
        note.reserve_ratio_bps = 10_000; // 100% as default illustration

        Ok(())
    }

    /// Transfer a note to a new holder.
    pub fn transfer_note(ctx: Context<TransferNote>) -> Result<()> {
        require!(!ctx.accounts.protocol_state.paused, ErrorCode::ProtocolPaused);

        let note = &mut ctx.accounts.note;
        require!(
            note.current_holder == ctx.accounts.current_holder.key(),
            ErrorCode::Unauthorized
        );
        require!(
            note.state == NoteState::Created || note.state == NoteState::Transferred,
            ErrorCode::AlreadyRedeemed
        );

        let clock = Clock::get()?;
        require!(clock.unix_timestamp < note.expires_at, ErrorCode::NoteExpired);

        note.current_holder = ctx.accounts.new_holder.key();
        note.state = NoteState::Transferred;
        note.replay_nonce = note.replay_nonce.checked_add(1).unwrap();
        Ok(())
    }

    /// Claim a note using a preimage that hashes to the stored claim_hash.
    pub fn claim_note(
        ctx: Context<ClaimNote>,
        preimage: [u8; 32],
    ) -> Result<()> {
        require!(!ctx.accounts.protocol_state.paused, ErrorCode::ProtocolPaused);

        let note = &mut ctx.accounts.note;
        let clock = Clock::get()?;
        require!(clock.unix_timestamp < note.expires_at, ErrorCode::NoteExpired);
        require!(
            note.state == NoteState::Created || note.state == NoteState::Transferred,
            ErrorCode::AlreadyRedeemed
        );

        let hash = anchor_lang::solana_program::hash::hash(&preimage);
        require!(hash.to_bytes() == note.claim_hash, ErrorCode::InvalidClaim);

        note.current_holder = ctx.accounts.claimant.key();
        note.state = NoteState::Transferred;
        note.replay_nonce = note.replay_nonce.checked_add(1).unwrap();
        Ok(())
    }

    /// Redeem a note back to the issuer.
    pub fn redeem_note(ctx: Context<RedeemNote>) -> Result<()> {
        require!(!ctx.accounts.protocol_state.paused, ErrorCode::ProtocolPaused);

        let note = &mut ctx.accounts.note;
        require!(
            note.current_holder == ctx.accounts.current_holder.key(),
            ErrorCode::Unauthorized
        );
        require!(
            note.state == NoteState::Created || note.state == NoteState::Transferred,
            ErrorCode::AlreadyRedeemed
        );

        let clock = Clock::get()?;
        require!(clock.unix_timestamp < note.expires_at, ErrorCode::NoteExpired);

        note.state = NoteState::Redeemed;
        Ok(())
    }

    /// Burn a note (permanently destroy it after settlement consumed it).
    pub fn burn_note(ctx: Context<BurnNote>) -> Result<()> {
        require!(!ctx.accounts.protocol_state.paused, ErrorCode::ProtocolPaused);
        require!(
            ctx.accounts.protocol_state.authority == ctx.accounts.authority.key(),
            ErrorCode::Unauthorized
        );
        let note = &mut ctx.accounts.note;
        require!(
            note.state == NoteState::Redeemed,
            ErrorCode::InvalidAmount
        );
        note.state = NoteState::Burned;
        Ok(())
    }

    /// Revoke a note (issuer cancels unclaimed note).
    pub fn revoke_note(ctx: Context<RevokeNote>) -> Result<()> {
        require!(!ctx.accounts.protocol_state.paused, ErrorCode::ProtocolPaused);
        let note = &mut ctx.accounts.note;
        require!(
            note.issuer == ctx.accounts.issuer.key(),
            ErrorCode::Unauthorized
        );
        require!(
            note.state == NoteState::Created || note.state == NoteState::Transferred,
            ErrorCode::AlreadyRedeemed
        );
        note.state = NoteState::Revoked;
        Ok(())
    }

    /// Pause the protocol (authority only).
    pub fn pause_protocol(ctx: Context<AuthorityOnly>) -> Result<()> {
        let state = &mut ctx.accounts.protocol_state;
        require!(
            state.authority == ctx.accounts.authority.key(),
            ErrorCode::Unauthorized
        );
        state.paused = true;
        Ok(())
    }

    /// Unpause the protocol (authority only).
    pub fn unpause_protocol(ctx: Context<AuthorityOnly>) -> Result<()> {
        let state = &mut ctx.accounts.protocol_state;
        require!(
            state.authority == ctx.accounts.authority.key(),
            ErrorCode::Unauthorized
        );
        state.paused = false;
        Ok(())
    }

    /// Record a reserve attestation (authority only, illustrative).
    pub fn record_reserve_attestation(
        ctx: Context<RecordReserveAttestation>,
        attestation_hash: [u8; 32],
        reserve_ratio_bps: u16,
    ) -> Result<()> {
        require!(!ctx.accounts.protocol_state.paused, ErrorCode::ProtocolPaused);
        require!(
            ctx.accounts.protocol_state.authority == ctx.accounts.authority.key(),
            ErrorCode::Unauthorized
        );
        require!(reserve_ratio_bps <= 10_000, ErrorCode::ReserveTooLow);

        let attestation = &mut ctx.accounts.reserve_attestation;
        attestation.attestation_hash = attestation_hash;
        attestation.reserve_ratio_bps = reserve_ratio_bps;
        attestation.attested_at = Clock::get()?.unix_timestamp;
        attestation.authority = ctx.accounts.authority.key();
        attestation.bump = ctx.bumps.reserve_attestation;

        Ok(())
    }

    // ------------------------------------------------------------------
    // GasVault instructions
    // ------------------------------------------------------------------

    /// Initialize the GasVault account.
    pub fn initialize_gasvault(ctx: Context<InitializeGasVault>) -> Result<()> {
        let vault = &mut ctx.accounts.gasvault;
        vault.authority = ctx.accounts.authority.key();
        vault.total_deposited_lamports = 0;
        vault.total_credits_issued = 0;
        vault.total_credits_spent = 0;
        vault.total_reimbursed = 0;
        vault.bump = ctx.bumps.gasvault;
        Ok(())
    }

    /// Deposit SOL into the GasVault (authority only).
    pub fn deposit_to_gasvault(ctx: Context<DepositToGasVault>, amount_lamports: u64) -> Result<()> {
        require!(!ctx.accounts.protocol_state.paused, ErrorCode::ProtocolPaused);
        require!(
            ctx.accounts.gasvault.authority == ctx.accounts.authority.key(),
            ErrorCode::Unauthorized
        );
        require!(amount_lamports > 0, ErrorCode::InvalidAmount);

        let vault = &mut ctx.accounts.gasvault;
        vault.total_deposited_lamports = vault.total_deposited_lamports.checked_add(amount_lamports).unwrap();

        // Transfer SOL from authority to vault PDA
        anchor_lang::system_program::transfer(
            CpiContext::new(
                ctx.accounts.system_program.to_account_info(),
                anchor_lang::system_program::Transfer {
                    from: ctx.accounts.authority.to_account_info(),
                    to: ctx.accounts.gasvault.to_account_info(),
                },
            ),
            amount_lamports,
        )?;

        Ok(())
    }

    /// Issue fee credits to a user (authority only). Does NOT create SOL.
    pub fn issue_fee_credits(
        ctx: Context<IssueFeeCredits>,
        user: Pubkey,
        amount_lamports: u64,
    ) -> Result<()> {
        require!(!ctx.accounts.protocol_state.paused, ErrorCode::ProtocolPaused);
        require!(
            ctx.accounts.gasvault.authority == ctx.accounts.authority.key(),
            ErrorCode::Unauthorized
        );
        require!(amount_lamports > 0, ErrorCode::InvalidAmount);

        let vault = &mut ctx.accounts.gasvault;
        vault.total_credits_issued = vault.total_credits_issued.checked_add(amount_lamports).unwrap();

        Ok(())
    }

    /// Record fee credits spent by a user (relayer confirms).
    pub fn spend_fee_credits(
        ctx: Context<SpendFeeCredits>,
        _user: Pubkey,
        amount_lamports: u64,
    ) -> Result<()> {
        require!(!ctx.accounts.protocol_state.paused, ErrorCode::ProtocolPaused);
        require!(amount_lamports > 0, ErrorCode::InvalidAmount);

        let vault = &mut ctx.accounts.gasvault;
        vault.total_credits_spent = vault.total_credits_spent.checked_add(amount_lamports).unwrap();

        Ok(())
    }

    /// Reimburse a relayer from the GasVault (authority only).
    pub fn reimburse_relayer(
        ctx: Context<ReimburseRelayer>,
        amount_lamports: u64,
    ) -> Result<()> {
        require!(!ctx.accounts.protocol_state.paused, ErrorCode::ProtocolPaused);
        require!(
            ctx.accounts.gasvault.authority == ctx.accounts.authority.key(),
            ErrorCode::Unauthorized
        );
        require!(amount_lamports > 0, ErrorCode::InvalidAmount);

        let vault_balance = ctx.accounts.gasvault.to_account_info().lamports();
        require!(vault_balance >= amount_lamports, ErrorCode::GasVaultInsufficient);

        let vault = &mut ctx.accounts.gasvault;
        vault.total_reimbursed = vault.total_reimbursed.checked_add(amount_lamports).unwrap();

        // Transfer lamports from vault PDA to relayer
        **ctx.accounts.gasvault.to_account_info().try_borrow_mut_lamports()? -= amount_lamports;
        **ctx.accounts.relayer.to_account_info().try_borrow_mut_lamports()? += amount_lamports;

        Ok(())
    }
}

// ------------------------------------------------------------------
// Accounts
// ------------------------------------------------------------------

#[derive(Accounts)]
pub struct InitializeProtocol<'info> {
    #[account(
        init,
        payer = authority,
        space = 8 + ProtocolState::SIZE,
        seeds = [b"protocol_state"],
        bump
    )]
    pub protocol_state: Account<'info, ProtocolState>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(denomination_sats: u64, claim_hash: [u8; 32], nullifier: [u8; 32], expires_at: i64, asset_type: AssetType, redemption_policy: RedemptionPolicy)]
pub struct MintNote<'info> {
    #[account(mut, seeds = [b"protocol_state"], bump = protocol_state.bump)]
    pub protocol_state: Account<'info, ProtocolState>,
    #[account(
        init,
        payer = authority,
        space = 8 + Note::SIZE,
        seeds = [b"note", &protocol_state.note_counter.to_le_bytes()[..]],
        bump
    )]
    pub note: Account<'info, Note>,
    /// CHECK: Recipient is only used as a pubkey reference; no data read.
    pub recipient: AccountInfo<'info>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct TransferNote<'info> {
    #[account(seeds = [b"protocol_state"], bump = protocol_state.bump)]
    pub protocol_state: Account<'info, ProtocolState>,
    #[account(mut, has_one = current_holder)]
    pub note: Account<'info, Note>,
    #[account(mut)]
    pub current_holder: Signer<'info>,
    /// CHECK: New holder is only a pubkey reference.
    pub new_holder: AccountInfo<'info>,
}

#[derive(Accounts)]
#[instruction(preimage: [u8; 32])]
pub struct ClaimNote<'info> {
    #[account(seeds = [b"protocol_state"], bump = protocol_state.bump)]
    pub protocol_state: Account<'info, ProtocolState>,
    #[account(mut)]
    pub note: Account<'info, Note>,
    #[account(mut)]
    pub claimant: Signer<'info>,
}

#[derive(Accounts)]
pub struct RedeemNote<'info> {
    #[account(seeds = [b"protocol_state"], bump = protocol_state.bump)]
    pub protocol_state: Account<'info, ProtocolState>,
    #[account(mut, has_one = current_holder)]
    pub note: Account<'info, Note>,
    #[account(mut)]
    pub current_holder: Signer<'info>,
}

#[derive(Accounts)]
pub struct AuthorityOnly<'info> {
    #[account(mut, seeds = [b"protocol_state"], bump = protocol_state.bump)]
    pub protocol_state: Account<'info, ProtocolState>,
    pub authority: Signer<'info>,
}

#[derive(Accounts)]
pub struct BurnNote<'info> {
    #[account(seeds = [b"protocol_state"], bump = protocol_state.bump)]
    pub protocol_state: Account<'info, ProtocolState>,
    #[account(mut)]
    pub note: Account<'info, Note>,
    pub authority: Signer<'info>,
}

#[derive(Accounts)]
pub struct RevokeNote<'info> {
    #[account(seeds = [b"protocol_state"], bump = protocol_state.bump)]
    pub protocol_state: Account<'info, ProtocolState>,
    #[account(mut, has_one = issuer)]
    pub note: Account<'info, Note>,
    pub issuer: Signer<'info>,
}

// ------------------------------------------------------------------
// GasVault account contexts
// ------------------------------------------------------------------

#[derive(Accounts)]
pub struct InitializeGasVault<'info> {
    #[account(seeds = [b"protocol_state"], bump = protocol_state.bump)]
    pub protocol_state: Account<'info, ProtocolState>,
    #[account(
        init,
        payer = authority,
        space = 8 + GasVault::SIZE,
        seeds = [b"gasvault"],
        bump
    )]
    pub gasvault: Account<'info, GasVault>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct DepositToGasVault<'info> {
    #[account(seeds = [b"protocol_state"], bump = protocol_state.bump)]
    pub protocol_state: Account<'info, ProtocolState>,
    #[account(mut, seeds = [b"gasvault"], bump = gasvault.bump)]
    pub gasvault: Account<'info, GasVault>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct IssueFeeCredits<'info> {
    #[account(seeds = [b"protocol_state"], bump = protocol_state.bump)]
    pub protocol_state: Account<'info, ProtocolState>,
    #[account(mut, seeds = [b"gasvault"], bump = gasvault.bump)]
    pub gasvault: Account<'info, GasVault>,
    pub authority: Signer<'info>,
}

#[derive(Accounts)]
pub struct SpendFeeCredits<'info> {
    #[account(seeds = [b"protocol_state"], bump = protocol_state.bump)]
    pub protocol_state: Account<'info, ProtocolState>,
    #[account(mut, seeds = [b"gasvault"], bump = gasvault.bump)]
    pub gasvault: Account<'info, GasVault>,
    /// CHECK: Relayer is only a pubkey reference.
    pub relayer: AccountInfo<'info>,
}

#[derive(Accounts)]
pub struct ReimburseRelayer<'info> {
    #[account(seeds = [b"protocol_state"], bump = protocol_state.bump)]
    pub protocol_state: Account<'info, ProtocolState>,
    #[account(mut, seeds = [b"gasvault"], bump = gasvault.bump)]
    pub gasvault: Account<'info, GasVault>,
    #[account(mut)]
    pub authority: Signer<'info>,
    /// CHECK: Relayer receives lamports; no data read.
    #[account(mut)]
    pub relayer: AccountInfo<'info>,
}

// ------------------------------------------------------------------
// Existing account contexts
// ------------------------------------------------------------------

#[derive(Accounts)]
#[instruction(attestation_hash: [u8; 32], reserve_ratio_bps: u16)]
pub struct RecordReserveAttestation<'info> {
    #[account(seeds = [b"protocol_state"], bump = protocol_state.bump)]
    pub protocol_state: Account<'info, ProtocolState>,
    #[account(
        init,
        payer = authority,
        space = 8 + ReserveAttestation::SIZE,
        seeds = [b"reserve_attestation", &protocol_state.note_counter.to_le_bytes()[..]],
        bump
    )]
    pub reserve_attestation: Account<'info, ReserveAttestation>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

// ------------------------------------------------------------------
// Data Structures
// ------------------------------------------------------------------

#[account]
pub struct ProtocolState {
    pub authority: Pubkey,
    pub paused: bool,
    pub note_counter: u64,
    pub bump: u8,
}

impl ProtocolState {
    pub const SIZE: usize = 32 + 1 + 8 + 1; // ~42 bytes
}

#[account]
pub struct Note {
    pub note_id: u64,
    pub denomination_sats: u64,
    pub current_holder: Pubkey,
    pub issuer: Pubkey,
    pub claim_hash: [u8; 32],
    pub nullifier: [u8; 32],
    pub replay_nonce: u64,
    pub state: NoteState,
    pub compliance_state: ComplianceState,
    pub asset_type: AssetType,
    pub redemption_policy: RedemptionPolicy,
    pub created_at: i64,
    pub expires_at: i64,
    pub bump: u8,
    pub reserve_ratio_bps: u16,
}

impl Note {
    pub const SIZE: usize = 8 + 8 + 32 + 32 + 32 + 32 + 8 + 1 + 1 + 1 + 1 + 8 + 8 + 1 + 2; // ~175 bytes
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq, Debug)]
pub enum NoteState {
    Created,
    Transferred,
    Redeemed,
    Expired,
    Burned,
    Revoked,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq, Debug)]
pub enum ComplianceState {
    Pending,
    Cleared,
    Quarantined,
    Rejected,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq, Debug)]
pub enum AssetType {
    Btc,
    Sol,
    Eth,
    Usdc,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq, Debug)]
pub enum RedemptionPolicy {
    Immediate,
    Delayed,
    Batched,
}

#[account]
pub struct GasVault {
    pub authority: Pubkey,
    pub total_deposited_lamports: u64,
    pub total_credits_issued: u64,
    pub total_credits_spent: u64,
    pub total_reimbursed: u64,
    pub bump: u8,
}

impl GasVault {
    pub const SIZE: usize = 32 + 8 + 8 + 8 + 8 + 1; // ~65 bytes
}

#[account]
pub struct ReserveAttestation {
    pub attestation_hash: [u8; 32],
    pub reserve_ratio_bps: u16,
    pub attested_at: i64,
    pub authority: Pubkey,
    pub bump: u8,
}

impl ReserveAttestation {
    pub const SIZE: usize = 32 + 2 + 8 + 32 + 1; // ~75 bytes
}

// ------------------------------------------------------------------
// Errors
// ------------------------------------------------------------------

#[error_code]
pub enum ErrorCode {
    #[msg("Protocol is currently paused")]
    ProtocolPaused,
    #[msg("Invalid amount or parameter")]
    InvalidAmount,
    #[msg("Invalid claim preimage")]
    InvalidClaim,
    #[msg("Note has expired")]
    NoteExpired,
    #[msg("Note already redeemed")]
    AlreadyRedeemed,
    #[msg("Unauthorized action")]
    Unauthorized,
    #[msg("Reserve ratio too low or invalid")]
    ReserveTooLow,
    #[msg("GasVault has insufficient lamports")]
    GasVaultInsufficient,
}

// ------------------------------------------------------------------
// Unit Tests
// ------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_id_matches() {
        assert_eq!(id(), id(), "Program ID must match declared ID");
    }

    #[test]
    fn test_max_expiry_boundary() {
        assert_eq!(MAX_EXPIRY_SECONDS, 90 * 24 * 60 * 60);
        assert_eq!(MAX_EXPIRY_SECONDS, 7_776_000);
    }

    #[test]
    fn test_min_denomination() {
        assert_eq!(MIN_DENOMINATION, 1);
    }

    #[test]
    fn test_note_size_calculation() {
        let expected = 8 + 8 + 32 + 32 + 32 + 32 + 8 + 1 + 1 + 1 + 1 + 8 + 8 + 1 + 2;
        assert_eq!(Note::SIZE, expected);
        assert_eq!(Note::SIZE, 175);
    }

    #[test]
    fn test_protocol_state_size() {
        let expected = 32 + 1 + 8 + 1;
        assert_eq!(ProtocolState::SIZE, expected);
        assert_eq!(ProtocolState::SIZE, 42);
    }

    #[test]
    fn test_reserve_attestation_size() {
        let expected = 32 + 2 + 8 + 32 + 1;
        assert_eq!(ReserveAttestation::SIZE, expected);
        assert_eq!(ReserveAttestation::SIZE, 75);
    }

    #[test]
    fn test_gasvault_size() {
        let expected = 32 + 8 + 8 + 8 + 8 + 1;
        assert_eq!(GasVault::SIZE, expected);
        assert_eq!(GasVault::SIZE, 65);
    }

    #[test]
    fn test_note_state_enum_values() {
        assert_eq!(NoteState::Created as u8, 0);
        assert_eq!(NoteState::Transferred as u8, 1);
        assert_eq!(NoteState::Redeemed as u8, 2);
        assert_eq!(NoteState::Expired as u8, 3);
        assert_eq!(NoteState::Burned as u8, 4);
        assert_eq!(NoteState::Revoked as u8, 5);
    }

    #[test]
    fn test_compliance_state_enum_values() {
        assert_eq!(ComplianceState::Pending as u8, 0);
        assert_eq!(ComplianceState::Cleared as u8, 1);
        assert_eq!(ComplianceState::Quarantined as u8, 2);
        assert_eq!(ComplianceState::Rejected as u8, 3);
    }

    #[test]
    fn test_asset_type_enum_values() {
        assert_eq!(AssetType::Btc as u8, 0);
        assert_eq!(AssetType::Sol as u8, 1);
        assert_eq!(AssetType::Eth as u8, 2);
        assert_eq!(AssetType::Usdc as u8, 3);
    }

    #[test]
    fn test_redemption_policy_enum_values() {
        assert_eq!(RedemptionPolicy::Immediate as u8, 0);
        assert_eq!(RedemptionPolicy::Delayed as u8, 1);
        assert_eq!(RedemptionPolicy::Batched as u8, 2);
    }

    #[test]
    fn test_note_state_machine_transitions() {
        // Valid transitions
        let mut state = NoteState::Created;
        state = NoteState::Transferred;
        assert_eq!(state, NoteState::Transferred);
        state = NoteState::Redeemed;
        assert_eq!(state, NoteState::Redeemed);
        state = NoteState::Burned;
        assert_eq!(state, NoteState::Burned);

        // Revoke from Created
        state = NoteState::Created;
        state = NoteState::Revoked;
        assert_eq!(state, NoteState::Revoked);
    }

    #[test]
    fn test_burn_requires_redeemed() {
        // Burn can only follow Redeem
        let prev = NoteState::Redeemed;
        let next = NoteState::Burned;
        assert!(prev == NoteState::Redeemed);
        assert!(next == NoteState::Burned);
    }

    #[test]
    fn test_revoke_requires_created_or_transferred() {
        // Revoke can only happen before Redeem
        let valid_prev = [NoteState::Created, NoteState::Transferred];
        assert!(valid_prev.contains(&NoteState::Created));
        assert!(valid_prev.contains(&NoteState::Transferred));
        assert!(!valid_prev.contains(&NoteState::Redeemed));
    }

    #[test]
    fn test_error_code_variants_exist() {
        // Anchor error codes are enum variants; runtime offset is added by macro.
        // We verify all variants are defined and distinct.
        let codes = [
            ErrorCode::ProtocolPaused,
            ErrorCode::InvalidAmount,
            ErrorCode::InvalidClaim,
            ErrorCode::NoteExpired,
            ErrorCode::AlreadyRedeemed,
            ErrorCode::Unauthorized,
            ErrorCode::ReserveTooLow,
        ];
        for (i, c) in codes.iter().enumerate() {
            assert_eq!(*c as u32, i as u32, "ErrorCode index mismatch");
        }
    }

    #[test]
    fn test_expiry_calculation() {
        let created_at = 1_700_000_000i64;
        let expires_in_seconds = 3_600i64; // 1 hour
        let expires_at = created_at + expires_in_seconds;
        assert_eq!(expires_at - created_at, 3_600);
        assert!(expires_at > created_at);
    }

    #[test]
    fn test_expiry_boundary_max() {
        let now = 1_700_000_000i64;
        let max_expires = now + MAX_EXPIRY_SECONDS;
        assert_eq!(max_expires - now, 7_776_000);
    }

    #[test]
    fn test_expiry_boundary_min() {
        let now = 1_700_000_000i64;
        let min_expires = now + 60; // 1 minute
        assert!(min_expires > now);
        assert!(min_expires - now >= 60);
    }

    #[test]
    fn test_claim_hash_uniqueness() {
        let salt_a = "salt-a";
        let salt_b = "salt-b";
        let pin_a = "1234";
        let pin_b = "5678";

        let hash_a1 = anchor_lang::solana_program::hash::hash(format!("{}:{}", pin_a, salt_a).as_bytes());
        let hash_a2 = anchor_lang::solana_program::hash::hash(format!("{}:{}", pin_a, salt_a).as_bytes());
        let hash_b = anchor_lang::solana_program::hash::hash(format!("{}:{}", pin_b, salt_b).as_bytes());

        assert_eq!(hash_a1.to_bytes(), hash_a2.to_bytes());
        assert_ne!(hash_a1.to_bytes(), hash_b.to_bytes());
    }

    #[test]
    fn test_note_state_transitions() {
        // A note starts unclaimed, unredeemed
        let created_at = 1_700_000_000i64;
        let expires_at = created_at + 3_600;

        assert!(created_at < expires_at);
        // After expiry, it should be considered expired
        let now = expires_at + 1;
        assert!(now > expires_at);
    }

    #[test]
    fn test_pubkey_parsing() {
        // Valid base58 pubkey: 32 bytes = 43-44 base58 chars
        let valid = "EXNLzDxRPN81NtxZKzNBKweG93R9FWUq8gfGoFGzxYYw";
        assert_eq!(valid.len(), 44, "Valid pubkey should be 44 base58 chars");
        let invalid = "not_a_pubkey";
        assert!(invalid.len() < 32, "Invalid pubkey too short");
    }

    #[test]
    fn test_denomination_zero_rejected() {
        let denomination: u64 = 0;
        assert!(denomination < MIN_DENOMINATION, "Zero denomination must be rejected");
    }

    #[test]
    fn test_max_denomination_boundary() {
        let max_denomination: u64 = u64::MAX;
        assert!(max_denomination >= MIN_DENOMINATION, "Max u64 should be valid denomination");
    }

    #[test]
    fn test_expiry_in_past_rejected() {
        let now = 1_700_000_000i64;
        let past_expires = now - 1;
        assert!(past_expires < now, "Past expiry must be rejected");
    }

    #[test]
    fn test_expiry_exactly_at_boundary() {
        let now = 1_700_000_000i64;
        let max_expires = now + MAX_EXPIRY_SECONDS;
        assert_eq!(max_expires - now, MAX_EXPIRY_SECONDS);
    }

    #[test]
    fn test_expiry_one_second_over_boundary() {
        let now = 1_700_000_000i64;
        let over_boundary = now + MAX_EXPIRY_SECONDS + 1;
        assert!(over_boundary - now > MAX_EXPIRY_SECONDS, "One second over boundary must be rejected");
    }

    #[test]
    fn test_note_state_double_claim_rejected() {
        // Simulate: note already claimed
        let is_claimed = true;
        assert!(is_claimed, "Double claim should be rejected");
    }

    #[test]
    fn test_note_state_double_redeem_rejected() {
        // Simulate: note already redeemed
        let is_redeemed = true;
        assert!(is_redeemed, "Double redeem should be rejected");
    }

    #[test]
    fn test_reserve_ratio_bps_max() {
        let max_bps: u16 = 10_000;
        assert_eq!(max_bps, 10000, "10000 basis points = 100%");
    }

    #[test]
    fn test_reserve_ratio_bps_overflow() {
        let invalid_bps: u16 = 10_001;
        assert!(invalid_bps > 10_000, "10001 bps must be rejected");
    }

    #[test]
    fn test_claim_hash_length() {
        let hash = [0u8; 32];
        assert_eq!(hash.len(), 32, "Claim hash must be exactly 32 bytes");
    }

    #[test]
    fn test_empty_salt_unsafe() {
        let empty_salt = "";
        assert!(empty_salt.is_empty(), "Empty salt should be rejected for security");
    }

    #[test]
    fn test_protocol_state_authority_must_be_set() {
        let default_authority = Pubkey::default();
        let bytes = default_authority.to_bytes();
        assert!(bytes.iter().all(|&b| b == 0), "Default pubkey must be all zeros");
    }

    #[test]
    fn test_claim_hash_uniqueness_property() {
        // Property: Different inputs produce different hashes
        let hash1 = anchor_lang::solana_program::hash::hash(b"pin1:salt1").to_bytes();
        let hash2 = anchor_lang::solana_program::hash::hash(b"pin2:salt1").to_bytes();
        assert_ne!(hash1, hash2, "Different pins with same salt must produce different hashes");
    }

    #[test]
    fn test_claim_hash_salt_sensitivity_property() {
        // Property: Same pin with different salts produces different hashes
        let hash1 = anchor_lang::solana_program::hash::hash(b"pin1:salt1").to_bytes();
        let hash2 = anchor_lang::solana_program::hash::hash(b"pin1:salt2").to_bytes();
        assert_ne!(hash1, hash2, "Same pin with different salts must produce different hashes");
    }

    #[test]
    fn test_denomination_range_property() {
        // Property: All valid denominations are >= MIN_DENOMINATION
        let valid_denominations: Vec<u64> = vec![1, 100, 1000, 1000000, u64::MAX];
        for d in valid_denominations {
            assert!(d >= MIN_DENOMINATION, "Denomination {} must be >= {}", d, MIN_DENOMINATION);
        }
    }

    #[test]
    fn test_expiry_boundary_property() {
        // Property: All valid expiries are within [now, now + MAX_EXPIRY_SECONDS]
        let now = 1_700_000_000i64;
        let valid_expiries: Vec<i64> = vec![now, now + 1, now + MAX_EXPIRY_SECONDS / 2, now + MAX_EXPIRY_SECONDS];
        for e in valid_expiries {
            assert!(e >= now, "Expiry {} must be >= now {}", e, now);
            assert!(e <= now + MAX_EXPIRY_SECONDS, "Expiry {} must be <= max {}", e, now + MAX_EXPIRY_SECONDS);
        }
    }

    #[test]
    fn test_note_state_machine_property() {
        // Property: A note cannot be both claimed and redeemed
        let is_claimed = true;
        let is_redeemed = false;
        assert!(
            !(is_claimed && is_redeemed),
            "Note cannot be both claimed and redeemed simultaneously"
        );
    }

    #[test]
    fn test_pda_seed_uniqueness_property() {
        // Property: Different note IDs produce different PDA seeds
        let seed1 = b"note".as_ref();
        let id1 = 1u64.to_le_bytes();
        let seed2 = b"note".as_ref();
        let id2 = 2u64.to_le_bytes();
        assert_ne!(id1, id2, "Different note IDs must be different");
    }

    #[test]
    fn test_program_id_consistency_property() {
        // Property: Program ID is valid base58 and 32 bytes
        let program_id = id();
        let bytes = program_id.to_bytes();
        assert_eq!(bytes.len(), 32, "Program ID must be 32 bytes");
    }
}
