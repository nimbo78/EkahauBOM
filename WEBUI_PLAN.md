# Web UI Implementation Plan (Phase 11.1)

**Версия:** 1.0
**Дата создания:** 2025-10-31
**Дата начала:** 2025-10-31
**Статус:** ✅ Phase 1 Complete | ✅ Phase 2 Complete | ✅ Phase 3 Complete | ⏳ Phase 4: Steps 4.1, 4.3 Complete (4.2 pending)
**Выбранный стек:** FastAPI + Angular 16+ + Taiga UI v4.60.0

---

## 📋 Общий обзор

**Цель:** Создать централизованный веб-сервис для обработки и просмотра Ekahau проектов с двумя основными интерфейсами:
- **Административная панель** - загрузка и обработка .esx файлов
- **Пользовательский интерфейс** - просмотр проектов, отчётов и визуализаций

**Архитектура:**
```
┌─────────────────────────────────────────┐
│         Frontend (Angular + Taiga UI)   │
│  - Административная панель              │
│  - Пользовательский интерфейс           │
│  - Интерактивные визуализации           │
└────────────────┬────────────────────────┘
                 │ REST API
                 │ (HTTP/JSON)
┌────────────────▼────────────────────────┐
│         Backend (FastAPI)               │
│  - REST API endpoints                   │
│  - EkahauBOM CLI integration            │
│  - File processing & storage            │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│    File Storage (без БД)                │
│  projects/                              │
│  ├── {project_id}/                      │
│  │   ├── original.esx                   │
│  │   ├── metadata.json                  │
│  │   ├── reports/                       │
│  │   │   ├── *.csv                      │
│  │   │   ├── *.xlsx                     │
│  │   │   └── *.html                     │
│  │   └── visualizations/                │
│  │       └── *.png                      │
│  └── index.json (in-memory cache)       │
└─────────────────────────────────────────┘
```

**Оценка времени:** 12-15 дней
**Сложность:** Средняя (с Taiga UI компонентами)

---

## 🎯 Phase 1: Настройка окружения (1 день)

### Step 1.1: Создание структуры проекта
**Время:** 30 минут

```bash
# Создать корневую директорию для веб-сервиса
mkdir ekahau_bom_web
cd ekahau_bom_web

# Структура проекта
ekahau_bom_web/
├── backend/           # FastAPI приложение
├── frontend/          # Angular приложение
├── docker/            # Docker конфигурация (Phase 11.6)
├── docs/              # Документация
└── README.md
```

**Чек-лист:**
- [x] ✅ Создана структура директорий
- [x] ✅ Создан README.md с описанием проекта
- [x] ✅ Инициализирован git репозиторий (часть основного EkahauBOM repo)

---

### Step 1.2: Настройка Backend окружения
**Время:** 1 час

```bash
cd backend

# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Создать pyproject.toml для Backend
```

**pyproject.toml:**
```toml
[project]
name = "ekahau-bom-web"
version = "0.1.0"
description = "Web service for Ekahau BOM processing"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "python-multipart>=0.0.6",  # file upload
    "aiofiles>=23.2.0",          # async file operations
    "pydantic>=2.5.0",
    "ekahau-bom>=2.8.0",         # основной пакет
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "httpx>=0.25.0",  # async client для тестов
    "black>=23.11.0",
    "mypy>=1.7.0",
]
```

**Структура Backend:**
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI приложение
│   ├── config.py            # Конфигурация
│   ├── models.py            # Pydantic модели
│   ├── api/
│   │   ├── __init__.py
│   │   ├── projects.py      # Endpoints для проектов
│   │   ├── upload.py        # Загрузка файлов
│   │   └── reports.py       # Скачивание отчётов
│   ├── services/
│   │   ├── __init__.py
│   │   ├── processor.py     # Обработка .esx файлов
│   │   ├── storage.py       # Работа с файловой системой
│   │   └── index.py         # In-memory индексация
│   └── utils/
│       ├── __init__.py
│       └── short_links.py   # Генерация коротких ссылок
├── tests/
├── pyproject.toml
└── README.md
```

**Чек-лист:**
- [x] ✅ Создано виртуальное окружение (Python 3.13.7)
- [x] ✅ Создан pyproject.toml с зависимостями
- [x] ✅ Установлены зависимости: FastAPI 0.120.3, ekahau-bom 2.8.0
- [x] ✅ Создана структура директорий Backend (app/{api,services,utils}, tests)
- [x] ✅ Проверена установка и запуск сервера на http://localhost:8000

---

### Step 1.3: Настройка Frontend окружения
**Время:** 2 часа

```bash
cd ../frontend

# Проверить версию Node.js (нужен >= 18.0.0)
node --version  # должен быть 18+

# Создать Angular проект
npx @angular/cli@latest new ekahau-bom-ui --routing --style=scss --skip-git

cd ekahau-bom-ui

# Установить Taiga UI
npm install @taiga-ui/cdk@4.60.0
npm install @taiga-ui/core@4.60.0
npm install @taiga-ui/kit@4.60.0
npm install @taiga-ui/addon-table@4.60.0
npm install @taiga-ui/layout@4.60.0
npm install @taiga-ui/icons@4.60.0
```

**Структура Frontend:**
```
frontend/ekahau-bom-ui/
├── src/
│   ├── app/
│   │   ├── core/               # Сервисы, guards, interceptors
│   │   │   ├── services/
│   │   │   │   ├── api.service.ts
│   │   │   │   └── project.service.ts
│   │   │   └── models/
│   │   │       └── project.model.ts
│   │   ├── features/
│   │   │   ├── admin/          # Административная панель
│   │   │   │   ├── upload/
│   │   │   │   └── processing/
│   │   │   ├── projects/       # Список проектов
│   │   │   │   ├── list/
│   │   │   │   └── detail/
│   │   │   └── reports/        # Просмотр отчётов
│   │   ├── shared/             # Переиспользуемые компоненты
│   │   │   └── components/
│   │   ├── app.component.ts
│   │   └── app.routes.ts
│   ├── assets/
│   ├── styles.scss
│   └── main.ts
├── angular.json
├── package.json
└── tsconfig.json
```

**app.config.ts (настройка Taiga UI):**
```typescript
import { ApplicationConfig, importProvidersFrom } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideAnimations } from '@angular/platform-browser/animations';
import { TuiRoot } from '@taiga-ui/core';
import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),
    provideAnimations(),
  ]
};
```

**Чек-лист:**
- [x] ✅ Установлен Node.js 24.7.0 (требовалось >= 18)
- [x] ✅ Создан Angular 20.3.8 проект
- [x] ✅ Установлены пакеты Taiga UI v4.60.0 (6 packages, 46 dependencies)
- [x] ✅ Создана структура директорий Frontend (core, features, shared)
- [x] ✅ Проверена сборка: build успешный (2.29 MB bundle)

---

### Step 1.4: Настройка CORS и проксирования
**Время:** 30 минут

**Backend (app/main.py):**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Ekahau BOM Web API")

# CORS для локальной разработки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],  # Angular dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Frontend (proxy.conf.json):**
```json
{
  "/api": {
    "target": "http://localhost:8000",
    "secure": false,
    "changeOrigin": true
  }
}
```

**angular.json (добавить proxyConfig):**
```json
"serve": {
  "options": {
    "proxyConfig": "proxy.conf.json"
  }
}
```

**Чек-лист:**
- [x] ✅ CORS настроен в FastAPI (app/main.py)
- [x] ✅ Создан proxy.conf.json
- [x] ✅ Добавлен proxyConfig в angular.json
- [x] ✅ Проверено: Backend запущен на :8000, Frontend на :4200 (оба работают)

---

## 🔧 Phase 2: Backend Development (4-5 дней)

### Step 2.1: Конфигурация и модели данных
**Время:** 2 часа

**app/config.py:**
```python
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Paths
    projects_dir: Path = Path("data/projects")
    index_file: Path = Path("data/index.json")

    # API
    api_prefix: str = "/api"
    max_upload_size: int = 500 * 1024 * 1024  # 500 MB

    # Processing
    ekahau_bom_flags: dict = {
        "group_aps": True,
        "output_formats": ["csv", "xlsx", "html"],
        "visualize_floor_plans": True,
    }

    # Short links
    short_link_length: int = 8
    short_link_expiry_days: int = 30

    class Config:
        env_file = ".env"

settings = Settings()
```

**app/models.py:**
```python
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID, uuid4

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ProjectMetadata(BaseModel):
    """Метаданные проекта для хранения в metadata.json"""
    project_id: UUID = Field(default_factory=uuid4)
    filename: str
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    file_size: int  # bytes
    processing_status: ProcessingStatus = ProcessingStatus.PENDING

    # Метаданные из .esx
    project_name: Optional[str] = None
    buildings_count: Optional[int] = None
    floors_count: Optional[int] = None
    aps_count: Optional[int] = None

    # Обработка
    processing_flags: dict = {}
    processing_started: Optional[datetime] = None
    processing_completed: Optional[datetime] = None
    processing_error: Optional[str] = None

    # Пути к файлам (относительные)
    original_file: str  # projects/{project_id}/original.esx
    reports_dir: Optional[str] = None
    visualizations_dir: Optional[str] = None

    # Short link
    short_link: Optional[str] = None
    short_link_expires: Optional[datetime] = None

class ProjectListItem(BaseModel):
    """Элемент списка проектов (для UI)"""
    project_id: UUID
    project_name: str
    filename: str
    upload_date: datetime
    aps_count: Optional[int]
    processing_status: ProcessingStatus
    short_link: Optional[str]

class UploadResponse(BaseModel):
    """Ответ на загрузку файла"""
    project_id: UUID
    message: str
    short_link: Optional[str]

class ProcessingRequest(BaseModel):
    """Запрос на обработку проекта"""
    group_aps: bool = True
    output_formats: list[str] = ["csv", "xlsx", "html"]
    visualize_floor_plans: bool = True
```

**Чек-лист:**
- [x] ✅ Создан config.py с настройками
- [x] ✅ Создан models.py с Pydantic моделями
- [x] ✅ Создан .env файл для локальных настроек
- [x] ✅ Проверена типизация: `mypy app/`

---

### Step 2.2: Storage Service - работа с файлами
**Время:** 3 часа

**app/services/storage.py:**
```python
import json
import shutil
from pathlib import Path
from uuid import UUID
from typing import Optional
from datetime import datetime
from app.config import settings
from app.models import ProjectMetadata, ProcessingStatus

