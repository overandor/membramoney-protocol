#!/usr/bin/env bash
set -euo pipefail

echo "========================================"
echo "Membra Money Protocol — Toolchain Install"
echo "========================================"

OS=$(uname -s)
ARCH=$(uname -m)

# 1. Solana CLI
echo "[1/3] Solana CLI..."
if command -v solana &>/dev/null; then
    echo "  Solana already installed: $(solana --version)"
else
    if [ "$OS" = "Darwin" ] && [ "$ARCH" = "arm64" ]; then
        echo "  Installing Solana CLI for macOS ARM64..."
        sh -c "$(curl -sSfL https://release.solana.com/v1.18.8/solana-install-init-x86_64-apple-darwin)" || \
        echo "  Fallback: download manually from https://github.com/solana-labs/solana/releases"
    else
        echo "  Installing Solana CLI..."
        sh -c "$(curl -sSfL https://release.solana.com/v1.18.8/install)"
    fi
fi

if ! command -v solana &>/dev/null; then
    echo "  ERROR: Solana CLI installation failed."
    echo "  Check https://docs.solanalabs.com/cli/install for manual steps."
    exit 1
fi

solana config set --url devnet
solana config get

# 2. Anchor CLI
echo "[2/3] Anchor CLI..."
if command -v anchor &>/dev/null; then
    echo "  Anchor already installed: $(anchor --version)"
else
    echo "  Installing Anchor CLI..."
    cargo install --git https://github.com/coral-xyz/anchor --tag v0.29.0 anchor-cli 2>/dev/null || {
        echo "  cargo install anchor-cli failed. Trying avm fallback..."
        cargo install --git https://github.com/coral-xyz/anchor avm 2>/dev/null || true
        if command -v avm &>/dev/null; then
            avm install latest
            avm use latest
        fi
    }
fi

if ! command -v anchor &>/dev/null; then
    echo "  ERROR: Anchor CLI installation failed."
    echo "  Check https://www.anchor-lang.com/docs/installation for manual steps."
    exit 1
fi

# 3. Rust (needed for Anchor build)
echo "[3/3] Rust..."
if command -v rustc &>/dev/null; then
    echo "  Rust already installed: $(rustc --version)"
else
    echo "  Installing Rust via rustup..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
fi

echo "========================================"
echo "Next commands:"
echo "  solana-keygen new --no-passphrase --outfile ~/.config/solana/id.json"
echo "  solana airdrop 2"
echo "  anchor build"
echo "  anchor test"
echo "========================================"
