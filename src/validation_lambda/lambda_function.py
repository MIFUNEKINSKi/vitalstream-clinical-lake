"""AWS Lambda handler: validates incoming FHIR Bundles and starts Step Functions.

Triggered by S3 ObjectCreated events on the landing zone bucket.
Dependencies: boto3 and stdlib only — no Lambda layer needed.
"""

from __future__ import annotations

import json
import os

import boto3

from src.validation_lambda.fhir_validator import validate_bundle

s3_client = boto3.client("s3")
sfn_client = boto3.client("stepfunctions")

STATE_MACHINE_ARN = os.environ.get("STATE_MACHINE_ARN", "")
ERRORS_PREFIX = os.environ.get("ERRORS_PREFIX", "errors/")


def lambda_handler(event, context):
    """Process S3 event: validate FHIR Bundle, start pipeline or write error."""
    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    key = event["Records"][0]["s3"]["object"]["key"]

    print(f"Processing s3://{bucket}/{key}")

    response = s3_client.get_object(Bucket=bucket, Key=key)
    body = response["Body"].read().decode("utf-8")

    try:
        bundle = json.loads(body)
    except json.JSONDecodeError as e:
        _write_error(bucket, key, [f"Invalid JSON: {str(e)}"])
        return {"statusCode": 400, "body": "Invalid JSON"}

    errors = validate_bundle(bundle)

    if errors:
        print(f"Validation failed for {key}: {errors}")
        _write_error(bucket, key, errors)
        return {
            "statusCode": 400,
            "body": json.dumps({"errors": errors}),
        }

    # Start Step Functions pipeline
    pipeline_input = {
        "source_bucket": bucket,
        "source_key": key,
    }

    execution = sfn_client.start_execution(
        stateMachineArn=STATE_MACHINE_ARN,
        input=json.dumps(pipeline_input),
    )

    print(f"Started pipeline execution: {execution['executionArn']}")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": f"Pipeline started for {key}",
            "executionArn": execution["executionArn"],
        }),
    }


def _write_error(bucket: str, key: str, errors: list[str]):
    """Write validation errors to the errors prefix in the landing zone."""
    error_key = f"{ERRORS_PREFIX}{key}.errors.json"
    s3_client.put_object(
        Bucket=bucket,
        Key=error_key,
        Body=json.dumps({"source_key": key, "errors": errors}, indent=2),
        ContentType="application/json",
    )
    print(f"Wrote error report to s3://{bucket}/{error_key}")
