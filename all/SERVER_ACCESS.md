# 🔐 Доступ к серверу Cars Bot

## Сервер

- **IP:** `72.56.77.44`
- **Пользователь:** `root`
- **SSH ключ:** `~/.ssh/carsbot_server`

---

## 🚀 Подключение

### Способ 1: Через алиас (рекомендуется)

```bash
ssh carsbot
```

### Способ 2: Напрямую

```bash
ssh root@72.56.77.44
```

Или с явным указанием ключа:

```bash
ssh -i ~/.ssh/carsbot_server root@72.56.77.44
```

---

## 📁 Структура проекта на сервере

Рекомендуемая структура:

```
/root/
├── cars-bot/              # Директория проекта
│   ├── .env              # Переменные окружения
│   ├── venv/             # Виртуальное окружение
│   ├── logs/             # Логи
│   ├── sessions/         # Telegram сессии
│   └── secrets/          # Секретные файлы (service_account.json)
```

---

## 🔧 Первоначальная настройка сервера

### 1. Обновление системы

```bash
ssh carsbot

# Обновление
apt update && apt upgrade -y

# Установка необходимых пакетов
apt install -y python3.11 python3.11-venv python3-pip \
    postgresql postgresql-contrib \
    redis-server \
    nginx \
    certbot python3-certbot-nginx \
    git supervisor
```

### 2. Настройка PostgreSQL

```bash
# Переключение на пользователя postgres
sudo -u postgres psql

# В PostgreSQL консоли:
CREATE DATABASE cars_bot;
CREATE USER cars_bot_user WITH PASSWORD 'ваш_надежный_пароль';
GRANT ALL PRIVILEGES ON DATABASE cars_bot TO cars_bot_user;
\q
```

### 3. Настройка Redis

```bash
# Запуск Redis
systemctl start redis-server
systemctl enable redis-server

# Проверка
redis-cli ping
# Должно вернуть: PONG
```

### 4. Клонирование проекта

```bash
cd /root
git clone <url_вашего_репозитория> cars-bot
cd cars-bot

# Создание виртуального окружения
python3.11 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt
```

### 5. Настройка .env

```bash
nano .env
```

Скопируйте содержимое из локального `.env` и обновите:

```bash
# Database
DATABASE__URL=postgresql+asyncpg://cars_bot_user:ваш_пароль@localhost:5432/cars_bot

# Redis
REDIS__URL=redis://localhost:6379/0

# И остальные переменные...
```

### 6. Применение миграций

```bash
source venv/bin/activate
alembic upgrade head
```

---

## 🚀 Развертывание с помощью Supervisor

### Создание конфигурации для бота

```bash
nano /etc/supervisor/conf.d/carsbot.conf
```

```ini
[program:carsbot]
command=/root/cars-bot/venv/bin/python -m cars_bot.bot.main
directory=/root/cars-bot
user=root
autostart=true
autorestart=true
stderr_logfile=/root/cars-bot/logs/bot_error.log
stdout_logfile=/root/cars-bot/logs/bot_output.log
environment=PYTHONPATH="/root/cars-bot"
```

### Создание конфигурации для Celery Worker

```bash
nano /etc/supervisor/conf.d/carsbot-celery-worker.conf
```

```ini
[program:carsbot-celery-worker]
command=/root/cars-bot/venv/bin/celery -A cars_bot.celery_app worker --loglevel=info
directory=/root/cars-bot
user=root
autostart=true
autorestart=true
stderr_logfile=/root/cars-bot/logs/celery_worker_error.log
stdout_logfile=/root/cars-bot/logs/celery_worker_output.log
environment=PYTHONPATH="/root/cars-bot"
```

### Создание конфигурации для Celery Beat

```bash
nano /etc/supervisor/conf.d/carsbot-celery-beat.conf
```

```ini
[program:carsbot-celery-beat]
command=/root/cars-bot/venv/bin/celery -A cars_bot.celery_app beat --loglevel=info
directory=/root/cars-bot
user=root
autostart=true
autorestart=true
stderr_logfile=/root/cars-bot/logs/celery_beat_error.log
stdout_logfile=/root/cars-bot/logs/celery_beat_output.log
environment=PYTHONPATH="/root/cars-bot"
```

