#!/bin/bash
# Deploy fixes to the server
# Run this FROM YOUR LOCAL MACHINE

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

SERVER="carsbot"
SERVER_PATH="/root/cars-bot"

echo -e "${BLUE}======================================"
echo "Deploying Fixes to Cars Bot Server"
echo "======================================${NC}"
echo ""

# Step 1: Upload files
echo -e "${BLUE}Step 1: Uploading files to server...${NC}"

echo "- Uploading fix scripts..."
scp fix_server.sh ${SERVER}:${SERVER_PATH}/
scp install_supervisor_config.sh ${SERVER}:${SERVER_PATH}/
scp supervisor_config.conf ${SERVER}:${SERVER_PATH}/
scp DIAGNOSIS_AND_FIX.md ${SERVER}:${SERVER_PATH}/

echo "- Uploading updated monitor code..."
scp -r src/cars_bot/monitor/ ${SERVER}:${SERVER_PATH}/src/cars_bot/

echo -e "${GREEN}✅ Files uploaded${NC}"
echo ""

# Step 2: Make scripts executable
echo -e "${BLUE}Step 2: Making scripts executable...${NC}"
ssh ${SERVER} "cd ${SERVER_PATH} && chmod +x fix_server.sh install_supervisor_config.sh"
echo -e "${GREEN}✅ Scripts are executable${NC}"
echo ""

# Step 3: Instructions
echo -e "${YELLOW}======================================"
echo "NEXT STEPS - Run on server:"
echo "======================================${NC}"
echo ""
echo "1. Connect to server:"
echo -e "   ${BLUE}ssh ${SERVER}${NC}"
echo ""
echo "2. Install supervisor configuration (as root):"
echo -e "   ${BLUE}sudo ./install_supervisor_config.sh${NC}"
echo ""
echo "3. Run the fix script:"
echo -e "   ${BLUE}./fix_server.sh${NC}"
echo ""
echo "4. Monitor the logs:"
echo -e "   ${BLUE}tail -f logs/*.log${NC}"
echo ""
echo "5. Test the bot:"
echo -e "   ${BLUE}Send /start to @Vedrro_bot in Telegram${NC}"
echo ""
echo -e "${YELLOW}======================================"
echo "Or run all at once:"
echo "======================================${NC}"
echo -e "${BLUE}ssh ${SERVER} 'cd ${SERVER_PATH} && sudo ./install_supervisor_config.sh && ./fix_server.sh'${NC}"
echo ""

