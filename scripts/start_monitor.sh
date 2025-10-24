#!/bin/bash
# Start Monitor Service

cd "/Users/edgark/CARS BOT"

# Load .env file
set -a
source .env
set +a

# Fix and map environment variables
export REDIS_URL="redis://localhost:6379/0"
export BOT_NEWS_CHANNEL_ID="$NEWS_CHANNEL_ID"
if [ -n "$ADMIN_USER_IDS" ]; then
  export BOT_ADMIN_USER_IDS="[$ADMIN_USER_IDS]"
fi
export GOOGLE_SPREADSHEET_ID="$GOOGLE_SHEETS_ID"
export GOOGLE_CREDENTIALS_FILE="$GOOGLE_SERVICE_ACCOUNT_FILE"
export PYTHONPATH="/Users/edgark/CARS BOT/src:$PYTHONPATH"

source venv/bin/activate

echo "🚀 Starting Monitor Service..."
python -m cars_bot.monitor.monitor