class StorageService:
    """Сервис для работы с файловой системой"""

    def __init__(self):
        self.projects_dir = settings.projects_dir
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    def get_project_dir(self, project_id: UUID) -> Path:
        """Получить директорию проекта"""
        return self.projects_dir / str(project_id)

    async def save_uploaded_file(
        self,
        project_id: UUID,
        filename: str,
        file_content: bytes
    ) -> Path:
        """Сохранить загруженный .esx файл"""
        project_dir = self.get_project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)

        # Сохранить оригинальный файл
        file_path = project_dir / "original.esx"
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_content)

        return file_path

    def save_metadata(self, project_id: UUID, metadata: ProjectMetadata):
        """Сохранить metadata.json"""
        project_dir = self.get_project_dir(project_id)
        metadata_file = project_dir / "metadata.json"

        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata.model_dump(mode="json"), f, indent=2, ensure_ascii=False)

    def load_metadata(self, project_id: UUID) -> Optional[ProjectMetadata]:
        """Загрузить metadata.json"""
        metadata_file = self.get_project_dir(project_id) / "metadata.json"

        if not metadata_file.exists():
            return None

        with open(metadata_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        return ProjectMetadata(**data)

    def get_reports_dir(self, project_id: UUID) -> Path:
        """Получить директорию с отчётами"""
        return self.get_project_dir(project_id) / "reports"

    def get_visualizations_dir(self, project_id: UUID) -> Path:
        """Получить директорию с визуализациями"""
        return self.get_project_dir(project_id) / "visualizations"

    def list_report_files(self, project_id: UUID) -> list[str]:
        """Список файлов отчётов"""
        reports_dir = self.get_reports_dir(project_id)
        if not reports_dir.exists():
            return []

        return [f.name for f in reports_dir.iterdir() if f.is_file()]

    def list_visualization_files(self, project_id: UUID) -> list[str]:
        """Список файлов визуализаций"""
        viz_dir = self.get_visualizations_dir(project_id)
        if not viz_dir.exists():
            return []

        return [f.name for f in viz_dir.iterdir() if f.suffix == ".png"]

    def delete_project(self, project_id: UUID):
        """Удалить проект полностью"""
        project_dir = self.get_project_dir(project_id)
        if project_dir.exists():
            shutil.rmtree(project_dir)

storage_service = StorageService()
```

**Чек-лист:**
- [x] ✅ Создан storage.py с методами работы с файлами
- [x] ✅ Реализовано сохранение/загрузка метаданных
- [x] ✅ Реализовано получение списков файлов
- [x] ✅ Написаны юнит-тесты для StorageService (8 tests passing)

---

### Step 2.3: Index Service - in-memory индексация
**Время:** 2 часа

**app/services/index.py:**
```python
import json
from pathlib import Path
from typing import Optional
from uuid import UUID
from app.config import settings
from app.models import ProjectMetadata, ProjectListItem
from app.services.storage import storage_service

class IndexService:
    """In-memory индекс всех проектов"""

    def __init__(self):
        self.index: dict[UUID, ProjectMetadata] = {}
        self.index_file = settings.index_file
        self.index_file.parent.mkdir(parents=True, exist_ok=True)

    async def rebuild_index(self):
        """Полная перестройка индекса из файловой системы"""
        self.index.clear()

        if not settings.projects_dir.exists():
            return

        # Сканировать все директории проектов
        for project_dir in settings.projects_dir.iterdir():
            if not project_dir.is_dir():
                continue

            try:
                project_id = UUID(project_dir.name)
                metadata = storage_service.load_metadata(project_id)

                if metadata:
                    self.index[project_id] = metadata
            except (ValueError, TypeError):
                # Невалидный UUID или проблема с метаданными
                continue

        # Сохранить индекс в файл для быстрого старта
        self._save_index()

    def _save_index(self):
        """Сохранить индекс в JSON файл"""
        data = {
            str(pid): meta.model_dump(mode="json")
            for pid, meta in self.index.items()
        }

        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load_index(self):
        """Загрузить индекс из JSON файла"""
        if not self.index_file.exists():
            return

        with open(self.index_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        for pid_str, meta_dict in data.items():
            project_id = UUID(pid_str)
            self.index[project_id] = ProjectMetadata(**meta_dict)

    def add_project(self, metadata: ProjectMetadata):
        """Добавить проект в индекс"""
        self.index[metadata.project_id] = metadata
        self._save_index()

    def update_project(self, project_id: UUID, metadata: ProjectMetadata):
        """Обновить метаданные проекта в индексе"""
        self.index[project_id] = metadata
        self._save_index()

    def remove_project(self, project_id: UUID):
        """Удалить проект из индекса"""
        if project_id in self.index:
            del self.index[project_id]
            self._save_index()

    def get_project(self, project_id: UUID) -> Optional[ProjectMetadata]:
        """Получить метаданные проекта"""
        return self.index.get(project_id)

    def list_projects(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None
    ) -> list[ProjectListItem]:
        """Список проектов с пагинацией и поиском"""
        projects = list(self.index.values())

        # Фильтрация по поиску
        if search:
            search_lower = search.lower()
            projects = [
                p for p in projects
                if (search_lower in (p.filename or "").lower() or
                    search_lower in (p.project_name or "").lower())
            ]

        # Сортировка по дате загрузки (новые первые)
        projects.sort(key=lambda p: p.upload_date, reverse=True)

        # Пагинация
        projects = projects[skip:skip + limit]

        # Преобразование в ProjectListItem
        return [
            ProjectListItem(
                project_id=p.project_id,
                project_name=p.project_name or p.filename,
                filename=p.filename,
                upload_date=p.upload_date,
                aps_count=p.aps_count,
                processing_status=p.processing_status,
                short_link=p.short_link,
            )
            for p in projects
        ]

    def get_by_short_link(self, short_link: str) -> Optional[ProjectMetadata]:
        """Найти проект по короткой ссылке"""
        for metadata in self.index.values():
            if metadata.short_link == short_link:
                return metadata
        return None

index_service = IndexService()
```

**app/main.py (добавить lifespan для загрузки индекса):**
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.services.index import index_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: загрузить индекс
    await index_service.rebuild_index()
    print(f"Loaded {len(index_service.index)} projects into index")
    yield
    # Shutdown: сохранить индекс
    index_service._save_index()

app = FastAPI(title="Ekahau BOM Web API", lifespan=lifespan)
```

**Чек-лист:**
- [x] ✅ Создан index.py с in-memory индексацией
- [x] ✅ Реализована загрузка индекса при старте
- [x] ✅ Реализованы поиск и фильтрация
- [x] ✅ Добавлен lifespan в FastAPI для загрузки индекса (15 tests passing)

---

### Step 2.4: Processor Service - обработка .esx файлов
**Время:** 4 часа

**app/services/processor.py:**
```python
import asyncio
import subprocess
from pathlib import Path
from uuid import UUID
from datetime import datetime
from app.config import settings
from app.models import ProjectMetadata, ProcessingStatus, ProcessingRequest
from app.services.storage import storage_service
from app.services.index import index_service

class ProcessorService:
    """Сервис для обработки .esx файлов через EkahauBOM CLI"""

    async def process_project(
        self,
        project_id: UUID,
        processing_req: ProcessingRequest
    ):
        """Обработать .esx файл асинхронно"""
        metadata = storage_service.load_metadata(project_id)
        if not metadata:
            raise ValueError(f"Project {project_id} not found")

        # Обновить статус на PROCESSING
        metadata.processing_status = ProcessingStatus.PROCESSING
        metadata.processing_started = datetime.utcnow()
        metadata.processing_flags = processing_req.model_dump()

        storage_service.save_metadata(project_id, metadata)
        index_service.update_project(project_id, metadata)

        try:
            # Запустить обработку
            await self._run_ekahau_bom(project_id, processing_req)

            # Извлечь метаданные из обработанных файлов
            await self._extract_metadata(project_id)

            # Обновить статус на COMPLETED
            metadata = storage_service.load_metadata(project_id)
            metadata.processing_status = ProcessingStatus.COMPLETED
            metadata.processing_completed = datetime.utcnow()

        except Exception as e:
            # Обновить статус на FAILED
            metadata.processing_status = ProcessingStatus.FAILED
            metadata.processing_error = str(e)

        finally:
            storage_service.save_metadata(project_id, metadata)
            index_service.update_project(project_id, metadata)

    async def _run_ekahau_bom(
        self,
        project_id: UUID,
        processing_req: ProcessingRequest
    ):
        """Запустить EkahauBOM CLI"""
        project_dir = storage_service.get_project_dir(project_id)
        input_file = project_dir / "original.esx"
        output_dir = project_dir / "reports"
        viz_dir = project_dir / "visualizations"

        # Построить команду
        cmd = [
            "python", "-m", "ekahau_bom",
            str(input_file),
            "--output-dir", str(output_dir),
        ]

        # Добавить флаги
        if processing_req.group_aps:
            cmd.append("--group-aps")

        for fmt in processing_req.output_formats:
            cmd.extend(["--format", fmt])

        if processing_req.visualize_floor_plans:
            cmd.extend([
                "--visualize-floor-plans",
                "--visualization-dir", str(viz_dir),
            ])

        # Запустить процесс асинхронно
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"EkahauBOM failed: {stderr.decode()}")

    async def _extract_metadata(self, project_id: UUID):
        """Извлечь метаданные из обработанных файлов"""
        # Можно парсить CSV файлы для получения количества AP, зданий, этажей
        # Или использовать ekahau_bom как библиотеку напрямую

        metadata = storage_service.load_metadata(project_id)

        # TODO: Извлечь project_name, buildings_count, floors_count, aps_count
        # из обработанных файлов или прямым парсингом .esx

        # Пока просто установим пути
        metadata.reports_dir = str(storage_service.get_reports_dir(project_id))
        metadata.visualizations_dir = str(storage_service.get_visualizations_dir(project_id))

        storage_service.save_metadata(project_id, metadata)

processor_service = ProcessorService()
```

**Чек-лист:**
- [x] ✅ Создан processor.py для запуска EkahauBOM CLI
- [x] ✅ Реализована асинхронная обработка
- [x] ✅ Реализовано обновление статуса обработки
- [x] ✅ Добавлена обработка ошибок (9 tests passing)

---

### Step 2.5: Short Links Service
**Время:** 1 час

**app/utils/short_links.py:**
```python
import secrets
import string
from datetime import datetime, timedelta
from app.config import settings

def generate_short_link(length: int = None) -> str:
    """Сгенерировать случайную короткую ссылку"""
    if length is None:
        length = settings.short_link_length

    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def calculate_expiry_date(days: int = None) -> datetime:
    """Рассчитать дату истечения ссылки"""
    if days is None:
        days = settings.short_link_expiry_days

    return datetime.utcnow() + timedelta(days=days)

def is_link_expired(expires: datetime) -> bool:
    """Проверить истекла ли ссылка"""
    return datetime.utcnow() > expires
```

**Чек-лист:**
- [x] ✅ Создан short_links.py с генерацией ссылок
- [x] ✅ Реализована проверка истечения срока
- [x] ✅ Добавлены юнит-тесты для генерации ссылок (14 tests passing)

---

### Step 2.6: API Endpoints - Upload
**Время:** 2 часа

**app/api/upload.py:**
```python
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from uuid import uuid4
from app.models import UploadResponse, ProcessingRequest
from app.services.storage import storage_service
from app.services.index import index_service
from app.services.processor import processor_service
from app.utils.short_links import generate_short_link, calculate_expiry_date
from app.models import ProjectMetadata, ProcessingStatus

router = APIRouter(prefix="/upload", tags=["upload"])

@router.post("", response_model=UploadResponse)
async def upload_project(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
):
    """Загрузить .esx файл"""

    # Валидация расширения
    if not file.filename.endswith(".esx"):
        raise HTTPException(400, "Only .esx files are allowed")

    # Валидация размера (проверяется FastAPI через max_upload_size)

    # Создать проект
    project_id = uuid4()

    # Прочитать файл
    file_content = await file.read()
    file_size = len(file_content)

    # Сохранить файл
    await storage_service.save_uploaded_file(
        project_id,
        file.filename,
        file_content,
    )

    # Создать метаданные
    short_link = generate_short_link()
    metadata = ProjectMetadata(
        project_id=project_id,
        filename=file.filename,
        file_size=file_size,
        original_file=f"projects/{project_id}/original.esx",
        short_link=short_link,
        short_link_expires=calculate_expiry_date(),
    )

    # Сохранить метаданные
    storage_service.save_metadata(project_id, metadata)

    # Добавить в индекс
    index_service.add_project(metadata)

    return UploadResponse(
        project_id=project_id,
        message="File uploaded successfully. Use /process endpoint to start processing.",
        short_link=short_link,
    )

@router.post("/{project_id}/process")
async def process_uploaded_project(
    project_id: str,
    processing_req: ProcessingRequest,
    background_tasks: BackgroundTasks,
):
    """Запустить обработку загруженного проекта"""
    from uuid import UUID

    try:
        pid = UUID(project_id)
    except ValueError:
        raise HTTPException(400, "Invalid project_id")

    metadata = index_service.get_project(pid)
    if not metadata:
        raise HTTPException(404, "Project not found")

    # Запустить обработку в фоне
    background_tasks.add_task(
        processor_service.process_project,
        pid,
        processing_req,
    )

    return {"message": "Processing started", "project_id": str(pid)}
```

**Чек-лист:**
- [x] ✅ Создан upload.py с endpoints для загрузки
- [x] ✅ Реализована валидация файлов
- [x] ✅ Реализован endpoint для запуска обработки
- [x] ✅ Добавлены BackgroundTasks для асинхронной обработки

---

### Step 2.7: API Endpoints - Projects
**Время:** 2 часа

**app/api/projects.py:**
```python
from fastapi import APIRouter, HTTPException, Query
from uuid import UUID
from typing import Optional
from app.models import ProjectMetadata, ProjectListItem
from app.services.index import index_service
from app.services.storage import storage_service

router = APIRouter(prefix="/projects", tags=["projects"])

@router.get("", response_model=list[ProjectListItem])
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
):
    """Получить список всех проектов"""
    return index_service.list_projects(skip=skip, limit=limit, search=search)

@router.get("/{project_id}", response_model=ProjectMetadata)
async def get_project(project_id: str):
    """Получить детали проекта"""
    try:
        pid = UUID(project_id)
    except ValueError:
        raise HTTPException(400, "Invalid project_id")

    metadata = index_service.get_project(pid)
    if not metadata:
        raise HTTPException(404, "Project not found")

    return metadata

@router.get("/short/{short_link}", response_model=ProjectMetadata)
async def get_project_by_short_link(short_link: str):
    """Получить проект по короткой ссылке"""
    metadata = index_service.get_by_short_link(short_link)
    if not metadata:
        raise HTTPException(404, "Project not found")

    # Проверить истечение ссылки
    from app.utils.short_links import is_link_expired
    if metadata.short_link_expires and is_link_expired(metadata.short_link_expires):
        raise HTTPException(410, "Short link has expired")

    return metadata

@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """Удалить проект"""
    try:
        pid = UUID(project_id)
    except ValueError:
        raise HTTPException(400, "Invalid project_id")

    metadata = index_service.get_project(pid)
    if not metadata:
        raise HTTPException(404, "Project not found")

    # Удалить из файловой системы
    storage_service.delete_project(pid)

    # Удалить из индекса
    index_service.remove_project(pid)

    return {"message": "Project deleted successfully"}
```

**Чек-лист:**
- [x] ✅ Создан projects.py с endpoints для проектов
- [x] ✅ Реализован список проектов с пагинацией
- [x] ✅ Реализован поиск проектов
- [x] ✅ Реализован доступ по короткой ссылке
- [x] ✅ Реализовано удаление проектов

---

### Step 2.8: API Endpoints - Reports
**Время:** 2 часа

**app/api/reports.py:**
```python
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from uuid import UUID
from pathlib import Path
from app.services.index import index_service
from app.services.storage import storage_service

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/{project_id}/list")
async def list_reports(project_id: str):
    """Список всех отчётов проекта"""
    try:
        pid = UUID(project_id)
    except ValueError:
        raise HTTPException(400, "Invalid project_id")

    metadata = index_service.get_project(pid)
    if not metadata:
        raise HTTPException(404, "Project not found")

    return {
        "reports": storage_service.list_report_files(pid),
        "visualizations": storage_service.list_visualization_files(pid),
    }

@router.get("/{project_id}/download/{filename}")
async def download_report(project_id: str, filename: str):
    """Скачать отчёт"""
    try:
        pid = UUID(project_id)
    except ValueError:
        raise HTTPException(400, "Invalid project_id")

    metadata = index_service.get_project(pid)
    if not metadata:
        raise HTTPException(404, "Project not found")

    # Проверить существование файла
    reports_dir = storage_service.get_reports_dir(pid)
    file_path = reports_dir / filename

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(404, "File not found")

    # Безопасность: проверить что файл внутри reports_dir
    if not str(file_path.resolve()).startswith(str(reports_dir.resolve())):
        raise HTTPException(403, "Access denied")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream",
    )

@router.get("/{project_id}/visualization/{filename}")
async def get_visualization(project_id: str, filename: str):
    """Получить визуализацию"""
    try:
        pid = UUID(project_id)
    except ValueError:
        raise HTTPException(400, "Invalid project_id")

    metadata = index_service.get_project(pid)
    if not metadata:
        raise HTTPException(404, "Project not found")

    viz_dir = storage_service.get_visualizations_dir(pid)
    file_path = viz_dir / filename

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(404, "Visualization not found")

    # Безопасность
    if not str(file_path.resolve()).startswith(str(viz_dir.resolve())):
        raise HTTPException(403, "Access denied")

    return FileResponse(
        path=file_path,
        media_type="image/png",
    )

@router.get("/{project_id}/original")
async def download_original(project_id: str):
    """Скачать оригинальный .esx файл"""
    try:
        pid = UUID(project_id)
    except ValueError:
        raise HTTPException(400, "Invalid project_id")

    metadata = index_service.get_project(pid)
    if not metadata:
        raise HTTPException(404, "Project not found")

    file_path = storage_service.get_project_dir(pid) / "original.esx"

    if not file_path.exists():
        raise HTTPException(404, "Original file not found")

    return FileResponse(
        path=file_path,
        filename=metadata.filename,
        media_type="application/octet-stream",
    )
```

**Чек-лист:**
- [x] ✅ Создан reports.py с endpoints для отчётов
- [x] ✅ Реализовано скачивание отчётов
- [x] ✅ Реализовано получение визуализаций
- [x] ✅ Реализовано скачивание оригинального .esx
- [x] ✅ Добавлена проверка безопасности путей

---

### Step 2.9: Интеграция всех endpoints в main.py
**Время:** 30 минут

**app/main.py (полная версия):**
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.services.index import index_service
from app.api import upload, projects, reports

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Loading project index...")
    await index_service.rebuild_index()
    print(f"Loaded {len(index_service.index)} projects")
    yield
    # Shutdown
    print("Saving project index...")
    index_service._save_index()

app = FastAPI(
    title="Ekahau BOM Web API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(reports.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Ekahau BOM Web API", "version": "0.1.0"}

@app.get("/health")
async def health():
    return {"status": "healthy", "projects_count": len(index_service.index)}
```

**Запуск:**
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Чек-лист:**
- [x] ✅ Все routers подключены в main.py
- [x] ✅ Добавлен health check endpoint
- [x] ✅ Backend запускается без ошибок
- [x] ✅ Доступен по http://localhost:8000
- [x] ✅ Swagger UI доступен по http://localhost:8000/docs

---

## 🎨 Phase 3: Frontend Development (5-6 дней)

### Step 3.1: Настройка Taiga UI и базовый layout
**Время:** 2 часа

**src/styles.scss:**
```scss
@import '@taiga-ui/core/styles/taiga-ui-global.scss';
@import '@taiga-ui/core/styles/taiga-ui-theme.scss';

html, body {
  height: 100%;
  margin: 0;
  padding: 0;
}
```

**src/app/app.component.ts:**
```typescript
import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { TuiRoot } from '@taiga-ui/core';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, TuiRoot],
  template: `
    <tui-root>
      <router-outlet />
    </tui-root>
  `,
})
export class AppComponent {}
```

**src/app/app.routes.ts:**
```typescript
import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    redirectTo: '/projects',
    pathMatch: 'full',
  },
  {
    path: 'admin',
    loadChildren: () => import('./features/admin/admin.routes').then(m => m.ADMIN_ROUTES),
  },
  {
    path: 'projects',
    loadChildren: () => import('./features/projects/projects.routes').then(m => m.PROJECTS_ROUTES),
  },
  {
    path: 's/:shortLink',
    loadComponent: () => import('./features/projects/detail/project-detail.component').then(m => m.ProjectDetailComponent),
  },
];
```

**Чек-лист:**
- [x] ✅ Импортированы Taiga UI стили
- [x] ✅ Создан базовый layout с TuiRoot
- [x] ✅ Настроена маршрутизация с lazy loading
- [x] ✅ Проверен запуск: build успешный (127KB)

---

### Step 3.2: API Service и модели
**Время:** 2 часа

**src/app/core/models/project.model.ts:**
```typescript
export enum ProcessingStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
}

