# infra/terraform/variables.tf

variable "project_id" {
  description = "The GCP project ID"
  type        = string
  # No default, should be provided via environment or tfvars
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
  description = "The database machine tier (e.g., db-f1-micro, db-g1-small)"
  type        = string
  default     = "db-f1-micro"
}

variable "db_password" {
  description = "The database password for the agent_user"
  type        = string
  sensitive   = true
  # No default, should be provided securely
} 