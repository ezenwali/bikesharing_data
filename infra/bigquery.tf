resource "google_bigquery_dataset" "bike_silver" {
  dataset_id                 = "bike_silver"
  project                    = var.project_id
  location                   = var.region
  delete_contents_on_destroy = true
}

resource "google_bigquery_dataset" "bike_gold" {
  dataset_id                 = "bike_gold"
  project                    = var.project_id
  location                   = var.region
  delete_contents_on_destroy = true
}

resource "google_bigquery_dataset" "bike_audit" {
  dataset_id                 = "bike_audit"
  project                    = var.project_id
  location                   = var.region
  delete_contents_on_destroy = true
}