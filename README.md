# VitalStream: Serverless Clinical Data Lake

## Overview
Traditional clinical trials suffer from data silos and slow validation cycles. VitalStream is an event-driven data architecture that ingests CDISC ODM-XML data in real-time, validates it against study schemas, and makes it available for instant SQL analysis via Amazon Athena.

## Architecture

1.  **Ingestion**: S3 + Python Data Generator (Simulating EDC systems)
2.  **Processing**: AWS Lambda (Serverless ETL)
3.  **Storage**: S3 (Raw XML & Curated Parquet)
4.  **Catalog & Query**: AWS Glue + Amazon Athena

## Key Features

*   **Automated Validation**: Rejects non-compliant XML files automatically.
*   **Schema Evolution**: Glue Crawlers detect changes in form data (e.g., new Vital Signs added).
*   **Cost Efficiency**: 100% Serverless (Pay only for compute used).

## How to Run

1.  Deploy Infrastructure:
    ```bash
    cd infrastructure && terraform apply
    ```

2.  Generate Data:
    ```bash
    python src/data_generator/generate_clinical_data.py
    ```

3.  Analyze Data:
    Open AWS Athena and run:
    ```sql
    SELECT * FROM clinical_trials.vital_signs;
    ```
