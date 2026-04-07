# --- Step Functions State Machine ---

resource "aws_sfn_state_machine" "pipeline" {
  name     = "${var.project_name}_pipeline"
  role_arn = aws_iam_role.sfn_role.arn

  definition = templatefile("${path.module}/state_machine/pipeline.asl.json", {
    etl_job_name   = aws_glue_job.fhir_to_omop_etl.name
    dq_job_name    = aws_glue_job.data_quality.name
    crawler_name   = aws_glue_crawler.vitalstream_crawler.name
    target_path    = "s3://${aws_s3_bucket.curated_zone.bucket}/omop"
    dq_output_path = "s3://${aws_s3_bucket.curated_zone.bucket}/dq_reports"
  })
}
