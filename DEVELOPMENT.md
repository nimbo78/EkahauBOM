# Development Guide

## Setup Development Environment

### 1. Install Dependencies

```bash
# Install package with dev dependencies
pip install -e .[dev]

# Or using make
make install-dev
```

### 2. Install Git Hooks

**ВАЖНО**: Установите pre-commit и pre-push hooks чтобы избежать ошибок CI/CD:

```bash
# Install hooks
make install-hooks

# Or manually
pre-commit install
pre-commit install --hook-type pre-push
```

## Git Hooks

### Pre-commit Hooks (запускаются при каждом коммите)

Автоматически форматируют и проверяют код:

- ✅ **Black formatter** (line-length=100)
- ✅ **Trailing whitespace** removal
- ✅ **End of file** fixer
- ✅ **JSON/TOML** validation
- ✅ **Merge conflict** detection
- ✅ **Debug statements** detection

### Pre-push Hooks (запускаются перед каждым push)

Предотвращают ошибки CI/CD, проверяя **ДО push**:

1. **Black formatting check** (точно как CI/CD)
   - Проверяет что код отформатирован с line-length=100
   - Если fail: запустите `make format` или `black ekahau_bom/ tests/`

2. **Quick unit tests** (пропускает медленные интеграционные)
   - Запускает тесты с `-m "not slow"`
   - Если fail: исправьте тесты перед push

3. **Version consistency check**
   - Проверяет что версия в `pyproject.toml` == `__init__.py`
   - Предотвращает version mismatch как в issue с 2.8.0 vs 3.0.5

### Пропустить Pre-push Checks (НЕ рекомендуется)

Если очень нужно (например hotfix):

```bash
git push --no-verify
```

⚠️ **Внимание**: Это пропустит все проверки и может сломать CI/CD!

## Testing

### Quick Tests (fast, for development)

```bash
# Run quick unit tests (skip slow integration tests)
make test-quick

# Or directly
pytest tests/ -v -m "not slow" --tb=short
```

### Full Tests (with coverage)

```bash
# Run all tests with coverage report
make test

# Or run everything including slow tests
make test-full
```

### Mark Slow Tests

Пометьте медленные тесты декоратором:

```python
import pytest

@pytest.mark.slow
def test_slow_integration():
    # This test will be skipped in quick tests
    pass
```

## Code Quality

### Format Code

```bash
# Format all code with Black (line-length=100)
make format

# Check formatting (same as CI/CD)
make format-check
```

### Run Linters

```bash
# Run all linters (Black, flake8, mypy)
make lint
```

### Manual Pre-push Check

Запустить pre-push checks вручную (без push):

```bash
make pre-push-check
```

## Release Process

### Before Creating Release

```bash
# Check if everything is ready for release
make release-check
```

Эта команда проверяет:
- ✅ Version consistency (pyproject.toml == __init__.py)
- ✅ All tests pass
- ✅ Code quality checks pass

### Version Bump

1. Update version in **both** files:
   ```bash
   # pyproject.toml
   version = "3.0.6"

   # ekahau_bom/__init__.py
   __version__ = "3.0.6"
   ```

2. Update `CHANGELOG.md`

3. Commit and tag:
   ```bash
   git add pyproject.toml ekahau_bom/__init__.py CHANGELOG.md
   git commit -m "Bump version to 3.0.6"
   git tag v3.0.6
   git push origin main
   git push origin v3.0.6
   ```

## Common Issues

### Issue: Black formatting fails in CI/CD but passes locally

**Причина**: Разные настройки line-length

**Решение**:
1. Проверьте `.pre-commit-config.yaml` - там НЕ должно быть `args: [--line-length=88]`
2. Используйте настройки из `pyproject.toml` (line-length=100)
3. Запустите: `make format`

### Issue: Tests pass locally but fail in CI/CD

**Причина**: Разные версии зависимостей или тесты не запускались локально

**Решение**:
1. Установите pre-push hook: `make install-hooks`
2. Теперь тесты будут запускаться перед каждым push
3. Если нужно пропустить: `git push --no-verify` (НЕ рекомендуется)

### Issue: Version mismatch error

**Причина**: Версия в `pyproject.toml` != `__init__.py`

**Решение**:
```bash
# Check versions manually
grep -E '^version = ' pyproject.toml
grep -E '^__version__ = ' ekahau_bom/__init__.py

# Update both to same version
```

## Makefile Commands

Все доступные команды:

```bash
make help                 # Show all commands
make install              # Install package
make install-dev          # Install with dev dependencies
make install-hooks        # Install pre-commit/pre-push hooks
make test                 # Run tests with coverage
make test-quick           # Run quick tests (skip slow)
make test-full            # Run all tests including slow
make format               # Format code with Black
make format-check         # Check formatting (CI/CD style)
make lint                 # Run all linters
make pre-push-check       # Run pre-push checks manually
make clean                # Clean build artifacts
make build                # Build distribution packages
make release-check        # Check if ready for release
```

## CI/CD Workflows

### Tests Workflow

Запускается на: push to main/develop, pull requests

Проверяет:
- ✅ Tests на 3 OS (Ubuntu, macOS, Windows)
- ✅ Tests на 5 Python versions (3.9-3.13)
- ✅ Coverage >= 80%

### Code Quality Workflow

Запускается на: push to main/develop, pull requests

Проверяет:
- ✅ Black formatting (line-length=100)
- ✅ Flake8 linting
- ✅ MyPy type checking

### Release Workflow

Запускается на: push tag `v*.*.*`

Создаёт:
- ✅ GitHub Release with changelog
- ✅ Artifacts (wheel, source dist)

## Best Practices

1. **Always install hooks**: `make install-hooks` на новой машине
2. **Run quick tests often**: `make test-quick` во время разработки
3. **Run full tests before PR**: `make test-full` перед создан ием PR
4. **Check formatting**: `make format-check` перед коммитом
5. **Use make commands**: Проще и безопаснее чем ручные команды

## Questions?

См. также:
- `README.md` - основная документация
- `CHANGELOG.md` - история изменений
- `CLAUDE.md` - правила для Claude Code
- `WEBUI_PLAN.md` - план развития Web UI
