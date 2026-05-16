/**
 * Membra Money Protocol — Anchor Program Tests
 *
 * Prerequisites:
 *   - Solana CLI installed
 *   - Anchor CLI installed
 *   - Local validator running (anchor test handles this)
 *
 * If Anchor/Solana tooling is unavailable, these tests will not run.
 * Run with: anchor test
 */

import * as anchor from "@coral-xyz/anchor";
import { Program } from "@coral-xyz/anchor";
import { Membramoney } from "../target/types/membramoney";
import { expect } from "chai";

describe("membramoney", () => {
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);

  const program = anchor.workspace.Membramoney as Program<Membramoney>;
  const authority = provider.wallet;
  const recipient = anchor.web3.Keypair.generate();
  const newHolder = anchor.web3.Keypair.generate();
  const claimant = anchor.web3.Keypair.generate();

  let protocolState: anchor.web3.PublicKey;
  let note: anchor.web3.PublicKey;
  let reserveAttestation: anchor.web3.PublicKey;
  let noteCounter = 0;

  before(async () => {
    // Derive PDA addresses
    [protocolState] = anchor.web3.PublicKey.findProgramAddressSync(
      [Buffer.from("protocol_state")],
      program.programId
    );
  });

  // ------------------------------------------------------------------
  // 1. Initialize protocol
  // ------------------------------------------------------------------
  it("initializes the protocol", async () => {
    await program.methods
      .initializeProtocol()
      .accounts({
        protocolState,
        authority: authority.publicKey,
        systemProgram: anchor.web3.SystemProgram.programId,
      })
      .rpc();

    const state = await program.account.protocolState.fetch(protocolState);
    expect(state.authority.toBase58()).to.equal(authority.publicKey.toBase58());
    expect(state.paused).to.be.false;
    expect(state.noteCounter.toNumber()).to.equal(0);
  });

  // ------------------------------------------------------------------
  // 2. Mint note
  // ------------------------------------------------------------------
  it("mints a note", async () => {
    noteCounter += 1;
    const claimHash = Buffer.alloc(32, 1);
    const expirySeconds = 3600;

    [note] = anchor.web3.PublicKey.findProgramAddressSync(
      [Buffer.from("note"), Buffer.from(new anchor.BN(noteCounter).toArray("le", 8))],
      program.programId
    );

    await program.methods
      .mintNote(new anchor.BN(1000), claimHash, new anchor.BN(expirySeconds))
      .accounts({
        protocolState,
        note,
        recipient: recipient.publicKey,
        authority: authority.publicKey,
        systemProgram: anchor.web3.SystemProgram.programId,
      })
      .rpc();

    const noteAccount = await program.account.note.fetch(note);
    expect(noteAccount.denominationSats.toNumber()).to.equal(1000);
    expect(noteAccount.currentHolder.toBase58()).to.equal(recipient.publicKey.toBase58());
    expect(noteAccount.redeemed).to.be.false;
  });

  // ------------------------------------------------------------------
  // 3. Transfer note
  // ------------------------------------------------------------------
  it("transfers a note", async () => {
    // Airdrop to recipient so they can sign
    await provider.connection.confirmTransaction(
      await provider.connection.requestAirdrop(recipient.publicKey, 1_000_000_000),
      "confirmed"
    );

    await program.methods
      .transferNote()
      .accounts({
        protocolState,
        note,
        currentHolder: recipient.publicKey,
        newHolder: newHolder.publicKey,
      })
      .signers([recipient])
      .rpc();

    const noteAccount = await program.account.note.fetch(note);
    expect(noteAccount.currentHolder.toBase58()).to.equal(newHolder.publicKey.toBase58());
  });

  // ------------------------------------------------------------------
  // 4. Claim note
  // ------------------------------------------------------------------
  it("claims a note with correct preimage", async () => {
    const preimage = Buffer.alloc(32, 1);

    await program.methods
      .claimNote(preimage)
      .accounts({
        protocolState,
        note,
        claimant: claimant.publicKey,
      })
      .rpc();

    const noteAccount = await program.account.note.fetch(note);
    expect(noteAccount.currentHolder.toBase58()).to.equal(claimant.publicKey.toBase58());
  });

  // ------------------------------------------------------------------
  // 5. Redeem note
  // ------------------------------------------------------------------
  it("redeems a note", async () => {
    await program.methods
      .redeemNote()
      .accounts({
        protocolState,
        note,
        currentHolder: claimant.publicKey,
      })
      .rpc();

    const noteAccount = await program.account.note.fetch(note);
    expect(noteAccount.redeemed).to.be.true;
  });

  // ------------------------------------------------------------------
  // 6. Reject invalid claim
  // ------------------------------------------------------------------
  it("rejects an invalid claim preimage", async () => {
    noteCounter += 1;
    const claimHash = Buffer.alloc(32, 2);
    const expirySeconds = 3600;

    const [badNote] = anchor.web3.PublicKey.findProgramAddressSync(
      [Buffer.from("note"), Buffer.from(new anchor.BN(noteCounter).toArray("le", 8))],
      program.programId
    );

    await program.methods
      .mintNote(new anchor.BN(500), claimHash, new anchor.BN(expirySeconds))
      .accounts({
        protocolState,
        note: badNote,
        recipient: recipient.publicKey,
        authority: authority.publicKey,
        systemProgram: anchor.web3.SystemProgram.programId,
      })
      .rpc();

    const badPreimage = Buffer.alloc(32, 99);
    try {
      await program.methods
        .claimNote(badPreimage)
        .accounts({
          protocolState,
          note: badNote,
          claimant: claimant.publicKey,
        })
        .rpc();
      expect.fail("Expected InvalidClaim error");
    } catch (e) {
      expect(e.toString()).to.include("InvalidClaim");
    }
  });

  // ------------------------------------------------------------------
  // 7. Reject expired note
  // ------------------------------------------------------------------
  it("rejects an expired note", async () => {
    noteCounter += 1;
    const claimHash = Buffer.alloc(32, 3);
    const expirySeconds = 1; // 1 second expiry

    const [expiredNote] = anchor.web3.PublicKey.findProgramAddressSync(
      [Buffer.from("note"), Buffer.from(new anchor.BN(noteCounter).toArray("le", 8))],
      program.programId
    );

    await program.methods
      .mintNote(new anchor.BN(100), claimHash, new anchor.BN(expirySeconds))
      .accounts({
        protocolState,
        note: expiredNote,
        recipient: recipient.publicKey,
        authority: authority.publicKey,
        systemProgram: anchor.web3.SystemProgram.programId,
      })
      .rpc();

    // Wait for expiry
    await new Promise((r) => setTimeout(r, 2000));

    const preimage = Buffer.alloc(32, 3);
    try {
      await program.methods
        .claimNote(preimage)
        .accounts({
          protocolState,
          note: expiredNote,
          claimant: claimant.publicKey,
        })
        .rpc();
      expect.fail("Expected NoteExpired error");
    } catch (e) {
      expect(e.toString()).to.include("NoteExpired");
    }
  });

  // ------------------------------------------------------------------
  // 8. Pause / unpause protection
  // ------------------------------------------------------------------
  it("pauses and unpauses the protocol", async () => {
    await program.methods
      .pauseProtocol()
      .accounts({
        protocolState,
        authority: authority.publicKey,
      })
      .rpc();

    let state = await program.account.protocolState.fetch(protocolState);
    expect(state.paused).to.be.true;

    // Try to mint while paused
    noteCounter += 1;
    const [pausedNote] = anchor.web3.PublicKey.findProgramAddressSync(
      [Buffer.from("note"), Buffer.from(new anchor.BN(noteCounter).toArray("le", 8))],
      program.programId
    );

    try {
      await program.methods
        .mintNote(new anchor.BN(1), Buffer.alloc(32), new anchor.BN(3600))
        .accounts({
          protocolState,
          note: pausedNote,
          recipient: recipient.publicKey,
          authority: authority.publicKey,
          systemProgram: anchor.web3.SystemProgram.programId,
        })
        .rpc();
      expect.fail("Expected ProtocolPaused error");
    } catch (e) {
      expect(e.toString()).to.include("ProtocolPaused");
    }

    // Unpause
    await program.methods
      .unpauseProtocol()
      .accounts({
        protocolState,
        authority: authority.publicKey,
      })
      .rpc();

    state = await program.account.protocolState.fetch(protocolState);
    expect(state.paused).to.be.false;
  });

  // ------------------------------------------------------------------
  // 9. Record reserve attestation
  // ------------------------------------------------------------------
  it("records a reserve attestation", async () => {
    noteCounter += 1;
    const attestationHash = Buffer.alloc(32, 7);
    const reserveRatioBps = 10_000;

    [reserveAttestation] = anchor.web3.PublicKey.findProgramAddressSync(
      [
        Buffer.from("reserve_attestation"),
        Buffer.from(new anchor.BN(noteCounter).toArray("le", 8)),
      ],
      program.programId
    );

    await program.methods
      .recordReserveAttestation(attestationHash, reserveRatioBps)
      .accounts({
        protocolState,
        reserveAttestation,
        authority: authority.publicKey,
        systemProgram: anchor.web3.SystemProgram.programId,
      })
      .rpc();

    const att = await program.account.reserveAttestation.fetch(reserveAttestation);
    expect(att.reserveRatioBps).to.equal(10_000);
    expect(att.authority.toBase58()).to.equal(authority.publicKey.toBase58());
  });
});
