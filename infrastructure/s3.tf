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
