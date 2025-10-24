# План добавления фильтрации и группировки по цветам и тегам

## Дата: 2025-10-24
## Версия плана: 2.1

---

## Техническая возможность

### ✅ Подтверждено: Ekahau хранит все необходимые данные

**Источники данных в .esx файле:**

1. **Теги (Tags)**
   - Файл: `accessPoints.json` → `tags[]` массив с `tagKeyId` и `value`
   - Файл: `tagKeys.json` → определения тегов с `key` (имя) и `id`
   - Формат: key-value пары (например, "Location": "Building A")
   - Доступны с: Ekahau v10.2+

2. **Цвета (Colors)**
   - Файл: `accessPoints.json` → поле `color`
   - Формат: HEX код (например, "#FFE600")
   - Статус: ✅ Уже реализовано в v2.0.0

3. **Этажи (Floors)**
   - Файл: `accessPoints.json` → `location.floorPlanId`
   - Файл: `floorPlans.json` → детали этажей
   - Статус: ✅ Уже реализовано в v2.0.0

---

## Где в плане это реализуется

### Основные фазы для реализации:

#### 🔴 Фаза 5.1: Группировка и агрегация данных (ВЫСОКИЙ приоритет)
**Время:** 3-4 дня
**Сложность:** Средняя

**Задачи:**
- [ ] Группировка по тегам с подсчетом
- [ ] Группировка по цветам с подсчетом
- [ ] Группировка по этажам (улучшение текущей)
- [ ] Комбинированная группировка (например, по этажу + цвету)
- [ ] Процентное распределение для каждой группы
- [ ] Сводная таблица (pivot table) по всем измерениям

#### 🔴 Фаза 6.1: CLI фильтрация (ВЫСОКИЙ приоритет)
**Время:** 2-3 дня
**Сложность:** Средняя

**Задачи:**
- [ ] `--filter-floor "Floor 1,Floor 2"` - фильтр по этажам
- [ ] `--filter-color "Yellow,Red"` - фильтр по цветам
- [ ] `--filter-tag "Location:Building A"` - фильтр по тегам
- [ ] `--filter-vendor "Cisco,Aruba"` - фильтр по вендорам
- [ ] Комбинирование фильтров (AND/OR логика)
- [ ] `--exclude-*` опции для исключения

#### 🟠 Фаза 8.6: Извлечение тегов (СРЕДНИЙ приоритет)
**Время:** 2 дня
**Сложность:** Низкая-Средняя

**Задачи:**
- [ ] Парсинг `tagKeys.json`
- [ ] Связывание тегов с точками доступа
- [ ] Модель данных для тегов
- [ ] Включение тегов в экспорт

---

## Детальный план реализации

### Этап 1: Модели и парсинг (2 дня)

#### 1.1 Обновить модели данных

**Файл:** `ekahau_bom/models.py`

```python
@dataclass
class Tag:
    """Represents a tag key-value pair."""
    key: str          # Tag name (e.g., "Location")
    value: str        # Tag value (e.g., "Building A")
    tag_key_id: str   # UUID reference

@dataclass
class TagKey:
    """Represents a tag key definition."""
    id: str
    key: str

@dataclass
class AccessPoint:
    """Extended with tags support."""
    vendor: str
    model: str
    color: Optional[str]
    floor_name: str
    tags: list[Tag] = field(default_factory=list)  # NEW
    mine: bool = True
    floor_id: Optional[str] = None
```

#### 1.2 Обновить parser.py

**Новый метод:**
```python
def get_tag_keys(self) -> dict[str, Any]:
    """Get tag keys data from the project."""
    return self._read_json("tagKeys.json")
```

**Обновить константы:**
```python
# ekahau_bom/constants.py
ESX_TAG_KEYS_FILE = "tagKeys.json"
```

---

### Этап 2: Процессор тегов (1 день)

#### 2.1 Создать TagProcessor

**Файл:** `ekahau_bom/processors/tags.py`

