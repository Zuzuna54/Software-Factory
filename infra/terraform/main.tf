provider "google" {
  project = "tactile-flash-460016-s7"
  region  = "us-central1"
}

# Cloud SQL - PostgreSQL (smallest instance)
resource "google_sql_database_instance" "software_factory_db" {
  name             = "software-factory-db"
  database_version = "POSTGRES_16"
  region           = "us-central1"

  settings {
    tier              = "db-f1-micro"
    availability_type = "ZONAL"
    
    disk_size = 10
    disk_type = "PD_SSD"
    
    database_flags {
      name  = "cloudsql.enable_pgvector"
      value = "on"
    }
    
    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = false
      # Minimum necessary backup retention
      backup_retention_settings {
        retained_backups = 3
        retention_unit   = "COUNT"
      }
    }
  }
  
  deletion_protection = false  # Set to true in production
}

# Cloud SQL - PostgreSQL Database
resource "google_sql_database" "software_factory_database" {
  name     = "software_factory"
  instance = google_sql_database_instance.software_factory_db.name
}

# Cloud SQL - PostgreSQL User
resource "google_sql_user" "software_factory_user" {
  name     = "app_user"
  instance = google_sql_database_instance.software_factory_db.name
  password = "change-me-in-production"  # Use secret manager in production
}

# Minimal Redis with Memorystore
resource "google_redis_instance" "software_factory_cache" {
  name           = "software-factory-cache"
  memory_size_gb = 1
  region         = "us-central1"
  
  # Use basic tier to minimize costs
  tier           = "BASIC"
  
  # Use lowest reasonable version
  redis_version  = "REDIS_6_X"
  
  # Disable auth - only use in development
  # Enable auth_enabled and use AUTH in production
  auth_enabled   = false
  
  # No read replicas - only use in development
  read_replicas_mode = "READ_REPLICAS_DISABLED"
}

# Google Artifact Registry for container images
resource "google_artifact_registry_repository" "software_factory_repo" {
  location      = "us-central1"
  repository_id = "software-factory"
  description   = "Docker repository for Software Factory"
  format        = "DOCKER"
}

# Cloud Storage Bucket - For Static Assets
resource "google_storage_bucket" "software_factory_assets" {
  name     = "tactile-flash-460016-s7-assets"
  location = "us-central1"
  
  # Enable object versioning only if strictly needed
  versioning {
    enabled = false
  }
  
  # Optimize for cost with Standard storage class
  storage_class = "STANDARD"
  
  # Lifecycle rules to clean up old objects
  lifecycle_rule {
    condition {
      age = 90  # Days
    }
    action {
      type = "Delete"
    }
  }
}

# Cloud Run Service
resource "google_cloud_run_service" "software_factory_api" {
  name     = "software-factory-api"
  location = "us-central1"
  
  template {
    spec {
      containers {
        image = "us-central1-docker.pkg.dev/tactile-flash-460016-s7/software-factory/api:latest"
        
        # Set resource limits to control costs
        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }
        
        # Environment variables for configuration
        env {
          name  = "DB_HOST"
          value = "/cloudsql/${google_sql_database_instance.software_factory_db.connection_name}"
        }
        
        env {
          name  = "REDIS_HOST"
          value = google_redis_instance.software_factory_cache.host
        }
        
        env {
          name  = "REDIS_PORT"
          value = google_redis_instance.software_factory_cache.port
        }
      }
    }
  }
  
  traffic {
    percent         = 100
    latest_revision = true
  }
}

# IAM for Cloud Run service
resource "google_cloud_run_service_iam_member" "software_factory_api_public" {
  service  = google_cloud_run_service.software_factory_api.name
  location = google_cloud_run_service.software_factory_api.location
  role     = "roles/run.invoker"
  member   = "allUsers"  # Public access - restrict in production
}

# Output important information
output "db_connection_name" {
  value = google_sql_database_instance.software_factory_db.connection_name
}

output "redis_host" {
  value = google_redis_instance.software_factory_cache.host
}

output "cloud_run_url" {
  value = google_cloud_run_service.software_factory_api.status[0].url
} 