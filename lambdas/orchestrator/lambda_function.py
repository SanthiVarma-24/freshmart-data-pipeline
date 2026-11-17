
"""
FreshMart Analytics - Durable Pipeline Orchestrator
---------------------------------------------------

Purpose:
    Coordinate CSV validation and transformation using
    AWS Lambda Durable Functions.

Trigger:
    Amazon S3 ObjectCreated event.

Workflow:
    1. Receive the uploaded CSV file location.
    2. Invoke the CSV reader Lambda durably.
    3. Verify successful validation.
    4. Invoke the transformer Lambda durably.
    5. Return the processing summary.

Durability:
    The Durable Execution SDK checkpoints Lambda invocations
    and restores completed operation results during replay.

Environment Variables:
    CSV_READER_FUNCTION
    TRANSFORMER_FUNCTION
"""

import logging
import os
from urllib.parse import unquote_plus

from aws_durable_execution_sdk_python import (
    DurableContext,
    durable_execution,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@durable_execution
def lambda_handler(event: dict, context: DurableContext) -> dict:
    """
    Orchestrate FreshMart sales CSV processing.

    Args:
        event (dict): Amazon S3 ObjectCreated notification.
        context (DurableContext): Durable execution context.

    Returns:
        dict: Pipeline status, row counts, and output S3 path.

    Raises:
        Exception: If validation or transformation fails.
    """

    try:
        # Extract the uploaded file location.
        record = event["Records"][0]

        source_bucket = record["s3"]["bucket"]["name"]
        source_key = unquote_plus(
            record["s3"]["object"]["key"]
        )

        context.logger.info(
            "Starting FreshMart pipeline: s3://%s/%s",
            source_bucket,
            source_key,
        )

        # Ignore files other than CSV.
        if not source_key.lower().endswith(".csv"):
            return {
                "status": "skipped",
                "file_name": source_key,
            }

        payload = {
            "bucket": source_bucket,
            "key": source_key,
        }

        # Step 1: Durable CSV validation invocation.
        reader_result = context.invoke(
            os.environ["CSV_READER_FUNCTION"],
            payload,
            name="validate_csv",
        )

        if reader_result.get("status") != "success":
            raise RuntimeError(
                f"CSV validation failed: {reader_result}"
            )

        context.logger.info(
            "CSV validation passed: %s rows",
            reader_result["row_count"],
        )

        # Step 2: Durable data transformation invocation.
        transformer_result = context.invoke(
            os.environ["TRANSFORMER_FUNCTION"],
            payload,
            name="transform_sales",
        )

        if transformer_result.get("status") != "success":
            raise RuntimeError(
                f"Transformation failed: {transformer_result}"
            )

        # Step 3: Prepare the final processing summary.
        summary = {
            "status": "success",
            "source_file": f"s3://{source_bucket}/{source_key}",
            "rows_processed": transformer_result["rows_processed"],
            "rows_filtered": transformer_result["rows_filtered"],
            "rows_output": transformer_result["rows_output"],
            "output_file_path": transformer_result["output_file_path"],
        }

        context.logger.info(
            "FreshMart pipeline completed successfully"
        )

        return summary

    except Exception:
        context.logger.exception(
            "FreshMart durable pipeline failed"
        )
        raise
