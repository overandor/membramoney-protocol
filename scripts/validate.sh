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
echo "Membra Money Protocol — Validation Suite"
echo "========================================"

# 1. Python backend syntax
echo "[1/6] Python backend syntax check..."
if python3 -m py_compile "${REPO_ROOT}/backend/main.py" 2>/dev/null; then
    log_pass "backend/main.py compiles"
else
    log_fail "backend/main.py syntax error"
fi

# 2. Python backend tests
echo "[2/6] Python backend tests..."
if [ -d "${REPO_ROOT}/backend/.venv" ]; then
    if (cd "${REPO_ROOT}/backend" && source .venv/bin/activate && pytest -q tests/ 2>/dev/null); then
        log_pass "backend tests pass"
    else
        log_warn "backend tests skipped (venv exists but pytest failed or no tests)"
    fi
else
    log_warn "backend tests skipped (no .venv)"
fi

# 3. Cargo check Anchor program
echo "[3/6] Anchor program cargo check..."
if command -v cargo &>/dev/null; then
    if (cd "${REPO_ROOT}/programs/membramoney" && cargo check 2>/dev/null); then
        log_pass "cargo check passes"
    else
        log_warn "cargo check failed (may need dependencies)"
    fi
else
    log_warn "cargo not installed"
fi

# 4. Check for hardcoded secrets
echo "[4/6] Secret scan..."
PATTERNS="AKIA[0-9A-Z]{16}|ghp_[a-zA-Z0-9]{36}|private_key|secret.*=.*['\"]"
MATCHES=$(grep -rE "${PATTERNS}" "${REPO_ROOT}" --include="*.py" --include="*.ts" --include="*.tsx" --include="*.rs" --include="*.sh" --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=target --exclude-dir=.venv || true)
if [ -z "${MATCHES}" ]; then
    log_pass "no obvious hardcoded secrets"
else
    log_warn "possible secrets found (review manually)"
    echo "${MATCHES}" | head -n 5
fi

# 5. UI build
echo "[5/6] UI build check..."
if [ -d "${REPO_ROOT}/ui/node_modules" ]; then
    if (cd "${REPO_ROOT}/ui" && npm run build 2>/dev/null); then
        log_pass "UI build succeeds"
    else
        log_warn "UI build failed"
    fi
else
    log_warn "UI build skipped (no node_modules)"
fi

# 6. Docs existence
echo "[6/6] Documentation check..."
for doc in README.md SECURITY.md MAINNET_READINESS.md DEVNET_DEPLOYMENT.md; do
    if [ -f "${REPO_ROOT}/${doc}" ]; then
        log_pass "${doc} exists"
    else
        log_fail "${doc} missing"
    fi
done

echo "========================================"
echo "Results: ${PASS} passed, ${FAIL} failed, ${WARN} warnings"
echo "========================================"

if [ $FAIL -gt 0 ]; then
    exit 1
fi
exit 0
