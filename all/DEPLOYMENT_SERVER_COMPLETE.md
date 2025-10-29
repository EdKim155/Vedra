# ✅ Развертывание Cars Bot на сервере - ЗАВЕРШЕНО

## 📋 Выполненные работы

### 1. Настройка сервера
- ✅ Установлен Python 3.12
- ✅ Установлен и настроен PostgreSQL 16
- ✅ Установлен и настроен Redis
- ✅ Установлен и настроен Nginx
- ✅ Установлен Supervisor для управления процессами

### 2. База данных
- ✅ Создана база данных `cars_bot`
- ✅ Создан пользователь `cars_bot_user`
- ✅ Применены все миграции (10 таблиц создано)
- ✅ Добавлена таблица `payments` для YooKassa

### 3. Развертывание приложения
- ✅ Проект скопирован на сервер (`/root/cars-bot`)
- ✅ Создано виртуальное окружение
- ✅ Установлены все зависимости
- ✅ Настроен `.env` файл
- ✅ Скопированы учетные данные Google Sheets
- ✅ Скопированы сессии Telegram

### 4. Интеграция YooKassa
- ✅ Добавлена модель `Payment` в базу данных
- ✅ Создан сервис `YooKassaPaymentService`
- ✅ Создан обработчик вебхуков `YooKassaWebhookHandler`
- ✅ Обновлены обработчики подписок в боте
- ✅ Настроены цены: 190₽/месяц, 1990₽/год

### 5. Настройка Nginx
- ✅ Создана конфигурация для домена `formygooglesheet.ru`
- ✅ Настроен прокси для вебхуков `/webhooks/yookassa`
- ✅ Nginx активен и работает

### 6. Настройка Supervisor
- ✅ Созданы конфигурации для всех сервисов:
  - `cars-bot` - основной бот
  - `cars-monitor` - мониторинг каналов
  - `cars-celery-worker` - обработчик фоновых задач
  - `cars-celery-beat` - планировщик задач
  - `cars-webhook` - обработчик вебхуков YooKassa
- ✅ Все сервисы запущены и работают

## 🔧 Конфигурация

### База данных
```
Хост: localhost
Порт: 5432
База: cars_bot
Пользователь: cars_bot_user
Пароль: CarsBot2025Pass
```

### Вебхуки YooKassa
```
URL: https://formygooglesheet.ru/webhooks/yookassa
Порт (внутренний): 8080
События:
  - payment.succeeded
  - payment.waiting_for_capture
  - payment.canceled
  - refund.succeeded
```

### Цены подписок
```
Месячная: 190₽
Годовая: 1990₽
```

## 📁 Структура на сервере

```
/root/cars-bot/
├── .env                    # Переменные окружения
├── alembic/               # Миграции базы данных
├── logs/                  # Логи всех сервисов
├── secrets/               # service_account.json
├── sessions/              # Telegram сессии
├── src/                   # Исходный код
├── venv/                  # Виртуальное окружение
└── requirements.txt       # Зависимости
```

## 🚀 Управление сервисами

### Статус всех сервисов
```bash
supervisorctl status
```

### Перезапуск отдельного сервиса
```bash
supervisorctl restart carsbot:cars-bot
supervisorctl restart carsbot:cars-monitor
supervisorctl restart carsbot:cars-celery-worker
supervisorctl restart carsbot:cars-celery-beat
supervisorctl restart carsbot:cars-webhook
```

### Перезапуск всех сервисов
```bash
supervisorctl restart carsbot:*
```

### Просмотр логов
```bash
tail -f /root/cars-bot/logs/bot_output.log
tail -f /root/cars-bot/logs/monitor_output.log
tail -f /root/cars-bot/logs/celery_worker_output.log
tail -f /root/cars-bot/logs/celery_beat_output.log
tail -f /root/cars-bot/logs/webhook_output.log
```

### Остановка сервисов
```bash
supervisorctl stop carsbot:*
```

### Запуск сервисов
```bash
supervisorctl start carsbot:*
```

## 🔐 SSH доступ

```bash
ssh carsbot
```

Настроен SSH-ключ для безпарольного подключения.

## ⚙️ Настройка вебхуков YooKassa

Вебхуки уже настроены через Nginx. Для активации в панели YooKassa:

1. Войдите в личный кабинет YooKassa
2. Перейдите в "Настройки" → "Уведомления"
3. Добавьте URL: `https://formygooglesheet.ru/webhooks/yookassa`
4. Выберите события:
   - ✅ `payment.succeeded` - Успешная оплата
   - ✅ `payment.waiting_for_capture` - Ожидание подтверждения
   - ✅ `payment.canceled` - Отмена платежа
   - ✅ `refund.succeeded` - Успешный возврат
5. Сохраните настройки

## 📊 Мониторинг

### Проверка работы бота
1. Отправьте `/start` боту в Telegram
2. Проверьте логи: `tail -f /root/cars-bot/logs/bot_output.log`

### Проверка базы данных
```bash
ssh carsbot
sudo -u postgres psql -d cars_bot -c "\dt"
```

### Проверка Redis
```bash
redis-cli ping
```

### Проверка вебхука
```bash
curl -X POST http://127.0.0.1:8080/webhooks/yookassa \
  -H "Content-Type: application/json" \
  -d '{}'
```

## 🔄 Обновление кода

При обновлении кода на сервере:

```bash
# 1. Подключитесь к серверу
ssh carsbot

# 2. Перейдите в директорию проекта
cd /root/cars-bot

# 3. Обновите код (через git pull или scp)
# Например:
# scp -r /path/to/local/src/* carsbot:/root/cars-bot/src/

# 4. Активируйте виртуальное окружение
source venv/bin/activate

# 5. Установите новые зависимости (если есть)
pip install -r requirements.txt

# 6. Применитемиграции (если есть)
export DATABASE__URL='postgresql+asyncpg://cars_bot_user:CarsBot2025Pass@localhost:5432/cars_bot'
alembic upgrade head

# 7. Перезапустите сервисы
supervisorctl restart carsbot:*
```

## 📝 Важные замечания

1. **Пароль базы данных**: Рекомендуется сменить пароль `CarsBot2025Pass` на более безопасный после развертывания
2. **HTTPS**: Для продакшена рекомендуется настроить SSL (Let's Encrypt)
3. **Backup**: Настройте регулярное резервное копирование базы данных
4. **Мониторинг**: Рассмотрите использование Prometheus + Grafana для детального мониторинга
5. **Firewall**: Убедитесь, что порты 80, 443, 22 открыты, остальные закрыты

## 🎉 Готово!

Все компоненты развернуты и работают. Бот готов к приему платежей через YooKassa.

**Дата завершения**: 27 октября 2025
**Статус**: ✅ Полностью развернуто и работает

