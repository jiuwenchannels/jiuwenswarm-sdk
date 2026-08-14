# JiuwenSwarm SDK — developer Makefile
#
# Targets
# -------
#   install       Install all Python and TypeScript dependencies
#   test          Run the full Python test suite
#   test-ts       Run the TypeScript test suite
#   check         Run ruff linter + mypy type-checker (Python)
#   type-check    Run mypy only (Python)  /  tsc --noEmit (TypeScript)
#   fix           Auto-fix Python lint and format issues with ruff
#   build         Build the @jiuwenswarm/sdk TypeScript package (dist/)
#   clean         Remove build artefacts
#
# Prerequisites: Python ≥ 3.9, pip, Node.js ≥ 18, npm

.PHONY: install test test-ts check type-check fix build clean

# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------

install:
	pip install -e ".[dev]"
	cd packages/sdk && npm install

# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

test:
	python3 -m pytest tests/ -q

test-ts:
	cd packages/sdk && npm test

# ---------------------------------------------------------------------------
# Lint / type-check (Python)
# ---------------------------------------------------------------------------

check:
	ruff check openjiuwen/ tests/
	mypy openjiuwen/ --ignore-missing-imports

type-check:
	mypy openjiuwen/ --ignore-missing-imports

# ---------------------------------------------------------------------------
# Type-check (TypeScript)
# ---------------------------------------------------------------------------

type-check-ts:
	cd packages/sdk && npm run typecheck

# ---------------------------------------------------------------------------
# Auto-fix
# ---------------------------------------------------------------------------

fix:
	ruff check --fix openjiuwen/ tests/
	ruff format openjiuwen/ tests/

# ---------------------------------------------------------------------------
# Build TypeScript
# ---------------------------------------------------------------------------

build:
	cd packages/sdk && npm run build

# ---------------------------------------------------------------------------
# Clean
# ---------------------------------------------------------------------------

clean:
	rm -rf packages/sdk/dist packages/sdk/docs packages/sdk/node_modules
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
