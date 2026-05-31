resource "google_storage_bucket" "bike_share_raw_bucket" {
  name                        = "${var.project_id}-bike-share-raw-${var.env}"
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = true

  versioning {
    enabled = true
  }
}

resource "google_storage_bucket" "bike_share_temp_bucket" {
  name                        = "${var.project_id}-bike-share-temp-${var.env}"
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = true
}

resource "google_storage_bucket_object" "station_csv" {
  name         = "raw/stations/stations.csv"
  bucket       = google_storage_bucket.bike_share_raw_bucket.name
  source       = "${path.module}/../sample_data/stations.csv"
  content_type = "text/csv"
}