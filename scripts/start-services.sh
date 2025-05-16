#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting local services for Software Factory...${NC}"

# Check PostgreSQL status
if ! pg_ctl status > /dev/null 2>&1; then
    echo -e "${YELLOW}PostgreSQL is not running. Starting PostgreSQL...${NC}"
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        brew services start postgresql
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if [ -f /etc/systemd/system/postgresql.service ]; then
            sudo systemctl start postgresql
        else
            sudo service postgresql start
        fi
    else
        echo -e "${RED}Unsupported OS. Please start PostgreSQL manually.${NC}"
    fi
    
    # Wait for PostgreSQL to start
    echo -e "${YELLOW}Waiting for PostgreSQL to start...${NC}"
    sleep 5
    
    if pg_ctl status > /dev/null 2>&1; then
        echo -e "${GREEN}PostgreSQL started successfully.${NC}"
    else
        echo -e "${RED}Failed to start PostgreSQL. Please start it manually.${NC}"
    fi
else
    echo -e "${GREEN}PostgreSQL is already running.${NC}"
fi

# Check Redis status
if ! redis-cli ping > /dev/null 2>&1; then
    echo -e "${YELLOW}Redis is not running. Starting Redis...${NC}"
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        brew services start redis
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if [ -f /etc/systemd/system/redis.service ]; then
            sudo systemctl start redis
        else
            sudo service redis-server start
        fi
    else
        echo -e "${RED}Unsupported OS. Please start Redis manually.${NC}"
    fi
    
    # Wait for Redis to start
    echo -e "${YELLOW}Waiting for Redis to start...${NC}"
    sleep 2
    
    if redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}Redis started successfully.${NC}"
    else
        echo -e "${RED}Failed to start Redis. Please start it manually.${NC}"
    fi
else
    echo -e "${GREEN}Redis is already running.${NC}"
fi

echo -e "${GREEN}All services are running. You can now start the application.${NC}" 