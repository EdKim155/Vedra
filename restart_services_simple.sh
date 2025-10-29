#!/bin/bash
set -e

cd /root/cars-bot

echo "=== Stopping all processes ==="
pkill -9 -f "monitor.monitor" 2>/dev/null || true
pkill -9 -f "celery" 2>/dev/null || true
sleep 3
echo "All processes stopped"

# Load environment
source venv/bin/activate
set -a
source .env
set +a

# Fix environment variables
export REDIS_URL="redis://localhost:6379/0"
export CELERY_BROKER_URL="$REDIS_URL"
export CELERY_RESULT_BACKEND="$REDIS_URL"
export BOT_NEWS_CHANNEL_ID="$NEWS_CHANNEL_ID"
if [ -n "$ADMIN_USER_IDS" ]; then
  export BOT_ADMIN_USER_IDS="[$ADMIN_USER_IDS]"
fi
export GOOGLE_SPREADSHEET_ID="$GOOGLE_SHEETS_ID"
export GOOGLE_CREDENTIALS_FILE="$GOOGLE_SERVICE_ACCOUNT_FILE"
export PYTHONPATH="/root/cars-bot/src:$PYTHONPATH"

echo ""
echo "=== Starting Monitor ==="
nohup python -m cars_bot.monitor.monitor > logs/monitor_output.log 2>&1 &
MONITOR_PID=$!
echo "Monitor started (PID: $MONITOR_PID)"
sleep 2

echo ""
echo "=== Starting Celery Worker ==="
nohup celery -A cars_bot.celery_app worker --loglevel=info --concurrency=4 --max-tasks-per-child=100 --queues=default,ai_processing,publishing,sheets_sync,monitoring --logfile=logs/celery_worker.log --pidfile=logs/celery_worker.pid > logs/celery_worker_output.log 2>&1 &
WORKER_PID=$!
echo "Celery Worker started (PID: $WORKER_PID)"
sleep 2

echo ""
echo "=== Starting Celery Beat ==="
rm -f celerybeat-schedule celerybeat-schedule.db 2>/dev/null || true
nohup celery -A cars_bot.celery_app beat --loglevel=info --logfile=logs/celery_beat.log --pidfile=logs/celery_beat.pid > logs/celery_beat_output.log 2>&1 &
BEAT_PID=$!
echo "Celery Beat started (PID: $BEAT_PID)"
sleep 2

echo ""
echo "=== Process Status ==="
ps aux | grep -E "(monitor.monitor|celery)" | grep -v grep || echo "No processes found"

echo ""
echo "=== Services restarted successfully ==="
echo "Monitor logs: tail -f logs/monitor_output.log"
echo "Worker logs: tail -f logs/celery_worker_output.log"
echo "Beat logs: tail -f logs/celery_beat_output.log"


