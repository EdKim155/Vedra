# 🔧 ИНСТРУКЦИИ ПО ИСПРАВЛЕНИЮ СЕРВЕРА CARS BOT

**Дата**: 27 октября 2025  
**Статус**: Готово к развертыванию

---

## 📋 КРАТКОЕ РЕЗЮМЕ ПРОБЛЕМ

### 🚨 Критические проблемы:

1. **Множественные экземпляры Telegram бота** → бот не может получать обновления
2. **Celery Worker постоянно завершается** → задачи не обрабатываются
3. **Монитор часто перезапускается** → нестабильная работа мониторинга

### ✅ Решение:

- Остановить Docker Compose (если запущен)
- Использовать **только Supervisor** для управления сервисами
- Установить правильную конфигурацию Supervisor
- Исправить watchdog в мониторе (увеличить timeout)

---

## 🚀 БЫСТРОЕ ИСПРАВЛЕНИЕ (5 минут)

### Вариант 1: Автоматическое развертывание

**На вашем локальном компьютере:**

```bash
cd "/Users/edgark/CARS BOT"
./deploy_fix_to_server.sh
```

Затем **на сервере:**

```bash
ssh carsbot
cd /root/cars-bot

# Установить новую конфигурацию Supervisor (требует root)
sudo ./install_supervisor_config.sh

# Запустить скрипт исправления
./fix_server.sh

# Мониторить логи
tail -f logs/*.log
```

---

### Вариант 2: Ручное исправление

**На сервере:**

```bash
ssh carsbot
cd /root/cars-bot

# 1. Остановить всё
docker-compose down 2>/dev/null || true
supervisorctl stop carsbot:* 2>/dev/null || true
pkill -f "python -m cars_bot"
pkill -f "celery.*cars_bot"

# 2. Убедиться что всё остановлено
ps aux | grep "python -m cars_bot" | grep -v grep
ps aux | grep "celery" | grep -v grep
# (не должно быть процессов)

# 3. Установить конфигурацию Supervisor
sudo cp supervisor_config.conf /etc/supervisor/conf.d/cars-bot.conf
sudo supervisorctl reread
sudo supervisorctl update

# 4. Запустить сервисы
supervisorctl start carsbot:*

# 5. Проверить статус
supervisorctl status carsbot:*

# 6. Проверить логи на ошибки
tail -f logs/bot_output.log          # Должен запуститься без TelegramConflictError
tail -f logs/celery_worker_output.log  # Должен остаться запущенным, не завершаться
tail -f logs/monitor_output.log       # Должен работать стабильно
```

---

## 🔍 ПРОВЕРКА ПОСЛЕ ИСПРАВЛЕНИЯ

### 1. Проверить что запущены ТОЛЬКО Supervisor процессы

```bash
# Должно показать 5 RUNNING процессов
supervisorctl status carsbot:*

# Не должно быть Docker контейнеров
docker ps

# Должно быть ровно по одному процессу каждого типа
ps aux | grep "python -m cars_bot.bot" | grep -v grep        # 1 процесс
ps aux | grep "python -m cars_bot.monitor" | grep -v grep    # 1 процесс
ps aux | grep "celery.*worker" | grep -v grep                # 1 процесс
ps aux | grep "celery.*beat" | grep -v grep                  # 1 процесс
```

### 2. Проверить логи на ошибки

```bash
# Bot - не должно быть TelegramConflictError
grep "TelegramConflictError" logs/bot_output.log
# (пусто - хорошо)

# Celery Worker - не должно быть "Warm shutdown"
grep "Warm shutdown" logs/celery_worker_output.log | tail -1
# (если есть - проверить что это старая запись, а не новая)

# Monitor - не должно быть частых перезапусков
tail -20 logs/monitor_output.log
# (не должно быть "Auto-restarted" каждые 5 минут)
```

### 3. Протестировать функциональность

**Telegram Bot:**
```
1. Отправить /start боту @Vedrro_bot
2. Должен ответить приветственным сообщением
3. Отправить /subscription
4. Должен показать информацию о подписке
```

**Мониторинг:**
```
1. Отправить тестовый пост в один из мониторимых каналов
2. Проверить логи monitor_output.log - должно появиться "New message from..."
3. Проверить логи celery_worker_output.log - должна выполниться задача AI processing
```

**Публикация:**
```
1. После обработки AI, пост должен появиться в очереди публикации
2. Через несколько минут должен опубликоваться в канале -1002979557335
```

---

## 📊 МОНИТОРИНГ В РЕАЛЬНОМ ВРЕМЕНИ

### Смотреть все логи одновременно:

```bash
# В одном терминале
ssh carsbot
cd /root/cars-bot
tail -f logs/*.log
```

