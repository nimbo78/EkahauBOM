# GitHub Release Creation Instructions

## Создание GitHub Release для v2.5.0

### Шаг 1: Перейти на страницу Releases

1. Откройте браузер и перейдите на:
   ```
   https://github.com/htechno/EkahauBOM/releases
   ```

2. Нажмите кнопку **"Draft a new release"** (или "Create a new release")

---

### Шаг 2: Выбрать тег

1. В поле **"Choose a tag"** выберите из списка: `v2.5.0`
   - Тег уже создан и запушен на GitHub
   - Если не видите тег, обновите страницу

---

### Шаг 3: Заполнить Release Title

```
v2.5.0 - Production Ready Release
```

---

### Шаг 4: Скопировать Release Notes

Скопируйте содержимое файла `RELEASE_NOTES_v2.5.0.md` в поле **"Describe this release"**

Или используйте краткую версию:

```markdown
# 🎉 EkahauBOM v2.5.0 - Production Ready

Production-ready release completing Iteration 5 with all 6 phases!

## ✨ What's New

### 📄 PDF Export (Phase 3)
- Professional print-ready PDF reports with WeasyPrint
- Print-optimized A4 layout with all sections

### 🎨 Interactive CLI (Phase 4)
- Rich library integration
- Progress bars and styled tables
- Enhanced error messages

### 📦 Batch Processing (Phase 5)
- Process multiple .esx files at once
- Recursive directory search
- Batch summary with success/failure tracking

### 📚 Documentation & Testing (Phases 1-2)
- 258 tests passing, 70% coverage
- Complete README, user/developer guides
- Russian translations

### 🔧 Modern Packaging (Phase 6)
- pyproject.toml for PEP 517/518 compliance
- MANIFEST.in for config file inclusion

## 📦 Installation

```bash
# Download from GitHub Releases:
pip install ekahau_bom-2.5.0-py3-none-any.whl
```

## 🎯 Production Ready Features

✅ 5 export formats (CSV, Excel, HTML, JSON, PDF)
✅ Advanced analytics (radio, mounting, cost)
✅ Interactive CLI with progress bars
✅ Batch processing support
✅ 258 tests passing (70% coverage)
✅ Complete documentation

## 📋 Requirements

- Python 3.7+
- PyYAML >= 6.0
- openpyxl >= 3.0.0

Optional:
- WeasyPrint >= 60.0 (PDF export)
- rich >= 13.0.0 (enhanced CLI)

## 🔗 Links

- [Full Changelog](https://github.com/htechno/EkahauBOM/blob/main/CHANGELOG.md)
- [User Guide](https://github.com/htechno/EkahauBOM/blob/main/docs/USER_GUIDE.md)
- [Developer Guide](https://github.com/htechno/EkahauBOM/blob/main/docs/DEVELOPER_GUIDE.md)

---

**Made with ❤️ for the Wi-Fi community**
```

---

### Шаг 5: Прикрепить дистрибутивы

В секции **"Attach binaries"** прикрепите файлы из директории `dist/`:

1. Нажмите на область **"Attach binaries by dropping them here or selecting them"**
2. Выберите файлы:
   - `ekahau_bom-2.5.0.tar.gz` (source distribution)
   - `ekahau_bom-2.5.0-py3-none-any.whl` (wheel distribution)

**Путь к файлам:**
```
c:\Users\igors\OneDrive\Документы\Claude\EkahauBOM\dist\
```

---

### Шаг 6: Настройки Release

1. ✅ **Set as the latest release** - отметить галочкой
2. ⚪ **Set as a pre-release** - НЕ отмечать (это production release)
3. ⚪ **Create a discussion for this release** - опционально

---

### Шаг 7: Публикация

1. Нажмите кнопку **"Publish release"**
2. GitHub автоматически создаст Release с:
   - Тегом v2.5.0
   - Release notes
   - Прикрепленными дистрибутивами
   - Source code (автоматически: zip и tar.gz)

---

## Проверка

После публикации проверьте:

1. Release виден на странице: https://github.com/htechno/EkahauBOM/releases
2. Дистрибутивы доступны для скачивания
3. Release notes отображаются корректно
4. Тег `v2.5.0` отображается в списке тегов

---

## Альтернатива: GitHub CLI (если установлен)

Если у вас установлен `gh` CLI, можно создать release одной командой:

```bash
gh release create v2.5.0 \
  dist/ekahau_bom-2.5.0.tar.gz \
  dist/ekahau_bom-2.5.0-py3-none-any.whl \
  --title "v2.5.0 - Production Ready Release" \
  --notes-file RELEASE_NOTES_v2.5.0.md
```

---

## 🎉 Готово!

После создания GitHub Release:
- ✅ Phase 6 завершена
- ✅ Iteration 5 полностью завершена
- ✅ Продукт готов к production использованию!
