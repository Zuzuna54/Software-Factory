# infra/terraform/outputs.tf

output "database_connection_name" {
  description = "The connection name of the Cloud SQL instance."
  value       = google_sql_database_instance.postgres.connection_name
}

output "database_public_ip_address" {
  description = "The public IP address of the Cloud SQL instance (if configured)."
  value       = google_sql_database_instance.postgres.public_ip_address
}

output "database_private_ip_address" {
  description = "The private IP address of the Cloud SQL instance."
  value       = google_sql_database_instance.postgres.private_ip_address
}

output "redis_host" {
  description = "The hostname or IP address of the Redis instance."
  value       = google_redis_instance.agent_redis.host
}

output "redis_port" {
  description = "The port number of the Redis instance."
  value       = google_redis_instance.agent_redis.port
}

# output "storage_bucket_name" {
#   description = "The name of the Cloud Storage bucket for artifacts."
#   value       = google_storage_bucket.artifact_storage.name
# } 