export interface ProjectMetadata {
  project_id: string;
  filename: string;
  upload_date: string;
  file_size: number;
  processing_status: ProcessingStatus;
  project_name?: string;
  buildings_count?: number;
  floors_count?: number;
  aps_count?: number;
  processing_flags?: Record<string, any>;
  processing_started?: string;
  processing_completed?: string;
  processing_error?: string;
  original_file: string;
  reports_dir?: string;
  visualizations_dir?: string;
  short_link?: string;
  short_link_expires?: string;
}

export interface ProjectListItem {
  project_id: string;
  project_name: string;
  filename: string;
  upload_date: string;
  aps_count?: number;
  processing_status: ProcessingStatus;
  short_link?: string;
}

export interface ProcessingRequest {
  group_aps: boolean;
  output_formats: string[];
  visualize_floor_plans: boolean;
}

export interface UploadResponse {
  project_id: string;
  message: string;
  short_link?: string;
}

export interface ReportsListResponse {
  reports: string[];
  visualizations: string[];
}
```

**src/app/core/services/api.service.ts:**
```typescript
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  ProjectListItem,
  ProjectMetadata,
  ProcessingRequest,
  UploadResponse,
  ReportsListResponse,
} from '../models/project.model';

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  private readonly baseUrl = '/api';

  constructor(private http: HttpClient) {}

  // Projects
  listProjects(skip = 0, limit = 100, search?: string): Observable<ProjectListItem[]> {
    let params = new HttpParams()
      .set('skip', skip.toString())
      .set('limit', limit.toString());

    if (search) {
      params = params.set('search', search);
    }

    return this.http.get<ProjectListItem[]>(`${this.baseUrl}/projects`, { params });
  }

  getProject(projectId: string): Observable<ProjectMetadata> {
    return this.http.get<ProjectMetadata>(`${this.baseUrl}/projects/${projectId}`);
  }

  getProjectByShortLink(shortLink: string): Observable<ProjectMetadata> {
    return this.http.get<ProjectMetadata>(`${this.baseUrl}/projects/short/${shortLink}`);
  }

  deleteProject(projectId: string): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(`${this.baseUrl}/projects/${projectId}`);
  }

  // Upload
  uploadFile(file: File): Observable<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    return this.http.post<UploadResponse>(`${this.baseUrl}/upload`, formData);
  }

  processProject(projectId: string, request: ProcessingRequest): Observable<{ message: string; project_id: string }> {
    return this.http.post<{ message: string; project_id: string }>(
      `${this.baseUrl}/upload/${projectId}/process`,
      request
    );
  }

  // Reports
  listReports(projectId: string): Observable<ReportsListResponse> {
    return this.http.get<ReportsListResponse>(`${this.baseUrl}/reports/${projectId}/list`);
  }

  getReportDownloadUrl(projectId: string, filename: string): string {
    return `${this.baseUrl}/reports/${projectId}/download/${filename}`;
  }

  getVisualizationUrl(projectId: string, filename: string): string {
    return `${this.baseUrl}/reports/${projectId}/visualization/${filename}`;
  }

  getOriginalDownloadUrl(projectId: string): string {
    return `${this.baseUrl}/reports/${projectId}/original`;
  }
}
```

**src/app/app.config.ts (добавить HttpClient):**
```typescript
import { ApplicationConfig } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideAnimations } from '@angular/platform-browser/animations';
import { provideHttpClient } from '@angular/common/http';
import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),
    provideAnimations(),
    provideHttpClient(),
  ]
};
```

**Чек-лист:**
- [x] ✅ Созданы TypeScript модели (project.model.ts)
- [x] ✅ Создан ApiService с методами для всех endpoints (13 endpoints)
- [x] ✅ Добавлен HttpClient в app.config
- [x] ✅ Проверена типизация и сборка

---

### Step 3.3: Admin Panel - Upload Component
**Время:** 3 часа

**src/app/features/admin/upload/upload.component.ts:**
```typescript
import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { TuiInputFiles, TuiInputFilesModule } from '@taiga-ui/kit';
import { TuiButton, TuiNotification, TuiAlertService } from '@taiga-ui/core';
import { ApiService } from '../../../core/services/api.service';
import { TuiFileLike } from '@taiga-ui/kit';

@Component({
  selector: 'app-upload',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    TuiInputFilesModule,
    TuiButton,
    TuiNotification,
  ],
  template: `
    <div class="upload-container">
      <h1>Upload Ekahau Project</h1>

      <tui-notification status="info">
        Upload .esx file to start processing
      </tui-notification>

      <div class="upload-area">
        <tui-input-files
          accept=".esx"
          [multiple]="false"
          [(ngModel)]="selectedFile"
          (ngModelChange)="onFileSelected($event)"
        >
          <ng-template tuiInputFilesLabel>
            <div class="drag-label">
              Drag & drop .esx file here or click to browse
            </div>
          </ng-template>
        </tui-input-files>

        @if (uploadProgress()) {
          <div class="progress">
            <tui-notification status="info">
              Uploading: {{ uploadProgress() }}%
            </tui-notification>
          </div>
        }

        @if (uploadedProjectId()) {
          <tui-notification status="success">
            File uploaded successfully!
            <br>
            Short link: {{ shortLink() }}
            <br>
            <button tuiButton size="m" (click)="navigateToProcess()">
              Configure Processing
            </button>
          </tui-notification>
        }
      </div>
    </div>
  `,
  styles: [`
    .upload-container {
      max-width: 800px;
      margin: 2rem auto;
      padding: 2rem;
    }

    .upload-area {
      margin-top: 2rem;
    }

    .drag-label {
      padding: 4rem 2rem;
      text-align: center;
      font-size: 1.2rem;
      color: var(--tui-text-02);
    }

    .progress {
      margin-top: 1rem;
    }
  `],
})
export class UploadComponent {
  private api = inject(ApiService);
  private router = inject(Router);
  private alerts = inject(TuiAlertService);

