# --- S3 Buckets ---

resource "aws_s3_bucket" "landing_zone" {
  bucket = "${var.project_name}-landing-zone-${random_id.suffix.hex}"
}

resource "aws_s3_bucket_versioning" "landing_zone" {
  bucket = aws_s3_bucket.landing_zone.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket" "curated_zone" {
  bucket = "${var.project_name}-curated-zone-${random_id.suffix.hex}"
}

resource "aws_s3_bucket_versioning" "curated_zone" {
  bucket = aws_s3_bucket.curated_zone.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket" "glue_scripts" {
  bucket = "${var.project_name}-glue-scripts-${random_id.suffix.hex}"
}

# Upload Glue ETL script
resource "aws_s3_object" "etl_script" {
  bucket = aws_s3_bucket.glue_scripts.id
  key    = "scripts/fhir_to_omop_etl.py"
  source = "${path.module}/../src/glue_jobs/fhir_to_omop_etl.py"
  etag   = filemd5("${path.module}/../src/glue_jobs/fhir_to_omop_etl.py")
}

# Upload DQ script
resource "aws_s3_object" "dq_script" {
  bucket = aws_s3_bucket.glue_scripts.id
  key    = "scripts/data_quality.py"
  source = "${path.module}/../src/glue_jobs/data_quality.py"
  etag   = filemd5("${path.module}/../src/glue_jobs/data_quality.py")
}

# Package the src/ modules the job scripts import (both scripts import from
# src.*, which is not on the path of a bare Glue script) and ship the zip
# via --extra-py-files.
data "archive_file" "src_package" {
  type        = "zip"
  output_path = "${path.module}/build/vitalstream_src.zip"

  dynamic "source" {
    for_each = [
      "__init__.py",
      "data_generator/__init__.py",
      "data_generator/vocabulary.py",
      "glue_jobs/__init__.py",
      "glue_jobs/fhir_parser.py",
      "glue_jobs/omop_mapper.py",
      "shared/__init__.py",
      "shared/constants.py",
      "shared/omop_schema.py",
    ]
    content {
      content  = file("${path.module}/../src/${source.value}")
      filename = "src/${source.value}"
    }
  }
}

resource "aws_s3_object" "src_package" {
  bucket = aws_s3_bucket.glue_scripts.id
  key    = "scripts/vitalstream_src.zip"
  source = data.archive_file.src_package.output_path
  etag   = data.archive_file.src_package.output_md5
}
