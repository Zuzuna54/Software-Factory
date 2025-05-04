# infra/terraform/main.tf

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# Cloud SQL (PostgreSQL)
resource "google_sql_database_instance" "postgres" {
  name             = "agent-team-postgres"
  database_version = "POSTGRES_16" # Updated to 16 per blueprint
  region           = var.region

  settings {
    tier = var.db_tier

    database_flags {
      name  = "cloudsql.enable_pgvector"
      value = "on"
    }

    backup_configuration {
      enabled = true
      point_in_time_recovery_enabled = true
    }
  }

  deletion_protection = false # Set to true for production
}

resource "google_sql_database" "agent_db" {
  name     = "agent_team"
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "agent_user" {
  name     = "agent_user"
  instance = google_sql_database_instance.postgres.name
  password = var.db_password
}

# Redis (Memorystore)
resource "google_redis_instance" "agent_redis" {
  name           = "agent-team-redis"
  tier           = "BASIC" # Consider STANDARD_HA for production
  memory_size_gb = 1
  region         = var.region

  authorized_network = google_compute_network.vpc_network.id
}

# VPC Network for Redis (and potentially other services)
resource "google_compute_network" "vpc_network" {
  name = "agent-team-network"
  auto_create_subnetworks = true # Simple default, consider custom for production
}

# Cloud Storage Bucket (Optional, if needed for artifacts beyond DB)
# resource "google_storage_bucket" "artifact_storage" {
#   name     = "${var.project_id}-agent-artifacts"
#   location = var.region
#   uniform_bucket_level_access = true
# } 