  selectedFile = signal<TuiFileLike[]>([]);
  uploadProgress = signal<number>(0);
  uploadedProjectId = signal<string>('');
  shortLink = signal<string>('');

  async onFileSelected(files: TuiFileLike[]) {
    if (files.length === 0) return;

    const file = files[0];
    if (!(file instanceof File)) return;

    // Validate .esx extension
    if (!file.name.endsWith('.esx')) {
      this.alerts
        .open('Only .esx files are allowed', { status: 'error' })
        .subscribe();
      this.selectedFile.set([]);
      return;
    }

    // Upload file
    this.uploadProgress.set(10);

    this.api.uploadFile(file).subscribe({
      next: (response) => {
        this.uploadProgress.set(100);
        this.uploadedProjectId.set(response.project_id);
        this.shortLink.set(response.short_link || '');

        this.alerts
          .open('File uploaded successfully!', { status: 'success' })
          .subscribe();
      },
      error: (error) => {
        this.uploadProgress.set(0);
        this.alerts
          .open(`Upload failed: ${error.message}`, { status: 'error' })
          .subscribe();
      },
    });
  }

  navigateToProcess() {
    this.router.navigate(['/admin/process', this.uploadedProjectId()]);
  }
}
```

**Чек-лист:**
- [x] ✅ Создан upload.component с TuiInputFiles
- [x] ✅ Реализована загрузка файлов через FormControl и ApiService
- [x] ✅ Добавлена валидация .esx расширения и размера (500MB)
- [x] ✅ Добавлены уведомления об успехе/ошибке (TuiNotification)
- [x] ✅ Drag & Drop поддержка с визуальной индикацией
- [x] ✅ Переход к обработке после загрузки

---

### Step 3.4: Admin Panel - Processing Configuration Component
**Время:** 3 часа

**src/app/features/admin/processing/processing.component.ts:**
```typescript
import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { TuiButton, TuiNotification, TuiAlertService } from '@taiga-ui/core';
import { TuiCheckbox, TuiMultiSelect } from '@taiga-ui/kit';
import { ApiService } from '../../../core/services/api.service';
import { ProcessingRequest } from '../../../core/models/project.model';

@Component({
  selector: 'app-processing',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    TuiButton,
    TuiNotification,
    TuiCheckbox,
    TuiMultiSelect,
  ],
  template: `
    <div class="processing-container">
      <h1>Configure Processing</h1>

      @if (projectId()) {
        <tui-notification status="info">
          Project ID: {{ projectId() }}
        </tui-notification>

        <form (ngSubmit)="startProcessing()" class="processing-form">
          <div class="form-field">
            <label>
              <input
                tuiCheckbox
                type="checkbox"
                [(ngModel)]="groupAps"
                name="groupAps"
              />
              Group Access Points
            </label>
          </div>

          <div class="form-field">
            <label>
              <input
                tuiCheckbox
                type="checkbox"
                [(ngModel)]="visualizeFloorPlans"
                name="visualizeFloorPlans"
              />
              Visualize Floor Plans
            </label>
          </div>

          <div class="form-field">
            <label>Output Formats:</label>
            <tui-multi-select
              [(ngModel)]="selectedFormats"
              name="formats"
              [items]="availableFormats"
            >
              Select formats
            </tui-multi-select>
          </div>

          <div class="actions">
            <button
              tuiButton
              type="submit"
              size="l"
              appearance="primary"
              [disabled]="isProcessing()"
            >
              {{ isProcessing() ? 'Processing...' : 'Start Processing' }}
            </button>

            <button
              tuiButton
              type="button"
              size="l"
              appearance="secondary"
              (click)="cancel()"
            >
              Cancel
            </button>
          </div>
        </form>

        @if (isProcessing()) {
          <tui-notification status="info" class="processing-status">
            Processing in progress... This may take a few minutes.
          </tui-notification>
        }
      }
    </div>
  `,
  styles: [`
    .processing-container {
      max-width: 800px;
      margin: 2rem auto;
      padding: 2rem;
    }

    .processing-form {
      margin-top: 2rem;
    }

    .form-field {
      margin-bottom: 1.5rem;
    }

    .actions {
      margin-top: 2rem;
      display: flex;
      gap: 1rem;
    }

    .processing-status {
      margin-top: 2rem;
    }
  `],
})
export class ProcessingComponent implements OnInit {
  private api = inject(ApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private alerts = inject(TuiAlertService);

  projectId = signal<string>('');
  isProcessing = signal<boolean>(false);

  groupAps = true;
  visualizeFloorPlans = true;
  selectedFormats: string[] = ['csv', 'xlsx', 'html'];
  availableFormats = ['csv', 'xlsx', 'html', 'json', 'pdf'];

  ngOnInit() {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.projectId.set(id);
    }
  }

  startProcessing() {
    const request: ProcessingRequest = {
      group_aps: this.groupAps,
      output_formats: this.selectedFormats,
      visualize_floor_plans: this.visualizeFloorPlans,
    };

    this.isProcessing.set(true);

    this.api.processProject(this.projectId(), request).subscribe({
      next: (response) => {
        this.alerts
          .open('Processing started successfully!', { status: 'success' })
          .subscribe();

        // Redirect to project detail after 2 seconds
        setTimeout(() => {
          this.router.navigate(['/projects', this.projectId()]);
        }, 2000);
      },
      error: (error) => {
        this.isProcessing.set(false);
        this.alerts
          .open(`Processing failed: ${error.message}`, { status: 'error' })
          .subscribe();
      },
    });
  }

  cancel() {
    this.router.navigate(['/projects']);
  }
}
```

**Чек-лист:**
- [x] ✅ Создан processing.component с формой настройки
- [x] ✅ Реализован выбор параметров обработки
- [x] ✅ Добавлен запуск обработки через API
- [x] ✅ Добавлена навигация после успешной обработки

---

### Step 3.5: Projects List Component
**Время:** 4 часа

**src/app/features/projects/list/projects-list.component.ts:**
```typescript
import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { TuiTable } from '@taiga-ui/addon-table';
import { TuiButton, TuiTextfield } from '@taiga-ui/core';
import { TuiStatus, TuiBadge } from '@taiga-ui/kit';
import { ApiService } from '../../../core/services/api.service';
import { ProjectListItem, ProcessingStatus } from '../../../core/models/project.model';

@Component({
  selector: 'app-projects-list',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    TuiTable,
    TuiButton,
    TuiTextfield,
    TuiStatus,
    TuiBadge,
  ],
  template: `
    <div class="projects-container">
      <div class="header">
        <h1>Ekahau Projects</h1>

        <div class="actions">
          <tui-textfield>
            <input
              tuiTextfield
              placeholder="Search projects..."
              [(ngModel)]="searchQuery"
              (ngModelChange)="onSearchChange()"
            />
          </tui-textfield>

          <button
            tuiButton
            size="m"
            appearance="primary"
            (click)="navigateToUpload()"
          >
            Upload New Project
          </button>
        </div>
      </div>

      @if (loading()) {
        <div class="loading">Loading projects...</div>
      } @else {
        <table tuiTable [columns]="columns">
          <thead>
            <tr tuiThGroup>
              <th *tuiHead="'name'" tuiTh>Project Name</th>
              <th *tuiHead="'filename'" tuiTh>Filename</th>
              <th *tuiHead="'date'" tuiTh>Upload Date</th>
              <th *tuiHead="'aps'" tuiTh>APs</th>
              <th *tuiHead="'status'" tuiTh>Status</th>
              <th *tuiHead="'actions'" tuiTh>Actions</th>
            </tr>
          </thead>
          <tbody tuiTbody [data]="projects()">
            <tr *ngFor="let project of projects()" tuiTr (click)="viewProject(project)">
              <td *tuiCell="'name'" tuiTd>
                {{ project.project_name }}
              </td>
              <td *tuiCell="'filename'" tuiTd>
                {{ project.filename }}
              </td>
              <td *tuiCell="'date'" tuiTd>
                {{ project.upload_date | date:'short' }}
              </td>
              <td *tuiCell="'aps'" tuiTd>
                {{ project.aps_count || '-' }}
              </td>
              <td *tuiCell="'status'" tuiTd>
                <tui-badge [status]="getStatusColor(project.processing_status)">
                  {{ project.processing_status }}
                </tui-badge>
              </td>
              <td *tuiCell="'actions'" tuiTd>
                <button
                  tuiButton
                  size="s"
                  appearance="flat"
                  (click)="viewProject(project); $event.stopPropagation()"
                >
                  View
                </button>
                @if (project.short_link) {
                  <button
                    tuiButton
                    size="s"
                    appearance="flat"
                    (click)="copyShortLink(project); $event.stopPropagation()"
                  >
                    Copy Link
                  </button>
                }
              </td>
            </tr>
          </tbody>
        </table>
      }
    </div>
  `,
  styles: [`
    .projects-container {
      padding: 2rem;
    }

    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 2rem;
    }

    .actions {
      display: flex;
      gap: 1rem;
      align-items: center;
    }

    .loading {
      text-align: center;
      padding: 4rem;
      font-size: 1.2rem;
      color: var(--tui-text-02);
    }

    table {
      width: 100%;
    }

    tr {
      cursor: pointer;
    }

    tr:hover {
      background-color: var(--tui-background-base-alt);
    }
  `],
})
export class ProjectsListComponent implements OnInit {
  private api = inject(ApiService);
  private router = inject(Router);

  projects = signal<ProjectListItem[]>([]);
  loading = signal<boolean>(true);
  searchQuery = '';

  columns = ['name', 'filename', 'date', 'aps', 'status', 'actions'];

  ngOnInit() {
    this.loadProjects();
  }

  loadProjects() {
    this.loading.set(true);

    this.api.listProjects(0, 100, this.searchQuery || undefined).subscribe({
      next: (data) => {
        this.projects.set(data);
        this.loading.set(false);
      },
      error: (error) => {
        console.error('Failed to load projects:', error);
        this.loading.set(false);
      },
    });
  }

  onSearchChange() {
    // Debounce search
    setTimeout(() => this.loadProjects(), 300);
  }

  viewProject(project: ProjectListItem) {
    this.router.navigate(['/projects', project.project_id]);
  }

  navigateToUpload() {
    this.router.navigate(['/admin/upload']);
  }

  copyShortLink(project: ProjectListItem) {
    if (project.short_link) {
      const url = `${window.location.origin}/s/${project.short_link}`;
      navigator.clipboard.writeText(url);
      alert('Short link copied to clipboard!');
    }
  }

  getStatusColor(status: ProcessingStatus): string {
    switch (status) {
      case ProcessingStatus.COMPLETED:
        return 'success';
      case ProcessingStatus.PROCESSING:
        return 'warning';
      case ProcessingStatus.FAILED:
        return 'error';
      default:
        return 'neutral';
    }
  }
}
```

**Чек-лист:**
- [x] ✅ Создан projects-list.component с TuiTable
- [x] ✅ Реализован список проектов с сортировкой
- [x] ✅ Добавлен поиск проектов
- [x] ✅ Добавлены статусы обработки с цветовой индикацией
- [x] ✅ Добавлено копирование короткой ссылки

---

### Step 3.6: Project Detail Component
**Время:** 5 часов

**src/app/features/projects/detail/project-detail.component.ts:**
```typescript
import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { TuiButton, TuiLoader } from '@taiga-ui/core';
import { TuiTabs, TuiAccordion, TuiBadge } from '@taiga-ui/kit';
import { ApiService } from '../../../core/services/api.service';
import { ProjectMetadata, ReportsListResponse } from '../../../core/models/project.model';

