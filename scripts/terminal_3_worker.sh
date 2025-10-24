#!/bin/bash
# Terminal 3: Celery Worker - AI обработка

cd "/Users/edgark/CARS BOT"
source venv/bin/activate
set -a
source .env
set +a
export PYTHONPATH="/Users/edgark/CARS BOT/src:$PYTHONPATH"

clear
echo "╔═══════════════════════════════════════════════════════╗"
echo "║      ⚙️  CELERY WORKER - AI обработка постов          ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""
echo "Обрабатывает очередь задач:"
echo "  • AI анализ сообщений (OpenAI GPT-4)"
echo "  • Публикация постов"
echo "  • Синхронизация с Google Sheets"
echo ""
echo "Статус: Запускается..."
echo ""

celery -A cars_bot.celery_app worker \
    --loglevel=info \
    --concurrency=4 \
    --queues=default,ai_processing,publishing,sheets_sync,monitoring

