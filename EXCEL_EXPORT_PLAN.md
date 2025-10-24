# План реализации Excel экспорта (Iteration 2)

## Дата создания: 2025-10-24
## Версия плана: 2.2
## Статус: 🎯 Готов к реализации
## Приоритет: ВЫСОКИЙ

---

## Цель итерации

Создать профессиональный Excel экспортер с множественными листами, форматированием, диаграммами и полной интеграцией с аналитикой из v2.1.0.

## Основные возможности

### 1. Множественные листы (Worksheets)
- **Summary** - Общая статистика проекта
- **Access Points** - Детальная таблица всех точек доступа с тегами
- **Antennas** - Таблица антенн
- **By Floor** - Группировка по этажам
- **By Color** - Группировка по цветам
- **By Vendor** - Группировка по вендорам
- **By Model** - Группировка по моделям
- **By Tag** - Группировка по конкретному тегу (опционально)

### 2. Профессиональное форматирование
- Автоширина колонок
- Заголовки с цветом и жирным шрифтом
- Замороженные строки заголовков (freeze panes)
- Автофильтры для всех таблиц
- Границы ячеек
- Условное форматирование для цветов AP

### 3. Диаграммы и визуализация
- Pie chart: Распределение по вендорам
- Bar chart: Количество AP по этажам
- Bar chart: Топ 10 моделей
- Bar chart: Распределение по цветам

### 4. CLI интеграция
- Аргумент `--format` для выбора формата экспорта
- Поддержка множественных форматов: `csv`, `excel`, `csv,excel`

---

## Детальный план реализации

### День 1: Базовый Excel экспорт и форматирование

#### 1.1 Настройка зависимостей

**Файл:** `requirements.txt`

Добавить:
```
openpyxl>=3.1.0
```

**Выбор библиотеки:**
- **openpyxl** - отличная поддержка форматирования и диаграмм, активно поддерживается
- Альтернатива: xlsxwriter (быстрее, но не умеет читать существующие файлы)

#### 1.2 Создать базовый Excel экспортер

