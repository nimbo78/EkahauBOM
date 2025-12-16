# Руководство разработчика EkahauBOM

Руководство для участников и разработчиков, работающих над EkahauBOM.

## Содержание

- [Начало работы](#начало-работы)
- [Архитектура проекта](#архитектура-проекта)
- [Веб-приложение](#веб-приложение) _(Новое в v3.4.0)_
- [Docker](#docker) _(Новое в v3.5.0)_
- [Настройка разработки](#настройка-разработки)
- [Стиль кода](#стиль-кода)
- [Тестирование](#тестирование)
- [Добавление функций](#добавление-функций)
- [Внесение вклада](#внесение-вклада)

---

## Начало работы

### Предварительные требования

- Python 3.7+
- Git
- pip и virtualenv (рекомендуется)

### Настройка разработки

```bash
# Клонировать репозиторий
git clone https://github.com/htechno/EkahauBOM.git
cd EkahauBOM

# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # В Windows: venv\Scripts\activate

# Установить зависимости
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Установить в режиме редактирования
pip install -e .
```

---

## Архитектура проекта

### Структура директорий

```
ekahau_bom/
├── cli.py              # Интерфейс командной строки (Click)
├── parser.py           # Парсер файлов .esx (ZIP + JSON)
├── models.py           # Модели данных (dataclasses)
├── constants.py        # Константы и значения по умолчанию
├── utils.py            # Вспомогательные функции
├── filters.py          # Логика фильтрации
├── analytics.py        # Аналитика и группировка
├── pricing.py          # Расчет стоимости
├── processors/         # Процессоры данных
│   ├── access_points.py
│   ├── antennas.py
│   ├── radios.py
│   └── tags.py
├── exporters/          # Форматы экспорта
│   ├── base.py         # Базовый класс экспортера
│   ├── csv_exporter.py
│   ├── excel_exporter.py
│   ├── html_exporter.py
│   └── json_exporter.py
├── visualizers/        # Генерация планов этажей
│   └── floor_plan_visualizer.py
└── comparison/         # Сравнение проектов (v3.6.0+)
    ├── models.py       # ComparisonResult, APChange, FieldChange
    ├── engine.py       # ComparisonEngine - основная логика
    ├── matchers.py     # NameMatcher, CoordinateMatcher, CombinedMatcher
    ├── visual_diff.py  # Визуализация различий на планах этажей
    └── exporters.py    # Экспортеры для отчётов сравнения
```

### Ключевые компоненты

**Parser** (`parser.py`)
- Обрабатывает чтение файлов .esx (ZIP архивы)
- Парсит JSON файлы внутри архива
- Контекстный менеджер для очистки ресурсов

**Models** (`models.py`)
- Классы данных для AccessPoint, Antenna, Radio, Tag и т.д.
- Типобезопасные структуры данных
- Неизменяемые, где это возможно

**Processors** (`processors/`)
- Преобразуют сырые данные в модели
- Обрабатывают специфичную логику производителей
- Обработка тегов для v10.2+

**Exporters** (`exporters/`)
- Базовый класс с общим функционалом
- Реализации для конкретных форматов
- Единообразный интерфейс

**Analytics** (`analytics.py`)
- Функции группировки
- Статистические вычисления
- Многомерный анализ

**Comparison** (`comparison/`) _(Новое в v3.6.0)_
- Сравнение двух .esx файлов проектов
- Обнаружение изменений AP: добавлено, удалено, изменено, перемещено, переименовано
- Множество стратегий сопоставления (имя, координаты, комбинированная)
- Генерация визуального сравнения на планах этажей
- Специализированные экспортеры для отчётов сравнения

---

### Архитектура модуля сравнения

Модуль сравнения сравнивает два проекта Ekahau и определяет изменения:

```
                         ┌─────────────────────────────────────┐
                         │  Обработка "Обновить существующий"  │
                         └─────────────────────────────────────┘
                                          │
Предыдущая версия (.esx) → Parser ────────┤
                                          ├→ ComparisonEngine → ComparisonResult
Новая версия (.esx) → Parser ─────────────┘                          │
                                                    ┌────────────────┼────────────────┐
                                                    ▼                ▼                ▼
                                              Exporters        Visual Diff      Вкладка сравнения
                                           (CSV/Excel/HTML)   (PNG + стрелки)    (Web UI)
```

**Ключевые классы:**

| Класс | Назначение |
|-------|------------|
| `ComparisonEngine` | Главная точка входа, оркестрирует сравнение |
| `ComparisonResult` | Контейнер результатов со всеми изменениями |
| `APChange` | Одно изменение AP (добавлено/удалено/изменено/перемещено/переименовано) |
| `FieldChange` | Отдельное изменение поля внутри AP |
| `NameMatcher` | Сопоставление AP по имени |
| `CoordinateMatcher` | Сопоставление AP по координатам |
| `CombinedMatcher` | Сначала имя, затем координаты как запасной вариант |
| `VisualDiffGenerator` | Генерация изображений сравнения планов этажей |

**Логика обнаружения изменений:**

1. Парсинг обоих .esx файлов
2. Сопоставление AP с использованием выбранной стратегии
3. Классификация каждой AP:
   - **added**: Только в новом проекте
   - **removed**: Только в старом проекте
   - **modified**: Та же позиция, изменена конфигурация
   - **moved**: Позиция изменена > порога
   - **renamed**: Та же позиция, другое имя
   - **unchanged**: Нет различий

---

## Веб-приложение

### Архитектура

```
ekahau_bom_web/
├── backend/                 # FastAPI (Python)
│   ├── app/
│   │   ├── api/            # REST endpoints
│   │   │   ├── upload.py   # Загрузка файлов
│   │   │   ├── projects.py # CRUD проектов
│   │   │   ├── reports.py  # Скачивание отчётов
│   │   │   ├── notes.py    # API заметок
│   │   │   └── schedules.py # Планировщик
│   │   ├── services/       # Бизнес-логика
│   │   │   ├── processing.py
│   │   │   ├── scheduler_service.py
│   │   │   └── notification_service.py
│   │   └── main.py         # Точка входа
│   ├── data/               # Хранилище данных
│   └── requirements.txt
│
└── frontend/               # Angular + Taiga UI
    └── ekahau-bom-ui/
        ├── src/app/
        │   ├── core/       # Сервисы, модели
        │   ├── features/   # Компоненты страниц
        │   └── shared/     # Общие компоненты
        └── angular.json
```

### Backend (FastAPI)

**Порт**: 8001

**Ключевые компоненты**:
- 20+ REST API endpoints
- JWT + OAuth2/Keycloak аутентификация
- WebSocket для real-time обновлений
- APScheduler для планировщика

**Запуск**:
```bash
cd ekahau_bom_web/backend
./venv/Scripts/activate
uvicorn app.main:app --port 8001 --reload
```

### Frontend (Angular)

**Порт**: 4200

**Стек**:
- Angular 20
- Taiga UI v4.60.0
- TypeScript 5.x

**Запуск**:
```bash
cd ekahau_bom_web/frontend/ekahau-bom-ui
npm install
npm start
```

### API Proxy

Frontend проксирует `/api/*` запросы на backend:8001.

Конфигурация: `proxy.conf.json`

---

## Docker

### Структура

```
docker-compose.yml           # Основная конфигурация
docker-compose.keycloak.yml  # Keycloak overlay
.env.example                 # Шаблон переменных
├── ekahau_bom_web/
│   ├── backend/
│   │   └── Dockerfile      # Multi-stage Python build
│   └── frontend/
│       └── ekahau-bom-ui/
│           ├── Dockerfile  # Node.js + Nginx
│           └── nginx.conf  # Reverse proxy config
```

### Сборка и запуск

```bash
# Простой режим
docker-compose up --build

# С Keycloak SSO
docker-compose -f docker-compose.yml \
  -f docker-compose.keycloak.yml up --build
```

### Backend Dockerfile

Multi-stage сборка:
1. **Builder stage**: pip install зависимостей
2. **Runtime stage**: минимальный образ с WeasyPrint

Healthcheck: `/health` endpoint

### Frontend Dockerfile

Multi-stage сборка:
1. **Builder stage**: npm build Angular приложения
2. **Runtime stage**: Nginx с SPA конфигурацией

Nginx обрабатывает:
- `/api/*` → proxy к backend
- `/ws/*` → WebSocket proxy
- `/*` → Angular SPA

### Переменные окружения

См. `.env.example` для полного списка:
- `AUTH_BACKEND`: simple или oauth2
- `OAUTH2_*`: настройки OAuth2
- `STORAGE_BACKEND`: local или s3
- `S3_*`: настройки S3

---

## Стиль кода

### Стандарты Python

- Соответствие **PEP 8**
- **Подсказки типов** для всех функций
- **Docstrings** для всех публичных API (стиль Google)
- **F-строки** для форматирования строк

### Пример

```python
def process_access_points(
    access_points_data: dict[str, Any],
    floors: dict[str, Floor]
) -> list[AccessPoint]:
    """Обработка сырых данных точек доступа в объекты AccessPoint.

    Args:
        access_points_data: Сырые данные точек доступа от парсера
        floors: Словарь, сопоставляющий ID этажей с объектами Floor

    Returns:
        Список обработанных объектов AccessPoint

    Raises:
        ValueError: Если данные некорректны
    """
    # Реализация
```

### Инструменты

```bash
# Форматирование кода
black ekahau_bom/

# Линтинг
flake8 ekahau_bom/
pylint ekahau_bom/

# Проверка типов
mypy ekahau_bom/
```

---

## Тестирование

### Запуск тестов

```bash
# Все тесты
pytest

# С покрытием
pytest --cov=ekahau_bom --cov-report=html

# Конкретный файл
pytest tests/test_analytics.py -v

# Конкретный тест
pytest tests/test_analytics.py::TestGroupingAnalytics::test_group_by_floor
```

### Написание тестов

**Структура:**
```python
import pytest
from ekahau_bom.models import AccessPoint

@pytest.fixture
def sample_aps():
    """Создание примеров точек доступа для тестирования."""
    return [
        AccessPoint("Cisco", "C9120AXI", "Yellow", "Floor 1"),
        AccessPoint("Aruba", "AP-515", "Red", "Floor 2"),
    ]

class TestAnalytics:
    """Тестирование функционала аналитики."""

    def test_group_by_vendor(self, sample_aps):
        """Тест группировки по производителям."""
        result = GroupingAnalytics.group_by_vendor(sample_aps)
        assert result["Cisco"] == 1
        assert result["Aruba"] == 1
```

**Цели покрытия:**
- Новые функции: 80%+ покрытие
- Критические пути: 95%+ покрытие
- Текущее общее: 70%

---

## Добавление функций

### Добавление нового экспортера

1. **Создать класс экспортера:**

```python
# ekahau_bom/exporters/pdf_exporter.py
from .base import BaseExporter
from ..models import ProjectData

class PDFExporter(BaseExporter):
    @property
    def format_name(self) -> str:
        return "PDF"

    def export(self, project_data: ProjectData) -> list[Path]:
        # Реализация
        pass
```

2. **Зарегистрировать в CLI:**

```python
# ekahau_bom/cli.py
EXPORTERS = {
    'csv': CSVExporter,
    'excel': ExcelExporter,
    'html': HTMLExporter,
    'json': JSONExporter,
    'pdf': PDFExporter,  # Добавить новый экспортер
}
```

3. **Добавить тесты:**

```python
# tests/test_pdf_exporter.py
def test_pdf_export(sample_project_data, tmp_path):
    exporter = PDFExporter(tmp_path)
    files = exporter.export(sample_project_data)
    assert len(files) == 1
    assert files[0].suffix == '.pdf'
```

### Добавление аналитики

1. **Добавить метод в analytics.py:**

```python
@staticmethod
def analyze_channel_overlap(radios: list[Radio]) -> dict[str, Any]:
    """Анализ перекрытия каналов между радио.

    Args:
        radios: Список радио для анализа

    Returns:
        Словарь с анализом перекрытий
    """
    # Реализация
```

2. **Добавить тесты:**

```python
def test_channel_overlap(sample_radios):
    result = RadioAnalytics.analyze_channel_overlap(sample_radios)
    assert "overlap_count" in result
```

3. **Интегрировать в экспортеры** (опционально)

---

## Внесение вклада

### Рабочий процесс

1. **Форк** репозитория
2. **Создать ветку**: `git checkout -b feature/amazing-feature`
3. **Внести изменения** с тестами
4. **Запустить тесты**: `pytest`
5. **Форматировать код**: `black ekahau_bom/`
6. **Закоммитить**: `git commit -m 'Добавить потрясающую функцию'`
7. **Запушить**: `git push origin feature/amazing-feature`
8. **Открыть Pull Request**

### Руководство по Pull Request

**Заголовок:**
- Четкое, краткое описание
- Пример: "Добавить поддержку экспорта PDF"

**Описание:**
- Какие изменения были внесены
- Почему они были внесены
- Как протестировать

**Чеклист:**
- [ ] Тесты добавлены/обновлены
- [ ] Документация обновлена
- [ ] Все тесты проходят
- [ ] Код отформатирован (black)
- [ ] Подсказки типов добавлены
- [ ] Docstrings добавлены

### Сообщения коммитов

Формат:
```
<тип>: <тема>

<тело>

<подвал>
```

**Типы:**
- `feat`: Новая функция
- `fix`: Исправление ошибки
- `docs`: Документация
- `test`: Тесты
- `refactor`: Рефакторинг кода
- `style`: Форматирование
- `perf`: Улучшение производительности

**Пример:**
```
feat: Добавить поддержку экспорта PDF

- Реализовать класс PDFExporter с использованием WeasyPrint
- Добавить шаблон PDF с пользовательским стилем
- Включить диаграммы в вывод PDF
- Добавить тесты для генерации PDF

Closes #42
```

---

## Архитектурные решения

### Почему Dataclasses?

- Типобезопасные
- Неизменяемые по умолчанию
- Автоматически генерируемые __init__, __repr__ и т.д.
- Легко сериализуемые

### Почему Click для CLI?

- Отличная документация
- Валидация типов
- Поддержка вложенных команд
- Широкое распространение

### Почему openpyxl для Excel?

- Чистый Python (без внешних зависимостей)
- Хорошая поддержка диаграмм
- Активная поддержка
- Совместим с Excel 2010+

---

## Соображения производительности

### Память

- Потоковая обработка больших наборов данных, где это возможно
- Не загружать весь проект в память
- Использовать генераторы, где это уместно

### Скорость

- Ленивая загрузка опциональных данных
- Кэширование для дорогостоящих операций
- Параллельная обработка для независимых операций (в будущем)

---

## Процесс релиза

1. **Обновить версию** в setup.py и __init__.py
2. **Обновить CHANGELOG.md** с изменениями
3. **Запустить полный набор тестов**: `pytest --cov=ekahau_bom`
4. **Создать тег**: `git tag -a v2.5.0 -m "Release v2.5.0"`
5. **Запушить**: `git push origin v2.5.0`
6. **Создать GitHub release** с журналом изменений

---

## Поддержка и ресурсы

- **Проблемы**: https://github.com/htechno/EkahauBOM/issues
- **Обсуждения**: https://github.com/htechno/EkahauBOM/discussions
- **Telegram**: [@htechno](https://t.me/htechno)

---

**Версия**: 3.5.0
**Последнее обновление**: 2025-12-15

**Автор**: Pavel Semenischev @htechno
