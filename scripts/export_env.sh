#!/bin/bash
# Export environment variables with proper naming for pydantic settings

# Load .env file
set -a
source /Users/edgark/CARS\ BOT/.env
set +a

# Fix REDIS_URL for local development
export REDIS_URL="redis://localhost:6379/0"

# Map variables to expected names
export BOT_NEWS_CHANNEL_ID="$NEWS_CHANNEL_ID"
# BOT_ADMIN_USER_IDS should be a JSON list or comma-separated
if [ -n "$ADMIN_USER_IDS" ]; then
  export BOT_ADMIN_USER_IDS="[$ADMIN_USER_IDS]"
fi
export GOOGLE_SPREADSHEET_ID="$GOOGLE_SHEETS_ID"
export GOOGLE_CREDENTIALS_FILE="$GOOGLE_SERVICE_ACCOUNT_FILE"

# Set PYTHONPATH
export PYTHONPATH="/Users/edgark/CARS BOT/src:$PYTHONPATH"