**Файл:** `ekahau_bom/exporters/excel_exporter.py`

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Excel exporter with advanced formatting and charts."""

import logging
from pathlib import Path
from collections import Counter

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.chart import PieChart, BarChart, Reference

from .base import BaseExporter
from ..models import ProjectData, AccessPoint, Antenna

logger = logging.getLogger(__name__)


class ExcelExporter(BaseExporter):
    """Export project data to Excel files with formatting and charts.

    Creates Excel workbook with multiple sheets:
    - Summary: Project overview and statistics
    - Access Points: Detailed AP list with tags
    - Antennas: Antenna list
    - By Floor: Grouped by floor
    - By Color: Grouped by color
    - By Vendor: Grouped by vendor
    - By Model: Grouped by model
    """

    @property
    def format_name(self) -> str:
        """Human-readable name of the export format."""
        return "Excel"

    def export(self, project_data: ProjectData) -> list[Path]:
        """Export project data to Excel file.

        Args:
            project_data: Processed project data to export

        Returns:
            List with single Excel file path

        Raises:
            IOError: If file writing fails
        """
        output_file = self._get_output_filename(
            project_data.project_name,
            f"{project_data.project_name}.xlsx"
        )

        # Create workbook
        wb = Workbook()

        # Remove default sheet
        if 'Sheet' in wb.sheetnames:
            wb.remove(wb['Sheet'])

        # Create sheets
        self._create_summary_sheet(wb, project_data)
        self._create_access_points_sheet(wb, project_data.access_points)
        self._create_antennas_sheet(wb, project_data.antennas)
        self._create_grouped_sheets(wb, project_data.access_points)

        # Save workbook
        wb.save(output_file)

        logger.info(f"Excel file created: {output_file}")
        self.log_export_success([output_file])

        return [output_file]
```

#### 1.3 Реализовать форматирование

Добавить в ExcelExporter:

```python
    # Стили для заголовков
    HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
    HEADER_FILL = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    HEADER_ALIGNMENT = Alignment(horizontal="center", vertical="center")

    # Границы
    THIN_BORDER = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    def _apply_header_style(self, ws, row: int = 1):
        """Apply header style to first row."""
        for cell in ws[row]:
            cell.font = self.HEADER_FONT
            cell.fill = self.HEADER_FILL
            cell.alignment = self.HEADER_ALIGNMENT
            cell.border = self.THIN_BORDER

    def _auto_size_columns(self, ws):
        """Auto-size all columns based on content."""
        for column in ws.columns:
            max_length = 0
            column_letter = get_column_letter(column[0].column)

            for cell in column:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except:
                    pass

            adjusted_width = min(max_length + 2, 50)  # Max 50 chars
            ws.column_dimensions[column_letter].width = adjusted_width

    def _apply_autofilter(self, ws):
        """Apply autofilter to the sheet."""
        ws.auto_filter.ref = ws.dimensions

    def _freeze_header(self, ws, row: int = 2):
        """Freeze header row."""
        ws.freeze_panes = ws[f'A{row}']
```

---

### День 2: Листы с данными (Summary, APs, Antennas)

#### 2.1 Summary лист

```python
    def _create_summary_sheet(self, wb: Workbook, project_data: ProjectData):
        """Create summary sheet with project statistics."""
        ws = wb.create_sheet("Summary", 0)

        # Project info
        ws['A1'] = "Project Summary"
        ws['A1'].font = Font(bold=True, size=14)

        ws['A3'] = "Project Name:"
        ws['B3'] = project_data.project_name
        ws['A4'] = "Total Access Points:"
        ws['B4'] = len(project_data.access_points)
        ws['A5'] = "Total Antennas:"
        ws['B5'] = len(project_data.antennas)

        # Statistics by vendor
        ws['A7'] = "By Vendor"
        ws['A7'].font = Font(bold=True, size=12)

        vendor_counts = Counter(ap.vendor for ap in project_data.access_points)
        row = 8
        ws['A' + str(row)] = "Vendor"
        ws['B' + str(row)] = "Count"
        self._apply_header_style(ws, row)

        for vendor, count in sorted(vendor_counts.items()):
            row += 1
            ws[f'A{row}'] = vendor
            ws[f'B{row}'] = count

        # Add more statistics...

        self._auto_size_columns(ws)
```

#### 2.2 Access Points лист

```python
    def _create_access_points_sheet(self, wb: Workbook, access_points: list[AccessPoint]):
        """Create detailed access points sheet."""
        ws = wb.create_sheet("Access Points")

        # Headers
        headers = ["Vendor", "Model", "Floor", "Color", "Tags", "Quantity"]
        ws.append(headers)
        self._apply_header_style(ws)

        # Group and count APs
        ap_tuples = [
            (ap.vendor, ap.model, ap.floor_name, ap.color,
             frozenset(str(tag) for tag in ap.tags))
            for ap in access_points
        ]
        ap_counts = Counter(ap_tuples)

        # Write data
        for (vendor, model, floor, color, tags), count in sorted(ap_counts.items()):
            tags_str = "; ".join(sorted(tags)) if tags else ""
            ws.append([vendor, model, floor, color or "", tags_str, count])

        # Apply formatting
        self._auto_size_columns(ws)
        self._apply_autofilter(ws)
        self._freeze_header(ws)

        # Apply borders to all cells
        for row in ws.iter_rows(min_row=1, max_row=ws.max_row,
                                min_col=1, max_col=len(headers)):
            for cell in row:
                cell.border = self.THIN_BORDER
```

#### 2.3 Antennas лист

```python
    def _create_antennas_sheet(self, wb: Workbook, antennas: list[Antenna]):
        """Create antennas sheet."""
        ws = wb.create_sheet("Antennas")

        # Headers
        headers = ["Antenna Model", "Quantity"]
        ws.append(headers)
        self._apply_header_style(ws)

        # Count antennas
        antenna_names = [antenna.name for antenna in antennas]
        antenna_counts = Counter(antenna_names)

        # Write data
        for antenna_name, count in sorted(antenna_counts.items()):
            ws.append([antenna_name, count])

        # Apply formatting
        self._auto_size_columns(ws)
        self._apply_autofilter(ws)
        self._freeze_header(ws)
```

---

### День 3: Группировка (By Floor, By Color, By Vendor, By Model)

#### 3.1 Универсальный метод для группированных листов

```python
    def _create_grouped_sheet(
        self,
        wb: Workbook,
        sheet_name: str,
        grouped_data: dict[str, int],
        dimension_name: str
    ):
        """Create a grouped sheet with counts and percentages.

        Args:
            wb: Workbook
            sheet_name: Name of the sheet
            grouped_data: Dictionary with counts by dimension
            dimension_name: Name of the dimension (e.g., "Floor", "Vendor")
        """
        ws = wb.create_sheet(sheet_name)

        # Headers
        headers = [dimension_name, "Count", "Percentage"]
        ws.append(headers)
        self._apply_header_style(ws)

        # Calculate total
        total = sum(grouped_data.values())

        # Write data sorted by count (descending)
        for key, count in sorted(grouped_data.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total * 100) if total > 0 else 0
            ws.append([key, count, f"{percentage:.1f}%"])

        # Apply formatting
        self._auto_size_columns(ws)
        self._apply_autofilter(ws)
        self._freeze_header(ws)

        # Apply borders
        for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=3):
            for cell in row:
                cell.border = self.THIN_BORDER
```

#### 3.2 Создание всех группированных листов

```python
    def _create_grouped_sheets(self, wb: Workbook, access_points: list[AccessPoint]):
        """Create all grouped sheets."""
        from ..analytics import GroupingAnalytics

        analytics = GroupingAnalytics()

        # By Floor
        floor_data = analytics.group_by_floor(access_points)
        self._create_grouped_sheet(wb, "By Floor", floor_data, "Floor")

        # By Color
        color_data = analytics.group_by_color(access_points)
        self._create_grouped_sheet(wb, "By Color", color_data, "Color")

        # By Vendor
        vendor_data = analytics.group_by_vendor(access_points)
        self._create_grouped_sheet(wb, "By Vendor", vendor_data, "Vendor")

        # By Model
        model_data = analytics.group_by_model(access_points)
        self._create_grouped_sheet(wb, "By Model", model_data, "Model")
```

---

### День 4: Диаграммы и условное форматирование

#### 4.1 Добавление диаграмм

```python
    def _add_pie_chart(self, ws, data_range: str, title: str, position: str = "E2"):
        """Add pie chart to worksheet.

        Args:
            ws: Worksheet
            data_range: Range of data (e.g., "A2:B10")
            title: Chart title
            position: Cell position for chart
        """
        chart = PieChart()
        chart.title = title
        chart.style = 10
        chart.height = 10  # default is 7.5
        chart.width = 15   # default is 15

        # Data for chart
        labels = Reference(ws, min_col=1, min_row=2, max_row=ws.max_row)
        data = Reference(ws, min_col=2, min_row=1, max_row=ws.max_row)

        chart.add_data(data, titles_from_data=True)
        chart.set_categories(labels)

        ws.add_chart(chart, position)

    def _add_bar_chart(self, ws, data_range: str, title: str, position: str = "E2"):
        """Add bar chart to worksheet."""
        chart = BarChart()
        chart.type = "col"  # Column chart
        chart.title = title
        chart.style = 10
        chart.height = 10
        chart.width = 15

        # Data for chart
        labels = Reference(ws, min_col=1, min_row=2, max_row=ws.max_row)
        data = Reference(ws, min_col=2, min_row=1, max_row=ws.max_row)

        chart.add_data(data, titles_from_data=True)
        chart.set_categories(labels)

        ws.add_chart(chart, position)
```

#### 4.2 Добавление диаграмм к группированным листам

Обновить `_create_grouped_sheet`:

```python
    def _create_grouped_sheet(
        self,
        wb: Workbook,
        sheet_name: str,
        grouped_data: dict[str, int],
        dimension_name: str,
        add_chart: bool = True
    ):
        """Create a grouped sheet with counts, percentages, and optional chart."""
        ws = wb.create_sheet(sheet_name)

        # ... existing code ...

        # Add chart if requested
        if add_chart and len(grouped_data) > 0:
            if dimension_name == "Vendor":
                self._add_pie_chart(ws, "", f"Distribution by {dimension_name}", "E2")
            else:
                self._add_bar_chart(ws, "", f"Count by {dimension_name}", "E2")
```

#### 4.3 Условное форматирование для цветов

```python
    def _apply_conditional_formatting(self, ws, color_column: int = 4):
        """Apply conditional formatting for AP colors.

        Args:
            ws: Worksheet
            color_column: Column number with color data (1-indexed)
        """
        from openpyxl.formatting.rule import Rule
        from openpyxl.styles.differential import DifferentialStyle

        # Color mappings from config
        color_map = {
            "Yellow": "FFE600",
            "Orange": "FF8500",
            "Red": "FF0000",
            "Blue": "0000FF",
            # Add more colors
        }

        for color_name, hex_color in color_map.items():
            fill = PatternFill(start_color=hex_color, end_color=hex_color, fill_type="solid")
            dxf = DifferentialStyle(fill=fill)
            rule = Rule(type="containsText", operator="containsText",
                       text=color_name, dxf=dxf)
            rule.formula = [f'NOT(ISERROR(SEARCH("{color_name}",${get_column_letter(color_column)}2)))']

            ws.conditional_formatting.add(
                f'{get_column_letter(color_column)}2:{get_column_letter(color_column)}{ws.max_row}',
                rule
            )
```

---

### День 5: CLI интеграция и тестирование

#### 5.1 Обновить CLI

**Файл:** `ekahau_bom/cli.py`

Добавить аргумент:

```python
parser.add_argument(
    '--format',
    type=str,
    default='csv',
    help='Export format(s): csv, excel, or csv,excel (default: csv)'
)
```

Обновить `process_project`:

```python
def process_project(
    esx_file: Path,
    output_dir: Path,
    colors_config: Path | None = None,
    export_formats: list[str] = None,
    # ... other args ...
) -> int:
    # ... existing code ...

    # Default to CSV if no format specified
    if not export_formats:
        export_formats = ['csv']

    # Export to requested formats
    from .exporters.csv_exporter import CSVExporter
    from .exporters.excel_exporter import ExcelExporter

    exporters = {
        'csv': CSVExporter(output_dir),
        'excel': ExcelExporter(output_dir)
    }

    for format_name in export_formats:
        if format_name in exporters:
            exporter = exporters[format_name]
            exporter.export(project_data)
        else:
            logger.warning(f"Unknown export format: {format_name}")
```

#### 5.2 Обновить главную функцию

```python
def main() -> int:
    # ... existing code ...

    # Parse export formats
    export_formats = [f.strip().lower() for f in parsed_args.format.split(',')]

    return process_project(
        # ... other args ...
        export_formats=export_formats
    )
```

#### 5.3 Создать тесты

**Файл:** `tests/test_excel_exporter.py`

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Unit tests for Excel exporter."""