@Component({
  selector: 'app-project-detail',
  standalone: true,
  imports: [
    CommonModule,
    TuiButton,
    TuiLoader,
    TuiTabs,
    TuiAccordion,
    TuiBadge,
  ],
  template: `
    <div class="project-detail-container">
      @if (loading()) {
        <tui-loader />
      } @else if (project()) {
        <div class="project-header">
          <h1>{{ project()!.project_name || project()!.filename }}</h1>

          <div class="project-meta">
            <tui-badge [status]="getStatusColor()">
              {{ project()!.processing_status }}
            </tui-badge>

            <div class="info-item">
              <strong>Upload Date:</strong> {{ project()!.upload_date | date:'medium' }}
            </div>

            @if (project()!.aps_count) {
              <div class="info-item">
                <strong>Access Points:</strong> {{ project()!.aps_count }}
              </div>
            }

            @if (project()!.buildings_count) {
              <div class="info-item">
                <strong>Buildings:</strong> {{ project()!.buildings_count }}
              </div>
            }

            @if (project()!.floors_count) {
              <div class="info-item">
                <strong>Floors:</strong> {{ project()!.floors_count }}
              </div>
            }
          </div>

          <div class="actions">
            <button
              tuiButton
              size="m"
              appearance="primary"
              (click)="downloadOriginal()"
            >
              Download Original .esx
            </button>

            @if (project()!.short_link) {
              <button
                tuiButton
                size="m"
                appearance="secondary"
                (click)="copyShortLink()"
              >
                Copy Short Link
              </button>
            }
          </div>
        </div>

        <tui-tabs [(activeItemIndex)]="activeTab">
          <button tuiTab>Reports</button>
          <button tuiTab>Visualizations</button>
          <button tuiTab>Details</button>
        </tui-tabs>

        <div class="tab-content">
          @switch (activeTab) {
            @case (0) {
              <div class="reports-tab">
                <h2>Reports</h2>
                @if (reports().reports.length > 0) {
                  <ul class="file-list">
                    @for (file of reports().reports; track file) {
                      <li>
                        <span>{{ file }}</span>
                        <button
                          tuiButton
                          size="s"
                          appearance="flat"
                          (click)="downloadReport(file)"
                        >
                          Download
                        </button>
                      </li>
                    }
                  </ul>
                } @else {
                  <p>No reports available yet.</p>
                }
              </div>
            }
            @case (1) {
              <div class="visualizations-tab">
                <h2>Floor Plans</h2>
                @if (reports().visualizations.length > 0) {
                  <div class="visualizations-grid">
                    @for (file of reports().visualizations; track file) {
                      <div class="visualization-card">
                        <img
                          [src]="getVisualizationUrl(file)"
                          [alt]="file"
                          (click)="openVisualizationFullScreen(file)"
                        />
                        <div class="visualization-name">{{ file }}</div>
                      </div>
                    }
                  </div>
                } @else {
                  <p>No visualizations available yet.</p>
                }
              </div>
            }
            @case (2) {
              <div class="details-tab">
                <h2>Processing Details</h2>

                @if (project()!.processing_flags) {
                  <div class="details-section">
                    <h3>Processing Flags</h3>
                    <pre>{{ project()!.processing_flags | json }}</pre>
                  </div>
                }

                @if (project()!.processing_started) {
                  <div class="details-section">
                    <strong>Processing Started:</strong> {{ project()!.processing_started | date:'medium' }}
                  </div>
                }

                @if (project()!.processing_completed) {
                  <div class="details-section">
                    <strong>Processing Completed:</strong> {{ project()!.processing_completed | date:'medium' }}
                  </div>
                }

                @if (project()!.processing_error) {
                  <div class="details-section error">
                    <strong>Error:</strong>
                    <pre>{{ project()!.processing_error }}</pre>
                  </div>
                }
              </div>
            }
          }
        </div>
      }
    </div>
  `,
  styles: [`
    .project-detail-container {
      padding: 2rem;
      max-width: 1400px;
      margin: 0 auto;
    }

    .project-header {
      margin-bottom: 2rem;
    }

    .project-meta {
      display: flex;
      gap: 2rem;
      margin: 1rem 0;
      flex-wrap: wrap;
    }

    .info-item {
      display: flex;
      gap: 0.5rem;
    }

    .actions {
      display: flex;
      gap: 1rem;
      margin-top: 1rem;
    }

    .tab-content {
      margin-top: 2rem;
    }

    .file-list {
      list-style: none;
      padding: 0;
    }

    .file-list li {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1rem;
      border-bottom: 1px solid var(--tui-base-03);
    }

    .visualizations-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 2rem;
      margin-top: 1rem;
    }

    .visualization-card {
      border: 1px solid var(--tui-base-03);
      border-radius: 8px;
      overflow: hidden;
      cursor: pointer;
    }

    .visualization-card img {
      width: 100%;
      height: 200px;
      object-fit: cover;
    }

    .visualization-name {
      padding: 0.5rem;
      font-size: 0.875rem;
      text-align: center;
    }

    .details-section {
      margin-bottom: 1.5rem;
    }

    .details-section.error {
      color: var(--tui-status-negative);
    }

    pre {
      background: var(--tui-base-02);
      padding: 1rem;
      border-radius: 4px;
      overflow-x: auto;
    }
  `],
})
export class ProjectDetailComponent implements OnInit {
  private api = inject(ApiService);
  private route = inject(ActivatedRoute);

  project = signal<ProjectMetadata | null>(null);
  reports = signal<ReportsListResponse>({ reports: [], visualizations: [] });
  loading = signal<boolean>(true);
  activeTab = 0;

  ngOnInit() {
    const projectId = this.route.snapshot.paramMap.get('id');
    const shortLink = this.route.snapshot.paramMap.get('shortLink');

    if (projectId) {
      this.loadProject(projectId);
    } else if (shortLink) {
      this.loadProjectByShortLink(shortLink);
    }
  }

  loadProject(projectId: string) {
    this.api.getProject(projectId).subscribe({
      next: (data) => {
        this.project.set(data);
        this.loadReports(projectId);
        this.loading.set(false);
      },
      error: (error) => {
        console.error('Failed to load project:', error);
        this.loading.set(false);
      },
    });
  }

  loadProjectByShortLink(shortLink: string) {
    this.api.getProjectByShortLink(shortLink).subscribe({
      next: (data) => {
        this.project.set(data);
        this.loadReports(data.project_id);
        this.loading.set(false);
      },
      error: (error) => {
        console.error('Failed to load project by short link:', error);
        this.loading.set(false);
      },
    });
  }

  loadReports(projectId: string) {
    this.api.listReports(projectId).subscribe({
      next: (data) => {
        this.reports.set(data);
      },
      error: (error) => {
        console.error('Failed to load reports:', error);
      },
    });
  }

  downloadReport(filename: string) {
    const url = this.api.getReportDownloadUrl(this.project()!.project_id, filename);
    window.open(url, '_blank');
  }

  downloadOriginal() {
    const url = this.api.getOriginalDownloadUrl(this.project()!.project_id);
    window.open(url, '_blank');
  }

  getVisualizationUrl(filename: string): string {
    return this.api.getVisualizationUrl(this.project()!.project_id, filename);
  }

  openVisualizationFullScreen(filename: string) {
    const url = this.getVisualizationUrl(filename);
    window.open(url, '_blank');
  }

  copyShortLink() {
    if (this.project()?.short_link) {
      const url = `${window.location.origin}/s/${this.project()!.short_link}`;
      navigator.clipboard.writeText(url);
      alert('Short link copied to clipboard!');
    }
  }

  getStatusColor(): string {
    const status = this.project()?.processing_status;
    switch (status) {
      case 'completed':
        return 'success';
      case 'processing':
        return 'warning';
      case 'failed':
        return 'error';
      default:
        return 'neutral';
    }
  }
}
```

**Чек-лист:**
- [x] ✅ Создан project-detail.component
- [x] ✅ Реализовано отображение метаданных проекта
- [x] ✅ Реализованы вкладки для отчётов/визуализаций/деталей
- [x] ✅ Реализовано скачивание отчётов
- [x] ✅ Реализован просмотр визуализаций поэтажных планов с **Lightbox** (2025-11-02)
- [x] ✅ Добавлен доступ по короткой ссылке

---

### Step 3.7: Routing Configuration
**Время:** 1 час

**src/app/features/admin/admin.routes.ts:**
```typescript
import { Routes } from '@angular/router';

export const ADMIN_ROUTES: Routes = [
  {
    path: 'upload',
    loadComponent: () =>
      import('./upload/upload.component').then(m => m.UploadComponent),
  },
  {
    path: 'process/:id',
    loadComponent: () =>
      import('./processing/processing.component').then(m => m.ProcessingComponent),
  },
];
```

**src/app/features/projects/projects.routes.ts:**
```typescript
import { Routes } from '@angular/router';

export const PROJECTS_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./list/projects-list.component').then(m => m.ProjectsListComponent),
  },
  {
    path: ':id',
    loadComponent: () =>
      import('./detail/project-detail.component').then(m => m.ProjectDetailComponent),
  },
];
```

**Чек-лист:**
- [x] ✅ Созданы роуты для admin модуля
- [x] ✅ Созданы роуты для projects модуля
- [x] ✅ Проверена навигация между страницами

---

## 🔐 Phase 3.8: Authentication & Authorization (2-3 дня)

**Status:** 📋 Planned (Not Started)
**Цель:** Разделение доступа на администраторов и пользователей с изоляцией short links

### Архитектура и требования

#### 1. Роли пользователей
- **Administrator** - полный доступ ко всем функциям
  - Загрузка и удаление проектов
  - Настройка обработки
  - Просмотр всех проектов
  - Управление short links

- **Short Link User** - ограниченный доступ только к одному проекту
  - Доступ только по короткой ссылке `/s/{shortLink}`
  - Просмотр одного конкретного проекта
  - Скачивание отчётов
  - **ЗАПРЕЩЕНО:**
    - Переход на список всех проектов
    - Просмотр других проектов
    - Доступ к админ панели
    - Навигация через меню

#### 2. Изоляция Short Link режима

**Требования:**
- По короткой ссылке пользователь видит ТОЛЬКО один проект
- Отсутствует навигация "Back to Projects"
- Отключено главное меню навигации
- Нельзя изменить URL и перейти на другой проект
- При попытке доступа к `/projects` - редирект на 404 или login

**Frontend изменения:**

**src/app/core/guards/short-link.guard.ts** (новый файл):
```typescript
import { Injectable, inject } from '@angular/core';
import { CanActivate, Router, ActivatedRouteSnapshot } from '@angular/router';

@Injectable({ providedIn: 'root' })
export class ShortLinkGuard implements CanActivate {
  private router = inject(Router);

  canActivate(route: ActivatedRouteSnapshot): boolean {
    // Check if we're in short link mode
    const isShortLink = sessionStorage.getItem('short_link_mode') === 'true';

    if (isShortLink) {
      // If in short link mode, block access to other routes
      const allowedPaths = ['s'];
      const currentPath = route.url[0]?.path;

      if (!allowedPaths.includes(currentPath)) {
        this.router.navigate(['/forbidden']);
        return false;
      }
    }

    return true;
  }
}
```

**src/app/features/projects/detail/project-detail.component.ts** (обновить):
```typescript
export class ProjectDetailComponent implements OnInit {
  // ... existing code ...

  // New: detect short link mode
  isShortLinkMode = signal<boolean>(false);

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      if (params['shortLink']) {
        // We're in short link mode
        this.isShortLinkMode.set(true);
        sessionStorage.setItem('short_link_mode', 'true');
        this.loadProjectByShortLink(params['shortLink']);
      } else if (params['id']) {
        // Normal mode
        this.isShortLinkMode.set(false);
        sessionStorage.removeItem('short_link_mode');
        this.projectId = params['id'];
        this.loadProject();
      }
    });
  }

  // New: method to check if navigation should be shown
  canNavigate(): boolean {
    return !this.isShortLinkMode();
  }
}
```

**src/app/features/projects/detail/project-detail.component.html** (обновить):
```html
<!-- Header actions - только для обычного режима -->
@if (!isShortLinkMode()) {
  <div class="header-actions">
    <button tuiButton appearance="ghost" size="s" routerLink="/projects">
      <tui-icon icon="@tui.arrow-left"></tui-icon>
      Back to Projects
    </button>
    <button tuiButton appearance="secondary" size="s" (click)="copyShortLink()">
      <tui-icon icon="@tui.link"></tui-icon>
      Copy Short Link
    </button>
  </div>
}

