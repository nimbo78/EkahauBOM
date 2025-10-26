# Автоматизация GitHub Releases

Несколько способов автоматизировать создание GitHub Releases для EkahauBOM.

---

## Вариант 1: GitHub CLI (`gh`) ⭐ РЕКОМЕНДУЕТСЯ

**Самый простой и быстрый способ.**

### Установка GitHub CLI

#### Windows

**Вариант A: Через Winget** (рекомендуется)
```bash
winget install --id GitHub.cli
```

**Вариант B: Через Chocolatey**
```bash
choco install gh
```

**Вариант C: Через Scoop**
```bash
scoop install gh
```

**Вариант D: Скачать MSI installer**
- Скачать с https://github.com/cli/cli/releases/latest
- Установить `gh_*_windows_amd64.msi`

#### Linux/macOS

**Ubuntu/Debian:**
```bash
sudo apt install gh
```

**macOS (Homebrew):**
```bash
brew install gh
```

**Другие системы:** https://github.com/cli/cli#installation

---

### Первоначальная настройка

После установки нужно авторизоваться один раз:

```bash
# Авторизация (откроется браузер)
gh auth login

# Выберите:
# - GitHub.com
# - HTTPS
# - Authenticate via web browser
# - Следуйте инструкциям в браузере
```

Проверка авторизации:
```bash
gh auth status
```

---

### Использование для релизов

#### Одна команда для создания release:

```bash
gh release create v2.5.0 \
  dist/ekahau_bom-2.5.0.tar.gz \
  dist/ekahau_bom-2.5.0-py3-none-any.whl \
  --title "v2.5.0 - Production Ready Release" \
  --notes-file RELEASE_NOTES_v2.5.0.md
```

**Что происходит:**
- ✅ Создается GitHub Release
- ✅ Прикрепляются дистрибутивы (tar.gz, whl)
- ✅ Добавляются release notes из файла
- ✅ Автоматически генерируется changelog

#### Интерактивный режим:

```bash
gh release create v2.5.0 --generate-notes
```

`gh` CLI попросит:
- Выбрать дистрибутивы для загрузки
- Ввести title
- Отредактировать notes

---

### Скрипт для релизов

Создайте файл `scripts/create_release.sh`:

```bash
#!/bin/bash
# Скрипт для создания GitHub Release

VERSION=$1

if [ -z "$VERSION" ]; then
    echo "Usage: ./scripts/create_release.sh <version>"
    echo "Example: ./scripts/create_release.sh 2.5.0"
    exit 1
fi

TAG="v${VERSION}"
TITLE="v${VERSION} - Release"
NOTES_FILE="RELEASE_NOTES_v${VERSION}.md"

echo "Creating release for version ${VERSION}..."

# Проверка наличия файлов
if [ ! -f "dist/ekahau_bom-${VERSION}.tar.gz" ]; then
    echo "Error: Distribution files not found in dist/"
    echo "Run 'python -m build' first"
    exit 1
fi

if [ ! -f "$NOTES_FILE" ]; then
    echo "Warning: $NOTES_FILE not found, using auto-generated notes"
    NOTES_FLAG="--generate-notes"
else
    NOTES_FLAG="--notes-file $NOTES_FILE"
fi

# Создание release
gh release create "$TAG" \
  "dist/ekahau_bom-${VERSION}.tar.gz" \
  "dist/ekahau_bom-${VERSION}-py3-none-any.whl" \
  --title "$TITLE" \
  $NOTES_FLAG \
  --latest

echo "✅ Release $TAG created successfully!"
echo "View at: https://github.com/htechno/EkahauBOM/releases/tag/$TAG"
```

**Использование:**
```bash
chmod +x scripts/create_release.sh
./scripts/create_release.sh 2.5.0
```

---

## Вариант 2: GitHub Actions (CI/CD) 🤖

**Полная автоматизация при push тега.**

### Создайте `.github/workflows/release.yml`:

```yaml
name: Create Release

on:
  push:
    tags:
      - 'v*.*.*'  # Срабатывает на теги вида v1.0.0

jobs:
  build-and-release:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.10'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build twine

    - name: Build distributions
      run: python -m build

    - name: Create GitHub Release
      uses: softprops/action-gh-release@v1
      with:
        files: |
          dist/*.tar.gz
          dist/*.whl
        body_path: RELEASE_NOTES_${{ github.ref_name }}.md
        draft: false
        prerelease: false
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**Использование:**

```bash
# 1. Создать тег
git tag -a v2.6.0 -m "Release v2.6.0"

# 2. Запушить тег
git push origin v2.6.0

# 3. GitHub Actions автоматически:
#    - Соберет дистрибутивы
#    - Создаст Release
#    - Прикрепит файлы
```

**Преимущества:**
- ✅ Полная автоматизация
- ✅ Консистентная сборка в чистом окружении
- ✅ Не нужно собирать локально

**Недостатки:**
- ❌ Требует настройки workflow
- ❌ Сложнее отладить при проблемах

---

## Вариант 3: Python скрипт с GitHub API

Создайте `scripts/create_release.py`:

```python
#!/usr/bin/env python3
"""
Скрипт для создания GitHub Release через API
Требует: pip install PyGithub
"""

