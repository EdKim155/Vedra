#!/bin/bash

echo "🛑 Остановка всех процессов..."

# Stop celery
./scripts/stop_celery.sh 2>/dev/null

# Kill monitor
pkill -f "monitor.monitor" 2>/dev/null

# Remove session lock
rm -f sessions/monitor_session.session-journal

sleep 2

echo ""
echo "✅ Все процессы остановлены"
echo ""
echo "🚀 Запуск сервисов..."
echo ""

# Start monitor
echo "1️⃣ Запуск Monitor..."
./scripts/start_monitor.sh
sleep 3

# Start celery worker
echo "2️⃣ Запуск Celery Worker..."
./scripts/start_celery_worker.sh
sleep 2

# Start celery beat
echo "3️⃣ Запуск Celery Beat..."
./scripts/start_celery_beat.sh
sleep 2

echo ""
echo "✅ Все сервисы запущены!"
echo ""
echo "📊 Проверка статуса:"
ps aux | grep -E "(monitor.monitor|celery worker|celery beat)" | grep -v grep | head -10

echo ""
echo "📝 Логи монитора:"
echo "   tail -f logs/monitor_output.log"
echo ""
echo "🧪 Создайте тестовый пост в канале и проверьте логи"

