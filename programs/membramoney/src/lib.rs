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
        expires_at: i64,
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
        state.note_counter = state.note_counter.checked_add(1).unwrap();
        let note_id = state.note_counter;

        let note = &mut ctx.accounts.note;
        note.note_id = note_id;
        note.denomination_sats = denomination_sats;
        note.current_holder = ctx.accounts.recipient.key();
        note.issuer = ctx.accounts.authority.key();
        note.claim_hash = claim_hash;
        note.redeemed = false;
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
        require!(!note.redeemed, ErrorCode::AlreadyRedeemed);

        let clock = Clock::get()?;
        require!(clock.unix_timestamp < note.expires_at, ErrorCode::NoteExpired);

        note.current_holder = ctx.accounts.new_holder.key();
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
        require!(!note.redeemed, ErrorCode::AlreadyRedeemed);

        let hash = anchor_lang::solana_program::hash::hash(&preimage);
        require!(hash.to_bytes() == note.claim_hash, ErrorCode::InvalidClaim);

        note.current_holder = ctx.accounts.claimant.key();
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
        require!(!note.redeemed, ErrorCode::AlreadyRedeemed);

        let clock = Clock::get()?;
        require!(clock.unix_timestamp < note.expires_at, ErrorCode::NoteExpired);

        note.redeemed = true;
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
#[instruction(denomination_sats: u64, claim_hash: [u8; 32], expires_at: i64)]
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
    pub redeemed: bool,
    pub created_at: i64,
    pub expires_at: i64,
    pub bump: u8,
    pub reserve_ratio_bps: u16,
}

impl Note {
    pub const SIZE: usize = 8 + 8 + 32 + 32 + 32 + 1 + 8 + 8 + 1 + 2; // ~132 bytes
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
}
