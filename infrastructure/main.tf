provider "aws" {
  region = var.aws_region
}

# --- S3 Buckets ---
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "landing_zone" {
  bucket = "${var.project_name}-landing-zone-${random_id.bucket_suffix.hex}"
}

resource "aws_s3_bucket" "curated_zone" {
  bucket = "${var.project_name}-curated-zone-${random_id.bucket_suffix.hex}"
}

# --- IAM Role for Lambda ---
resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}_lambda_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_policy" "lambda_policy" {
  name        = "${var.project_name}_lambda_policy"
  description = "IAM policy for Lambda to access S3 and Logs"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Effect   = "Allow"
        Resource = [
            aws_s3_bucket.landing_zone.arn,
            "${aws_s3_bucket.landing_zone.arn}/*",
            aws_s3_bucket.curated_zone.arn,
            "${aws_s3_bucket.curated_zone.arn}/*"
        ]
      },
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_attach" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

# --- Lambda Function ---
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "../src/ingestion_lambda"
  output_path = "${path.module}/lambda_function.zip"
  excludes    = ["requirements.txt"] 
}

# Note: For production, use an AWS Layer for Pandas/PyArrow (e.g., AWS SDK Pandas Layer)
# Changing this to standard python3.10 and assuming a layer exists or the user packs it.
# As a placeholder for the "Resume-Worthy" style, we'll configure it but comment on the layer.

resource "aws_lambda_function" "ingestion_lambda" {
  filename      = data.archive_file.lambda_zip.output_path
  function_name = "${var.project_name}_ingestion"
  role          = aws_iam_role.lambda_role.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.10"
  timeout       = 60
  memory_size   = 512 # Increased memory for pandas processing
  layers        = ["arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python310:24"]

  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      LANDING_BUCKET = aws_s3_bucket.landing_zone.bucket
      CURATED_BUCKET = aws_s3_bucket.curated_zone.bucket
    }
  }
}

# --- S3 Trigger ---
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.landing_zone.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.ingestion_lambda.arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".xml"
  }

  depends_on = [aws_lambda_permission.allow_s3]
}

resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingestion_lambda.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.landing_zone.arn
}

# --- Glue Data Catalog & Crawler ---
resource "aws_glue_catalog_database" "vitalstream_db" {
  name = "${var.project_name}_db"
}

resource "aws_glue_crawler" "vitalstream_crawler" {
  database_name = aws_glue_catalog_database.vitalstream_db.name
  name          = "${var.project_name}_crawler"
  role          = aws_iam_role.glue_role.arn

  s3_target {
    path = "s3://${aws_s3_bucket.curated_zone.bucket}/"
  }
}

# --- IAM Role for Glue ---
resource "aws_iam_role" "glue_role" {
  name = "${var.project_name}_glue_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "glue.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_policy" "glue_policy" {
    name = "${var.project_name}_glue_policy"
    
    policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
            {
                Effect = "Allow"
                Action = [
                    "s3:GetObject",
                    "s3:PutObject"
                ]
                Resource = [
                    "${aws_s3_bucket.curated_zone.arn}/*"
                ]
            }
        ]
    })
}

resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy_attachment" "glue_s3" {
  role       = aws_iam_role.glue_role.name
  policy_arn = aws_iam_policy.glue_policy.arn
}
