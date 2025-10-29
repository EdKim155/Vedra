#!/bin/bash
# Install Supervisor configuration for Cars Bot
# Run this ON THE SERVER: ssh carsbot, then ./install_supervisor_config.sh

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}======================================"
echo "Installing Supervisor Configuration"
echo "======================================${NC}"
echo ""

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
    echo -e "${YELLOW}This script requires root privileges.${NC}"
    echo "Run with: sudo ./install_supervisor_config.sh"
    exit 1
fi

SUPERVISOR_CONF="/etc/supervisor/conf.d/cars-bot.conf"
BACKUP_CONF="/etc/supervisor/conf.d/cars-bot.conf.backup.$(date +%Y%m%d_%H%M%S)"

# Backup existing configuration
if [ -f "$SUPERVISOR_CONF" ]; then
    echo -e "${YELLOW}Backing up existing configuration...${NC}"
    cp "$SUPERVISOR_CONF" "$BACKUP_CONF"
    echo -e "${GREEN}✅ Backup saved to: $BACKUP_CONF${NC}"
fi

# Copy new configuration
echo -e "${BLUE}Installing new configuration...${NC}"
cp /root/cars-bot/supervisor_config.conf "$SUPERVISOR_CONF"
echo -e "${GREEN}✅ Configuration installed to: $SUPERVISOR_CONF${NC}"

# Set proper permissions
chmod 644 "$SUPERVISOR_CONF"

# Reload Supervisor
echo -e "${BLUE}Reloading Supervisor...${NC}"
supervisorctl reread
supervisorctl update

echo ""
echo -e "${GREEN}======================================"
echo "Installation Complete!"
echo "======================================${NC}"
echo ""
echo "To start services, run:"
echo "  supervisorctl start carsbot:*"
echo ""
echo "To check status:"
echo "  supervisorctl status carsbot:*"
echo ""

