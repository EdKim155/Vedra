# Настройка платежной системы ЮКасса

Руководство по интеграции платежной системы ЮКасса для приема платежей за подписку в Cars Bot.

## 📋 Оглавление

1. [Получение учетных данных ЮКасса](#получение-учетных-данных-юкасса)
2. [Настройка переменных окружения](#настройка-переменных-окружения)
3. [Настройка вебхуков](#настройка-вебхуков)
4. [Применение миграций](#применение-миграций)
5. [Запуск вебхук-сервера](#запуск-вебхук-сервера)
6. [Тестирование](#тестирование)
7. [Устранение неполадок](#устранение-неполадок)

---

## 🔑 Получение учетных данных ЮКасса

### 1. Регистрация в ЮКасса

1. Перейдите на [yookassa.ru](https://yookassa.ru)
2. Зарегистрируйтесь или войдите в личный кабинет
3. Заполните данные организации и подпишите договор

### 2. Получение Shop ID и Secret Key

1. В личном кабинете ЮКасса перейдите в раздел **"Интеграция" → "Ключи API"**
2. **Shop ID** находится в верхней части страницы (например: `123456`)
3. **Secret Key** можно сгенерировать нажав кнопку "Создать ключ":
   - Выберите тип ключа: **Production (боевой)**
   - Скопируйте секретный ключ (начинается с `live_`)
   - ⚠️ **ВАЖНО**: Ключ показывается только один раз! Сохраните его в надежном месте

### 3. Тестовый режим (опционально)

Для тестирования можно использовать **тестовый магазин**:
- Перейдите в раздел "Тестирование"
- Получите тестовые Shop ID и Secret Key (начинается с `test_`)
- Используйте [тестовые карты](https://yookassa.ru/developers/payment-acceptance/testing-and-going-live/testing) для проверки

---

## ⚙️ Настройка переменных окружения

Добавьте следующие переменные в файл `.env`:

```bash
# ===== ЮКасса Payment Settings =====
PAYMENT__YOOKASSA_SECRET_KEY=live_iyiUt1CmVGU7HqpJvKu5oh1b4gIvtft4pzFD4GyO1pQ
PAYMENT__YOOKASSA_SHOP_ID=ваш_shop_id

# Prices (в рублях)
PAYMENT__MONTHLY_PRICE=190
PAYMENT__YEARLY_PRICE=1990

# Webhook settings
PAYMENT__WEBHOOK_ENABLED=true
PAYMENT__WEBHOOK_URL=https://ваш_домен.ru/webhooks/yookassa
PAYMENT__WEBHOOK_PATH=/webhooks/yookassa

# Payment timeout (в секундах, по умолчанию 1 час)
PAYMENT__PAYMENT_TIMEOUT=3600

# Return URL (необязательно, по умолчанию ссылка на бота)
# PAYMENT__RETURN_URL=https://t.me/ваш_бот
```

### Описание параметров:

| Параметр | Обязательный | Описание |
|----------|--------------|----------|
| `PAYMENT__YOOKASSA_SECRET_KEY` | ✅ Да | Секретный ключ из личного кабинета ЮКасса |
| `PAYMENT__YOOKASSA_SHOP_ID` | ✅ Да | Идентификатор магазина (Shop ID) |
| `PAYMENT__MONTHLY_PRICE` | Нет | Цена месячной подписки (по умолчанию 190₽) |
| `PAYMENT__YEARLY_PRICE` | Нет | Цена годовой подписки (по умолчанию 1990₽) |
| `PAYMENT__WEBHOOK_ENABLED` | Нет | Включить уведомления от ЮКасса (по умолчанию true) |
| `PAYMENT__WEBHOOK_URL` | Условно* | Полный URL для получения вебхуков |
| `PAYMENT__WEBHOOK_PATH` | Нет | Путь для вебхук endpoint (по умолчанию `/webhooks/yookassa`) |
| `PAYMENT__PAYMENT_TIMEOUT` | Нет | Время жизни ссылки на оплату в секундах |
| `PAYMENT__RETURN_URL` | Нет | URL для редиректа после оплаты |

_* Обязательно если `WEBHOOK_ENABLED=true`_

---

## 🔔 Настройка вебхуков

Вебхуки необходимы для автоматической активации подписки после успешной оплаты.

### 1. В личном кабинете ЮКасса

1. Перейдите в **"Интеграция" → "HTTP-уведомления"**
2. Включите уведомления
3. Укажите **URL для уведомлений**: `https://ваш_домен.ru/webhooks/yookassa`
4. Выберите события для уведомлений:
   - ✅ `payment.succeeded` - успешная оплата
   - ✅ `payment.canceled` - отмененная оплата
   - ✅ `payment.waiting_for_capture` - ожидание подтверждения
5. Сохраните настройки

### 2. Настройка домена с А-записью

Для работы вебхуков необходим домен с А-записью, указывающей на ваш сервер:

```
Тип записи: A
Имя: @ (или subdomain)
Значение: IP_адрес_вашего_сервера
TTL: 3600
```

Пример:
- Домен: `carbot.example.com`
- IP сервера: `195.123.45.67`
- URL вебхука: `https://carbot.example.com/webhooks/yookassa`

### 3. SSL сертификат

⚠️ **ВАЖНО**: ЮКасса работает только с HTTPS!

Установите SSL сертификат (например, бесплатный от Let's Encrypt):

```bash
# Установка certbot
sudo apt install certbot python3-certbot-nginx

# Получение сертификата
sudo certbot --nginx -d ваш_домен.ru
```

---

## 🗄️ Применение миграций

Примените миграцию для создания таблицы `payments`:

```bash
# Активируйте виртуальное окружение
source venv/bin/activate

# Примените миграцию
alembic upgrade head
```

Проверьте, что миграция применилась успешно:

```bash
alembic current
# Должно показать: b9742090b83e (head) - add payments table and update payment enums
```

---

## 🚀 Запуск вебхук-сервера

Вебхук-сервер может быть запущен отдельно или встроен в основное приложение.

### Вариант 1: Отдельный процесс (рекомендуется)

Создайте файл `start_webhook_server.py`:

```python
import asyncio
import logging

from cars_bot.payments import start_webhook_server
from cars_bot.config import get_settings

logging.basicConfig(level=logging.INFO)

async def main():
    settings = get_settings()
    await start_webhook_server(host="0.0.0.0", port=8080)
    
    # Keep running
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
```

Запустите сервер:

```bash
python start_webhook_server.py
```

### Вариант 2: Nginx как reverse proxy

Настройте Nginx для проксирования запросов к вебхук-серверу:

```nginx
server {
    listen 443 ssl http2;
    server_name ваш_домен.ru;

    ssl_certificate /etc/letsencrypt/live/ваш_домен.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ваш_домен.ru/privkey.pem;

    # Webhook endpoint
    location /webhooks/yookassa {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Остальные настройки...
}
```

### Вариант 3: Systemd service

Создайте файл `/etc/systemd/system/carbot-webhook.service`:

```ini
[Unit]
Description=Cars Bot YooKassa Webhook Server
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/CARS BOT
Environment="PATH=/path/to/CARS BOT/venv/bin"
ExecStart=/path/to/CARS BOT/venv/bin/python start_webhook_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Запустите сервис:

```bash
sudo systemctl daemon-reload
sudo systemctl enable carbot-webhook
sudo systemctl start carbot-webhook
sudo systemctl status carbot-webhook
```

---

## 🧪 Тестирование

### 1. Проверка создания платежа

Запустите бота и попробуйте оформить подписку:

```bash
# В Telegram боте
/subscription → Месячная подписка
```

Должна появиться кнопка "💳 Оплатить" с рабочей ссылкой на страницу оплаты ЮКасса.

### 2. Проверка вебхуков

Проверьте доступность вебхук endpoint:

```bash
curl -X POST https://ваш_домен.ru/webhooks/yookassa \
  -H "Content-Type: application/json" \
  -d '{"event": "test"}'
```

Ожидаемый ответ: `200 OK` или `400 Bad Request` (если данные неверны)

### 3. Тестовая оплата

Используйте тестовые данные карт для проверки:

**Успешная оплата:**
- Номер карты: `5555 5555 5555 4477`
- Срок действия: любая дата в будущем
- CVC: любые 3 цифры

**Отклоненная оплата:**
- Номер карты: `5555 5555 5555 4444`
- Остальное аналогично

### 4. Проверка логов

Следите за логами для отладки:

```bash
# Логи бота
tail -f logs/bot_output.log

# Логи вебхук-сервера
tail -f logs/webhook_server.log
```

---

## 🔧 Устранение неполадок

### Проблема: Платеж создается, но уведомления не приходят

**Решение:**
1. Проверьте, что вебхук-сервер запущен и доступен извне
2. Убедитесь, что SSL сертификат валиден
3. Проверьте настройки вебхуков в личном кабинете ЮКасса
4. Проверьте логи вебхук-сервера на наличие ошибок

### Проблема: Ошибка "Invalid signature" в вебхуках

**Решение:**
1. Убедитесь, что используете правильный Secret Key
2. Проверьте, что в `.env` нет лишних пробелов или переносов строк
3. Временно отключите проверку подписи для отладки (закомментируйте в `webhook_handler.py`)

### Проблема: Платеж завис в статусе "pending"

**Решение:**
1. Проверьте статус платежа в личном кабинете ЮКасса
2. Используйте кнопку "🔄 Проверить оплату" в боте для ручной проверки
3. Проверьте, не истек ли срок действия ссылки на оплату (по умолчанию 1 час)

### Проблема: Ошибка при создании платежа

**Решение:**
1. Проверьте, что Shop ID и Secret Key корректны
2. Убедитесь, что в ЮКасса есть активный договор
3. Проверьте баланс и лимиты в личном кабинете ЮКасса
4. Посмотрите подробности ошибки в логах

---

## 📞 Поддержка

При возникновении проблем:

1. **Документация ЮКасса**: [yookassa.ru/developers](https://yookassa.ru/developers)
2. **Техподдержка ЮКасса**: support@yookassa.ru
3. **Логи бота**: проверьте `logs/` директорию

---

## ✅ Чеклист готовности к продакшену

- [ ] Получены боевые учетные данные ЮКасса (live_ ключ)
- [ ] Настроены переменные окружения в `.env`
- [ ] Применены миграции базы данных
- [ ] Настроен домен с SSL сертификатом
- [ ] Вебхуки настроены в личном кабинете ЮКасса
- [ ] Вебхук-сервер запущен и доступен извне
- [ ] Проведено тестирование с тестовыми картами
- [ ] Настроен мониторинг и логирование
- [ ] Созданы резервные копии базы данных

---

**Версия документа:** 1.0  
**Дата создания:** 2025-10-27  
**Статус:** Готово к использованию