<!-- В short link режиме показываем только информацию о проекте -->
@if (isShortLinkMode()) {
  <div class="short-link-banner">
    <tui-icon icon="@tui.info"></tui-icon>
    <span>You are viewing this project via a shared link</span>
  </div>
}
```

**src/app/app.component.html** (обновить):
```html
<tui-root>
  <header class="header">
    <div class="header-content">
      <h1>Ekahau BOM Registry</h1>

      <!-- Навигационное меню - скрыть в short link режиме -->
      @if (!isShortLinkMode()) {
        <nav class="nav-menu">
          <a tuiButton appearance="flat" routerLink="/projects" routerLinkActive="active">
            <tui-icon icon="@tui.folder"></tui-icon>
            Projects
          </a>
          <a tuiButton appearance="flat" routerLink="/admin/upload" routerLinkActive="active">
            <tui-icon icon="@tui.upload"></tui-icon>
            Upload
          </a>
          <a tuiButton appearance="flat" routerLink="/admin/processing" routerLinkActive="active">
            <tui-icon icon="@tui.settings"></tui-icon>
            Processing
          </a>
        </nav>
      }
    </div>
  </header>

  <main class="main-content">
    <router-outlet></router-outlet>
  </main>
</tui-root>
```

**src/app/app.component.ts** (обновить):
```typescript
export class AppComponent {
  // Check if we're in short link mode
  isShortLinkMode = signal<boolean>(false);

  constructor(private router: Router) {
    // Watch for route changes
    this.router.events.subscribe(event => {
      if (event instanceof NavigationEnd) {
        const shortLinkMode = sessionStorage.getItem('short_link_mode') === 'true';
        this.isShortLinkMode.set(shortLinkMode);
      }
    });
  }
}
```

#### 3. Аутентификация для админ панели

**Backend: app/auth.py** (новый файл):
```python
"""Simple authentication for admin panel."""
from datetime import datetime, timedelta, UTC
from typing import Optional
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import secrets

# Security scheme
security = HTTPBearer()

# Configuration (в production читать из .env)
SECRET_KEY = secrets.token_urlsafe(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

# Simple admin credentials (в production хранить в БД с хешированием)
ADMIN_CREDENTIALS = {
    "admin": "change_me_in_production"  # username: password
}

def create_access_token(username: str) -> str:
    """Create JWT access token."""
    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": username, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """Verify JWT token and return username."""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def verify_admin(username: str = Depends(verify_token)) -> str:
    """Verify that user is an admin."""
    if username not in ADMIN_CREDENTIALS:
        raise HTTPException(status_code=403, detail="Admin access required")
    return username
```

**Backend: app/api/auth.py** (новый файл):
```python
"""Authentication endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.auth import create_access_token, ADMIN_CREDENTIALS

router = APIRouter(prefix="/auth", tags=["Authentication"])

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Admin login endpoint."""
    # Verify credentials
    if (request.username not in ADMIN_CREDENTIALS or
        ADMIN_CREDENTIALS[request.username] != request.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Create access token
    access_token = create_access_token(request.username)

    return TokenResponse(access_token=access_token)

@router.post("/logout")
async def logout():
    """Logout endpoint (client-side token removal)."""
    return {"message": "Logged out successfully"}
```

**Backend: app/api/upload.py, projects.py** (обновить):
```python
from app.auth import verify_admin
from fastapi import Depends

# Добавить защиту к admin endpoints
@router.post("/api/upload")
async def upload_project(
    file: UploadFile,
    _admin: str = Depends(verify_admin)  # ← Требует авторизации
):
    # ... existing code ...

@router.delete("/api/projects/{project_id}")
async def delete_project(
    project_id: UUID,
    _admin: str = Depends(verify_admin)  # ← Требует авторизации
):
    # ... existing code ...
```

**Frontend: src/app/core/services/auth.service.ts** (новый файл):
```typescript
import { Injectable, signal, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';

interface LoginRequest {
  username: string;
  password: string;
}

interface TokenResponse {
  access_token: string;
  token_type: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private http = inject(HttpClient);
  private router = inject(Router);

  isAuthenticated = signal<boolean>(false);

  constructor() {
    // Check if token exists on init
    const token = localStorage.getItem('admin_token');
    this.isAuthenticated.set(!!token);
  }

  login(username: string, password: string): Observable<TokenResponse> {
    return this.http.post<TokenResponse>('/api/auth/login', { username, password })
      .pipe(
        tap(response => {
          localStorage.setItem('admin_token', response.access_token);
          this.isAuthenticated.set(true);
        })
      );
  }

  logout(): void {
    localStorage.removeItem('admin_token');
    this.isAuthenticated.set(false);
    this.router.navigate(['/login']);
  }

  getToken(): string | null {
    return localStorage.getItem('admin_token');
  }
}
```

**Frontend: src/app/core/interceptors/auth.interceptor.ts** (новый файл):
```typescript
import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { AuthService } from '../services/auth.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);
  const token = authService.getToken();

  // Add token to admin requests
  if (token && (req.url.includes('/admin') || req.url.includes('/upload'))) {
    const cloned = req.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`
      }
    });
    return next(cloned);
  }

  return next(req);
};
```

**Frontend: src/app/core/guards/admin.guard.ts** (новый файл):
```typescript
import { Injectable, inject } from '@angular/core';
import { CanActivate, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

@Injectable({ providedIn: 'root' })
export class AdminGuard implements CanActivate {
  private authService = inject(AuthService);
  private router = inject(Router);

  canActivate(): boolean {
    if (this.authService.isAuthenticated()) {
      return true;
    }

    // Redirect to login
    this.router.navigate(['/login']);
    return false;
  }
}
```

**Frontend: src/app/features/auth/login/login.component.ts** (новый файл):
```typescript
import { Component, signal, inject } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { TuiButton, TuiError } from '@taiga-ui/core';
import { TuiFieldErrorPipe } from '@taiga-ui/kit';
import { TuiInputModule, TuiInputPasswordModule } from '@taiga-ui/legacy';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    TuiButton,
    TuiInputModule,
    TuiInputPasswordModule,
    TuiError,
    TuiFieldErrorPipe
  ],
  template: `
    <div class="login-container">
      <div class="login-card">
        <h2>Admin Login</h2>
        <form [formGroup]="loginForm" (ngSubmit)="onSubmit()">
          <tui-input formControlName="username">
            Username
            <input tuiTextfield />
          </tui-input>

          <tui-input-password formControlName="password">
            Password
          </tui-input-password>

          @if (error()) {
            <div class="error-message">{{ error() }}</div>
          }

          <button
            tuiButton
            type="submit"
            appearance="primary"
            size="l"
            [disabled]="loginForm.invalid || loading()"
          >
            {{ loading() ? 'Logging in...' : 'Login' }}
          </button>
        </form>
      </div>
    </div>
  `,
  styles: [`
    .login-container {
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      background: var(--tui-base-01);
    }

    .login-card {
      width: 400px;
      padding: 2rem;
      background: var(--tui-base-02);
      border-radius: 8px;
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    }

    h2 {
      margin-bottom: 1.5rem;
      text-align: center;
    }

    form {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .error-message {
      color: var(--tui-error-fill);
      font-size: 0.875rem;
    }
  `]
})
export class LoginComponent {
  private authService = inject(AuthService);
  private router = inject(Router);

  loading = signal(false);
  error = signal<string | null>(null);

  loginForm = new FormGroup({
    username: new FormControl('', [Validators.required]),
    password: new FormControl('', [Validators.required])
  });

  onSubmit(): void {
    if (this.loginForm.invalid) return;

    const { username, password } = this.loginForm.value;

    this.loading.set(true);
    this.error.set(null);

    this.authService.login(username!, password!).subscribe({
      next: () => {
        this.loading.set(false);
        this.router.navigate(['/admin/upload']);
      },
      error: (err) => {
        this.loading.set(false);
        this.error.set('Invalid username or password');
        console.error('Login error:', err);
      }
    });
  }
}
```

**Frontend: src/app/app.routes.ts** (обновить):
```typescript
import { Routes } from '@angular/router';
import { AdminGuard } from './core/guards/admin.guard';
import { ShortLinkGuard } from './core/guards/short-link.guard';

export const routes: Routes = [
  {
    path: '',
    redirectTo: '/projects',
    pathMatch: 'full',
  },
  {
    path: 'login',
    loadComponent: () =>
      import('./features/auth/login/login.component').then(
        (m) => m.LoginComponent
      ),
  },
  {
    path: 'projects',
    canActivate: [ShortLinkGuard],  // ← Блокирует доступ из short link режима
    loadComponent: () =>
      import('./features/projects/list/projects-list.component').then(
        (m) => m.ProjectsListComponent
      ),
  },
  {
    path: 'projects/:id',
    canActivate: [ShortLinkGuard],  // ← Блокирует доступ из short link режима
    loadComponent: () =>
      import('./features/projects/detail/project-detail.component').then(
        (m) => m.ProjectDetailComponent
      ),
  },
  {
    path: 'admin',
    canActivate: [AdminGuard],  // ← Требует авторизации
    children: [
      {
        path: 'upload',
        loadComponent: () =>
          import('./features/admin/upload/upload.component').then(
            (m) => m.UploadComponent
          ),
      },
      {
        path: 'processing',
        loadComponent: () =>
          import('./features/admin/processing/processing.component').then(
            (m) => m.ProcessingComponent
          ),
      },
      {
        path: '',
        redirectTo: 'upload',
        pathMatch: 'full',
      },
    ],
  },
  {
    path: 's/:shortLink',
    loadComponent: () =>
      import('./features/projects/detail/project-detail.component').then(
        (m) => m.ProjectDetailComponent
      ),
  },
  {
    path: 'forbidden',
    loadComponent: () =>
      import('./features/error/forbidden.component').then(
        (m) => m.ForbiddenComponent
      ),
  },
  {
    path: '**',
    redirectTo: '/projects',
  },
];
```

**Frontend: src/app/app.config.ts** (обновить):
```typescript
import { ApplicationConfig } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideAnimations } from '@angular/platform-browser/animations';

import { routes } from './app.routes';
import { authInterceptor } from './core/interceptors/auth.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),
    provideHttpClient(
      withInterceptors([authInterceptor])  // ← Добавить auth interceptor
    ),
    provideAnimations()
  ]
};
```

#### 4. Security considerations

**Best practices:**
1. **JWT токены:**
   - Используйте короткий срок жизни (8 часов)
   - Храните SECRET_KEY в переменных окружения
   - В production используйте refresh tokens

2. **Пароли:**
   - В production хранить хеши паролей (bcrypt)
   - Использовать БД для хранения пользователей
   - Добавить rate limiting на /login endpoint

3. **Short links:**
   - Проверять expiry на каждый запрос
   - Логировать доступы для аудита
   - Возможность отозвать (revoke) ссылку

4. **CORS:**
   - Настроить allowed origins
   - Не использовать `*` в production

**Backend: app/config.py** (обновить):
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ... existing settings ...

    # Authentication
    jwt_secret_key: str = "CHANGE_ME_IN_PRODUCTION"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    # Admin credentials (в production использовать БД)
    admin_username: str = "admin"
    admin_password_hash: str = "hashed_password_here"

    class Config:
        env_file = ".env"
```

**Чек-лист Phase 3.8:**
- [ ] Создан ShortLinkGuard для изоляции short link режима
- [ ] Обновлён ProjectDetailComponent с определением режима
- [ ] Скрыта навигация в short link режиме
- [ ] Создан AuthService для работы с JWT
- [ ] Создан AdminGuard для защиты админ роутов
- [ ] Создан auth interceptor для добавления токенов
- [ ] Создан LoginComponent
- [ ] Backend: добавлен auth.py с JWT логикой
- [ ] Backend: добавлены /api/auth/login и /logout endpoints
- [ ] Backend: защищены admin endpoints (upload, delete)
- [ ] Обновлены роуты с guards
- [ ] Создан ForbiddenComponent для ошибок доступа
- [ ] Добавлены переменные окружения для JWT

---

## 🧪 Phase 4: Testing & Integration (2 дня)

**Status:** ⏳ In Progress
- ✅ Step 4.1: Backend тесты (69 tests passing)
- ⏳ Step 4.2: Frontend тесты (pending)
- ✅ Step 4.3: E2E тестирование (Playwright MCP, 5 screenshots)
- ⏳ Step 4.4: Authentication & Authorization тесты (pending - after Phase 3.8)

---

### Step 4.1: Backend тесты
**Время:** 4 часа

**tests/test_storage.py:**
```python
import pytest
from uuid import uuid4
from app.services.storage import storage_service
from app.models import ProjectMetadata, ProcessingStatus

@pytest.fixture
def sample_metadata():
    return ProjectMetadata(
        project_id=uuid4(),
        filename="test.esx",
        file_size=1024,
        processing_status=ProcessingStatus.PENDING,
        original_file="projects/test/original.esx",
    )

def test_save_and_load_metadata(sample_metadata, tmp_path):
    # Override projects_dir for testing
    storage_service.projects_dir = tmp_path

    # Save metadata
    storage_service.save_metadata(sample_metadata.project_id, sample_metadata)

    # Load metadata
    loaded = storage_service.load_metadata(sample_metadata.project_id)

    assert loaded is not None
    assert loaded.project_id == sample_metadata.project_id
    assert loaded.filename == sample_metadata.filename
```

**tests/test_api.py:**
```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()

def test_list_projects():
    response = client.get("/api/projects")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

**Чек-лист:**
- [x] Написаны тесты для StorageService ✅ (2 tests fixed)
- [x] Написаны тесты для IndexService ✅ (already had 15 tests)
- [x] Написаны тесты для API endpoints ✅ (23 new tests in test_api.py)
- [x] Все тесты проходят: `pytest tests/` ✅ (69/69 passing)

---

### Step 4.2: Frontend тесты
**Время:** 3 часа

**src/app/core/services/api.service.spec.ts:**
```typescript
import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { ApiService } from './api.service';

describe('ApiService', () => {
  let service: ApiService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [ApiService],
    });

    service = TestBed.inject(ApiService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should fetch projects list', () => {
    const mockProjects = [
      {
        project_id: '123',
        project_name: 'Test Project',
        filename: 'test.esx',
        upload_date: '2025-10-31',
        processing_status: 'completed',
      },
    ];

    service.listProjects().subscribe((projects) => {
      expect(projects.length).toBe(1);
      expect(projects[0].project_name).toBe('Test Project');
    });

    const req = httpMock.expectOne('/api/projects?skip=0&limit=100');
    expect(req.request.method).toBe('GET');
    req.flush(mockProjects);
  });
});
```

**Чек-лист:**
- [ ] Написаны unit тесты для ApiService
- [ ] Написаны тесты для ключевых компонентов
- [ ] Все тесты проходят: `npm test`

---

### Step 4.3: End-to-End тестирование
**Время:** 3 часа

**Сценарий E2E тестирования:**
1. ✅ Запустить Backend: `uvicorn app.main:app --port 8001`
2. ✅ Запустить Frontend: `npm start`
3. ✅ Протестировано с Playwright MCP:
   - [x] Загрузку .esx файла ✅
   - [x] Настройку параметров обработки ✅
   - [x] Запуск обработки ✅
   - [x] Просмотр списка проектов ✅ (screenshot: 01-projects-list.png)
   - [x] Просмотр деталей проекта ✅ (screenshot: 02-project-detail-overview.png)
   - [x] Скачивание отчётов ✅ (verified 8 reports available)
   - [x] Просмотр визуализаций ✅ (screenshot: 04-project-detail-visualizations.png)
   - [x] Копирование короткой ссылки ✅ (verified in UI)
   - [x] Доступ по короткой ссылке ✅
   - [x] Удаление проекта ✅ (delete button verified)

**Чек-лист E2E:**
- [x] Полный цикл upload → process → view работает ✅
- [x] Все отчёты генерируются корректно ✅ (8 files: CSV, Excel, HTML, PDF, JSON)
- [x] Визуализации отображаются корректно ✅ (floor plans with Lightbox)
- [x] Short links работают ✅
- [x] Обработка ошибок работает корректно ✅

**E2E Testing Screenshots** (saved in `.playwright-mcp/output/test/playwright/`):
- 01-projects-list.png - Projects list with statistics (3 projects)
- 02-project-detail-overview.png - Overview tab with metadata
- 03-project-detail-reports.png - Reports tab (8 files)
- 04-project-detail-visualizations.png - Visualizations tab
- 05-lightbox-fullscreen.png - Lightbox modal with floor plan

---

### Step 4.4: Authentication & Authorization тесты
**Время:** 3 часа
**Prerequisite:** Phase 3.8 должен быть завершён

#### Backend тесты (pytest)

**tests/test_auth.py** (новый файл):
```python
"""Tests for authentication and authorization."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_login_success():
    """Test successful admin login."""
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "change_me_in_production"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_credentials():
    """Test login with invalid credentials."""
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "wrong_password"}
    )
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]

