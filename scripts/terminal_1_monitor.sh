#!/bin/bash
# Terminal 1: Monitor - Мониторинг каналов

cd "/Users/edgark/CARS BOT"
source venv/bin/activate
set -a
source .env
set +a
export PYTHONPATH="/Users/edgark/CARS BOT/src:$PYTHONPATH"

clear
echo "╔═══════════════════════════════════════════════════════╗"
echo "║     📡 MONITOR - Мониторинг Telegram каналов         ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""
echo "Мониторит: @teathdhs"
echo "Статус: Запускается..."
echo ""

python -m cars_bot.monitor.monitor

