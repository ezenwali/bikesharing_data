# VPC
resource "google_compute_network" "bike_share_vpc" {
  name                    = "bike-share-vpc"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
}

# Private subnet for Dataflow, Dataproc, Composer
resource "google_compute_subnetwork" "bike_share_private_subnet" {
  name          = "bike-share-private-subnet"
  ip_cidr_range = "10.0.1.0/24"
  region        = var.region
  network       = google_compute_network.bike_share_vpc.id

  # Allows private workers without external IPs to access Google APIs
  # such as BigQuery, Cloud Storage, Pub/Sub, and Dataflow.
  private_ip_google_access = true

  log_config {
    aggregation_interval = "INTERVAL_30_SEC"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

# Cloud Router for NAT
resource "google_compute_router" "bike_share_router" {
  name    = "bike-share-router"
  region  = var.region
  network = google_compute_network.bike_share_vpc.id
}

# Cloud NAT
# Provides controlled outbound access for private workers
resource "google_compute_router_nat" "bike_share_nat" {
  name                               = "bike-share-nat"
  router                             = google_compute_router.bike_share_router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "LIST_OF_SUBNETWORKS"

  subnetwork {
    name                    = google_compute_subnetwork.bike_share_private_subnet.id
    source_ip_ranges_to_nat = ["ALL_IP_RANGES"]
  }

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# Allow internal communication inside the VPC
# Needed for Dataproc/Spark workers and internal services
resource "google_compute_firewall" "bike_share_allow_internal" {
  name    = "bike-share-allow-internal"
  network = google_compute_network.bike_share_vpc.name

  direction = "INGRESS"

  allow {
    protocol = "tcp"
  }

  allow {
    protocol = "udp"
  }

  allow {
    protocol = "icmp"
  }

  source_ranges = [
    google_compute_subnetwork.bike_share_private_subnet.ip_cidr_range
  ]
}