```python
class TagProcessor:
    """Process tags data from Ekahau project."""

    def __init__(self, tag_keys_data: dict[str, Any]):
        """Build tag key lookup dictionary."""
        self.tag_keys_map = {
            tk["id"]: tk["key"]
            for tk in tag_keys_data.get("tagKeys", [])
        }

    def process_ap_tags(self, ap_tags: list[dict]) -> list[Tag]:
        """Convert AP tags to Tag objects."""
        tags = []
        for tag_data in ap_tags:
            tag_key_id = tag_data.get("tagKeyId")
            value = tag_data.get("value", "")

            key = self.tag_keys_map.get(tag_key_id, "Unknown")

            tags.append(Tag(
                key=key,
                value=value,
                tag_key_id=tag_key_id
            ))
        return tags
```

#### 2.2 Обновить AccessPointProcessor

**Интеграция тегов:**
```python
def __init__(self, color_database: dict[str, str], tag_processor: TagProcessor):
    self.color_database = color_database
    self.tag_processor = tag_processor

def _process_single_ap(self, ap_data, floors):
    # ... existing code ...

    # Process tags
    tags = []
    if "tags" in ap_data:
        tags = self.tag_processor.process_ap_tags(ap_data["tags"])

    return AccessPoint(
        vendor=vendor,
        model=model,
        color=color,
        floor_name=floor_name,
        tags=tags,  # NEW
        mine=ap_data.get("mine", True),
        floor_id=floor_id
    )
```

---

### Этап 3: Группировка и аналитика (2 дня)

#### 3.1 Создать модуль группировки

**Файл:** `ekahau_bom/analytics.py`

```python
from collections import Counter, defaultdict
from typing import Callable

class GroupingAnalytics:
    """Analytics and grouping for project data."""

    @staticmethod
    def group_by_floor(access_points: list[AccessPoint]) -> dict[str, int]:
        """Group APs by floor with counts."""
        return Counter(ap.floor_name for ap in access_points)

    @staticmethod
    def group_by_color(access_points: list[AccessPoint]) -> dict[str, int]:
        """Group APs by color with counts."""
        return Counter(ap.color or "No Color" for ap in access_points)

    @staticmethod
    def group_by_tag(access_points: list[AccessPoint], tag_key: str) -> dict[str, int]:
        """Group APs by specific tag key."""
        tag_values = []
        for ap in access_points:
            for tag in ap.tags:
                if tag.key == tag_key:
                    tag_values.append(tag.value)
                    break
            else:
                tag_values.append(f"No {tag_key}")
        return Counter(tag_values)

    @staticmethod
    def group_by_vendor(access_points: list[AccessPoint]) -> dict[str, int]:
        """Group APs by vendor with counts."""
        return Counter(ap.vendor for ap in access_points)

    @staticmethod
    def multi_dimensional_grouping(
        access_points: list[AccessPoint],
        dimensions: list[str]
    ) -> dict[tuple, int]:
        """Multi-dimensional grouping (e.g., floor + color + vendor)."""
        groups = defaultdict(int)

        for ap in access_points:
            key = []
            for dim in dimensions:
                if dim == "floor":
                    key.append(ap.floor_name)
                elif dim == "color":
                    key.append(ap.color or "No Color")
                elif dim == "vendor":
                    key.append(ap.vendor)
                elif dim == "model":
                    key.append(ap.model)
                # Tags handled separately

            groups[tuple(key)] += 1

        return dict(groups)

    @staticmethod
    def calculate_percentages(counts: dict) -> dict[str, tuple[int, float]]:
        """Calculate percentages for each group."""
        total = sum(counts.values())
        return {
            key: (count, (count / total * 100) if total > 0 else 0)
            for key, count in counts.items()
        }
```

---

### Этап 4: CLI фильтрация (2 дня)

#### 4.1 Создать модуль фильтрации

**Файл:** `ekahau_bom/filters.py`

