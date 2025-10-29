# 🚀 Cars Bot - Быстрая справка по управлению сервером

## 🔐 Подключение к серверу

```bash
ssh carsbot
```

## 📊 Проверка статуса

### Все сервисы
```bash
supervisorctl status
```

### Отдельные сервисы
```bash
systemctl status nginx
systemctl status postgresql
systemctl status redis
systemctl status supervisor
```

## 🔄 Управление сервисами

### Перезапуск всех компонентов бота
```bash
supervisorctl restart carsbot:*
```

### Перезапуск отдельных компонентов
```bash
supervisorctl restart carsbot:cars-bot          # Telegram бот
supervisorctl restart carsbot:cars-monitor      # Мониторинг каналов
supervisorctl restart carsbot:cars-celery-worker # Celery worker
supervisorctl restart carsbot:cars-celery-beat   # Celery beat
supervisorctl restart carsbot:cars-webhook       # YooKassa вебхуки
```

### Остановка/запуск
```bash
supervisorctl stop carsbot:*
supervisorctl start carsbot:*
```

## 📝 Логи

### Просмотр логов (в реальном времени)
```bash
cd /root/cars-bot/logs

# Бот
tail -f bot_output.log

# Монитор
tail -f monitor_output.log

# Celery Worker
tail -f celery_worker_output.log

# Celery Beat
tail -f celery_beat_output.log

# YooKassa Webhook
tail -f webhook_output.log

# Все логи одновременно
tail -f *.log
```

### Последние 100 строк
```bash
tail -100 bot_output.log
```

### Поиск по логам
```bash
grep "ERROR" bot_output.log
grep "payment" webhook_output.log
```

## 💾 База данных

### Подключение к PostgreSQL
```bash
sudo -u postgres psql -d cars_bot
```

### Быстрые запросы
```bash
# Список всех таблиц
sudo -u postgres psql -d cars_bot -c "\dt"

# Последние платежи
sudo -u postgres psql -d cars_bot -c "SELECT * FROM payments ORDER BY created_at DESC LIMIT 10;"

# Активные подписки
sudo -u postgres psql -d cars_bot -c "SELECT * FROM subscriptions WHERE is_active = true;"

# Статистика пользователей
sudo -u postgres psql -d cars_bot -c "SELECT COUNT(*) FROM users;"
```

### Резервное копирование
```bash
# Создать backup
sudo -u postgres pg_dump cars_bot > /root/backups/cars_bot_$(date +%Y%m%d_%H%M%S).sql

# Восстановить из backup
sudo -u postgres psql -d cars_bot < /root/backups/cars_bot_YYYYMMDD_HHMMSS.sql
```

## 🔧 Обновление кода

```bash
# 1. Подключитесь к серверу
ssh carsbot

# 2. Перейдите в директорию проекта
cd /root/cars-bot

# 3. Сделайте backup (опционально)
cp -r src src.backup.$(date +%Y%m%d)

# 4. Обновите код (через scp с вашего компьютера)
# На вашем локальном компьютере:
# scp -r /Users/edgark/CARS\ BOT/src/* carsbot:/root/cars-bot/src/

# 5. Обновите зависимости (если изменились)
source venv/bin/activate
pip install -r requirements.txt

# 6. Применитемиграции (если есть новые)
alembic upgrade head

# 7. Перезапустите сервисы
supervisorctl restart carsbot:*
```

## 🌐 Nginx

### Проверка конфигурации
```bash
nginx -t
```

### Перезагрузка
```bash
systemctl reload nginx
```

### Просмотр конфигурации
```bash
cat /etc/nginx/sites-enabled/formygooglesheet.ru
```

## 🔍 Мониторинг системы

### Использование ресурсов
```bash
# CPU и память
htop

# Диск
df -h

# Процессы Python
ps aux | grep python

# Сетевые подключения
netstat -tulpn | grep LISTEN
```

### Redis
```bash
# Проверка соединения
redis-cli ping

# Просмотр ключей
redis-cli keys "*"

# Очистка кеша (ОСТОРОЖНО!)
redis-cli FLUSHALL
```

## ⚙️ Конфигурация

### Изменение переменных окружения
```bash
# Редактировать конфигурацию Supervisor
nano /etc/supervisor/conf.d/cars-bot.conf

# После изменений:
supervisorctl reread
supervisorctl update
supervisorctl restart carsbot:*
```

### Основные файлы конфигурации
```
/etc/supervisor/conf.d/cars-bot.conf  # Supervisor
/etc/nginx/sites-enabled/formygooglesheet.ru  # Nginx
/root/cars-bot/.env  # Переменные окружения (НЕ используется, см. Supervisor)
/root/cars-bot/alembic.ini  # Alembic миграции
```

## 🚨 Экстренные команды

### Остановить все
```bash
supervisorctl stop carsbot:*
systemctl stop nginx
```

### Полная перезагрузка сервера
```bash
sudo reboot
```

### Проверить, почему сервис не запускается
```bash
supervisorctl tail -f carsbot:cars-bot
supervisorctl tail -f carsbot:cars-bot stderr
```

## 📞 Полезные команды

### Проверить, что бот отвечает
```bash
curl -X POST https://api.telegram.org/bot8355579123:AAEkNnPXst0b3RxCqnqydCfcFkug3QXNoXE/getMe
```

### Проверить вебхук
```bash
curl -X POST http://127.0.0.1:8080/webhooks/yookassa \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Проверить Nginx проксирование
```bash
curl -X POST https://formygooglesheet.ru/webhooks/yookassa \
  -H "Content-Type: application/json" \
  -d '{}'
```

## 🎯 Типичные проблемы и решения

### Сервис не запускается
```bash
# Проверить логи
supervisorctl tail -1000 carsbot:cars-bot

# Проверить права доступа
ls -la /root/cars-bot/

# Проверить переменные окружения
cat /etc/supervisor/conf.d/cars-bot.conf
```

### База данных не отвечает
```bash
# Проверить статус PostgreSQL
systemctl status postgresql

# Перезапустить PostgreSQL
systemctl restart postgresql

# Проверить подключение
PGPASSWORD=CarsBot2025Pass psql -h localhost -U cars_bot_user -d cars_bot -c "SELECT 1;"
```

### Нет места на диске
```bash
# Проверить использование
df -h

# Очистить старые логи
cd /root/cars-bot/logs
> bot_output.log
> monitor_output.log
> celery_worker_output.log

# Или удалить старые логи
find /root/cars-bot/logs -name "*.log" -mtime +7 -delete
```

---

## 📍 Важные пути

```
/root/cars-bot/                    # Директория проекта
/root/cars-bot/src/                # Исходный код
/root/cars-bot/logs/               # Логи
/root/cars-bot/sessions/           # Telegram сессии
/root/cars-bot/secrets/            # Секреты (service_account.json)
/root/cars-bot/venv/               # Виртуальное окружение
/etc/supervisor/conf.d/cars-bot.conf   # Конфигурация Supervisor
/etc/nginx/sites-enabled/formygooglesheet.ru  # Конфигурация Nginx
```

---

## 🔑 Учетные данные

```
SSH: ssh carsbot
PostgreSQL User: cars_bot_user
PostgreSQL Password: CarsBot2025Pass
PostgreSQL DB: cars_bot
Redis: localhost:6379 (без пароля)
Bot Token: 8355579123:AAEkNnPXst0b3RxCqnqydCfcFkug3QXNoXE
```

---

**Последнее обновление**: 27 октября 2025

