# Руководство пользователя EkahauBOM

Полное руководство по использованию EkahauBOM для генерации спецификаций из проектов Ekahau.

## Содержание

- [Начало работы](#начало-работы)
- [Базовое использование](#базовое-использование)
- [Фильтрация](#фильтрация)
- [Группировка и аналитика](#группировка-и-аналитика)
- [Форматы экспорта](#форматы-экспорта)
- [Метаданные проекта](#метаданные-проекта-новое-в-v250) _(Новое в v2.5.0)_
- [Расчет стоимости](#расчет-стоимости)
- [Пакетная обработка](#пакетная-обработка-новое-в-v300) _(Новое в v3.0.0)_
- [Сравнение проектов](#сравнение-проектов-новое-в-v360) _(Новое в v3.6.0)_
- [Веб-интерфейс](#веб-интерфейс-новое-в-v340) _(Новое в v3.4.0)_
- [Docker](#docker-новое-в-v350) _(Новое в v3.5.0)_
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

## Метаданные проекта _(Новое в v2.5.0)_

### Автоматическое извлечение информации о проекте

EkahauBOM автоматически извлекает метаданные проекта из файла Ekahau и включает их во все форматы экспорта:

**Извлекаемые данные:**
- Название проекта
- Заказчик
- Местоположение
- Ответственное лицо
- Версия схемы Ekahau

### Отображение метаданных в разных форматах

**CSV:**
```csv
# Ekahau BOM - Access Points Bill of Materials
# Project Name: Corporate Office WiFi
# Customer: ACME Corporation
# Location: New York HQ, Building A
# Responsible Person: John Smith
#
"Vendor","Model","Floor","Color","Tags","Quantity"
...
```

**Excel:**
- Секция "Project Information" в Summary листе
- Четко отформатированная с жирным текстом
- Автоматически включается если данные доступны

**HTML:**
- Отформатированная карточка с метаданными в начале отчета
- Профессиональный внешний вид
- Адаптивный дизайн

**JSON:**
```json
{
  "metadata": {
    "file_name": "corporate_office",
    "export_format": "json",
    "version": "2.5.0",
    "project_info": {
      "project_name": "Corporate Office WiFi",
      "customer": "ACME Corporation",
      "location": "New York HQ, Building A",
      "responsible_person": "John Smith",
      "schema_version": "1.4.0"
    }
  }
}
```

**PDF:**
- Секция с информацией о проекте на титульной странице
- Профессиональное форматирование
- Готово для печати

### Заполнение метаданных в Ekahau

Для получения полных метаданных в экспорте, убедитесь что вы заполнили информацию о проекте в Ekahau:

1. Откройте проект в Ekahau AI Pro
2. Перейдите в Project Properties / Project Info
3. Заполните поля:
   - Project Name (Название проекта)
   - Customer (Заказчик)
   - Location (Местоположение)
   - Responsible Person (Ответственное лицо)
4. Сохраните изменения

Метаданные будут автоматически извлечены и включены во все экспортированные отчеты.

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

## Пакетная обработка _(Новое в v3.0.0)_

### Обработка нескольких проектов

Обработка всех .esx файлов в директории:

```bash
# Базовая пакетная обработка
ekahau-bom --batch projects/

# Параллельное выполнение (быстрее)
ekahau-bom --batch projects/ --parallel 4

# С агрегированным отчётом
ekahau-bom --batch projects/ --aggregate-report
```

### Фильтрация файлов

```bash
# Включить только определённые файлы
ekahau-bom --batch projects/ --batch-include "*office*.esx"

# Исключить файлы
ekahau-bom --batch projects/ --batch-exclude "*backup*"
```

### Результат пакетной обработки

При использовании `--aggregate-report` создаётся объединённый BOM со всех проектов.

---

## Сравнение проектов _(Новое в v3.6.0)_

Сравнение двух версий проекта Ekahau для отслеживания изменений в инвентаре точек доступа, размещении и конфигурации. Полезно для:

- Сравнения версий проекта (до/после редизайна)
- Отслеживания изменений со временем
- Определения различий в BOM между версиями
- Визуального "до-после" на планах этажей со стрелками перемещения

### Базовое сравнение

```bash
# Сравнить старую версию с новой
ekahau-bom old_design.esx --compare new_design.esx

# Генерация отчётов сравнения в нескольких форматах
ekahau-bom original.esx --compare updated.esx --format csv,excel,html
```

### Стратегии сопоставления

Управление способом сопоставления AP между проектами:

```bash
# Только по имени (строгое сопоставление)
ekahau-bom old.esx --compare new.esx --match-strategy name

# По координатам (полезно когда AP переименованы)
ekahau-bom old.esx --compare new.esx --match-strategy coordinates

# Комбинированный - сначала имя, затем координаты (по умолчанию, рекомендуется)
ekahau-bom old.esx --compare new.esx --match-strategy combined
```

### Визуальное сравнение

Генерация изображений планов этажей с визуализацией изменений:

```bash
ekahau-bom old.esx --compare new.esx --visualize-floor-plans
```

Визуальное сравнение показывает:
- **Зелёные круги** - Добавленные AP
- **Красные круги** - Удалённые AP
- **Жёлтые круги** - Изменённые AP (изменена конфигурация)
- **Синие→Фиолетовые стрелки** - Перемещённые AP
- **Оранжевые круги** - Переименованные AP

### Определение перемещения

Настройка чувствительности определения перемещения:

```bash
# Порог по умолчанию (0.5 метра)
ekahau-bom old.esx --compare new.esx

# Строгий порог (10 см)
ekahau-bom old.esx --compare new.esx --move-threshold 0.1

# Мягкий порог (1 метр)
ekahau-bom old.esx --compare new.esx --move-threshold 1.0
```

### Отчёты сравнения

Сравнение генерирует специальные отчёты:

**CSV** (`comparison_changes.csv`):
```csv
AP Name,Status,Floor,Details
AP-101,moved,Этаж 1,"Перемещено 5.2м: (10,20) → (15,25)"
AP-102,modified,Этаж 1,"Канал: 36 → 44"
AP-103,removed,Этаж 2,""
AP-104,added,Этаж 2,""
```

**Excel** - Включает лист сводки с количеством изменений и детальную таблицу

**HTML** - Интерактивный отчёт с встроенными изображениями сравнения этажей

### Полный пример

```bash
ekahau-bom original_design.esx \
  --compare updated_design.esx \
  --match-strategy combined \
  --move-threshold 0.3 \
  --format csv,excel,html \
  --visualize-floor-plans \
  --output-dir reports/comparison/
```

---

## Веб-интерфейс _(Новое в v3.4.0)_

EkahauBOM включает веб-интерфейс для удобной работы с проектами.

### Возможности

- **Загрузка перетаскиванием** - Drag & drop .esx файлов
- **Обзор проектов** - Список всех проектов со статусом
- **Отчёты онлайн** - Скачивание CSV, Excel, HTML, PDF, JSON
- **Визуализации** - Интерактивные планы этажей
- **Планировщик** - Автоматическая обработка по расписанию
- **Уведомления** - Email, Slack, Webhooks

### Запуск веб-интерфейса

```bash
# Терминал 1: Backend
cd ekahau_bom_web/backend
./venv/Scripts/activate  # Windows
uvicorn app.main:app --port 8001 --reload

# Терминал 2: Frontend
cd ekahau_bom_web/frontend/ekahau-bom-ui
npm start

# Открыть http://localhost:4200
```

### Аутентификация

**Простой режим (по умолчанию):**
- Логин: `admin`
- Пароль: `admin123`

**OAuth2/SSO (v3.5.0):**
- Поддержка Keycloak, Azure AD, Okta
- Единый вход (SSO)
- Ролевой доступ

### Горячие клавиши

| Клавиша | Действие |
|---------|----------|
| `Alt+U` | Загрузка (админ) |
| `Ctrl+K` или `/` | Поиск |
| `←` `→` | Навигация вкладок |
| `1-4` | Переход к вкладке |

Подробнее: [WEB_UI_GUIDE.ru.md](examples/WEB_UI_GUIDE.ru.md)

---

## Docker _(Новое в v3.5.0)_

### Быстрый запуск

```bash
# Клонировать репозиторий
git clone https://github.com/htechno/EkahauBOM.git
cd EkahauBOM

# Скопировать конфигурацию
cp .env.example .env

# Запустить
docker-compose up --build

# Открыть http://localhost:8080
```

### С Keycloak SSO

```bash
docker-compose -f docker-compose.yml -f docker-compose.keycloak.yml up --build

# Keycloak: http://localhost:8180 (admin/admin)
# Приложение: http://localhost:8080
```

### Переменные окружения

```bash
# .env
AUTH_BACKEND=simple           # или "oauth2"
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
JWT_SECRET_KEY=your-secret

# OAuth2 (если AUTH_BACKEND=oauth2)
OAUTH2_ISSUER=http://localhost:8180/realms/ekahau
OAUTH2_CLIENT_ID=ekahau-bom-web

# Порт приложения
FRONTEND_PORT=8080
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
- **Проблемы**: https://github.com/htechno/EkahauBOM/issues
- **Обсуждения**: https://github.com/htechno/EkahauBOM/discussions
- **Telegram**: [@htechno](https://t.me/htechno)

---

**Версия**: 3.6.0
**Последнее обновление**: 2025-12-16

**Автор**: Pavel Semenischev @htechno
