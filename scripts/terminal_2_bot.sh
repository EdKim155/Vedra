#!/bin/bash
# Terminal 2: Telegram Bot

cd "/Users/edgark/CARS BOT"
source venv/bin/activate
set -a
source .env
set +a
export PYTHONPATH="/Users/edgark/CARS BOT/src:$PYTHONPATH"

clear
echo "╔═══════════════════════════════════════════════════════╗"
echo "║          🤖 TELEGRAM BOT - @Vedrro_bot                ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""
echo "Обрабатывает команды пользователей"
echo "Управляет подписками"
echo "Статус: Запускается..."
echo ""

python scripts/run_bot.py

