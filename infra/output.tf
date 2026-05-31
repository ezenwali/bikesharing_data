output "raw_bucket_name" {
  value = google_storage_bucket.bike_share_raw_bucket.name
}

output "temp_bucket_name" {
  value = google_storage_bucket.bike_share_temp_bucket.name
}

output "dataproc_cluster_name" {
  value = google_dataproc_cluster.bike_share_cluster.name
}

output "dataproc_service_account" {
  value = google_service_account.dataproc_sa.email
}

output "station_csv_gcs_path" {
  value = "gs://${google_storage_bucket.bike_share_raw_bucket.name}/raw/stations/stations.csv"
}

output "trip_stream_gcs_path" {
  value = "gs://${google_storage_bucket.bike_share_raw_bucket.name}/raw/trips/"
}