```python
from typing import Callable

class APFilter:
    """Filter access points by various criteria."""

    @staticmethod
    def by_floors(access_points: list[AccessPoint], floors: list[str]) -> list[AccessPoint]:
        """Filter by floor names."""
        if not floors:
            return access_points
        return [ap for ap in access_points if ap.floor_name in floors]

    @staticmethod
    def by_colors(access_points: list[AccessPoint], colors: list[str]) -> list[AccessPoint]:
        """Filter by colors."""
        if not colors:
            return access_points
        return [ap for ap in access_points if ap.color in colors]

    @staticmethod
    def by_vendors(access_points: list[AccessPoint], vendors: list[str]) -> list[AccessPoint]:
        """Filter by vendors."""
        if not vendors:
            return access_points
        return [ap for ap in access_points if ap.vendor in vendors]

    @staticmethod
    def by_tag(access_points: list[AccessPoint], tag_key: str, tag_values: list[str]) -> list[AccessPoint]:
        """Filter by tag key-value pairs."""
        if not tag_values:
            return access_points

        filtered = []
        for ap in access_points:
            for tag in ap.tags:
                if tag.key == tag_key and tag.value in tag_values:
                    filtered.append(ap)
                    break
        return filtered

    @staticmethod
    def apply_filters(
        access_points: list[AccessPoint],
        floors: list[str] = None,
        colors: list[str] = None,
        vendors: list[str] = None,
        tags: dict[str, list[str]] = None
    ) -> list[AccessPoint]:
        """Apply multiple filters (AND logic)."""
        result = access_points

        if floors:
            result = APFilter.by_floors(result, floors)
        if colors:
            result = APFilter.by_colors(result, colors)
        if vendors:
            result = APFilter.by_vendors(result, vendors)
        if tags:
            for tag_key, tag_values in tags.items():
                result = APFilter.by_tag(result, tag_key, tag_values)

        return result
```

#### 4.2 Обновить CLI

**Файл:** `ekahau_bom/cli.py`

**Добавить аргументы:**
```python
# Filtering options
filter_group = parser.add_argument_group('filtering options')

filter_group.add_argument(
    '--filter-floor',
    type=str,
    help='Filter by floor names (comma-separated): "Floor 1,Floor 2"'
)

filter_group.add_argument(
    '--filter-color',
    type=str,
    help='Filter by colors (comma-separated): "Yellow,Red,Blue"'
)

filter_group.add_argument(
    '--filter-vendor',
    type=str,
    help='Filter by vendors (comma-separated): "Cisco,Aruba"'
)

filter_group.add_argument(
    '--filter-tag',
    action='append',
    help='Filter by tag (format: "TagKey:TagValue"). Can be used multiple times.'
)

# Grouping options
group_group = parser.add_argument_group('grouping options')

group_group.add_argument(
    '--group-by',
    type=str,
    choices=['floor', 'color', 'vendor', 'tag'],
    help='Group results by specified dimension'
)

group_group.add_argument(
    '--tag-key',
    type=str,
    help='Tag key to use when --group-by tag is selected'
)
```

**Обновить process_project:**
```python
def process_project(
    esx_file: Path,
    output_dir: Path,
    colors_config: Path | None = None,
    filter_floors: list[str] = None,
    filter_colors: list[str] = None,
    filter_vendors: list[str] = None,
    filter_tags: dict[str, list[str]] = None,
    group_by: str = None,
    tag_key: str = None
) -> int:
    # ... existing parsing code ...

    # Process tags
    tag_keys_data = parser.get_tag_keys()
    tag_processor = TagProcessor(tag_keys_data)

    # Process APs with tags
    ap_processor = AccessPointProcessor(color_db, tag_processor)
    access_points = ap_processor.process(access_points_data, floors)

    # Apply filters if specified
    if any([filter_floors, filter_colors, filter_vendors, filter_tags]):
        access_points = APFilter.apply_filters(
            access_points,
            floors=filter_floors,
            colors=filter_colors,
            vendors=filter_vendors,
            tags=filter_tags
        )
        logger.info(f"Filtered to {len(access_points)} access points")

    # Apply grouping if specified
    if group_by:
        analytics = GroupingAnalytics()
        if group_by == 'floor':
            grouped = analytics.group_by_floor(access_points)
        elif group_by == 'color':
            grouped = analytics.group_by_color(access_points)
        elif group_by == 'vendor':
            grouped = analytics.group_by_vendor(access_points)
        elif group_by == 'tag' and tag_key:
            grouped = analytics.group_by_tag(access_points, tag_key)

        # Print grouped results
        percentages = analytics.calculate_percentages(grouped)
        logger.info("Grouping results:")
        for key, (count, pct) in percentages.items():
            logger.info(f"  {key}: {count} ({pct:.1f}%)")

    # ... rest of code ...
```

