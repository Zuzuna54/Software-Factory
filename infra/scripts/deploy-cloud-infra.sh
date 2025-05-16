#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="tactile-flash-460016-s7"
REGION="us-central1"

echo -e "${GREEN}Software Factory Cloud Infrastructure Deployment${NC}"
echo "This script will deploy the cloud infrastructure for the Software Factory project."
echo "Make sure you have gcloud and terraform installed and configured."
echo ""

# Check that gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud is not installed. Please install it first.${NC}"
    exit 1
fi

# Check that terraform is installed
if ! command -v terraform &> /dev/null; then
    echo -e "${RED}Error: terraform is not installed. Please install it first.${NC}"
    exit 1
fi

# Ensure we're using the correct project
echo -e "${YELLOW}Setting project to $PROJECT_ID${NC}"
gcloud config set project $PROJECT_ID

# Ensure required APIs are enabled
echo -e "${YELLOW}Enabling required APIs...${NC}"
gcloud services enable compute.googleapis.com \
    sqladmin.googleapis.com \
    artifactregistry.googleapis.com \
    redis.googleapis.com \
    run.googleapis.com

# Navigate to terraform directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$SCRIPT_DIR/../terraform"

if [ ! -d "$TERRAFORM_DIR" ]; then
    echo -e "${RED}Error: Terraform directory not found at $TERRAFORM_DIR${NC}"
    exit 1
fi

cd $TERRAFORM_DIR

# Initialize Terraform
echo -e "${YELLOW}Initializing Terraform...${NC}"
terraform init

# Plan the deployment
echo -e "${YELLOW}Planning Terraform deployment...${NC}"
terraform plan -out=plan.out

# Ask for confirmation
echo ""
echo -e "${YELLOW}Ready to apply the Terraform plan. This will create cloud resources and incur costs.${NC}"
read -p "Do you want to continue? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}Deployment cancelled.${NC}"
    exit 0
fi

# Apply the deployment
echo -e "${YELLOW}Applying Terraform plan...${NC}"
terraform apply plan.out

# Display outputs
echo ""
echo -e "${GREEN}Infrastructure deployed successfully!${NC}"
echo ""
echo "Cloud SQL Connection Name: $(terraform output db_connection_name)"
echo "Redis Host: $(terraform output redis_host)"
echo "Cloud Run URL: $(terraform output cloud_run_url)"
echo ""

# Set up budget alert
echo -e "${YELLOW}Setting up budget alert for $100...${NC}"
BILLING_ACCOUNT=$(gcloud billing projects describe $PROJECT_ID --format='value(billingAccountName)')

if [ -z "$BILLING_ACCOUNT" ]; then
    echo -e "${RED}No billing account found for project $PROJECT_ID${NC}"
else
    BILLING_ACCOUNT_ID=${BILLING_ACCOUNT#billingAccounts/}
    
    # Check if budget already exists
    BUDGET_EXISTS=$(gcloud billing budgets list --billing-account=$BILLING_ACCOUNT_ID --filter="displayName:Software Factory Budget" --format="value(name)")
    
    if [ -n "$BUDGET_EXISTS" ]; then
        echo "Budget alert already exists."
    else
        # Create budget JSON file
        cat > budget.json << EOL
{
  "displayName": "Software Factory Budget",
  "budgetFilter": {
    "projects": ["projects/$PROJECT_ID"]
  },
  "amount": {
    "specifiedAmount": {
      "currencyCode": "USD",
      "units": "100"
    }
  },
  "thresholdRules": [
    {
      "thresholdPercent": 0.5
    },
    {
      "thresholdPercent": 0.75
    },
    {
      "thresholdPercent": 0.9
    },
    {
      "thresholdPercent": 1.0
    }
  ]
}
EOL
        
        gcloud billing budgets create --billing-account=$BILLING_ACCOUNT_ID --budget-file=budget.json
        rm budget.json
        echo "Budget alert created for $100."
    fi
fi

# Provide cost monitoring command
echo ""
echo -e "${GREEN}To monitor costs, run:${NC}"
echo "  gcloud billing accounts list-budgets $BILLING_ACCOUNT_ID"
echo ""
echo -e "${GREEN}To view current resource usage:${NC}"
echo "  gcloud compute instances list"
echo "  gcloud sql instances list"
echo "  gcloud redis instances list"
echo "  gcloud run services list"
echo ""
echo -e "${YELLOW}Remember: Clean up resources when not in use to minimize costs!${NC}" 