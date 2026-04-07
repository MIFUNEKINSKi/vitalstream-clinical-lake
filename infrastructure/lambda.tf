# --- Validation Lambda ---

data "archive_file" "validation_lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src/validation_lambda"
  output_path = "${path.module}/validation_lambda.zip"
}

resource "aws_lambda_function" "validation_lambda" {
  filename         = data.archive_file.validation_lambda_zip.output_path
  function_name    = "${var.project_name}_validation"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  timeout          = 30
  memory_size      = 128
  source_code_hash = data.archive_file.validation_lambda_zip.output_base64sha256

  environment {
    variables = {
      LANDING_BUCKET    = aws_s3_bucket.landing_zone.bucket
      CURATED_BUCKET    = aws_s3_bucket.curated_zone.bucket
      STATE_MACHINE_ARN = aws_sfn_state_machine.pipeline.arn
      ERRORS_PREFIX     = "errors/"
    }
  }
}

# S3 trigger: invoke Lambda on .json file uploads to landing zone
resource "aws_s3_bucket_notification" "landing_zone_notification" {
  bucket = aws_s3_bucket.landing_zone.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.validation_lambda.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "raw/"
    filter_suffix       = ".json"
  }

  depends_on = [aws_lambda_permission.allow_s3]
}

resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.validation_lambda.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.landing_zone.arn
}