---

### Этап 5: Обновление экспортеров (1 день)

#### 5.1 Обновить CSV экспортер

**Включить теги в CSV:**
```python
def _export_access_points(self, access_points, project_name):
    # ... existing code ...

    # Header with tags
    writer.writerow(["Vendor", "Model", "Floor", "Color", "Tags", "Quantity"])

    for (vendor, model, floor, color, tags_str), count in ap_counts.items():
        writer.writerow([vendor, model, floor, color or "", tags_str, count])
```

#### 5.2 Создать новые экспортеры для групп

**Файл:** `ekahau_bom/exporters/analytics_exporter.py`

```python
class AnalyticsExporter(BaseExporter):
    """Export analytics and groupings."""

    def export_grouped_data(
        self,
        grouped_data: dict,
        filename: str,
        dimension: str
    ) -> Path:
        """Export grouped data to CSV."""
        output_file = self.output_dir / filename

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, dialect='excel', quoting=csv.QUOTE_ALL)

            # Calculate percentages
            total = sum(grouped_data.values())

            # Write header
            writer.writerow([dimension.capitalize(), "Count", "Percentage"])

            # Write data
            for key, count in sorted(grouped_data.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total * 100) if total > 0 else 0
                writer.writerow([key, count, f"{percentage:.1f}%"])

        return output_file
```

---

## Примеры использования

### Фильтрация

```bash
# По этажам
python EkahauBOM.py project.esx --filter-floor "Floor 1,Floor 2"

# По цветам
python EkahauBOM.py project.esx --filter-color "Yellow,Red"

# По вендорам
python EkahauBOM.py project.esx --filter-vendor "Cisco,Aruba"

# По тегам
python EkahauBOM.py project.esx --filter-tag "Location:Building A" --filter-tag "Zone:Public"

# Комбинированные фильтры
python EkahauBOM.py project.esx \
  --filter-floor "Floor 1" \
  --filter-color "Yellow" \
  --filter-vendor "Cisco"
```

### Группировка

```bash
# Группировка по этажам
python EkahauBOM.py project.esx --group-by floor

# Группировка по цветам
python EkahauBOM.py project.esx --group-by color

# Группировка по вендорам
python EkahauBOM.py project.esx --group-by vendor

# Группировка по тегу
python EkahauBOM.py project.esx --group-by tag --tag-key Location
```

### Комбинирование

```bash
# Фильтр + Группировка
python EkahauBOM.py project.esx \
  --filter-floor "Floor 1,Floor 2" \
  --group-by color \
  --output-dir reports/
```

---

## Обновленная структура проекта

```
EkahauBOM/
├── ekahau_bom/
│   ├── models.py              # +Tag, +TagKey models
│   ├── parser.py              # +get_tag_keys()
│   ├── processors/
│   │   ├── access_points.py   # Updated with tags
│   │   ├── antennas.py
│   │   └── tags.py            # NEW: TagProcessor
│   ├── exporters/
│   │   ├── csv_exporter.py    # Updated with tags
│   │   └── analytics_exporter.py  # NEW: Grouped exports
│   ├── analytics.py           # NEW: GroupingAnalytics
│   ├── filters.py             # NEW: APFilter
│   └── cli.py                 # Updated with filter/group args
```

---

## Интеграция в DEVELOPMENT_PLAN.md

### Обновленная Фаза 5: Расширенная аналитика

**Приоритет:** ВЫСОКИЙ ↑ (было СРЕДНИЙ)
**Время:** 3-4 дня (было 2-3 дня)

**5.1 Группировка и агрегация данных**
- [x] ~~Группировка по этажам с подсчетом~~ (базово есть)
- [ ] **Группировка по цветам с подсчетом** ⭐ НОВОЕ
- [ ] **Группировка по тегам** ⭐ НОВОЕ
- [ ] Группировка по вендорам
- [ ] Комбинированная группировка (multi-dimensional)
- [ ] Процентное распределение
- [ ] Сводная таблица (pivot table)

