#!/bin/bash
# Start Celery Beat scheduler for Cars Bot

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting Celery Beat for Cars Bot...${NC}"

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

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: Virtual environment not activated"
fi

# Check if Redis is running
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Error: Redis is not running. Please start Redis first."
    exit 1
fi

# Start Celery Beat
# -A: Application
# -l: Log level
# --scheduler: Scheduler class (default: PersistentScheduler)

celery -A cars_bot.celery_app beat \
    --loglevel=info \
    --logfile=logs/celery_beat.log \
    --pidfile=logs/celery_beat.pid

echo -e "${GREEN}✅ Celery Beat started${NC}"


