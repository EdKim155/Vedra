#!/bin/bash
# Run all Cars Bot services

cd "/Users/edgark/CARS BOT"

# Load environment variables
set -a
source .env
set +a

# Fix and map environment variables
export REDIS_URL="redis://localhost:6379/0"
export CELERY_BROKER_URL="$REDIS_URL"
export CELERY_RESULT_BACKEND="$REDIS_URL"
export BOT_NEWS_CHANNEL_ID="$NEWS_CHANNEL_ID"
if [ -n "$ADMIN_USER_IDS" ]; then
  export BOT_ADMIN_USER_IDS="[$ADMIN_USER_IDS]"
fi
export GOOGLE_SPREADSHEET_ID="$GOOGLE_SHEETS_ID"
export GOOGLE_CREDENTIALS_FILE="$GOOGLE_SERVICE_ACCOUNT_FILE"
export PYTHONPATH="/Users/edgark/CARS BOT/src:$PYTHONPATH"

# Activate virtual environment
source venv/bin/activate

# Start services
echo "🚀 Starting all services..."

# Monitor Service
echo "Starting Monitor Service..."
nohup python -m cars_bot.monitor.monitor > logs/monitor_output.log 2>&1 &
MONITOR_PID=$!
echo "Monitor started with PID: $MONITOR_PID"

# Telegram Bot
echo "Starting Telegram Bot..."
nohup python scripts/run_bot.py > logs/bot_output.log 2>&1 &
BOT_PID=$!
echo "Bot started with PID: $BOT_PID"

# Celery Worker
echo "Starting Celery Worker..."
nohup celery -A cars_bot.celery_app worker \
    --loglevel=info \
    --concurrency=4 \
    --max-tasks-per-child=100 \
    --queues=default,ai_processing,publishing,sheets_sync,monitoring \
    --logfile=logs/celery_worker.log \
    --pidfile=logs/celery_worker.pid > logs/celery_worker_output.log 2>&1 &
WORKER_PID=$!
echo "Celery Worker started with PID: $WORKER_PID"

# Celery Beat
echo "Starting Celery Beat..."
nohup celery -A cars_bot.celery_app beat \
    --loglevel=info \
    --logfile=logs/celery_beat.log \
    --pidfile=logs/celery_beat.pid > logs/celery_beat_output.log 2>&1 &
BEAT_PID=$!
echo "Celery Beat started with PID: $BEAT_PID"

echo ""
echo "✅ All services started!"
echo "PIDs: Monitor=$MONITOR_PID, Bot=$BOT_PID, Worker=$WORKER_PID, Beat=$BEAT_PID"
echo ""
echo "To check status: ps aux | grep -E '(monitor|run_bot|celery)' | grep -v grep"
echo "To stop all: pkill -f 'monitor.py'; pkill -f 'run_bot.py'; pkill -f 'celery.*cars_bot'"



