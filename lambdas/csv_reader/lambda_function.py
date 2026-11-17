
"""
FreshMart Analytics - CSV Reader Lambda
---------------------------------------

Purpose:
    Read and validate daily sales CSV files uploaded to Amazon S3.

Trigger:
    Amazon S3 ObjectCreated event or direct Lambda invocation.

AWS Services:
    - Amazon S3
    - AWS Lambda
    - Amazon CloudWatch Logs

Dependencies:
    - boto3
    - pandas

Workflow:
    1. Receive an S3 event containing the bucket and object key.
    2. Check whether the uploaded file is a CSV.
    3. Download the CSV file from S3 using boto3.
    4. Load the CSV into a Pandas DataFrame.
    5. Validate the required columns and non-empty rows.
    6. Log file metadata to Amazon CloudWatch.
    7. Return the validation result.

Error Handling:
    Validation or S3 errors are logged and re-raised so the
    invoking service can detect the failure.

Project:
    FreshMart Automated Data Pipeline
"""

import json
import logging
from datetime import UTC, datetime
from io import BytesIO
from urllib.parse import unquote_plus

import boto3
import pandas as pd

# ---------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------

logger = logging.getLogger()
logger.setLevel(logging.INFO)


# ---------------------------------------------------------
# AWS Clients
# ---------------------------------------------------------

s3 = boto3.client("s3")


# ---------------------------------------------------------
# Required CSV Schema
# ---------------------------------------------------------

EXPECTED_COLUMNS = {
    "invoice_id",
    "branch",
    "city",
    "product_line",
    "unit_price",
    "quantity",
    "date",
    "payment",
    "rating",
}


# ---------------------------------------------------------
# CSV Validation Function
# ---------------------------------------------------------

def validate_csv(bucket, key):
    """
    Read and validate a sales CSV file stored in Amazon S3.

    Args:
        bucket (str):
            Name of the source S3 bucket.

        key (str):
            S3 object key identifying the uploaded CSV file.

    Returns:
        dict:
            Metadata containing:
                - file_name
                - row_count
                - column_count
                - processing_timestamp

    Raises:
        ValueError:
            If the CSV is empty or required columns are missing.

        botocore.exceptions.ClientError:
            If the S3 object cannot be accessed.
    """

    logger.info("Reading file: s3://%s/%s", bucket, key)

    # Download the CSV file from Amazon S3.
    response = s3.get_object(Bucket=bucket, Key=key)
    file_content = response["Body"].read()

    # Convert the CSV content into a Pandas DataFrame.
    df = pd.read_csv(BytesIO(file_content))

    # Validate that the dataset contains data rows.
    if df.empty:
        raise ValueError("CSV file contains no data rows")

    # Identify missing columns in the uploaded dataset.
    missing_columns = EXPECTED_COLUMNS - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    # Capture file metadata for auditing and monitoring.
    metadata = {
        "file_name": key,
        "row_count": len(df),
        "column_count": len(df.columns),
        "processing_timestamp": datetime.now(
            UTC
        ).isoformat(),
    }

    logger.info(
        "CSV validation successful: %s",
        json.dumps(metadata),
    )

    return metadata


# ---------------------------------------------------------
# AWS Lambda Entry Point
# ---------------------------------------------------------

def lambda_handler(event, context):
    """
    AWS Lambda entry point for processing an S3 CSV upload.

    Args:
        event (dict):
            S3 event notification containing bucket and object key,
            or a direct invocation payload with bucket and key.

        context:
            AWS Lambda runtime context object.

    Returns:
        dict:
            On success, returns validation metadata and S3 location.
            For non-CSV files, returns a skipped status.

    Raises:
        Exception:
            Re-raises processing errors after logging them.
    """

    try:
        # Extract the S3 bucket and object key.
        if "Records" in event:
            record = event["Records"][0]

            bucket = record["s3"]["bucket"]["name"]

            # Decode URL-encoded S3 object keys.
            key = unquote_plus(
                record["s3"]["object"]["key"]
            )

        else:
            # Support direct invocation by the orchestrator.
            bucket = event["bucket"]
            key = event["key"]

        # Ignore files that do not have a CSV extension.
        if not key.lower().endswith(".csv"):
            logger.info("Skipping non-CSV file: %s", key)

            return {
                "status": "skipped",
                "file_name": key,
            }

        # Read and validate the uploaded CSV file.
        metadata = validate_csv(bucket, key)

        # Return the validation result to the caller.
        return {
            "status": "success",
            "bucket": bucket,
            "key": key,
            **metadata,
        }

    except Exception:
        # Log the complete traceback for CloudWatch debugging.
        logger.exception("CSV reader failed")
        raise
