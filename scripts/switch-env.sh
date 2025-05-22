#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env.docker and .env.local exist
if [ ! -f .env.docker ] && [ ! -f .env.local ]; then
    echo -e "${RED}Error: Neither .env.docker nor .env.local were found.${NC}"
    echo "Please make sure these files exist before trying to switch environments."
    exit 1
fi

# If .env.docker doesn't exist but .env exists, rename it
if [ ! -f .env.docker ] && [ -f .env ]; then
    echo -e "${YELLOW}Renaming .env to .env.docker...${NC}"
    mv .env .env.docker
fi

# Function to switch to Docker environment
switch_to_docker() {
    if [ ! -f .env.docker ]; then
        echo -e "${RED}Error: .env.docker not found.${NC}"
        exit 1
    fi
    
    # If .env exists, save it as .env.local first
    if [ -f .env ] && [ ! -f .env.local ]; then
        echo -e "${YELLOW}Backing up current .env to .env.local...${NC}"
        cp .env .env.local
    fi
    
    # Copy docker environment to .env
    echo -e "${YELLOW}Switching to Docker environment...${NC}"
    cp .env.docker .env
    
    echo -e "${GREEN}Now using Docker environment. Use docker-compose to start your services.${NC}"
}

# Function to switch to local environment
switch_to_local() {
    if [ ! -f .env.local ]; then
        echo -e "${RED}Error: .env.local not found.${NC}"
        exit 1
    fi
    
    # If .env exists, save it as .env.docker first
    if [ -f .env ] && [ ! -f .env.docker ]; then
        echo -e "${YELLOW}Backing up current .env to .env.docker...${NC}"
        cp .env .env.docker
    fi
    
    # Copy local environment to .env
    echo -e "${YELLOW}Switching to local environment...${NC}"
    cp .env.local .env
    
    echo -e "${GREEN}Now using local environment. Run the following to start services:${NC}"
    echo -e "./scripts/start-services.sh"
    echo -e "pipenv run start"
}

# Main script logic
if [ "$1" == "docker" ]; then
    switch_to_docker
elif [ "$1" == "local" ]; then
    switch_to_local
else
    echo "Usage: $0 [docker|local]"
    echo ""
    echo "  docker  - Switch to Docker environment"
    echo "  local   - Switch to local direct development environment"
    echo ""
    
    # Show current environment
    if [ -f .env ]; then
        if grep -q "DOCKER_ENVIRONMENT=true" .env; then
            echo -e "Current environment: ${GREEN}Docker${NC}"
        else
            echo -e "Current environment: ${GREEN}Local${NC}"
        fi
    else
        echo -e "Current environment: ${RED}Not set${NC}"
    fi
fi 