provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# Cloud SQL (PostgreSQL)
resource "google_sql_database_instance" "postgres" {
  name             = "agent-team-postgres"
  database_version = "POSTGRES_14"
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

  deletion_protection = false
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
  tier           = "BASIC"
  memory_size_gb = 1
  region         = var.region

  authorized_network = google_compute_network.vpc_network.id
}

# VPC Network for Redis
resource "google_compute_network" "vpc_network" {
  name = "agent-team-network"
}

# Cloud Storage Bucket
resource "google_storage_bucket" "artifact_storage" {
  name     = "${var.project_id}-artifacts"
  location = var.region
  uniform_bucket_level_access = true
} 