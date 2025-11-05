#!/bin/bash
# Pre-push hook to verify code quality and tests before pushing to GitHub
# This prevents CI/CD failures by catching issues locally

echo "🔍 Running pre-push checks..."

# Check if we're pushing to main or develop
branch=$(git rev-parse --abbrev-ref HEAD)
if [[ "$branch" != "main" && "$branch" != "develop" ]]; then
    echo "✅ Not pushing to main/develop, skipping checks"
    exit 0
fi

# 1. Check Black formatting (same as CI/CD)
echo ""
echo "1️⃣ Checking Black formatting..."
if ! python -m black --check ekahau_bom/ tests/; then
    echo "❌ Black formatting check failed!"
    echo "💡 Fix: Run 'python -m black ekahau_bom/ tests/' to format code"
    exit 1
fi
echo "✅ Black formatting OK"

# 2. Run quick unit tests (skip slow integration tests)
echo ""
echo "2️⃣ Running quick unit tests..."
if ! python -m pytest tests/ -v -m "not slow" --tb=short -x; then
    echo "❌ Tests failed!"
    echo "💡 Fix failing tests before pushing"
    exit 1
fi
echo "✅ Tests passed"

# 3. Check that version matches in both files (prevent version mismatch)
echo ""
echo "3️⃣ Checking version consistency..."
VERSION_PYPROJECT=$(grep -E '^version = ' pyproject.toml | cut -d'"' -f2)
VERSION_INIT=$(grep -E '^__version__ = ' ekahau_bom/__init__.py | cut -d'"' -f2)

if [[ "$VERSION_PYPROJECT" != "$VERSION_INIT" ]]; then
    echo "❌ Version mismatch!"
    echo "   pyproject.toml: $VERSION_PYPROJECT"
    echo "   __init__.py: $VERSION_INIT"
    echo "💡 Fix: Update both files to same version"
    exit 1
fi
echo "✅ Version consistent: $VERSION_PYPROJECT"

echo ""
echo "✅ All pre-push checks passed! Pushing to GitHub..."
exit 0
