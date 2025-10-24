#!/bin/bash
# Terminal 4: Celery Beat - Планировщик

cd "/Users/edgark/CARS BOT"
source venv/bin/activate
set -a
source .env
set +a
export PYTHONPATH="/Users/edgark/CARS BOT/src:$PYTHONPATH"

clear
echo "╔═══════════════════════════════════════════════════════╗"
echo "║       ⏰ CELERY BEAT - Планировщик задач              ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""
echo "Запускает периодические задачи:"
echo "  • Проверка истекших подписок"
echo "  • Обновление аналитики"
echo "  • Мониторинг системы"
echo ""
echo "Статус: Запускается..."
echo ""

celery -A cars_bot.celery_app beat --loglevel=info