def test_login_nonexistent_user():
    """Test login with non-existent user."""
    response = client.post(
        "/api/auth/login",
        json={"username": "hacker", "password": "password"}
    )
    assert response.status_code == 401

def test_protected_endpoint_without_token():
    """Test accessing protected endpoint without token."""
    response = client.post("/api/upload")
    assert response.status_code == 403  # или 401, зависит от настройки

def test_protected_endpoint_with_invalid_token():
    """Test accessing protected endpoint with invalid token."""
    headers = {"Authorization": "Bearer invalid_token"}
    response = client.delete("/api/projects/some-uuid", headers=headers)
    assert response.status_code == 401
    assert "Invalid token" in response.json()["detail"]

def test_protected_endpoint_with_valid_token():
    """Test accessing protected endpoint with valid token."""
    # First, login to get token
    login_response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "change_me_in_production"}
    )
    token = login_response.json()["access_token"]

    # Try to access protected endpoint (use a safe one for testing)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/projects", headers=headers)
    assert response.status_code == 200

def test_token_expiry():
    """Test that expired tokens are rejected."""
    # This requires mocking time or creating an expired token
    import jwt
    from datetime import datetime, timedelta, UTC
    from app.auth import SECRET_KEY, ALGORITHM

    expired_token = jwt.encode(
        {"sub": "admin", "exp": datetime.now(UTC) - timedelta(hours=1)},
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    headers = {"Authorization": f"Bearer {expired_token}"}
    response = client.delete("/api/projects/some-uuid", headers=headers)
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()

def test_logout():
    """Test logout endpoint."""
    response = client.post("/api/auth/logout")
    assert response.status_code == 200
    assert response.json()["message"] == "Logged out successfully"
```

**tests/test_short_links.py** (обновить существующий):
```python
def test_short_link_expiry_check():
    """Test that expired short links return 410 Gone."""
    from app.services.short_links import ShortLinkManager
    from datetime import datetime, timedelta, UTC

    manager = ShortLinkManager()

    # Create expired link
    expired_date = datetime.now(UTC) - timedelta(days=1)
    expired_link = "expired123"

    # Simulate checking expired link
    is_expired = manager.is_expired(expired_link, expired_date)
    assert is_expired == True

def test_short_link_not_expired():
    """Test that non-expired short links work."""
    from app.services.short_links import ShortLinkManager
    from datetime import datetime, timedelta, UTC

    manager = ShortLinkManager()

    # Create future expiry
    future_date = datetime.now(UTC) + timedelta(days=10)
    link = "valid123"

    is_expired = manager.is_expired(link, future_date)
    assert is_expired == False
```

**tests/test_api.py** (добавить тесты):
```python
def test_get_project_by_short_link_expired():
    """Test accessing project via expired short link."""
    # Setup: Create project with expired link
    # Mock the expiry date in metadata
    response = client.get("/api/projects/short/expired_link_here")
    assert response.status_code == 410  # Gone
    assert "expired" in response.json()["detail"].lower()

def test_get_project_by_short_link_valid():
    """Test accessing project via valid short link."""
    # Setup: Use existing test project with valid link
    response = client.get("/api/projects/short/valid_test_link")
    assert response.status_code == 200
    data = response.json()
    assert "project_id" in data
    assert "short_link" in data
```

#### Frontend тесты (Jasmine/Karma)

**src/app/core/services/auth.service.spec.ts**:
```typescript
import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { AuthService } from './auth.service';

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [AuthService]
    });

    service = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);

    // Clear localStorage
    localStorage.clear();
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should login successfully and store token', () => {
    const mockResponse = {
      access_token: 'test_token_123',
      token_type: 'bearer'
    };

    service.login('admin', 'password').subscribe(response => {
      expect(response.access_token).toBe('test_token_123');
      expect(localStorage.getItem('admin_token')).toBe('test_token_123');
      expect(service.isAuthenticated()).toBe(true);
    });

    const req = httpMock.expectOne('/api/auth/login');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ username: 'admin', password: 'password' });
    req.flush(mockResponse);
  });

  it('should handle login error', () => {
    service.login('admin', 'wrong').subscribe({
      error: (error) => {
        expect(error.status).toBe(401);
        expect(localStorage.getItem('admin_token')).toBeNull();
        expect(service.isAuthenticated()).toBe(false);
      }
    });

    const req = httpMock.expectOne('/api/auth/login');
    req.flush({ detail: 'Invalid credentials' }, { status: 401, statusText: 'Unauthorized' });
  });

  it('should logout and clear token', () => {
    // Setup: store token first
    localStorage.setItem('admin_token', 'test_token');
    service.isAuthenticated.set(true);

    // Logout
    service.logout();

    expect(localStorage.getItem('admin_token')).toBeNull();
    expect(service.isAuthenticated()).toBe(false);
  });

  it('should get stored token', () => {
    localStorage.setItem('admin_token', 'stored_token');
    expect(service.getToken()).toBe('stored_token');
  });

  it('should return null when no token stored', () => {
    expect(service.getToken()).toBeNull();
  });
});
```

**src/app/core/guards/admin.guard.spec.ts**:
```typescript
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { AdminGuard } from './admin.guard';
import { AuthService } from '../services/auth.service';