**5.2 Расчет стоимости** (без изменений)

### Обновленная Фаза 6: Расширенный CLI

**Приоритет:** ВЫСОКИЙ ↑
**Время:** 3-4 дня (было 2-3 дня)

**6.1 Аргументы командной строки**
- [ ] Множественные входные файлы
- [ ] Выбор формата вывода
- [ ] **Фильтрация по этажам** ⭐ НОВОЕ
- [ ] **Фильтрация по цветам** ⭐ НОВОЕ
- [ ] **Фильтрация по вендорам** ⭐ НОВОЕ
- [ ] **Фильтрация по тегам** ⭐ НОВОЕ
- [ ] **Группировка через CLI** ⭐ НОВОЕ
- [ ] Сортировка
- [ ] Конфигурационный файл

### Новая Фаза 8.6: Теги

**Приоритет:** СРЕДНИЙ
**Время:** 2 дня

**8.6 Теги и метаданные**
- [ ] **Парсинг tagKeys.json** ⭐ НОВОЕ
- [ ] **Связывание тегов с AP** ⭐ НОВОЕ
- [ ] **Включение тегов в экспорт** ⭐ НОВОЕ
- [ ] **Фильтрация по тегам** ⭐ НОВОЕ
- [ ] **Группировка по тегам** ⭐ НОВОЕ

---

## Последовательность реализации

### ✅ Рекомендуемый подход - Итерация 2.1 (Новая)

**Фокус:** Фильтрация и группировка
**Время:** 1-1.5 недели

**День 1-2: Теги и модели**
1. Обновить models.py (Tag, TagKey)
2. Обновить parser.py (get_tag_keys)
3. Создать TagProcessor
4. Обновить AccessPointProcessor

**День 3-4: Фильтрация**
1. Создать filters.py (APFilter)
2. Обновить CLI с filter аргументами
3. Интегрировать в process_project
4. Тестирование фильтрации

**День 5-6: Группировка**
1. Создать analytics.py (GroupingAnalytics)
2. Обновить CLI с group-by аргументами
3. Создать analytics_exporter.py
4. Тестирование группировки

**День 7: Финализация**
1. Обновить экспортеры (теги в CSV)
2. Обновить README с примерами
3. Unit тесты для новых модулей
4. Документация

**Результат:** Полная поддержка фильтрации и группировки по этажам, цветам и тегам

---

## Зависимости

**Что уже есть (v2.0.0):**
- ✅ Модульная архитектура
- ✅ Парсер .esx файлов
- ✅ Обработка цветов
- ✅ Обработка этажей
- ✅ CLI инфраструктура

**Что нужно добавить:**
- [ ] Парсинг tagKeys.json
- [ ] Модели для тегов
- [ ] Процессор тегов
- [ ] Модуль фильтрации
- [ ] Модуль группировки/аналитики
- [ ] Обновленные экспортеры

**Новые зависимости:** Нет (используем стандартную библиотеку)

---

## Риски и митигация

### Риск 1: Теги могут отсутствовать в старых проектах
**Митигация:**
- Graceful handling если tagKeys.json отсутствует
- Пустой список тегов по умолчанию
- Предупреждение в логах

### Риск 2: Производительность при множественных фильтрах
**Митигация:**
- Использовать list comprehensions (быстро)
- Применять фильтры последовательно (избегать копирования)
- Для больших проектов - показывать прогресс

### Риск 3: Сложность комбинированных фильтров
**Митигация:**
- Четкая документация с примерами
- Логирование примененных фильтров
- Показывать количество отфильтрованных AP

---

## Следующие шаги

После реализации фильтрации/группировки можно перейти к:

1. **Итерация 1 (MVP+):** Excel экспорт с группированными листами
2. **Итерация 2 (Professional):** HTML отчеты с диаграммами по группам
3. **Итерация 3 (Advanced):** Расширенная аналитика и расчет стоимости

---

**Версия плана:** 2.1
**Дата:** 2025-10-24
**Статус:** Готов к реализации
**Приоритет:** ВЫСОКИЙ
