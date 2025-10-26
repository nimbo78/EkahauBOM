# Release Process

This document describes the automated release process for EkahauBOM using GitHub Actions.

## Overview

The project uses GitHub Actions workflows for:
1. **Automated GitHub Releases** - Creates releases when version tags are pushed
2. **PyPI Publishing** - Publishes packages to PyPI (optional)
3. **Continuous Testing** - Runs tests on all commits and pull requests
4. **Code Quality Checks** - Validates code formatting and linting

## Creating a New Release

### Prerequisites

1. All changes committed and pushed to `main` branch
2. All tests passing
3. Documentation updated (CHANGELOG.md, README.md, etc.)
4. Version bumped in `pyproject.toml` and `ekahau_bom/__init__.py`

### Release Steps

#### 1. Update Version Number

Update version in two places:

**pyproject.toml:**
```toml
[project]
version = "2.8.0"  # Update this
```

**ekahau_bom/__init__.py:**
```python
__version__ = "2.8.0"  # Update this
```

#### 2. Update CHANGELOG.md

Add a new section for the version:

```markdown
## [2.8.0] - 2025-10-27

### Added
- New feature description

### Changed
- Changes description

### Fixed
- Bug fixes description
```

#### 3. Commit Version Changes

```bash
git add pyproject.toml ekahau_bom/__init__.py CHANGELOG.md
git commit -m "Bump version to 2.8.0"
git push origin main
```

#### 4. Create and Push Git Tag

```bash
git tag v2.8.0
git push origin v2.8.0
```

#### 5. Automated Process

Once the tag is pushed, GitHub Actions automatically:

1. **Builds the package** - Creates wheel and source distribution
2. **Extracts changelog** - Pulls release notes from CHANGELOG.md
3. **Creates GitHub Release** - Creates a release with:
   - Release title: "Release v2.8.0"
   - Release notes from CHANGELOG.md
   - Attached build artifacts (wheel and tar.gz)
4. **Publishes to PyPI** (if configured) - Uploads package to PyPI

### Monitoring the Release

1. Go to **Actions** tab in GitHub repository
2. Check the **Release** workflow run
3. Verify all steps completed successfully
4. Check **Releases** page for the new release

## Workflows Description

### 1. release.yml

**Trigger:** Push tag matching `v*.*.*` (e.g., v2.8.0)

**Actions:**
- Checks out code
- Sets up Python 3.11
- Builds package with `python -m build`
- Extracts changelog for the version
- Creates GitHub release with artifacts
- Uploads build artifacts

**Required:** No secrets needed (uses GITHUB_TOKEN automatically)

### 2. publish-pypi.yml

**Trigger:**
- When a GitHub release is published
- Manual trigger via workflow_dispatch

**Actions:**
- Builds package
- Validates package with `twine check`
- Publishes to PyPI

**Required:** `PYPI_API_TOKEN` secret must be configured

#### Setting up PyPI Publishing

1. Create PyPI API token at https://pypi.org/manage/account/token/
2. Add token to GitHub Secrets:
   - Go to repository **Settings** → **Secrets and variables** → **Actions**
   - Click **New repository secret**
   - Name: `PYPI_API_TOKEN`
   - Value: Your PyPI API token (starts with `pypi-`)

### 3. tests.yml

**Trigger:** Push or pull request to `main` or `develop` branches

**Actions:**
- Runs tests on multiple OS (Ubuntu, Windows, macOS)
- Tests Python versions 3.8, 3.9, 3.10, 3.11, 3.12
- Generates coverage report
- Uploads coverage to Codecov (optional)

**Matrix:** 15 test combinations (3 OS × 5 Python versions)

### 4. code-quality.yml

**Trigger:** Push or pull request to `main` or `develop` branches

**Actions:**
- Checks code formatting with `black`
- Lints code with `flake8`
- Type checks with `mypy` (informational)

## Manual Release (Fallback)

If you need to create a release manually:

### Build Package Locally

```bash
python -m pip install --upgrade build twine
python -m build
```

### Check Package

```bash
twine check dist/*
```

### Create GitHub Release

1. Go to repository **Releases** page
2. Click **Draft a new release**
3. Choose tag: v2.8.0 (or create new)
4. Fill in release title and notes
5. Upload artifacts from `dist/` folder
6. Click **Publish release**

### Publish to PyPI

```bash
twine upload dist/*
# You'll be prompted for PyPI username and password/token
```

## Rollback a Release

If you need to rollback a release:

1. **Delete the GitHub release:**
   - Go to Releases page
   - Click on the release
   - Click **Delete**

2. **Delete the Git tag:**
   ```bash
   git tag -d v2.8.0
   git push origin :refs/tags/v2.8.0
   ```

3. **Remove from PyPI:**
   - You cannot delete releases from PyPI
   - Instead, publish a new patch version with fixes

## Best Practices

1. **Always test before releasing:**
   - Run `pytest` locally
   - Check all CI workflows pass
   - Test package installation: `pip install -e .`

2. **Semantic Versioning:**
   - MAJOR.MINOR.PATCH (e.g., 2.8.0)
   - MAJOR: Breaking changes
   - MINOR: New features (backward compatible)
   - PATCH: Bug fixes

3. **Changelog:**
   - Update CHANGELOG.md before every release
   - Follow format: Added, Changed, Deprecated, Removed, Fixed, Security
   - Include all notable changes since last release

4. **Version Consistency:**
   - Always update version in both `pyproject.toml` and `__init__.py`
   - Version should match git tag (without 'v' prefix)

5. **Branch Strategy:**
   - Develop new features in feature branches
   - Merge to `develop` for testing
   - Merge to `main` for release
   - Tag releases from `main` branch only

## Troubleshooting

### Workflow Fails to Create Release

**Problem:** "Resource not accessible by integration"

**Solution:** Check repository permissions:
- Settings → Actions → General → Workflow permissions
- Select "Read and write permissions"
- Save

### PyPI Upload Fails

**Problem:** "Invalid or non-existent authentication information"

**Solution:**
1. Check `PYPI_API_TOKEN` secret is set correctly
2. Verify token hasn't expired
3. Regenerate token if needed

### Version Mismatch

**Problem:** Package version doesn't match tag

**Solution:**
1. Ensure `pyproject.toml` version matches tag
2. Rebuild package: `python -m build`
3. Re-upload if necessary

### Changelog Not Extracted

**Problem:** Release notes say "See CHANGELOG.md for details"

**Solution:**
- Ensure CHANGELOG.md has section with format: `## [2.8.0] - YYYY-MM-DD`
- Version in CHANGELOG must match tag version (without 'v' prefix)

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [PyPI Publishing Guide](https://packaging.python.org/en/latest/tutorials/packaging-projects/)
- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)
