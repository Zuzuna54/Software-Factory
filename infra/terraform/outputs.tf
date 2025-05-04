output "database_connection_name" {
  value = google_sql_database_instance.postgres.connection_name
}

output "redis_host" {
  value = google_redis_instance.agent_redis.host
}

output "redis_port" {
  value = google_redis_instance.agent_redis.port
}

output "storage_bucket" {
  value = google_storage_bucket.artifact_storage.name
} 