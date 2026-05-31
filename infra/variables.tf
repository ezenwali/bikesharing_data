variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region"
  type        = string
  default     = "us-central1"
}

variable "iap_ssh_tag" {
  description = "Firewall tag for allowing SSH through Identity-Aware Proxy (IAP)"
  type        = string
  default     = "allow-iap-ssh"
}

variable "env" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}