### Создание конфигурации для Webhook Server

```bash
nano /etc/supervisor/conf.d/carsbot-webhook.conf
```

```ini
[program:carsbot-webhook]
command=/root/cars-bot/venv/bin/python start_webhook_server.py
directory=/root/cars-bot
user=root
autostart=true
autorestart=true
stderr_logfile=/root/cars-bot/logs/webhook_error.log
stdout_logfile=/root/cars-bot/logs/webhook_output.log
environment=PYTHONPATH="/root/cars-bot"
```

### Применение конфигураций

```bash
supervisorctl reread
supervisorctl update
supervisorctl start all
```

### Управление сервисами

```bash
# Проверка статуса
supervisorctl status

# Перезапуск
supervisorctl restart carsbot
supervisorctl restart carsbot-celery-worker
supervisorctl restart carsbot-celery-beat
supervisorctl restart carsbot-webhook

# Перезапуск всех
supervisorctl restart all

# Просмотр логов
supervisorctl tail -f carsbot
supervisorctl tail -f carsbot-celery-worker
```

---

## 🌐 Настройка Nginx + SSL

### 1. Создание конфигурации Nginx

```bash
nano /etc/nginx/sites-available/carsbot
```

```nginx
server {
    listen 80;
    server_name ваш_домен.ru;

    # Webhook endpoint
    location /webhooks/yookassa {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 2. Активация конфигурации

```bash
ln -s /etc/nginx/sites-available/carsbot /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

### 3. Установка SSL сертификата

```bash
certbot --nginx -d ваш_домен.ru
```

---

## 📊 Мониторинг

### Проверка логов

```bash
# Логи бота
tail -f /root/cars-bot/logs/bot_output.log

# Логи Celery Worker
tail -f /root/cars-bot/logs/celery_worker_output.log

# Логи вебхука
tail -f /root/cars-bot/logs/webhook_output.log

# Системные логи
journalctl -u supervisor -f
```

### Проверка процессов

```bash
# Supervisor статус
supervisorctl status

# Системные процессы
ps aux | grep python

# Использование ресурсов
htop
```

### Проверка базы данных

```bash
sudo -u postgres psql -d cars_bot -c "SELECT COUNT(*) FROM users;"
sudo -u postgres psql -d cars_bot -c "SELECT COUNT(*) FROM payments;"
```

---

## 🔄 Обновление кода

```bash
ssh carsbot
cd /root/cars-bot

# Остановка сервисов
supervisorctl stop all

# Обновление кода
git pull

# Установка зависимостей
source venv/bin/activate
pip install -r requirements.txt

# Применение миграций
alembic upgrade head

# Запуск сервисов
supervisorctl start all
```

---

## 🆘 Быстрые команды

```bash
# Подключение
ssh carsbot

# Перезапуск всех сервисов
ssh carsbot "supervisorctl restart all"

# Проверка статуса
ssh carsbot "supervisorctl status"

# Просмотр логов бота
ssh carsbot "tail -f /root/cars-bot/logs/bot_output.log"

# Проверка базы данных
ssh carsbot "sudo -u postgres psql -d cars_bot -c 'SELECT COUNT(*) FROM payments;'"
```

---

## 🔒 Безопасность

### Рекомендации:

1. ✅ **SSH ключи настроены** (беспарольный доступ)
2. ⚠️ **TODO:** Отключить парольный вход SSH
3. ⚠️ **TODO:** Настроить firewall (ufw)
4. ⚠️ **TODO:** Настроить fail2ban
5. ⚠️ **TODO:** Регулярные бэкапы базы данных

### Отключение парольного входа (после проверки ключей):

```bash
nano /etc/ssh/sshd_config
```

Измените:
```
PasswordAuthentication no
PermitRootLogin prohibit-password
```

Перезапуск SSH:
```bash
systemctl restart sshd
```

---

## 📞 Поддержка

При возникновении проблем:
- Проверьте логи: `tail -f /root/cars-bot/logs/*.log`
- Проверьте статус сервисов: `supervisorctl status`
- Проверьте системные логи: `journalctl -xe`

---

**IP сервера:** `72.56.77.44`  
**Дата настройки:** 2025-10-27  
**Статус:** ✅ SSH ключ настроен


