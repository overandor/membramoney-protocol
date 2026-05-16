# Contributing to Membra Money Protocol

**Status:** DEVNET / RESEARCH PREVIEW ONLY

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/membramoney-protocol.git`
3. Follow the setup in [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

## Development Workflow

### 1. Branch Naming

- `feat/description` — New features
- `fix/description` — Bug fixes
- `docs/description` — Documentation
- `test/description` — Tests
- `chore/description` — Maintenance

### 2. Before Committing

Run the pre-flight checks:
```bash
bash scripts/pre_flight_check.sh
```

Run tests:
```bash
# Rust
cargo test --lib

# Backend
cd backend
pytest tests/ -v

# Frontend
cd ui
npm run build
```

### 3. Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add reserve attestation endpoint
fix: correct expiry calculation in claim validation
docs: update API_REFERENCE with new endpoints
test: add negative tests for denomination boundaries
chore: update dependencies
```

### 4. Pull Request Template

```markdown
## What
Brief description of changes.

## Why
Motivation and context.

## Testing
- [ ] `cargo test --lib` passes
- [ ] `pytest backend/tests/` passes
- [ ] `npm run build` succeeds
- [ ] Pre-flight checks pass

## Checklist
- [ ] No secrets exposed
- [ ] DEVNET classification preserved
- [ ] Documentation updated
```

## Code Standards

### Rust
- Follow `cargo fmt` formatting
- Run `cargo clippy` before committing
- Document public functions with `///`
- Add tests for new logic

### Python
- Follow PEP 8
- Use type hints
- Run `pytest` before committing
- Add docstrings for public functions

### TypeScript / React
- Follow existing component patterns
- Use functional components with hooks
- Add `aria-*` attributes for accessibility
- Keep components small and focused

## Security

- Never commit secrets or API keys
- Rotate exposed tokens immediately
- Report vulnerabilities via SECURITY.md
- All claims are DEVNET ONLY — never imply production readiness

## Questions?

Open an issue or reach out in the project discussions.
