
"""
FreshMart Analytics - Data Transformer Worker Lambda
----------------------------------------------------

Purpose:
    Transform daily supermarket sales CSV files and store
    cleaned output in Amazon S3.

Invoked By:
    pipeline_orchestrator Lambda

AWS Services:
    - AWS Lambda
    - Amazon S3
    - Amazon CloudWatch Logs

Transformations:
    1. Read CSV data from the source S3 bucket.
    2. Remove records with zero quantity or unit price.
    3. Calculate total_amount = unit_price * quantity.
    4. Categorize customer ratings:
       Low: rating < 5
       Medium: 5 <= rating <= 7
       High: rating > 7
    5. Convert date to YYYY-MM-DD format.
    6. Write cleaned CSV to the destination S3 bucket.

Returns:
    Processing summary including row counts and output path.
"""

import json
import logging
import os
from io import BytesIO
from pathlib import PurePosixPath

import boto3
import pandas as pd

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")

REQUIRED_COLUMNS = {
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


def transform_sales(df):
    """
    Clean and transform FreshMart sales data.

    Args:
        df (pandas.DataFrame): Raw sales records.

    Returns:
        pandas.DataFrame: Cleaned records with derived columns.

    Raises:
        ValueError: If required columns are missing or invalid.
    """

    missing = REQUIRED_COLUMNS - set(df.columns)

    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    df = df.copy()

    # Convert numeric fields and reject malformed values.
    for column in ("unit_price", "quantity", "rating"):
        df[column] = pd.to_numeric(df[column], errors="raise")

    # Remove records with zero quantity or unit price.
    df = df[
        (df["quantity"] != 0)
        & (df["unit_price"] != 0)
    ].copy()

    # Calculate revenue for each sale.
    df["total_amount"] = (
        df["unit_price"] * df["quantity"]
    ).round(2)

    # Categorize ratings using the assignment thresholds.
    def categorize_rating(rating):
        if pd.isna(rating):
            return "Unknown"
        if rating < 5:
            return "Low"
        if rating <= 7:
            return "Medium"
        return "High"

    df["rating_category"] = df["rating"].apply(
        categorize_rating
    )

    # Parse dates and standardize their output format.
    df["date"] = pd.to_datetime(
        df["date"],
        format="%Y-%m-%d",
        errors="raise",
    ).dt.strftime("%Y-%m-%d")

    return df


def lambda_handler(event, context):
    """
    Process an S3 CSV file and upload its cleaned output.

    Expected event:
        {
            "bucket": "freshmart-raw-data",
            "key": "daily/sales.csv"
        }

    Returns:
        dict: Processing status, row counts, and output S3 path.
    """

    try:
        source_bucket = event["bucket"]
        source_key = event["key"]

        destination_bucket = os.environ[
            "DESTINATION_BUCKET"
        ]

        logger.info(
            "Starting transformation: s3://%s/%s",
            source_bucket,
            source_key,
        )

        # Download and load the source CSV.
        response = s3.get_object(
            Bucket=source_bucket,
            Key=source_key,
        )

        raw_content = response["Body"].read()
        df = pd.read_csv(BytesIO(raw_content))

        if df.empty:
            raise ValueError("Source CSV contains no data rows")

        input_rows = len(df)

        # Apply the transformation rules.
        cleaned_df = transform_sales(df)

        output_rows = len(cleaned_df)
        filtered_rows = input_rows - output_rows

        # Preserve the original filename under processed/.
        filename = PurePosixPath(source_key).name
        output_key = f"processed/{filename}"

        # Convert the cleaned DataFrame back to CSV.
        csv_output = cleaned_df.to_csv(index=False)

        # Upload processed data to the destination bucket.
        s3.put_object(
            Bucket=destination_bucket,
            Key=output_key,
            Body=csv_output.encode("utf-8"),
            ContentType="text/csv",
        )

        output_path = (
            f"s3://{destination_bucket}/{output_key}"
        )

        summary = {
            "status": "success",
            "rows_processed": input_rows,
            "rows_filtered": filtered_rows,
            "rows_output": output_rows,
            "output_file_path": output_path,
        }

        logger.info(
            "Transformation completed: %s",
            json.dumps(summary),
        )

        return summary

    except Exception:
        logger.exception("Data transformation failed")
        raise