### Или в разных терминалах:

```bash
# Терминал 1: Bot
ssh carsbot "tail -f /root/cars-bot/logs/bot_output.log"

# Терминал 2: Monitor
ssh carsbot "tail -f /root/cars-bot/logs/monitor_output.log"

# Терминал 3: Celery Worker
ssh carsbot "tail -f /root/cars-bot/logs/celery_worker_output.log"

# Терминал 4: Celery Beat
ssh carsbot "tail -f /root/cars-bot/logs/celery_beat_output.log"
```

---

## 🆘 ЕСЛИ ЧТО-ТО ПОШЛО НЕ ТАК

### Проблема: Bot всё ещё показывает TelegramConflictError

**Диагностика:**
```bash
# Найти все процессы бота
ps aux | grep "cars_bot.bot" | grep -v grep

# Должен быть только ОДИН процесс
```

**Решение:**
```bash
# Убить все процессы бота
pkill -f "cars_bot.bot.main"

# Запустить заново
supervisorctl start carsbot:cars-bot
```

---

### Проблема: Celery Worker завершается после запуска

**Диагностика:**
```bash
# Проверить последние строки лога
tail -50 logs/celery_worker_output.log

# Искать "Warm shutdown" или ошибки
```

**Возможные причины:**
1. Не хватает памяти
2. Redis не отвечает
3. Ошибка в задаче

**Решение:**
```bash
# Проверить Redis
redis-cli ping

# Проверить память
free -h

# Перезапустить worker
supervisorctl restart carsbot:cars-celery-worker

# Если не помогло, запустить с более низким concurrency
# Отредактировать /etc/supervisor/conf.d/cars-bot.conf
# Изменить --concurrency=4 на --concurrency=2
supervisorctl reread && supervisorctl update && supervisorctl restart carsbot:cars-celery-worker
```

---

### Проблема: Монитор всё ещё часто перезапускается

**Диагностика:**
```bash
# Проверить файл monitor_restarts.log
cat logs/monitor_restarts.log | tail -20

# Если перезапуски всё ещё каждые несколько минут - watchdog всё ещё агрессивный
```

**Решение:**
```bash
# Убедиться что обновленный код монитора развернут
grep "max_idle_time = 300" src/cars_bot/monitor/monitor.py

# Должно показать: self.max_idle_time = 300

# Если показывает 60 - нужно обновить код
# На локальной машине:
scp -r src/cars_bot/monitor/ carsbot:/root/cars-bot/src/cars_bot/

# На сервере:
supervisorctl restart carsbot:cars-monitor
```

---

## 📁 СОЗДАННЫЕ ФАЙЛЫ

Для исправления были созданы следующие файлы:

1. **`DIAGNOSIS_AND_FIX.md`** - Полный отчет о проблемах и решениях
2. **`supervisor_config.conf`** - Правильная конфигурация Supervisor
3. **`fix_server.sh`** - Скрипт автоматического исправления
4. **`install_supervisor_config.sh`** - Скрипт установки конфигурации
5. **`deploy_fix_to_server.sh`** - Скрипт развертывания с локальной машины
6. **`SERVER_FIX_INSTRUCTIONS.md`** - Этот файл с инструкциями

И обновлен код:
- **`src/cars_bot/monitor/monitor.py`** - Увеличен `max_idle_time` с 60 до 300 секунд

---

## ✅ ОЖИДАЕМЫЙ РЕЗУЛЬТАТ

После успешного исправления:

- ✅ **Telegram Bot** работает стабильно, отвечает на команды
- ✅ **Celery Worker** работает постоянно, не завершается
- ✅ **Celery Beat** отправляет периодические задачи
- ✅ **Monitor** работает стабильно, не перезапускается часто
- ✅ **Webhook** принимает уведомления от YooKassa
- ✅ **Только ОДИН экземпляр** каждого сервиса запущен
- ✅ **Нет конфликтов** между процессами
- ✅ **Логи чистые**, без ошибок

---

## 📞 ПОДДЕРЖКА

Если после выполнения всех инструкций проблемы остались:

1. Запустить диагностический скрипт и сохранить отчет:
   ```bash
   /root/cars-bot/diagnose.sh > diagnostic_report.txt
   ```

2. Сохранить все логи:
   ```bash
   cd /root/cars-bot
   tar -czf logs_backup.tar.gz logs/
   ```

3. Предоставить:
   - `diagnostic_report.txt`
   - `logs_backup.tar.gz`
   - Описание что именно не работает

---

**Время выполнения**: ~5-10 минут  
**Сложность**: Средняя  
**Требуется**: SSH доступ к серверу, права sudo

**Следующий шаг**: Запустить `./deploy_fix_to_server.sh`