describe('AdminGuard', () => {
  let guard: AdminGuard;
  let authService: jasmine.SpyObj<AuthService>;
  let router: jasmine.SpyObj<Router>;

  beforeEach(() => {
    const authServiceSpy = jasmine.createSpyObj('AuthService', ['isAuthenticated']);
    const routerSpy = jasmine.createSpyObj('Router', ['navigate']);

    TestBed.configureTestingModule({
      providers: [
        AdminGuard,
        { provide: AuthService, useValue: authServiceSpy },
        { provide: Router, useValue: routerSpy }
      ]
    });

    guard = TestBed.inject(AdminGuard);
    authService = TestBed.inject(AuthService) as jasmine.SpyObj<AuthService>;
    router = TestBed.inject(Router) as jasmine.SpyObj<Router>;
  });

  it('should be created', () => {
    expect(guard).toBeTruthy();
  });

  it('should allow access when authenticated', () => {
    authService.isAuthenticated.and.returnValue(true);

    expect(guard.canActivate()).toBe(true);
    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('should block access and redirect when not authenticated', () => {
    authService.isAuthenticated.and.returnValue(false);

    expect(guard.canActivate()).toBe(false);
    expect(router.navigate).toHaveBeenCalledWith(['/login']);
  });
});
```

**src/app/core/guards/short-link.guard.spec.ts**:
```typescript
import { TestBed } from '@angular/core/testing';
import { Router, ActivatedRouteSnapshot } from '@angular/router';
import { ShortLinkGuard } from './short-link.guard';

describe('ShortLinkGuard', () => {
  let guard: ShortLinkGuard;
  let router: jasmine.SpyObj<Router>;

  beforeEach(() => {
    const routerSpy = jasmine.createSpyObj('Router', ['navigate']);

    TestBed.configureTestingModule({
      providers: [
        ShortLinkGuard,
        { provide: Router, useValue: routerSpy }
      ]
    });

    guard = TestBed.inject(ShortLinkGuard);
    router = TestBed.inject(Router) as jasmine.SpyObj<Router>;

    // Clear sessionStorage
    sessionStorage.clear();
  });

  it('should be created', () => {
    expect(guard).toBeTruthy();
  });

  it('should allow access when not in short link mode', () => {
    const mockRoute = {
      url: [{ path: 'projects' }]
    } as any as ActivatedRouteSnapshot;

    expect(guard.canActivate(mockRoute)).toBe(true);
    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('should block access to projects when in short link mode', () => {
    sessionStorage.setItem('short_link_mode', 'true');

    const mockRoute = {
      url: [{ path: 'projects' }]
    } as any as ActivatedRouteSnapshot;

    expect(guard.canActivate(mockRoute)).toBe(false);
    expect(router.navigate).toHaveBeenCalledWith(['/forbidden']);
  });

  it('should allow access to /s/ when in short link mode', () => {
    sessionStorage.setItem('short_link_mode', 'true');

    const mockRoute = {
      url: [{ path: 's' }]
    } as any as ActivatedRouteSnapshot;

    expect(guard.canActivate(mockRoute)).toBe(true);
    expect(router.navigate).not.toHaveBeenCalled();
  });
});
```

**src/app/core/interceptors/auth.interceptor.spec.ts**:
```typescript
import { TestBed } from '@angular/core/testing';
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { authInterceptor } from './auth.interceptor';
import { AuthService } from '../services/auth.service';

describe('authInterceptor', () => {
  let httpMock: HttpTestingController;
  let httpClient: HttpClient;
  let authService: AuthService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
        AuthService
      ]
    });

    httpMock = TestBed.inject(HttpTestingController);
    httpClient = TestBed.inject(HttpClient);
    authService = TestBed.inject(AuthService);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should add Authorization header to admin requests', () => {
    spyOn(authService, 'getToken').and.returnValue('test_token_123');

    httpClient.get('/api/admin/something').subscribe();

    const req = httpMock.expectOne('/api/admin/something');
    expect(req.request.headers.get('Authorization')).toBe('Bearer test_token_123');
    req.flush({});
  });

  it('should add Authorization header to upload requests', () => {
    spyOn(authService, 'getToken').and.returnValue('test_token_456');

    httpClient.post('/api/upload', {}).subscribe();

    const req = httpMock.expectOne('/api/upload');
    expect(req.request.headers.get('Authorization')).toBe('Bearer test_token_456');
    req.flush({});
  });

  it('should not add Authorization header to public requests', () => {
    spyOn(authService, 'getToken').and.returnValue('test_token_789');

    httpClient.get('/api/projects').subscribe();

    const req = httpMock.expectOne('/api/projects');
    expect(req.request.headers.has('Authorization')).toBe(false);
    req.flush({});
  });

  it('should not add Authorization header when no token', () => {
    spyOn(authService, 'getToken').and.returnValue(null);

    httpClient.post('/api/upload', {}).subscribe();

    const req = httpMock.expectOne('/api/upload');
    expect(req.request.headers.has('Authorization')).toBe(false);
    req.flush({});
  });
});
```

#### E2E тесты с Playwright

**Сценарии для тестирования:**

1. **Admin Login Flow**:
   - Navigate to /admin/upload (should redirect to /login)
   - Enter invalid credentials → error message shown
   - Enter valid credentials → redirected to /admin/upload
   - Verify token stored in localStorage

2. **Protected Routes**:
   - Try to access /admin/upload without login → redirect to /login
   - Login as admin → access granted
   - Logout → redirect to /login
   - Try to access /admin again → redirect to /login

3. **Short Link Isolation**:
   - Navigate to /s/{valid_link}
   - Verify: No navigation menu visible
   - Verify: No "Back to Projects" button
   - Verify: Banner "You are viewing this project via a shared link" shown
   - Try to manually navigate to /projects → redirect to /forbidden
   - Try to access another project by URL → redirect to /forbidden

4. **Short Link Expiry**:
   - Create project with short expiry (mock or wait)
   - Access expired short link → 410 error shown
   - Message: "This link has expired"

**Playwright test example**:
```typescript
// tests/e2e/auth.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test('should redirect to login when accessing admin without auth', async ({ page }) => {
    await page.goto('http://localhost:4200/admin/upload');
    await expect(page).toHaveURL(/\/login/);
  });

  test('should login successfully with valid credentials', async ({ page }) => {
    await page.goto('http://localhost:4200/login');
    await page.fill('input[type="text"]', 'admin');
    await page.fill('input[type="password"]', 'change_me_in_production');
    await page.click('button[type="submit"]');

    await expect(page).toHaveURL(/\/admin\/upload/);

    // Verify token in localStorage
    const token = await page.evaluate(() => localStorage.getItem('admin_token'));
    expect(token).toBeTruthy();
  });

  test('should show error with invalid credentials', async ({ page }) => {
    await page.goto('http://localhost:4200/login');
    await page.fill('input[type="text"]', 'admin');
    await page.fill('input[type="password"]', 'wrong_password');
    await page.click('button[type="submit"]');

    await expect(page.locator('.error-message')).toContainText('Invalid');
  });
});

test.describe('Short Link Isolation', () => {
  test('should hide navigation in short link mode', async ({ page }) => {
    await page.goto('http://localhost:4200/s/test_short_link');

    // Wait for page load
    await page.waitForSelector('h1');

    // Verify navigation menu is hidden
    await expect(page.locator('.nav-menu')).not.toBeVisible();

    // Verify "Back to Projects" button is hidden
    await expect(page.locator('text=Back to Projects')).not.toBeVisible();

    // Verify short link banner is shown
    await expect(page.locator('.short-link-banner')).toContainText('shared link');
  });

  test('should block access to projects list from short link', async ({ page }) => {
    // First, set short link mode
    await page.goto('http://localhost:4200/s/test_short_link');

    // Try to navigate to projects list
    await page.goto('http://localhost:4200/projects');

    // Should be redirected to forbidden
    await expect(page).toHaveURL(/\/forbidden/);
  });
});
```

**Чек-лист Step 4.4:**
- [ ] Backend: тесты для /login endpoint (success, failure)
- [ ] Backend: тесты для protected endpoints (с/без токена)
- [ ] Backend: тесты для token expiry
- [ ] Backend: тесты для short link expiry
- [ ] Frontend: AuthService unit tests
- [ ] Frontend: AdminGuard unit tests
- [ ] Frontend: ShortLinkGuard unit tests
- [ ] Frontend: auth interceptor unit tests
- [ ] E2E: Admin login flow
- [ ] E2E: Protected routes access control
- [ ] E2E: Short link isolation (no navigation)
- [ ] E2E: Short link expiry handling
- [ ] Все тесты проходят: `pytest tests/` (Backend)
- [ ] Все тесты проходят: `ng test` (Frontend)
- [ ] E2E тесты проходят с Playwright

---

## 🚀 Phase 5: Deployment Preparation (1 день)

### Step 5.1: Production конфигурация Backend
**Время:** 2 часа

**backend/.env.production:**
```env
PROJECTS_DIR=/data/projects
INDEX_FILE=/data/index.json
API_PREFIX=/api
MAX_UPLOAD_SIZE=524288000
```

**backend/app/config.py (обновить):**
```python
class Settings(BaseSettings):
    # Environment
    environment: str = "development"  # development | production

    # ... остальные настройки

    # CORS для production
    cors_origins: list[str] = ["http://localhost:4200"]

    class Config:
        env_file = ".env"

settings = Settings()

# Production CORS
if settings.environment == "production":
    settings.cors_origins = [
        "https://ekahau-bom.example.com",
        # Добавить production домены
    ]
```

**Чек-лист:**
- [ ] Создан .env.production
- [ ] Обновлены настройки для production
- [ ] Проверена работа с production переменными

---

### Step 5.2: Production сборка Frontend
**Время:** 1 час

**Build команды:**
```bash
cd frontend/ekahau-bom-ui

# Production build
npm run build -- --configuration=production

# Результат в dist/ekahau-bom-ui/
```

**angular.json (проверить production конфигурацию):**
```json
"configurations": {
  "production": {
    "optimization": true,
    "outputHashing": "all",
    "sourceMap": false,
    "namedChunks": false,
    "extractLicenses": true,
    "budgets": [
      {
        "type": "initial",
        "maximumWarning": "2mb",
        "maximumError": "5mb"
      }
    ]
  }
}
```

**Чек-лист:**
- [ ] Production build успешно создаётся
- [ ] Размер bundle оптимизирован
- [ ] Source maps отключены
- [ ] Asset hashing включен

---

### Step 5.3: Nginx конфигурация
**Время:** 1 час

**nginx.conf:**
```nginx
server {
    listen 80;
    server_name ekahau-bom.example.com;

    # Frontend (Angular)
    location / {
        root /var/www/ekahau-bom-ui;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Для больших файлов
        client_max_body_size 500M;
    }
}
```

**Чек-лист:**
- [ ] Создана nginx конфигурация
- [ ] Проверено проксирование API запросов
- [ ] Настроен client_max_body_size для загрузки файлов

---

## 📚 Phase 6: Documentation (1 день)

### Step 6.1: API документация
**Время:** 2 часа

FastAPI автоматически генерирует Swagger UI:
- http://localhost:8000/docs - Swagger UI
- http://localhost:8000/redoc - ReDoc

**Добавить описания endpoints:**
```python
@router.post("", response_model=UploadResponse, summary="Upload .esx file")
async def upload_project(
    file: UploadFile = File(..., description="Ekahau .esx project file"),
    background_tasks: BackgroundTasks = None,
):
    """
    Upload an Ekahau .esx project file.

    Returns:
        UploadResponse with project_id and short_link
    """
    # ...
```

**Чек-лист:**
- [ ] Все endpoints имеют описания
- [ ] Request/Response модели документированы
- [ ] Примеры запросов добавлены

---

### Step 6.2: User Guide
**Время:** 3 часа

**docs/USER_GUIDE.md:**
```markdown
# Ekahau BOM Web Service - User Guide

## For Administrators

### Uploading Projects
1. Navigate to "Admin" → "Upload"
2. Drag & drop .esx file or click to browse
3. Click "Configure Processing"
4. Select processing options:
   - Group Access Points
   - Output formats (CSV, Excel, HTML)
   - Visualize Floor Plans
5. Click "Start Processing"

### Monitoring Processing
- Processing status visible in Projects list
- Click on project to see detailed status

## For Users

### Viewing Projects
...
```

**Чек-лист:**
- [ ] Создан USER_GUIDE.md
- [ ] Добавлены скриншоты
- [ ] Описаны все основные функции

---

### Step 6.3: Developer Documentation
**Время:** 3 часа

**docs/DEVELOPER.md:**
```markdown
# Developer Documentation

## Architecture
...

## Running Locally
...

## API Reference
...

## Adding New Features
...
```

**Чек-лист:**
- [ ] Создан DEVELOPER.md
- [ ] Описана архитектура
- [ ] Добавлены примеры кода

---

## ✅ Final Checklist

### Backend
- [ ] Все API endpoints работают
- [ ] Файлы загружаются и обрабатываются
- [ ] Метаданные сохраняются корректно
- [ ] Индексация работает
- [ ] Short links генерируются
- [ ] Тесты проходят (coverage >= 70%)

### Frontend
- [ ] Все страницы работают
- [ ] Upload файлов работает
- [ ] Обработка запускается
- [ ] Список проектов отображается
- [ ] Детали проекта отображаются
- [ ] Отчёты скачиваются
- [ ] Визуализации отображаются
- [ ] Short links работают
- [ ] Responsive дизайн

### Integration
- [ ] Backend ↔ Frontend коммуникация работает
- [ ] CORS настроен корректно
- [ ] File upload работает для больших файлов
- [ ] Обработка ошибок работает

### Documentation
- [ ] API документация полная
- [ ] User guide написан
- [ ] Developer documentation написана
- [ ] README.md обновлён

---

## 🎉 Result

После выполнения всех шагов этого плана у вас будет полностью рабочий веб-сервис для Ekahau BOM с:

✅ Административной панелью для загрузки и обработки .esx файлов
✅ Пользовательским интерфейсом для просмотра проектов и отчётов
✅ Системой коротких ссылок для шаринга проектов
✅ REST API для программного доступа
✅ Интерактивными визуализациями поэтажных планов
✅ In-memory индексацией без базы данных

**Готово к Phase 11.6 (Docker контейнеризация)**
