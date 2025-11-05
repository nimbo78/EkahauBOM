.PHONY: help install install-dev install-hooks test test-quick test-full format lint clean

help:  ## Show this help message
	@echo "EkahauBOM Development Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install package in development mode
	pip install -e .

install-dev:  ## Install package with dev dependencies
	pip install -e .[dev]

install-hooks:  ## Install pre-commit and pre-push hooks
	@echo "Installing pre-commit hooks..."
	pre-commit install
	@echo "Installing pre-push hooks..."
	pre-commit install --hook-type pre-push
	@echo "✅ Hooks installed successfully!"
	@echo ""
	@echo "Pre-commit hooks will run on every commit:"
	@echo "  - Black formatter (line-length=100)"
	@echo "  - Trailing whitespace"
	@echo "  - End of file fixer"
	@echo "  - JSON/TOML validation"
	@echo ""
	@echo "Pre-push hooks will run before every push:"
	@echo "  - Black formatting check (same as CI/CD)"
	@echo "  - Quick unit tests (skips slow tests)"
	@echo "  - Version consistency check"
	@echo ""
	@echo "To skip pre-push checks (NOT recommended):"
	@echo "  git push --no-verify"

test:  ## Run all tests with coverage
	pytest tests/ -v --cov=ekahau_bom --cov-report=term --cov-report=html

test-quick:  ## Run quick unit tests (skip slow integration tests)
	pytest tests/ -v -m "not slow" --tb=short

test-full:  ## Run all tests including slow integration tests
	pytest tests/ -v --cov=ekahau_bom --cov-report=term --cov-report=html --tb=short

format:  ## Format code with Black
	black ekahau_bom/ tests/

format-check:  ## Check code formatting (same as CI/CD)
	black --check ekahau_bom/ tests/

lint:  ## Run all linters (black, flake8, mypy)
	@echo "Running Black..."
	black --check ekahau_bom/ tests/
	@echo ""
	@echo "Running flake8..."
	flake8 ekahau_bom/ --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 ekahau_bom/ --count --exit-zero --max-complexity=10 --max-line-length=100 --statistics
	@echo ""
	@echo "Running mypy..."
	mypy ekahau_bom/ --ignore-missing-imports

pre-push-check:  ## Run pre-push checks manually (same as pre-push hook)
	bash .pre-push-hook.sh

clean:  ## Clean build artifacts and cache
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.pyo' -delete

build:  ## Build distribution packages
	python -m build

release-check:  ## Check if ready for release
	@echo "Checking version consistency..."
	@VERSION_PYPROJECT=$$(grep -E '^version = ' pyproject.toml | cut -d'"' -f2); \
	VERSION_INIT=$$(grep -E '^__version__ = ' ekahau_bom/__init__.py | cut -d'"' -f2); \
	if [ "$$VERSION_PYPROJECT" != "$$VERSION_INIT" ]; then \
		echo "❌ Version mismatch!"; \
		echo "   pyproject.toml: $$VERSION_PYPROJECT"; \
		echo "   __init__.py: $$VERSION_INIT"; \
		exit 1; \
	fi; \
	echo "✅ Version consistent: $$VERSION_PYPROJECT"
	@echo ""
	@echo "Running tests..."
	@make test-full
	@echo ""
	@echo "Checking code quality..."
	@make lint
	@echo ""
	@echo "✅ Ready for release!"
