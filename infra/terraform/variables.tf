variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region to deploy resources"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "The GCP zone within the region"
  type        = string
  default     = "us-central1-a"
}

variable "db_tier" {
  description = "The database machine tier"
  type        = string
  default     = "db-f1-micro"
}

variable "db_password" {
  description = "The database password"
  type        = string
  sensitive   = true
} 