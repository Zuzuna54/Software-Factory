# Cloud Infrastructure Setup

This document outlines the cloud infrastructure setup for the Software Factory project, with a focus on cost optimization while meeting the requirements from `iteration_0.md`.

## Cost Optimization Strategy

Our primary goal is to keep monthly costs under $100 while providing all necessary services. To achieve this:

1. We leverage Google Cloud Free Tier wherever possible
2. We use minimal resource configurations for paid services
3. We implement automated cleanup policies for unused resources
4. We choose serverless options that scale to zero when not in use

## Infrastructure Components

### 1. PostgreSQL Database (Cloud SQL)

We use a cost-effective Cloud SQL PostgreSQL instance:

- **Instance Type**: db-f1-micro (shared CPU, 0.6GB RAM)
- **Estimated Cost**: ~$9/month
- **Storage**: 10GB SSD (~$1.70/month)
- **Optimizations**:
  - Minimal backup retention (3 backups)
  - Point-in-time recovery disabled
  - Zonal availability (no high-availability)
  - Extensions enabled: uuid-ossp, pgvector

### 2. Redis Cache (Memorystore)

We use a minimal Memorystore Redis instance:

- **Size**: 1GB
- **Estimated Cost**: ~$12-16/month
- **Optimizations**:
  - BASIC tier (no redundancy)
  - No read replicas
  - Authentication disabled for development (enable in production)

### 3. Docker Registry (Artifact Registry)

- **Location**: us-central1
- **Estimated Cost**: Free for first 500MB, then ~$0.10/GB/month
- **Optimizations**:
  - Regular cleanup of unused images
  - Layer sharing between images

### 4. Application Runtime (Cloud Run)

- **Configuration**: 1 CPU, 512MB RAM
- **Estimated Cost**: Pay only for actual usage (~$0.00002384/vCPU-second)
- **Optimizations**:
  - Scales to zero when not in use
  - Conservative resource allocation

### 5. Storage (Cloud Storage)

- **Configuration**: Standard storage class
- **Estimated Cost**: Free for first 5GB, then ~$0.02/GB/month
- **Optimizations**:
  - Automatic cleanup of objects older than 90 days
  - No versioning enabled

## Total Estimated Monthly Cost

| Service           | Base Cost | Variable Cost           | Total (Estimated) |
| ----------------- | --------- | ----------------------- | ----------------- |
| Cloud SQL         | $9.00     | $1.70 (10GB)            | $10.70            |
| Memorystore       | $12.00    | -                       | $12.00            |
| Artifact Registry | $0.00     | $1.00 (10GB)            | $1.00             |
| Cloud Run         | $0.00     | $5.00 (estimated usage) | $5.00             |
| Cloud Storage     | $0.00     | $1.00 (50GB)            | $1.00             |
| **Total**         |           |                         | **~$30 - $50**    |

This configuration provides all required services while keeping costs well under the $100/month target. Actual costs will depend on usage patterns.

## Deployment

The infrastructure is defined using Terraform in `infra/terraform/main.tf`. To deploy:

```bash
cd infra/terraform
terraform init
terraform plan -out=plan.out
terraform apply plan.out
```

## Monitoring Costs

To monitor and control costs:

1. Set up a budget alert in Google Cloud Console
2. Run regular cost reports with `gcloud billing accounts list-budgets`
3. Monitor resource usage with Cloud Monitoring

## Future Optimization

As the project grows, consider:

1. Using preemptible or spot instances for batch workloads
2. Implementing autoscaling policies based on actual usage patterns
3. Optimizing database queries to reduce CPU usage
4. Using BigQuery for analytics instead of running queries on the primary database