import pytest
from pathlib import Path
from ekahau_bom.exporters.excel_exporter import ExcelExporter
from ekahau_bom.models import ProjectData, AccessPoint, Antenna, Tag


@pytest.fixture
def sample_project_data():
    """Create sample project data."""
    aps = [
        AccessPoint("Cisco", "AP-515", "Yellow", "Floor 1",
                   tags=[Tag("Location", "Building A", "1")]),
        AccessPoint("Cisco", "AP-635", "Red", "Floor 2", tags=[]),
        AccessPoint("Aruba", "AP-515", "Yellow", "Floor 1", tags=[]),
    ]
    antennas = [
        Antenna("ANT-2513P4M-N-R"),
        Antenna("ANT-2513P4M-N-R"),
    ]
    return ProjectData("Test Project", aps, antennas)


class TestExcelExporter:
    """Test ExcelExporter class."""

    def test_export_creates_file(self, sample_project_data, tmp_path):
        """Test that export creates Excel file."""
        exporter = ExcelExporter(tmp_path)
        files = exporter.export(sample_project_data)

        assert len(files) == 1
        assert files[0].exists()
        assert files[0].suffix == '.xlsx'

    def test_export_has_required_sheets(self, sample_project_data, tmp_path):
        """Test that Excel file has all required sheets."""
        from openpyxl import load_workbook

        exporter = ExcelExporter(tmp_path)
        files = exporter.export(sample_project_data)

        wb = load_workbook(files[0])
        sheet_names = wb.sheetnames

        assert "Summary" in sheet_names
        assert "Access Points" in sheet_names
        assert "Antennas" in sheet_names
        assert "By Floor" in sheet_names
        assert "By Vendor" in sheet_names