import sys
import os
from pathlib import Path
from github import Github

def create_release(version, token):
    """Создает GitHub Release."""

    # Параметры
    repo_name = "htechno/EkahauBOM"
    tag = f"v{version}"
    title = f"v{version} - Release"

    # Файлы для загрузки
    dist_dir = Path("dist")
    files = [
        dist_dir / f"ekahau_bom-{version}.tar.gz",
        dist_dir / f"ekahau_bom-{version}-py3-none-any.whl",
    ]

    # Проверка файлов
    for f in files:
        if not f.exists():
            print(f"❌ File not found: {f}")
            sys.exit(1)

    # Release notes
    notes_file = Path(f"RELEASE_NOTES_v{version}.md")
    if notes_file.exists():
        notes = notes_file.read_text(encoding="utf-8")
    else:
        notes = f"Release v{version}"

    # Подключение к GitHub
    g = Github(token)
    repo = g.get_repo(repo_name)

    # Создание release
    print(f"Creating release {tag}...")
    release = repo.create_git_release(
        tag=tag,
        name=title,
        message=notes,
        draft=False,
        prerelease=False
    )

    # Загрузка файлов
    for file_path in files:
        print(f"Uploading {file_path.name}...")
        release.upload_asset(
            str(file_path),
            name=file_path.name
        )

    print(f"✅ Release created: {release.html_url}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python create_release.py <version>")
        print("Example: python create_release.py 2.5.0")
        sys.exit(1)

    version = sys.argv[1]

    # GitHub token из переменной окружения
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("❌ GITHUB_TOKEN environment variable not set")
        print("Create token at: https://github.com/settings/tokens")
        sys.exit(1)

    create_release(version, token)
```

**Установка зависимостей:**
```bash
pip install PyGithub
```

**Создание токена:**
1. Перейти на https://github.com/settings/tokens
2. Generate new token (classic)
3. Выбрать scopes: `repo` (Full control)
4. Скопировать токен

**Использование:**
```bash
# Windows
set GITHUB_TOKEN=ghp_yourtoken
python scripts/create_release.py 2.5.0

# Linux/macOS
export GITHUB_TOKEN=ghp_yourtoken
python scripts/create_release.py 2.5.0
```

---

## Вариант 4: Makefile (для удобства)

Создайте `Makefile`:

```makefile
.PHONY: help build release clean

VERSION := $(shell python -c "import ekahau_bom; print(ekahau_bom.__version__)")

help:
	@echo "EkahauBOM Release Automation"
	@echo ""
	@echo "Available commands:"
	@echo "  make build      - Build distributions"
	@echo "  make release    - Create GitHub Release (requires gh CLI)"
	@echo "  make clean      - Clean build artifacts"
	@echo ""
	@echo "Current version: $(VERSION)"

build:
	@echo "Building distributions for version $(VERSION)..."
	python -m build
	@echo "✅ Build complete!"

release: build
	@echo "Creating GitHub Release for v$(VERSION)..."
	gh release create v$(VERSION) \
		dist/ekahau_bom-$(VERSION).tar.gz \
		dist/ekahau_bom-$(VERSION)-py3-none-any.whl \
		--title "v$(VERSION) - Release" \
		--notes-file RELEASE_NOTES_v$(VERSION).md \
		--latest
	@echo "✅ Release created!"

clean:
	rm -rf build/ dist/ *.egg-info
	@echo "✅ Clean complete!"
```

**Использование:**
```bash
# Собрать и создать release одной командой
make release

# Или по шагам
make build
make release
```

---

## Рекомендации

### Для быстрого старта:
1. ✅ Установите **GitHub CLI** (`gh`)
2. ✅ Авторизуйтесь: `gh auth login`
3. ✅ Используйте одну команду для release

### Для автоматизации:
1. ✅ Настройте **GitHub Actions** workflow
2. ✅ Просто пушьте теги, все остальное автоматически

### Для гибкости:
1. ✅ Используйте **Python скрипт** с PyGithub
2. ✅ Настраивайте под свои нужды

---

## Пример полного workflow

```bash
# 1. Обновить версию
# Редактируем __init__.py, setup.py, pyproject.toml, CHANGELOG.md

# 2. Собрать дистрибутивы
python -m build

# 3. Создать коммит
git add .
git commit -m "Release v2.6.0"

# 4. Создать тег
git tag -a v2.6.0 -m "Release v2.6.0"

# 5. Запушить
git push origin main v2.6.0

# 6. Создать GitHub Release (с gh CLI)
gh release create v2.6.0 \
  dist/ekahau_bom-2.6.0.tar.gz \
  dist/ekahau_bom-2.6.0-py3-none-any.whl \
  --title "v2.6.0 - Release" \
  --notes-file RELEASE_NOTES_v2.6.0.md
```

**Или с GitHub Actions - просто шаги 1-5, релиз создастся автоматически!**

---

## Установка `gh` для вашей системы (Windows)

```bash
# Проверить есть ли winget
winget --version

# Если есть - установить gh
winget install --id GitHub.cli

# Перезапустить терминал

# Проверить установку
gh --version

# Авторизоваться
gh auth login
```

После этого можете использовать `gh release create` 🚀
