# Scripts Directory

Коллекция утилит и скриптов для управления Cars Bot.

## Скрипты

### create_session.py

**Назначение**: Создание Telegram User Session для мониторинга каналов.

**Использование**:

```bash
# Создать новую сессию (интерактивно)
python scripts/create_session.py

# Протестировать существующую сессию
python scripts/create_session.py test
```

**Что делает**:
1. Загружает настройки из .env
2. Интерактивно запрашивает номер телефона
3. Отправляет код подтверждения
4. Обрабатывает 2FA (если включен)
5. Создает session файл в `sessions/` директории
6. Сохраняет резервную копию (string session)

**Требования**:
- `TELEGRAM_API_ID` и `TELEGRAM_API_HASH` в .env
- Доступ к Telegram аккаунту

**Output**:
- `sessions/monitor_session.session` - основной файл сессии
- `sessions/monitor_session_backup.txt` - резервная копия

---

### create_sheets_template.py

**Назначение**: Создание шаблона Google Sheets для управления ботом.

**Использование**:

```bash
python scripts/create_sheets_template.py
```

**Что делает**:
- Создает новую Google Таблицу
- Добавляет все необходимые листы
- Настраивает заголовки и форматирование
- Добавляет примеры данных

**Требования**:
- Google Service Account JSON файл
- Настроенный `GOOGLE_CREDENTIALS_FILE` в .env

---

### setup_existing_sheets.py

**Назначение**: Настройка существующей Google Sheets.

**Использование**:

```bash
python scripts/setup_existing_sheets.py
```

**Что делает**:
- Подключается к существующей таблице
- Добавляет недостающие листы
- Обновляет структуру

---

### populate_test_data.py

**Назначение**: Заполнение тестовыми данными для разработки.

**Использование**:

```bash
python scripts/populate_test_data.py
```

**Что делает**:
- Создает тестовые каналы в БД
- Добавляет тестовые посты
- Заполняет Google Sheets примерами

**⚠️ Только для development!**

---

### test_google_sheets.py

**Назначение**: Тестирование подключения к Google Sheets.

**Использование**:

```bash
python scripts/test_google_sheets.py
```

**Что делает**:
- Проверяет доступ к Google Sheets API
- Читает данные из таблицы
- Пишет тестовые данные
- Выводит результаты

---

### run_migrations.py

**Назначение**: Запуск миграций базы данных.

**Использование**:

```bash
# Применить все миграции
python scripts/run_migrations.py upgrade head

# Откатить одну миграцию
python scripts/run_migrations.py downgrade -1

# Показать текущую версию
python scripts/run_migrations.py current
```

---

## Создание Новых Скриптов

При создании новых скриптов следуйте этим рекомендациям:

### 1. Структура

```python
#!/usr/bin/env python3
"""
Short description of the script.

Detailed explanation of what it does.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# Your imports here
from cars_bot.config import get_settings


def main():
    """Main entry point."""
    # Your code here
    pass


if __name__ == "__main__":
    main()
```

### 2. Best Practices

- ✅ Добавляйте shebang (`#!/usr/bin/env python3`)
- ✅ Включайте docstring с описанием
- ✅ Добавляйте project root в Python path
- ✅ Используйте `get_settings()` для конфигурации
- ✅ Обрабатывайте ошибки gracefully
- ✅ Логируйте важные действия
- ✅ Делайте скрипт исполняемым: `chmod +x script.py`

### 3. Логирование

```python
from loguru import logger

logger.info("Starting operation...")
logger.warning("Warning message")
logger.error("Error occurred", exc_info=True)
```

### 4. Async Скрипты

```python
import asyncio

async def async_main():
    """Async main function."""
    # Your async code here
    pass

def main():
    """Entry point."""
    asyncio.run(async_main())
```

### 5. Интерактивность

```python
def confirm(prompt: str) -> bool:
    """Ask user for confirmation."""
    response = input(f"{prompt} (yes/no): ").strip().lower()
    return response in ["yes", "y"]

# Usage
if confirm("Continue with operation?"):
    # Do something
    pass
```

## Debugging

### Enable Debug Mode

```bash
# Set debug level
export LOG_LEVEL=DEBUG

# Run script
python scripts/your_script.py
```

### Common Issues

#### ModuleNotFoundError

```python
# Make sure project root is in path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
```

#### Environment Variables Not Loaded

```python
# Load .env explicitly if needed
from dotenv import load_dotenv
load_dotenv()
```

## Testing Scripts

Рекомендуется создавать тесты для скриптов:

```python
# tests/scripts/test_create_session.py
import pytest
from scripts.create_session import create_session

@pytest.mark.asyncio
async def test_create_session():
    # Your test here
    pass
```

## Документация

Каждый скрипт должен иметь:
1. **Docstring** в начале файла
2. **Usage примеры** в docstring или комментариях
3. **Описание в этом README**
4. **Help message** при вызове с `--help` (если используется argparse)

---

**Обновлено**: 2024-10-23
