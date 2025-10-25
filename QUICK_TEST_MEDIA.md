# Быстрое тестирование публикации медиа

## Как протестировать исправления

### 1. Перезапуск сервисов

```bash
# В папке проекта
cd "/Users/edgark/CARS BOT"

# Остановить Celery
./scripts/stop_celery.sh

# Перезапустить монитор
pkill -f check_monitor.py
sleep 2
nohup python check_monitor.py > logs/monitor_output.log 2>&1 &

# Запустить Celery worker
./scripts/start_celery_worker.sh

# Запустить Celery beat
./scripts/start_celery_beat.sh
```

### 2. Отправка тестового поста

Отправьте в один из мониторимых каналов пост с:

**Вариант 1: Одно фото**
```
Продам BMW X5 2015, 3.0 дизель автомат
Пробег 120к, 1 владелец
Полная комплектация, панорама
Цена 2 млн ₽
@username
```
+ 1 фото машины

**Вариант 2: Видео**
```
Audi A4 2018, идеальное состояние
Полный сервис у дилера
Цена 1.5 млн
```
+ видео машины

**Вариант 3: Несколько фото (медиа-группа)**
```
Mercedes E-класс 2016
Максимальная комплектация
```
+ 3-5 фото

### 3. Мониторинг логов

Откройте 3 терминала:

**Терминал 1: Монитор**
```bash
tail -f logs/monitor_output.log
```
Ожидаемый вывод:
```
✅ Message processed and saved: Post ID=123
💾 Saved post 123 to database (media_files=['photo:...'])
🎯 Queued post 123 for AI processing
```

**Терминал 2: Celery Worker (AI + Publishing)**
```bash
tail -f logs/celery_worker_output.log
```
Ожидаемый вывод:
```
🤖 Processing post 123
✓ AI classification complete
✓ Car data extracted
Attempting to copy message 456 from -1001234567890
✓ Successfully copied message 456
✓ Published post 123: media message 789, caption message 790
Successfully published post 123 to channel
```

**Терминал 3: Bot output**
```bash
tail -f logs/bot_output.log
```

### 4. Проверка результата

Перейдите в ваш **новостной канал** и проверьте:

✅ **Для одного фото/видео:**
- [ ] Медиа скопировано
- [ ] Под медиа отправлен форматированный текст
- [ ] Есть кнопка "Получить контакты 📞"
- [ ] Текст правильно отформатирован (эмодзи, структура)

✅ **Для медиа-группы:**
- [ ] Хотя бы одно фото скопировано (первое из группы)
- [ ] Текст и кнопка присутствуют

✅ **Общее:**
- [ ] Нет дублирования информации в описании
- [ ] Цена не повторяется
- [ ] Автотека не показывается если unknown

### 5. Проблемы и решения

#### Медиа не публикуется, только текст

**Проверить в логах:**
```bash
grep -i "copy_message failed" logs/celery_worker_output.log
grep -i "forward_message also failed" logs/celery_worker_output.log
```

**Возможные причины:**
1. Бот не имеет доступа к исходному каналу
   - **Решение:** Добавить бота в исходный канал хотя бы с правами на чтение
   
2. Неправильный формат channel_id
   - **Решение:** Проверить в Google Sheets, что channel_id в правильном формате
   - Примеры: `-1001234567890`, `@channelname`

3. Сообщение удалено из исходного канала
   - **Результат:** Публикация только текста (это нормально)

#### Посты не обрабатываются

**Проверить:**
```bash
# Celery worker запущен?
ps aux | grep celery

# Есть ошибки?
tail -50 logs/celery_worker_output.log
```

#### AI не генерирует описание

**Проверить:**
```bash
# OpenAI API ключ настроен?
grep OPENAI_API_KEY .env

# Логи AI обработки
grep "AI processing" logs/celery_worker_output.log
```

### 6. Дополнительные команды

**Посмотреть последние 10 постов в базе:**
```bash
# Через psql
psql postgresql://cars_bot_user:change_this_secure_password@localhost:5432/cars_bot -c "SELECT id, source_channel_id, original_message_id, media_files IS NOT NULL as has_media, published FROM posts ORDER BY date_found DESC LIMIT 10;"
```

**Очистить очередь Celery:**
```bash
celery -A cars_bot.celery_app purge -f
```

**Перезапустить все сервисы:**
```bash
./scripts/stop_celery.sh
pkill -f check_monitor.py
sleep 3
./scripts/run_all.sh
```

## Что изменилось в коде

### Message Processor (`message_processor.py`)
- Теперь сохраняет полную информацию о медиа: `type:id:access_hash:file_reference`
- Поддержка фото, видео и документов

### Publishing Service (`service.py`)
- Улучшенная обработка `channel_id` (разные форматы)
- Двойной fallback: `copy_message` → `forward_message` → `text_only`
- Детальное логирование каждого шага
- Добавлен импорт `InputMediaVideo`

## Известные ограничения

⚠️ **Медиа-группы (несколько фото):**
- Копируется только **первое** медиа из группы
- Это ограничение Telegram API
- Для полной поддержки нужна доработка монитора

✅ **Что работает:**
- Одно фото ✓
- Одно видео ✓
- Документы ✓
- Текст без медиа ✓

## Следующие шаги

После успешного тестирования одиночных медиа, можно:

1. **Реализовать поддержку медиа-групп:**
   - Обновить монитор для сохранения всех message_id группы
   - Копировать все сообщения группы
   - Или скачивать и отправлять через `send_media_group`

2. **Добавить кеширование медиа:**
   - Скачивать медиа при первой обработке
   - Сохранять локально или в S3
   - Использовать при публикации

3. **Улучшить обработку ошибок:**
   - Retry логика для временных ошибок
   - Уведомления в админ чат о проблемах

