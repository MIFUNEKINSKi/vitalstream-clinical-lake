# --- Glue Data Catalog ---

resource "aws_glue_catalog_database" "vitalstream_db" {
  name = "${var.project_name}_db"
}

# --- Glue ETL Job: FHIR → OMOP ---

resource "aws_glue_job" "fhir_to_omop_etl" {
  name     = "${var.project_name}_fhir_to_omop"
  role_arn = aws_iam_role.glue_role.arn

  glue_version      = var.glue_version
  worker_type       = var.glue_worker_type
  number_of_workers = var.glue_number_of_workers

  command {
    name            = "glueetl"
    script_location = "s3://${aws_s3_bucket.glue_scripts.bucket}/scripts/fhir_to_omop_etl.py"
    python_version  = "3"
  }

  default_arguments = {
    "--source_path"                = "s3://${aws_s3_bucket.landing_zone.bucket}/raw/"
    "--target_path"                = "s3://${aws_s3_bucket.curated_zone.bucket}/omop"
    "--pcornet_target_path"        = "s3://${aws_s3_bucket.curated_zone.bucket}/pcornet"
    "--extra-py-files"             = "s3://${aws_s3_bucket.glue_scripts.bucket}/${aws_s3_object.src_package.key}"
    "--enable-metrics"             = "true"
    "--enable-continuous-cloudwatch-log" = "true"
    "--job-language"               = "python"
  }
}

# --- Glue DQ Job ---

resource "aws_glue_job" "data_quality" {
  name     = "${var.project_name}_data_quality"
  role_arn = aws_iam_role.glue_role.arn

  glue_version      = var.glue_version
  worker_type       = var.glue_worker_type
  number_of_workers = var.glue_number_of_workers

  command {
    name            = "glueetl"
    script_location = "s3://${aws_s3_bucket.glue_scripts.bucket}/scripts/data_quality.py"
    python_version  = "3"
  }

  default_arguments = {
    "--target_path"                = "s3://${aws_s3_bucket.curated_zone.bucket}/omop"
    "--pcornet_target_path"        = "s3://${aws_s3_bucket.curated_zone.bucket}/pcornet"
    "--dq_output_path"             = "s3://${aws_s3_bucket.curated_zone.bucket}/dq_reports"
    "--extra-py-files"             = "s3://${aws_s3_bucket.glue_scripts.bucket}/${aws_s3_object.src_package.key}"
    "--enable-metrics"             = "true"
    "--enable-continuous-cloudwatch-log" = "true"
    "--job-language"               = "python"
  }
}

# --- Glue Crawler ---

resource "aws_glue_crawler" "vitalstream_crawler" {
  database_name = aws_glue_catalog_database.vitalstream_db.name
  name          = "${var.project_name}_crawler"
  role          = aws_iam_role.glue_role.arn

  # One target per table folder: with CombineCompatibleSchemas a parent target
  # (omop/, pcornet/) collapses into a single partitioned table instead of the
  # per-table names Athena queries and the dbt athena target expect.
  dynamic "s3_target" {
    for_each = [
      "omop/person/",
      "omop/visit_occurrence/",
      "omop/measurement/",
      "pcornet/demographic/",
      "pcornet/encounter/",
      "pcornet/vital/",
      "pcornet/obs_clin/",
    ]
    content {
      path = "s3://${aws_s3_bucket.curated_zone.bucket}/${s3_target.value}"
    }
  }

  s3_target {
    path = "s3://${aws_s3_bucket.curated_zone.bucket}/dq_reports/data_quality_report/"
  }

  s3_target {
    path = "s3://${aws_s3_bucket.curated_zone.bucket}/dq_reports/pcornet_data_quality_report/"
  }

  configuration = jsonencode({
    Grouping = {
      TableGroupingPolicy = "CombineCompatibleSchemas"
    }
  })
}
