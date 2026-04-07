"""CLI tool to generate synthetic FHIR R4 Bundles for the VitalStream pipeline.

Usage:
    python -m src.data_generator.generate_fhir_bundles --count 10 --output-dir /tmp/fhir
    python -m src.data_generator.generate_fhir_bundles --count 5 --upload-s3 --bucket-name my-bucket
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid

import boto3

from src.data_generator.fhir_templates import generate_clinical_bundle


def write_bundles_to_disk(bundles: list[dict], output_dir: str) -> list[str]:
    """Write FHIR bundles as JSON files to a local directory."""
    os.makedirs(output_dir, exist_ok=True)
    paths = []
    for bundle in bundles:
        filename = f"bundle_{uuid.uuid4()}.json"
        path = os.path.join(output_dir, filename)
        with open(path, "w") as f:
            json.dump(bundle, f, indent=2)
        paths.append(path)
        print(f"Generated {path}")
    return paths


def upload_bundles_to_s3(
    bundles: list[dict], bucket_name: str, prefix: str = "raw/"
) -> list[str]:
    """Upload FHIR bundles as JSON to an S3 bucket."""
    s3 = boto3.client("s3")
    keys = []
    for bundle in bundles:
        key = f"{prefix}bundle_{uuid.uuid4()}.json"
        s3.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=json.dumps(bundle, indent=2),
            ContentType="application/json",
        )
        keys.append(key)
        print(f"Uploaded s3://{bucket_name}/{key}")
    return keys


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic FHIR R4 Bundles for VitalStream"
    )
    parser.add_argument(
        "--count", type=int, default=10, help="Number of bundles to generate"
    )
    parser.add_argument(
        "--output-dir", type=str, default=None, help="Local directory for output files"
    )
    parser.add_argument(
        "--upload-s3", action="store_true", help="Upload to S3 instead of local disk"
    )
    parser.add_argument(
        "--bucket-name",
        type=str,
        default=os.environ.get("VITALSTREAM_LANDING_BUCKET"),
        help="S3 bucket name (defaults to VITALSTREAM_LANDING_BUCKET env var)",
    )

    args = parser.parse_args()

    bundles = [generate_clinical_bundle() for _ in range(args.count)]
    print(f"Generated {len(bundles)} FHIR R4 Bundles")

    if args.upload_s3:
        if not args.bucket_name:
            print(
                "Error: --bucket-name or VITALSTREAM_LANDING_BUCKET env var required",
                file=sys.stderr,
            )
            sys.exit(1)
        upload_bundles_to_s3(bundles, args.bucket_name)
    else:
        output_dir = args.output_dir or "output/fhir_bundles"
        write_bundles_to_disk(bundles, output_dir)


if __name__ == "__main__":
    main()
