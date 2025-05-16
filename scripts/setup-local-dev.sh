#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check for pipenv
if ! command -v pipenv &> /dev/null; then
    echo -e "${RED}Error: pipenv is not installed. Please install it first:${NC}"
    echo "pip install pipenv"
    exit 1
fi

# Check for PostgreSQL
if ! command -v psql &> /dev/null; then
    echo -e "${RED}Error: PostgreSQL is not installed. Please install it first.${NC}"
    echo "Visit: https://www.postgresql.org/download/ for installation instructions."
    exit 1
fi

# Check for Redis
if ! command -v redis-cli &> /dev/null; then
    echo -e "${RED}Error: Redis is not installed. Please install it first.${NC}"
    echo "Visit: https://redis.io/download for installation instructions."
    exit 1
fi

echo -e "${GREEN}Setting up local development environment...${NC}"

# Create .env.local if it doesn't exist
if [ ! -f .env.local ]; then
    echo -e "${YELLOW}Creating .env.local from template...${NC}"
    cp .env.example .env.local
    echo -e "${GREEN}Created .env.local. Please edit it with your local settings.${NC}"
fi

# Install dependencies using pipenv
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pipenv install --dev

# Create PostgreSQL database
echo -e "${YELLOW}Setting up PostgreSQL database...${NC}"

# Source the .env.local file to get DB_ variables
if [ -f .env.local ]; then
    source .env.local
else
    echo -e "${RED}Error: .env.local file not found.${NC}"
    exit 1
fi

# Test PostgreSQL connection
echo -e "${YELLOW}Testing PostgreSQL connection...${NC}"
if ! psql -h $DB_HOST -p $DB_PORT -U $DB_USER -c '\q' postgres; then
    echo -e "${RED}Error: Could not connect to PostgreSQL.${NC}"
    echo "Please make sure PostgreSQL is running and accessible with the credentials in .env.local"
    exit 1
fi

# Create database if it doesn't exist
echo -e "${YELLOW}Creating database if it doesn't exist...${NC}"
if ! psql -h $DB_HOST -p $DB_PORT -U $DB_USER -lqt | cut -d \| -f 1 | grep -qw $DB_NAME; then
    echo -e "${YELLOW}Creating database $DB_NAME...${NC}"
    psql -h $DB_HOST -p $DB_PORT -U $DB_USER -c "CREATE DATABASE $DB_NAME;" postgres
fi

# Connect to the database and create extensions
echo -e "${YELLOW}Creating PostgreSQL extensions...${NC}"
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS \"pgvector\";"

# Test Redis connection
echo -e "${YELLOW}Testing Redis connection...${NC}"
if ! redis-cli -h $REDIS_HOST -p $REDIS_PORT ping; then
    echo -e "${RED}Error: Could not connect to Redis.${NC}"
    echo "Please make sure Redis is running and accessible with the settings in .env.local"
    exit 1
fi

# Create local storage directory if needed
if [ "$USE_CLOUD_STORAGE" = "false" ]; then
    if [ ! -d "$LOCAL_STORAGE_PATH" ]; then
        mkdir -p $LOCAL_STORAGE_PATH
        echo -e "${GREEN}Created local storage directory at $LOCAL_STORAGE_PATH${NC}"
    fi
fi

# Run database migrations
echo -e "${YELLOW}Running database migrations...${NC}"
pipenv run alembic upgrade head

echo -e "${GREEN}Local development environment setup complete!${NC}"
echo -e "${GREEN}You can now start the application with: pipenv run start${NC}" 