```

---

### День 6-7: Доработка и документация

#### 6.1 Дополнительные улучшения

- [ ] Добавить лист "By Tag" если используется --group-by tag
- [ ] Улучшить Summary с дополнительной статистикой
- [ ] Добавить логотип/изображение на Summary лист (опционально)
- [ ] Оптимизация для больших проектов (>1000 AP)

#### 6.2 Обновить документацию

**README.md:**

Добавить примеры:

```bash
# Export to Excel
python EkahauBOM.py project.esx --format excel

# Export to both CSV and Excel
python EkahauBOM.py project.esx --format csv,excel

# Excel with filtering
python EkahauBOM.py project.esx --format excel --filter-vendor "Cisco"
```

#### 6.3 Обновить requirements.txt

```
PyYAML>=6.0
openpyxl>=3.1.0
```

---

## Структура файлов

```
EkahauBOM/
├── ekahau_bom/
│   ├── exporters/
│   │   ├── base.py
│   │   ├── csv_exporter.py
│   │   └── excel_exporter.py      # NEW
│   └── cli.py                      # UPDATED: --format argument
├── tests/
│   └── test_excel_exporter.py     # NEW
├── requirements.txt                # UPDATED: +openpyxl
└── README.md                       # UPDATED: Excel examples
```

---

## Примеры использования

### Базовый Excel экспорт
```bash
python EkahauBOM.py project.esx --format excel
```

### Excel + CSV
```bash
python EkahauBOM.py project.esx --format csv,excel
```

### Excel с фильтрацией
```bash
python EkahauBOM.py project.esx \
  --format excel \
  --filter-floor "Floor 1,Floor 2" \
  --filter-vendor "Cisco"
