## Service Account
resource "google_service_account" "dataproc_sa" {
  account_id   = "bike-share-dataproc-sa"
  display_name = "Bike Share Dataproc Service Account"
}

#IAM Permissions
resource "google_project_iam_member" "dataproc_worker" {
  project = var.project_id
  role    = "roles/dataproc.worker"
  member  = "serviceAccount:${google_service_account.dataproc_sa.email}"
}

resource "google_project_iam_member" "dataproc_bigquery_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.dataproc_sa.email}"
}

resource "google_project_iam_member" "dataproc_bigquery_data_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.dataproc_sa.email}"
}

resource "google_project_iam_member" "dataproc_storage_object_admin" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.dataproc_sa.email}"
}

resource "google_project_iam_member" "dataproc_logging_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.dataproc_sa.email}"
}

resource "google_project_iam_member" "dataproc_monitoring_writer" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.dataproc_sa.email}"
}

resource "google_project_iam_member" "dataproc_bigquery_read_session_user" {
  project = var.project_id
  role    = "roles/bigquery.readSessionUser"
  member  = "serviceAccount:${google_service_account.dataproc_sa.email}"
}

resource "google_dataproc_cluster" "bike_share_cluster" {
  name   = "bike-share-spark-cluster"
  project = var.project_id
  region = var.region

  cluster_config {
    staging_bucket = google_storage_bucket.bike_share_temp_bucket.name
    temp_bucket    = google_storage_bucket.bike_share_temp_bucket.name

    gce_cluster_config {
      subnetwork          = google_compute_subnetwork.bike_share_private_subnet.self_link
      service_account     = google_service_account.dataproc_sa.email
      internal_ip_only    = true
      tags = [var.iap_ssh_tag]
      service_account_scopes = [
        "https://www.googleapis.com/auth/cloud-platform"
      ]
    }

    master_config {
      num_instances = 1
      machine_type  = "e2-standard-2"

      disk_config {
        boot_disk_type    = "pd-balanced"
        boot_disk_size_gb = 50
      }
    }

    worker_config {
      num_instances = 2
      machine_type  = "e2-standard-2"

      disk_config {
        boot_disk_type    = "pd-balanced"
        boot_disk_size_gb = 50
      }
    }

    software_config {
      image_version = "2.2-debian12"
    }

    endpoint_config {
      enable_http_port_access = true
    }
  }

  depends_on = [
    google_project_iam_member.dataproc_worker,
    google_project_iam_member.dataproc_bigquery_job_user,
    google_project_iam_member.dataproc_bigquery_data_editor,
    google_project_iam_member.dataproc_storage_object_admin,
    google_project_iam_member.dataproc_bigquery_read_session_user
  ]
}

