#!/bin/bash
# Stop all Celery workers and beat

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${RED}Stopping all Celery processes...${NC}"

# Change to project root
cd "$(dirname "$0")/.."

# Stop workers gracefully
if [ -f logs/celery_worker.pid ]; then
    PID=$(cat logs/celery_worker.pid)
    if kill -0 $PID 2>/dev/null; then
        echo "Stopping Celery worker (PID: $PID)..."
        kill -TERM $PID
        sleep 2
        # Force kill if still running
        if kill -0 $PID 2>/dev/null; then
            echo "Force stopping worker..."
            kill -9 $PID
        fi
    fi
    rm -f logs/celery_worker.pid
fi

# Stop beat
if [ -f logs/celery_beat.pid ]; then
    PID=$(cat logs/celery_beat.pid)
    if kill -0 $PID 2>/dev/null; then
        echo "Stopping Celery beat (PID: $PID)..."
        kill -TERM $PID
    fi
    rm -f logs/celery_beat.pid
fi

# Clean up schedule file
rm -f celerybeat-schedule

echo -e "${GREEN}✅ All Celery processes stopped${NC}"




