#!/bin/bash
# Script to diagnose and fix Cars Bot server issues
# Run this ON THE SERVER: ssh carsbot, then ./fix_server.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================"
echo "CARS BOT - SERVER FIX SCRIPT"
echo "======================================${NC}"
echo ""

# Function to print colored messages
print_step() {
    echo -e "${BLUE}>>> $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if running on server
if [ ! -d "/root/cars-bot" ]; then
    print_error "This script must be run on the server in /root/cars-bot"
    exit 1
fi

cd /root/cars-bot

# Step 1: Backup current logs
print_step "STEP 1: Creating backup of current logs"
mkdir -p backups/logs_$(date +%Y%m%d_%H%M%S)
cp logs/*.log backups/logs_$(date +%Y%m%d_%H%M%S)/ 2>/dev/null || true
print_success "Logs backed up"

# Step 2: Stop all running instances
print_step "STEP 2: Stopping all running instances"

# Stop Docker containers
if docker ps -q | grep -q .; then
    print_warning "Docker containers found, stopping..."
    docker-compose down 2>/dev/null || true
    print_success "Docker containers stopped"
else
    print_success "No Docker containers running"
fi

# Stop Supervisor services
if supervisorctl status carsbot:* 2>/dev/null | grep -q "RUNNING"; then
    print_warning "Supervisor services found, stopping..."
    supervisorctl stop carsbot:* 2>/dev/null || true
    print_success "Supervisor services stopped"
else
    print_success "No Supervisor services running"
fi

# Kill any remaining Python processes (carefully)
print_warning "Checking for orphaned Python processes..."
pkill -f "python -m cars_bot" 2>/dev/null || true
pkill -f "celery.*cars_bot" 2>/dev/null || true
sleep 2
print_success "Orphaned processes killed"

# Step 3: Verify everything is stopped
print_step "STEP 3: Verifying all processes stopped"
PYTHON_PROCS=$(ps aux | grep "python -m cars_bot" | grep -v grep | wc -l)
CELERY_PROCS=$(ps aux | grep "celery.*cars_bot" | grep -v grep | wc -l)

if [ "$PYTHON_PROCS" -eq 0 ] && [ "$CELERY_PROCS" -eq 0 ]; then
    print_success "All processes stopped"
else
    print_error "Some processes still running:"
    ps aux | grep -E "python -m cars_bot|celery.*cars_bot" | grep -v grep
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Step 4: Check dependencies
print_step "STEP 4: Checking system dependencies"

# PostgreSQL
if systemctl is-active --quiet postgresql; then
    print_success "PostgreSQL running"
else
    print_error "PostgreSQL not running"
    read -p "Start PostgreSQL? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        systemctl start postgresql
    fi
fi

# Redis
if systemctl is-active --quiet redis; then
    print_success "Redis running"
elif redis-cli ping > /dev/null 2>&1; then
    print_success "Redis running (via other method)"
else
    print_error "Redis not running"
    read -p "Start Redis? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        systemctl start redis 2>/dev/null || redis-server --daemonize yes
    fi
fi

# Step 5: Update Supervisor configuration
print_step "STEP 5: Checking Supervisor configuration"

SUPERVISOR_CONF="/etc/supervisor/conf.d/cars-bot.conf"
if [ -f "$SUPERVISOR_CONF" ]; then
    print_warning "Supervisor config exists"
    echo "Current config:"
    head -20 "$SUPERVISOR_CONF"
    echo ""
    read -p "Recreate Supervisor config? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_warning "Please manually update the config file at:"
        echo "$SUPERVISOR_CONF"
        echo "See DIAGNOSIS_AND_FIX.md for the correct configuration"
    fi
else
    print_error "Supervisor config NOT found at $SUPERVISOR_CONF"
    print_warning "Please create it manually (see DIAGNOSIS_AND_FIX.md)"
fi

# Step 6: Start services via Supervisor
print_step "STEP 6: Starting services via Supervisor"

# Reload Supervisor config
supervisorctl reread
supervisorctl update

# Start all services
print_warning "Starting carsbot services..."
supervisorctl start carsbot:*

sleep 3

# Check status
print_step "Service Status:"
supervisorctl status carsbot:*

# Step 7: Verify services are working
print_step "STEP 7: Verifying services"

sleep 5

# Check for conflicts in bot log
if grep -q "TelegramConflictError" logs/bot_output.log 2>/dev/null; then
    print_error "Bot still has TelegramConflictError - multiple instances running!"
    echo "Check processes:"
    ps aux | grep "python -m cars_bot.bot" | grep -v grep
else
    print_success "No Telegram conflicts detected"
fi

# Check if Celery worker is running
if supervisorctl status carsbot:cars-celery-worker | grep -q "RUNNING"; then
    print_success "Celery worker is running"
    
    # Wait a bit and check if it's still running (not shutting down)
    sleep 10
    if supervisorctl status carsbot:cars-celery-worker | grep -q "RUNNING"; then
        print_success "Celery worker stable (not shutting down)"
    else
        print_error "Celery worker shut down after starting"
    fi
else
    print_error "Celery worker not running"
fi

# Check if monitor is running
if supervisorctl status carsbot:cars-monitor | grep -q "RUNNING"; then
    print_success "Monitor is running"
else
    print_error "Monitor not running"
fi

# Step 8: Show recent logs
print_step "STEP 8: Recent log entries"

echo ""
echo -e "${YELLOW}=== Bot Log (last 20 lines) ===${NC}"
tail -20 logs/bot_output.log 2>/dev/null || echo "No bot log yet"

echo ""
echo -e "${YELLOW}=== Monitor Log (last 20 lines) ===${NC}"
tail -20 logs/monitor_output.log 2>/dev/null || echo "No monitor log yet"

echo ""
echo -e "${YELLOW}=== Celery Worker Log (last 20 lines) ===${NC}"
tail -20 logs/celery_worker_output.log 2>/dev/null || echo "No worker log yet"

# Final summary
echo ""
echo -e "${BLUE}======================================"
echo "FIX COMPLETE"
echo "======================================${NC}"
echo ""
print_warning "NEXT STEPS:"
echo "1. Monitor logs for 5 minutes: tail -f logs/*.log"
echo "2. Test the bot in Telegram: /start"
echo "3. Check for TelegramConflictError in logs"
echo "4. Verify Celery worker doesn't shut down"
echo ""
print_warning "If issues persist, check DIAGNOSIS_AND_FIX.md"
echo ""

