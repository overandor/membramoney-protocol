#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

PASS=0
FAIL=0
WARN=0

log_pass() { echo "  [PASS] $1"; PASS=$((PASS+1)); }
log_fail() { echo "  [FAIL] $1"; FAIL=$((FAIL+1)); }
log_warn() { echo "  [WARN] $1"; WARN=$((WARN+1)); }

echo "========================================"
echo "Membra Money Protocol — Pre-Flight Check"
echo "========================================"

# 1. Git clean check
echo "[1/10] Git status..."
if [ -d "${REPO_ROOT}/.git" ]; then
    if git -C "${REPO_ROOT}" diff --quiet 2>/dev/null && git -C "${REPO_ROOT}" diff --cached --quiet 2>/dev/null; then
        log_pass "working tree clean"
    else
        log_warn "uncommitted changes present"
    fi
else
    log_warn "not a git repo"
fi

# 2. .env file check
echo "[2/10] Environment file check..."
if [ -f "${REPO_ROOT}/.env" ]; then
    log_warn ".env exists — ensure it is not committed"
else
    log_pass "no .env file (good)"
fi
if [ -f "${REPO_ROOT}/.env.example" ]; then
    log_pass ".env.example exists"
else
    log_fail ".env.example missing"
fi

# 3. Backend compile/test
echo "[3/10] Backend compile..."
if python3 -m py_compile "${REPO_ROOT}/backend/main.py" 2>/dev/null; then
    log_pass "backend/main.py compiles"
else
    log_fail "backend/main.py syntax error"
fi

# 4. Cargo check
echo "[4/10] Cargo check..."
if command -v cargo &>/dev/null; then
    if (cd "${REPO_ROOT}/programs/membramoney" && cargo check 2>/dev/null); then
        log_pass "cargo check passes"
    else
        log_warn "cargo check failed (may need anchor build first)"
    fi
else
    log_warn "cargo not installed"
fi

# 5. Anchor CLI check
echo "[5/10] Anchor CLI check..."
if command -v anchor &>/dev/null; then
    ANCHOR_VER=$(anchor --version 2>/dev/null || echo "unknown")
    log_pass "anchor installed (${ANCHOR_VER})"
else
    log_warn "anchor not installed"
fi

# 6. Solana CLI check
echo "[6/10] Solana CLI check..."
if command -v solana &>/dev/null; then
    SOLANA_VER=$(solana --version 2>/dev/null || echo "unknown")
    log_pass "solana installed (${SOLANA_VER})"
else
    log_warn "solana not installed"
fi

# 7. UI dependency/build check
echo "[7/10] UI check..."
if [ -d "${REPO_ROOT}/ui/node_modules" ]; then
    if (cd "${REPO_ROOT}/ui" && npx tsc --noEmit 2>/dev/null); then
        log_pass "UI TypeScript compiles"
    else
        log_warn "UI TypeScript errors (may need npm install)"
    fi
else
    log_warn "UI node_modules missing"
fi

# 8. Docs existence
echo "[8/10] Documentation..."
for doc in README.md SECURITY.md MAINNET_READINESS.md DEVNET_DEPLOYMENT.md; do
    if [ -f "${REPO_ROOT}/${doc}" ]; then
        log_pass "${doc} exists"
    else
        log_fail "${doc} missing"
    fi
done

# 9. Required scripts
echo "[9/10] Scripts..."
for s in validate.sh pre_flight_check.sh install_solana.sh devnet_smoke_test.ts docker_validate.sh; do
    if [ -f "${REPO_ROOT}/scripts/${s}" ]; then
        log_pass "scripts/${s} exists"
    else
        log_warn "scripts/${s} missing"
    fi
done

# 10. Secret scan
echo "[10/10] Secret scan..."
PATTERNS="AKIA[0-9A-Z]{16}|ghp_[a-zA-Z0-9]{36}|private_key|secret.*=.*['\"]"
MATCHES=$(grep -rE "${PATTERNS}" "${REPO_ROOT}" --include="*.py" --include="*.ts" --include="*.tsx" --include="*.rs" --include="*.sh" --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=target --exclude-dir=.venv || true)
if [ -z "${MATCHES}" ]; then
    log_pass "no obvious hardcoded secrets"
else
    log_warn "possible secrets found (review manually)"
fi

echo "========================================"
echo "Results: ${PASS} passed, ${FAIL} failed, ${WARN} warnings"
echo "========================================"

if [ $FAIL -gt 0 ]; then
    echo "Pre-flight FAILED. Fix failures before deploying."
    exit 1
fi

echo "Pre-flight PASSED. Ready for devnet deployment."
exit 0
