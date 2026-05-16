# Membra Money Protocol — Makefile
# Common development tasks

.PHONY: help install build test lint preflight push deploy clean

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install all dependencies
	@echo "Installing Rust dependencies..."
	cargo fetch
	@echo "Installing Python dependencies..."
	cd backend && pip install -r requirements.txt
	@echo "Installing Node.js dependencies..."
	cd ui && npm install

build: ## Build all components
	@echo "Building Anchor program..."
	anchor build
	@echo "Building UI..."
	cd ui && npm run build

test: ## Run all tests
	@echo "Running Rust tests..."
	cargo test --lib
	@echo "Running backend tests..."
	cd backend && pytest tests/ -v
	@echo "Running pre-flight checks..."
	bash scripts/pre_flight_check.sh

lint: ## Run linters
	@echo "Linting Rust..."
	cargo fmt -- --check
	cargo clippy --lib -- -D warnings
	@echo "Linting Python..."
	cd backend && flake8 . --max-line-length=100 || true
	@echo "Linting TypeScript..."
	cd ui && npx tsc --noEmit

preflight: ## Run pre-flight checks
	bash scripts/pre_flight_check.sh

deploy: ## Deploy to devnet
	anchor deploy --provider.cluster devnet

push: ## Commit and push (manual review required)
	@echo "Run the following manually:"
	@echo "  git add -A"
	@echo "  git commit -m 'feat: your changes'"
	@echo "  git push"

clean: ## Clean build artifacts
	cargo clean
	cd ui && rm -rf node_modules dist
	cd backend && rm -rf .venv __pycache__

run-backend: ## Start backend server
	cd backend && uvicorn main:app --reload --port 8000

run-ui: ## Start UI dev server
	cd ui && npm run dev
