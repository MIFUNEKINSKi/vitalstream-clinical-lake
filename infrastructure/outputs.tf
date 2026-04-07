output "landing_zone_bucket" {
  description = "S3 bucket for raw FHIR Bundle uploads"
  value       = aws_s3_bucket.landing_zone.bucket
}

output "curated_zone_bucket" {
  description = "S3 bucket for processed OMOP Parquet tables"
  value       = aws_s3_bucket.curated_zone.bucket
}

output "glue_scripts_bucket" {
  description = "S3 bucket for Glue job scripts"
  value       = aws_s3_bucket.glue_scripts.bucket
}

output "glue_database" {
  description = "Glue Data Catalog database name"
  value       = aws_glue_catalog_database.vitalstream_db.name
}

output "glue_crawler" {
  description = "Glue Crawler name"
  value       = aws_glue_crawler.vitalstream_crawler.name
}

output "state_machine_arn" {
  description = "Step Functions state machine ARN"
  value       = aws_sfn_state_machine.pipeline.arn
}

output "validation_lambda_name" {
  description = "Validation Lambda function name"
  value       = aws_lambda_function.validation_lambda.function_name
}

output "etl_job_name" {
  description = "Glue ETL job name"
  value       = aws_glue_job.fhir_to_omop_etl.name
}

output "dq_job_name" {
  description = "Glue DQ job name"
  value       = aws_glue_job.data_quality.name
}
