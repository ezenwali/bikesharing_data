# -----------------------------
# Enable Dataform API
# -----------------------------
resource "google_project_service" "dataform" {
  project            = var.project_id
  service            = "dataform.googleapis.com"
  disable_on_destroy = false
}

# -----------------------------
# Create Dataform execution service account
# -----------------------------
resource "google_service_account" "dataform_sa" {
  project      = var.project_id
  account_id   = "bike-share-dataform-sa"
  display_name = "Bike Share Dataform Service Account"
}

# -----------------------------
# Create/get Dataform service agent
# -----------------------------
resource "google_project_service_identity" "dataform" {
  provider = google-beta
  project  = var.project_id
  service  = "dataform.googleapis.com"

  depends_on = [
    google_project_service.dataform
  ]
}

# -----------------------------
# Allow Dataform service agent to impersonate custom Dataform SA
# Required for strict act-as mode
# -----------------------------
resource "google_service_account_iam_member" "dataform_service_agent_sa_user" {
  service_account_id = google_service_account.dataform_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_project_service_identity.dataform.email}"
}

resource "google_service_account_iam_member" "dataform_service_agent_token_creator" {
  service_account_id = google_service_account.dataform_sa.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${google_project_service_identity.dataform.email}"
}

# -----------------------------
# BigQuery permissions for Dataform execution SA
# -----------------------------
resource "google_project_iam_member" "dataform_bigquery_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.dataform_sa.email}"
}

# Read silver tables
resource "google_bigquery_dataset_iam_member" "dataform_silver_viewer" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.bike_silver.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.dataform_sa.email}"
}

# Write gold marts
resource "google_bigquery_dataset_iam_member" "dataform_gold_editor" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.bike_gold.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.dataform_sa.email}"
}

# Optional: allow assertions/audit writes if you use bike_audit for Dataform assertions
resource "google_bigquery_dataset_iam_member" "dataform_audit_editor" {
  project    = var.project_id
  dataset_id = google_bigquery_dataset.bike_audit.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.dataform_sa.email}"
}

# -----------------------------
# Dataform repository
# -----------------------------
resource "google_dataform_repository" "bike_share_repo" {
  provider = google-beta

  project = var.project_id
  region  = var.region
  name    = "bike-share-dataform-repo"

  service_account = google_service_account.dataform_sa.email

  depends_on = [
    google_project_service.dataform,
    google_service_account_iam_member.dataform_service_agent_sa_user,
    google_service_account_iam_member.dataform_service_agent_token_creator,
    google_project_iam_member.dataform_bigquery_job_user,
    google_bigquery_dataset_iam_member.dataform_silver_viewer,
    google_bigquery_dataset_iam_member.dataform_gold_editor,
    google_bigquery_dataset_iam_member.dataform_audit_editor
  ]
}