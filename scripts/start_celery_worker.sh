#!/bin/bash
# Start Celery worker for Cars Bot

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting Celery Worker for Cars Bot...${NC}"

# Change to project root
cd "$(dirname "$0")/.."

# Load .env file
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
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "✅ Loaded environment variables from .env"
else
    echo "⚠️  Warning: .env file not found"
fi

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Virtual environment activated"
elif [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: Virtual environment not found or activated"
fi

# Check if Redis is running
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Error: Redis is not running. Please start Redis first."
    echo "   Run: redis-server (or via Docker: docker run -d -p 6379:6379 redis)"
    exit 1
fi

# Start Celery worker with concurrency
# -A: Application
# -l: Log level
# -c: Concurrency (number of worker processes)
# --max-tasks-per-child: Restart worker after N tasks (prevent memory leaks)
# -Q: Queues to consume from

celery -A cars_bot.celery_app worker \
    --loglevel=info \
    --concurrency=4 \
    --max-tasks-per-child=100 \
    --queues=default,ai_processing,publishing,sheets_sync,monitoring \
    --logfile=logs/celery_worker.log \
    --pidfile=logs/celery_worker.pid

# Alternative: Start with specific queue priorities
# celery -A cars_bot.celery_app worker \
#     --loglevel=info \
#     --concurrency=2 \
#     --queues=ai_processing \
#     --logfile=logs/celery_worker_ai.log \
#     --pidfile=logs/celery_worker_ai.pid