```

### Excel с группировкой
```bash
python EkahauBOM.py project.esx \
  --format excel \
  --group-by vendor \
  --output-dir reports/
```

---

## Зависимости

**Что уже есть (v2.1.0):**
- ✅ Модульная архитектура экспортеров (BaseExporter)
- ✅ Группировка и аналитика (GroupingAnalytics)
- ✅ Поддержка тегов в моделях
- ✅ CLI инфраструктура

**Что нужно добавить:**
- [ ] openpyxl библиотека
- [ ] ExcelExporter класс
- [ ] --format CLI аргумент
- [ ] Интеграция с GroupingAnalytics
- [ ] Unit тесты

---

## Риски и митигация

### Риск 1: Производительность при больших проектах
**Митигация:**
- Использовать write_only режим openpyxl для больших файлов
- Ограничить количество диаграмм
- Оптимизировать форматирование

### Риск 2: Совместимость с Excel версиями
**Митигация:**
- Тестировать с разными версиями Excel
- Использовать стандартные возможности openpyxl
- Проверять на LibreOffice/Google Sheets

### Риск 3: Размер файлов
**Митигация:**
- Не хранить избыточные данные
- Использовать эффективное форматирование
- Предупреждать о больших проектах

---

## Метрики успеха

- ✅ Excel файл создается успешно
- ✅ Все 7+ листов присутствуют
- ✅ Диаграммы отображаются корректно
- ✅ Форматирование применяется правильно
- ✅ Файл открывается в Excel/LibreOffice
- ✅ Производительность: <5 сек для проекта с 500 AP
- ✅ Unit тесты покрывают основной функционал

---

## Следующие шаги после Iteration 2

1. **Iteration 3: HTML отчеты** - Интерактивные HTML с графиками
2. **Iteration 4: JSON экспорт** - Для интеграций
3. **Iteration 5: Advanced Analytics** - Расчет стоимости, метрики

---

**Версия плана:** 2.2
**Дата:** 2025-10-24
**Статус:** 🎯 Готов к реализации
**Приоритет:** ВЫСОКИЙ
**Оценка времени:** 1 неделя (5-7 дней)
