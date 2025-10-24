# Руководство пользователя EkahauBOM

Полное руководство по использованию EkahauBOM для генерации спецификаций из проектов Ekahau.

## Содержание

- [Начало работы](#начало-работы)
- [Базовое использование](#базовое-использование)
- [Фильтрация](#фильтрация)
- [Группировка и аналитика](#группировка-и-аналитика)
- [Форматы экспорта](#форматы-экспорта)
- [Расчет стоимости](#расчет-стоимости)
- [Расширенное использование](#расширенное-использование)
- [Устранение неполадок](#устранение-неполадок)

---

## Начало работы

### Предварительные требования

- Python 3.7 или выше
- Проектный файл Ekahau .esx
- Установленные зависимости (`pip install -r requirements.txt`)

### Первый запуск

```bash
# Базовое использование - генерирует CSV файлы
python EkahauBOM.py path/to/project.esx

# Вывод будет в директории ./output/
```

---

## Базовое использование

### Генерация отчетов

```bash
# Формат CSV (по умолчанию)
ekahau-bom project.esx

# Формат Excel (рекомендуется)
ekahau-bom project.esx --format excel

# Формат HTML (интерактивный веб-отчет)
ekahau-bom project.esx --format html

# Все форматы сразу
ekahau-bom project.esx --format csv,excel,html,json
```

### Указание выходной директории

```bash
ekahau-bom project.esx --output-dir /path/to/reports/
```

### Включение логирования

```bash
# Подробный вывод
ekahau-bom project.esx --verbose

# Сохранение логов в файл
ekahau-bom project.esx --log-file processing.log
```

---

## Фильтрация

### Фильтрация по этажу

Включить только конкретные этажи:

```bash
ekahau-bom project.esx --filter-floor "Этаж 1,Этаж 2,Этаж 3"
```

### Фильтрация по производителю

```bash
# Один производитель
ekahau-bom project.esx --filter-vendor "Cisco"

# Несколько производителей
ekahau-bom project.esx --filter-vendor "Cisco,Aruba"
```

### Фильтрация по цвету

Ekahau использует цвета для обозначения разных типов AP:

```bash
ekahau-bom project.esx --filter-color "Yellow,Red"
```

### Фильтрация по модели

```bash
ekahau-bom project.esx --filter-model "C9120AXI,AP-515"
```

### Фильтрация по тегам

Для проектов Ekahau v10.2+ с тегами:

```bash
# Один тег
ekahau-bom project.esx --filter-tag "Location:Здание А"

# Несколько тегов (логика AND)
ekahau-bom project.esx \
  --filter-tag "Location:Здание А" \
  --filter-tag "Zone:Офис"
```

### Исключение элементов

```bash
# Исключить конкретные этажи
ekahau-bom project.esx --exclude-floor "Подвал,Крыша"

# Исключить цвета
ekahau-bom project.esx --exclude-color "Gray"
```

### Комбинированная фильтрация

```bash
# Пример: Только Cisco AP на Этажах 1 и 2, желтого цвета
ekahau-bom project.esx \
  --filter-floor "Этаж 1,Этаж 2" \
  --filter-vendor "Cisco" \
  --filter-color "Yellow"
```

---

## Группировка и аналитика

### Группировка по измерению

```bash
# Группировка по этажам
ekahau-bom project.esx --group-by floor

# Группировка по производителям
ekahau-bom project.esx --group-by vendor

# Группировка по моделям
ekahau-bom project.esx --group-by model

# Группировка по цветам
ekahau-bom project.esx --group-by color
```

### Группировка по тегам

```bash
ekahau-bom project.esx --group-by tag --tag-key "Location"
```

### Комбинирование с фильтрацией

```bash
# Группировка Cisco AP по этажам
ekahau-bom project.esx \
  --filter-vendor "Cisco" \
  --group-by floor
```

---

## Форматы экспорта

### Экспорт CSV

Формат по умолчанию. Создает несколько файлов:

- `project_access_points.csv` - Агрегированный список AP
- `project_access_points_detailed.csv` - Отдельные AP с параметрами установки
- `project_antennas.csv` - Список антенн
- `project_analytics.csv` - Данные аналитики (если доступны)

**Лучше всего для:**
- Импорта в другие инструменты
- Импорта в базы данных
- Простого анализа в таблицах

### Экспорт Excel

Профессиональная книга с несколькими листами:

**Листы:**
- Summary (Сводка)
- Access Points (Точки доступа)
- AP Installation Details (Детали установки AP)
- Antennas (Антенны)
- By Floor (По этажам) (с диаграммой)
- By Color (По цветам) (с диаграммой)
- By Vendor (По производителям) (с диаграммой)
- By Model (По моделям) (с диаграммой)
- Radio Analytics (Аналитика радио) (если данные доступны)
- Mounting Analytics (Аналитика монтажа) (если данные доступны)
- Cost Breakdown (Разбивка стоимости) (если использовался --calculate-cost)

**Лучше всего для:**
- Презентаций клиентам
- Закупок
- Документации проекта
- Профессиональных отчетов

### Экспорт HTML

Интерактивный веб-отчет:

**Возможности:**
- Адаптивный дизайн
- Визуализации Chart.js
- Сортируемые таблицы
- Подходит для печати
- Автономный (без внешних файлов)

**Лучше всего для:**
- Отправки по email
- Публикации в веб
- Презентаций
- Быстрого просмотра

### Экспорт JSON

Машиночитаемый формат:

**Структура:**
```json
{
  "metadata": {...},
  "summary": {...},
  "access_points": {
    "aggregated": [...],
    "details": [...]
  },
  "antennas": [...],
  "radio_analytics": {...},
  "mounting_analytics": {...}
}
```

**Лучше всего для:**
- Интеграций с API
- Автоматизированных рабочих процессов
- Пользовательской обработки
- Конвейеров данных

---

## Расчет стоимости

### Базовый расчет стоимости

```bash
ekahau-bom project.esx --calculate-cost
```

Использует ценообразование по умолчанию из `config/pricing.yaml`.

### Пользовательская скидка

```bash
# Применить скидку 15%
ekahau-bom project.esx --calculate-cost --discount 15
```

### Отключение объемных скидок

```bash
ekahau-bom project.esx --calculate-cost --no-volume-discounts
```

### Настройка ценообразования

Отредактируйте `config/pricing.yaml`:

```yaml
access_points:
  Cisco:
    C9120AXI: 850.00
    C9130AXI: 1200.00
  Aruba:
    AP-515: 750.00

volume_discounts:
  - min_quantity: 50
    discount_percent: 10.0
```

---

## Расширенное использование

### Пользовательская конфигурация цветов

Создайте файл пользовательских цветов:

```yaml
# my_colors.yaml
"#FFE600": "Желтый"
"#FF0000": "Красный"
"#CUSTOM": "Пользовательский цвет"
```

Используйте его:

```bash
ekahau-bom project.esx --colors-config my_colors.yaml
```

### Рабочий процесс для нескольких проектов

Обработка нескольких проектов:

```bash
for project in projects/*.esx; do
  ekahau-bom "$project" --output-dir "reports/$(basename $project .esx)/"
done
```

### Интеграция с CI/CD

```yaml
# Пример GitHub Actions
- name: Generate BOM
  run: |
    python EkahauBOM.py project.esx --format excel,html

- name: Upload Reports
  uses: actions/upload-artifact@v2
  with:
    name: reports
    path: output/
```

---

## Устранение неполадок

### Распространенные проблемы

**Проблема: "File not found" (Файл не найден)**
```
Решение: Проверьте путь к файлу и убедитесь в наличии расширения .esx
```

**Проблема: "Invalid .esx file" (Недействительный файл .esx)**
```
Решение: Файл может быть поврежден. Попробуйте повторно экспортировать из Ekahau
```

**Проблема: "No access points found" (Точки доступа не найдены)**
```
Решение: Убедитесь, что AP помечены как "mine" в Ekahau (а не survey/neighbor AP)
```

**Проблема: "Tags not working" (Теги не работают)**
```
Решение: Теги требуют Ekahau v10.2+. Старые проекты не содержат tagKeys.json
```

**Проблема: "Missing prices for equipment" (Отсутствуют цены на оборудование)**
```
Решение: Добавьте оборудование в config/pricing.yaml или используйте без --calculate-cost
```

### Режим отладки

```bash
# Включить подробное логирование
ekahau-bom project.esx --verbose --log-file debug.log

# Проверить файл логов для детальной информации
cat debug.log
```

### Советы по производительности

**Большие проекты (500+ AP):**
- Используйте формат CSV для наиболее быстрой обработки
- Генерация Excel занимает больше времени из-за диаграмм
- HTML медленнее для очень больших наборов данных

**Использование памяти:**
- Проекты до 1000 AP: < 500МБ
- Очень большие проекты могут потребовать закрытия других приложений

---

## Советы и лучшие практики

### Для Wi-Fi инженеров

1. **Используйте теги в Ekahau** для лучшей организации (Расположение, Зона, Тип)
2. **Цветовое кодирование AP** по типу или производителю для визуальной ясности
3. **Экспорт в Excel** для профессиональных презентаций клиентам
4. **Включайте данные монтажа** в отчеты для монтажных бригад

### Для отделов закупок

1. **Используйте расчет стоимости** для генерации точных предложений
2. **Фильтрация по производителю** для создания отдельных заказов на закупку
3. **Группировка по этажам** для отслеживания затрат по зданиям
4. **Экспорт в CSV** для простого импорта в системы закупок

### Для монтажных бригад

1. **Экспорт детального CSV** для инструкций по монтажу
2. **Включайте данные азимута/наклона** в отчеты Excel
3. **Группировка по этажам** для организации установки по уровням
4. **Печать HTML отчетов** для справки на месте

### Для руководителей проектов

1. **Используйте экспорт HTML** для презентаций заинтересованным сторонам
2. **Отслеживайте изменения** сравнивая экспорты из разных итераций проектирования
3. **Архивируйте отчеты Excel** для документации проекта
4. **Используйте JSON** для интеграции с инструментами управления проектами

---

## Примеры

### Пример 1: Отчет для закупок

```bash
ekahau-bom office_building.esx \
  --format excel \
  --calculate-cost \
  --discount 12 \
  --output-dir procurement/
```

### Пример 2: Пакет для установки

```bash
ekahau-bom warehouse.esx \
  --format csv,excel,html \
  --group-by floor \
  --output-dir installation_docs/
```

### Пример 3: Отчет по фильтрованному производителю

```bash
ekahau-bom campus.esx \
  --filter-vendor "Cisco" \
  --filter-floor "Здание А*" \
  --format excel \
  --output-dir cisco_quote/
```

### Пример 4: Только аналитика

```bash
ekahau-bom project.esx \
  --format json \
  --group-by vendor \
  --output-dir analytics/
```

---

## Поддержка и ресурсы

- **Документация**: См. README.ru.md для обзора функций
- **Проблемы**: https://github.com/nimbo78/EkahauBOM/issues
- **Обсуждения**: https://github.com/nimbo78/EkahauBOM/discussions
- **Telegram**: [@htechno](https://t.me/htechno)

---

**Версия**: 2.4.0
**Последнее обновление**: 2024

**Автор**: Pavel Semenischev @htechno
