# Исправление бага: media_group_id переполнение

## 🐛 Проблема

**Ошибка:**
```
asyncpg.exceptions.DataError: invalid input for query argument $7: 14090806734303146 (value out of int32 range)
```

**Причина:**  
Telegram использует очень большие числа для `media_group_id` (до 64-бит), но в модели `Post` поле было объявлено как `Integer` (32-бит, максимум ~2.1 млрд).

Значение `14090806734303146` не помещается в int32.

## ✅ Решение

### 1. Изменена модель
**Файл:** `src/cars_bot/database/models/post.py`

**Было:**
```python
media_group_id: Mapped[Optional[int]] = mapped_column(
    Integer,  # ❌ Только до 2,147,483,647
    nullable=True,
    comment="Telegram grouped_id for media groups (albums)"
)
```

**Стало:**
```python
media_group_id: Mapped[Optional[int]] = mapped_column(
    BigInteger,  # ✅ До 9,223,372,036,854,775,807
    nullable=True,
    comment="Telegram grouped_id for media groups (albums)"
)
```

**Импорты обновлены:**
```python
from sqlalchemy import BigInteger, Boolean, Float, ...
```

### 2. Создана миграция БД

**Файл:** `alembic/versions/2025_10_25_0026-e172e9fe894f_change_media_group_id_to_bigint.py`

```python
def upgrade() -> None:
    op.alter_column(
        'posts',
        'media_group_id',
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True
    )
```

**Применена командой:**
```bash
alembic upgrade head
```

## 📊 Технические детали

### Диапазоны типов:

| Тип | Минимум | Максимум | Telegram ID |
|-----|---------|----------|-------------|
| **INTEGER** (int32) | -2,147,483,648 | 2,147,483,647 | ❌ Недостаточно |
| **BIGINT** (int64) | -9,223,372,036,854,775,808 | 9,223,372,036,854,775,807 | ✅ Достаточно |

### Пример проблемного значения:
```
Telegram media_group_id: 14,090,806,734,303,146
INT32 максимум:           2,147,483,647

14,090,806,734,303,146 > 2,147,483,647 → ОШИБКА!
```

## 🚀 Что теперь работает

✅ Медиа-группы с любыми ID от Telegram сохраняются корректно  
✅ Нет ошибок переполнения при вставке в БД  
✅ Существующие данные сохранены (миграция безопасна)  

## 🧪 Проверка

После применения миграции медиа-группы сохраняются успешно:

```
2025-10-25 03:07:20.366 | INFO | Processing media group 14090806734303146 with 7 messages
✅ SUCCESS - Группа сохранена в БД
```

## 📝 Затронутые файлы

1. ✅ `src/cars_bot/database/models/post.py` - изменен тип поля
2. ✅ `alembic/versions/2025_10_25_0026-e172e9fe894f_change_media_group_id_to_bigint.py` - миграция
3. ✅ База данных - колонка `posts.media_group_id` теперь BIGINT

## ⚠️ Важно

Если вы разворачиваете на новом сервере, не забудьте применить все миграции:

```bash
cd /Users/edgark/CARS\ BOT
source venv/bin/activate
source scripts/export_env.sh
alembic upgrade head
```

## 🎉 Статус

**Исправлено:** ✅  
**Протестировано:** ✅  
**Миграция применена:** ✅  

---

**Дата исправления:** 25 октября 2025  
**Revision ID:** e172e9fe894f


