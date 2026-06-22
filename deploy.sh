#!/bin/bash

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Exit immediately if a command exits with a non-zero status
set -e

# Error trap to log errors nicely
error_handler() {
    echo -e "\n${RED}❌ Deployment failed at line $1! Please check the errors above.${NC}"
}
trap 'error_handler $LINENO' ERR

# Start stopwatch
START_TIME=$SECONDS

# Make sure we are in the script's directory
cd "$(dirname "$0")"

# Target IP argument fallback (Allows custom IP overrides: ./deploy.sh 1.2.3.4)
TARGET_IP="${1:-104.194.146.169}"
PASSWORD="8vKh6eZ15nxXKD"
REMOTE_PATH="/usr/local/x-ui/x-ui"

echo -e "${CYAN}🚀 NetFly Deployment Script Started${NC}"
echo -e "${BLUE}📍 Target Node:${NC} root@${TARGET_IP}"

# 1. Pre-requisite checks
echo -e "\n${BLUE}🔍 Checking build dependencies...${NC}"
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js is not installed. Please install Node.js first.${NC}"
    exit 1
fi
if ! command -v go &> /dev/null; then
    echo -e "${RED}❌ Go compiler is not installed. Please install Go first.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Build dependencies found.${NC}"

# 2. Build Frontend
echo -e "\n${BLUE}📦 1. Building React Frontend...${NC}"
cd frontend
npm run build
cd ..
echo -e "${GREEN}✅ Frontend built successfully.${NC}"

# 3. Build Go Backend
echo -e "\n${BLUE}⚙️ 2. Compiling Go Backend...${NC}"
go build -ldflags="-s -w" -o x-ui main.go
BINARY_SIZE=$(du -sh x-ui | cut -f1)
echo -e "${GREEN}✅ Go backend compiled successfully (Size: ${BINARY_SIZE}).${NC}"

# 4. SSH Connection setup & sshpass check
echo -e "\n${BLUE}🛡️ 3. Setting up secure connection...${NC}"
if ! command -v sshpass &> /dev/null; then
    echo -e "${YELLOW}⚠️ sshpass is not installed. Installing it...${NC}"
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y sshpass
    elif command -v yum &> /dev/null; then
        sudo yum install -y epel-release -y && sudo yum install -y sshpass
    else
        echo -e "${RED}❌ Could not auto-install sshpass. Please install it manually.${NC}"
        exit 1
    fi
fi

# SSH execution helper
run_remote_cmd() {
    sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@"$TARGET_IP" "$1"
}

# Test connection
echo -e "${BLUE}🔌 Pinging remote server connection...${NC}"
if ! run_remote_cmd "echo 'ping'" &> /dev/null; then
    echo -e "${RED}❌ Cannot connect to root@${TARGET_IP}. Check credentials or network.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Connection successful.${NC}"

# 5. Remote operations
echo -e "\n${BLUE}💾 4. Creating backup on remote server...${NC}"
run_remote_cmd "if [ -f $REMOTE_PATH ]; then cp $REMOTE_PATH ${REMOTE_PATH}.bak && echo 'Backup created'; else echo 'No existing binary to back up'; fi"

echo -e "\n${BLUE}🗑️ 5. Deleting old binary...${NC}"
run_remote_cmd "rm -f $REMOTE_PATH"

echo -e "\n${BLUE}📤 6. Uploading new x-ui binary...${NC}"
sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no x-ui root@"$TARGET_IP":"$REMOTE_PATH"
echo -e "${GREEN}✅ Upload complete.${NC}"

echo -e "\n${BLUE}🔄 7. Setting permissions & restarting service on remote server...${NC}"
run_remote_cmd "chmod +x $REMOTE_PATH && x-ui restart"
echo -e "${GREEN}✅ x-ui service restarted.${NC}"

# Calculate elapsed time
ELAPSED=$(( SECONDS - START_TIME ))
echo -e "\n${GREEN}🎉 Deployment completed successfully in ${ELAPSED}s!${NC}\n"
