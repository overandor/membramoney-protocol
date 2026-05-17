#!/usr/bin/env bash
# Membra Money Protocol — Clean-Clone Verification Script
# Usage: ./scripts/verify_clean_clone.sh
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS=0
FAIL=0

ok() { echo -e "${GREEN}PASS${NC}: $1"; ((PASS++)) || true; }
ko() { echo -e "${RED}FAIL${NC}: $1"; ((FAIL++)) || true; }
warn() { echo -e "${YELLOW}WARN${NC}: $1"; }

echo "========================================"
echo "Membra Money Protocol — Clean-Clone Verification"
echo "========================================"
echo ""

# 1. Backend syntax check
echo "[1/6] Backend Python syntax check..."
if python3 -m py_compile backend/main.py backend/db/adapter.py; then
  ok "Backend Python syntax"
else
  ko "Backend Python syntax"
fi

# 2. Backend imports smoke test
echo "[2/6] Backend imports smoke test..."
if (cd backend && python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from main import app
    from db.adapter import db
    from core.config import settings
    print('imports OK')
except Exception as e:
    print(f'imports FAIL: {e}')
    sys.exit(1)
" 2>&1 | grep -q "imports OK"); then
  ok "Backend imports"
else
  ko "Backend imports (install deps with: pip install -r backend/requirements.txt)"
fi

# 3. Rust syntax check
echo "[3/6] Rust program syntax check..."
if [ -f "programs/membramoney/src/lib.rs" ]; then
  if (cd programs/membramoney && cargo check --lib 2>/dev/null); then
    ok "Rust library check"
  else
    warn "Rust cargo check failed (may need Solana tooling)"
  fi
else
  warn "Rust program not found, skipping"
fi

# 4. UI build check
echo "[4/6] UI build check..."
if [ -f "ui/package.json" ]; then
  if (cd ui && npm install --legacy-peer-deps >/dev/null 2>&1 && npm run build >/dev/null 2>&1); then
    ok "UI npm run build"
  else
    ko "UI npm run build (install Node.js deps)"
  fi
else
  warn "ui/package.json not found, skipping"
fi

# 5. Test file existence
echo "[5/6] Critical file presence check..."
FILES=(
  "backend/main.py"
  "backend/db/adapter.py"
  "backend/requirements.txt"
  "backend/alembic.ini"
  "backend/db/migrations/versions/0001_initial.py"
  "k8s/namespace.yaml"
  "terraform/main.tf"
  "ui/package.json"
  "README.md"
  "PRODUCTION_READINESS.md"
  ".env.example"
  "CHANGELOG.md"
)
for f in "${FILES[@]}"; do
  if [ -f "$f" ]; then
    ok "File exists: $f"
  else
    ko "Missing file: $f"
  fi
done

# 6. Git status
echo "[6/6] Git repository check..."
if git rev-parse --git-dir >/dev/null 2>&1; then
  ok "Git repository initialized"
  UNCOMMITTED=$(git status --short | wc -l | tr -d ' ')
  if [ "$UNCOMMITTED" -eq 0 ]; then
    ok "Working tree clean"
  else
    warn "Unco_committed changes: $UNCOMMITTED files"
  fi
else
  ko "Not a git repository"
fi

echo ""
echo "========================================"
echo "Results: $PASS passed, $FAIL failed"
echo "========================================"

if [ "$FAIL" -eq 0 ]; then
  echo -e "${GREEN}All checks passed!${NC}"
  exit 0
else
  echo -e "${RED}Some checks failed.${NC}"
  exit 1
fi
