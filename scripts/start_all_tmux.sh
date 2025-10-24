#!/bin/bash
# Start all Cars Bot services in separate tmux panes

cd "/Users/edgark/CARS BOT"

# Kill existing tmux session if it exists
tmux kill-session -t cars_bot 2>/dev/null || true

# Create new tmux session
tmux new-session -d -s cars_bot -n "Cars Bot Services"

# Split into 4 panes
tmux split-window -h -t cars_bot:0
tmux split-window -v -t cars_bot:0.0
tmux split-window -v -t cars_bot:0.2

# Pane 0 (top-left): Monitor
tmux send-keys -t cars_bot:0.0 'cd "/Users/edgark/CARS BOT"' C-m
tmux send-keys -t cars_bot:0.0 'source venv/bin/activate' C-m
tmux send-keys -t cars_bot:0.0 'source .env' C-m
tmux send-keys -t cars_bot:0.0 'export PYTHONPATH="/Users/edgark/CARS BOT/src:$PYTHONPATH"' C-m
tmux send-keys -t cars_bot:0.0 'clear' C-m
tmux send-keys -t cars_bot:0.0 'echo "📡 MONITOR - Мониторинг каналов"' C-m
tmux send-keys -t cars_bot:0.0 'echo "================================"' C-m
tmux send-keys -t cars_bot:0.0 'python -m cars_bot.monitor.monitor' C-m

# Pane 1 (bottom-left): Telegram Bot
tmux send-keys -t cars_bot:0.1 'cd "/Users/edgark/CARS BOT"' C-m
tmux send-keys -t cars_bot:0.1 'source venv/bin/activate' C-m
tmux send-keys -t cars_bot:0.1 'source .env' C-m
tmux send-keys -t cars_bot:0.1 'export PYTHONPATH="/Users/edgark/CARS BOT/src:$PYTHONPATH"' C-m
tmux send-keys -t cars_bot:0.1 'clear' C-m
tmux send-keys -t cars_bot:0.1 'echo "🤖 TELEGRAM BOT - @Vedrro_bot"' C-m
tmux send-keys -t cars_bot:0.1 'echo "================================"' C-m
tmux send-keys -t cars_bot:0.1 'python scripts/run_bot.py' C-m

# Pane 2 (top-right): Celery Worker
tmux send-keys -t cars_bot:0.2 'cd "/Users/edgark/CARS BOT"' C-m
tmux send-keys -t cars_bot:0.2 'source venv/bin/activate' C-m
tmux send-keys -t cars_bot:0.2 'source .env' C-m
tmux send-keys -t cars_bot:0.2 'export PYTHONPATH="/Users/edgark/CARS BOT/src:$PYTHONPATH"' C-m
tmux send-keys -t cars_bot:0.2 'clear' C-m
tmux send-keys -t cars_bot:0.2 'echo "⚙️  CELERY WORKER - AI обработка"' C-m
tmux send-keys -t cars_bot:0.2 'echo "================================"' C-m
tmux send-keys -t cars_bot:0.2 'celery -A cars_bot.celery_app worker --loglevel=info --concurrency=4 --queues=default,ai_processing,publishing,sheets_sync,monitoring' C-m

# Pane 3 (bottom-right): Celery Beat
tmux send-keys -t cars_bot:0.3 'cd "/Users/edgark/CARS BOT"' C-m
tmux send-keys -t cars_bot:0.3 'source venv/bin/activate' C-m
tmux send-keys -t cars_bot:0.3 'source .env' C-m
tmux send-keys -t cars_bot:0.3 'export PYTHONPATH="/Users/edgark/CARS BOT/src:$PYTHONPATH"' C-m
tmux send-keys -t cars_bot:0.3 'clear' C-m
tmux send-keys -t cars_bot:0.3 'echo "⏰ CELERY BEAT - Планировщик"' C-m
tmux send-keys -t cars_bot:0.3 'echo "================================"' C-m
tmux send-keys -t cars_bot:0.3 'celery -A cars_bot.celery_app beat --loglevel=info' C-m

# Set pane titles
tmux select-pane -t cars_bot:0.0 -T "Monitor"
tmux select-pane -t cars_bot:0.1 -T "Bot"
tmux select-pane -t cars_bot:0.2 -T "Worker"
tmux select-pane -t cars_bot:0.3 -T "Beat"

# Enable pane titles
tmux set -g pane-border-status top
tmux set -g pane-border-format "#{pane_title}"

echo ""
echo "✅ Tmux сессия 'cars_bot' создана с 4 панелями!"
echo ""
echo "Подключитесь к сессии командой:"
echo "  tmux attach-session -t cars_bot"
echo ""
echo "Управление tmux:"
echo "  Ctrl+B -> стрелки    - переключение между панелями"
echo "  Ctrl+B -> [          - режим прокрутки (q для выхода)"
echo "  Ctrl+B -> d          - отсоединиться от сессии (сервисы продолжат работать)"
echo "  Ctrl+B -> :kill-session - остановить все"
echo ""

