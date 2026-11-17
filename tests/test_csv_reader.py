"""
Unit tests for the FreshMart CSV Reader Lambda.

Tests:
    - Successful CSV validation
    - Missing required columns
    - Empty CSV files
    - Non-CSV file handling

AWS S3 calls are mocked to avoid real AWS access.
"""

import importlib.util
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Import the Lambda module from its file path.
LAMBDA_PATH = (
    Path(__file__).resolve().parents[1]
    / "lambdas"
    / "csv_reader"
    / "lambda_function.py"
)


@pytest.fixture
def csv_reader(monkeypatch):
    """Load the CSV reader with a mocked S3 client."""

    mock_s3 = MagicMock()

    # Prevent boto3 from contacting AWS during module import.
    import boto3

    monkeypatch.setattr(
        boto3,
        "client",
        lambda service: mock_s3,
    )

    spec = importlib.util.spec_from_file_location(
        "csv_reader_lambda",
        LAMBDA_PATH,
    )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module, mock_s3


def test_valid_csv(csv_reader):
    """Verify a valid CSV returns correct metadata."""

    module, mock_s3 = csv_reader

    csv_content = (
        "invoice_id,branch,city,product_line,unit_price,"
        "quantity,date,payment,rating\n"
        "INV00001,A,Kanpur,Grocery,50.0,2,"
        "2025-11-01,Cash,8.5\n"
    )

    mock_s3.get_object.return_value = {
        "Body": BytesIO(csv_content.encode())
    }

    result = module.lambda_handler(
        {"bucket": "test-bucket", "key": "sales.csv"},
        None,
    )

    assert result["status"] == "success"
    assert result["row_count"] == 1
    assert result["column_count"] == 9


def test_missing_columns(csv_reader):
    """Verify missing required columns raise an error."""

    module, mock_s3 = csv_reader

    mock_s3.get_object.return_value = {
        "Body": BytesIO(b"invoice_id,quantity\nINV001,2\n")
    }

    with pytest.raises(ValueError, match="Missing required columns"):
        module.validate_csv("test-bucket", "invalid.csv")


def test_empty_csv(csv_reader):
    """Verify a header-only CSV is rejected."""

    module, mock_s3 = csv_reader

    csv_content = (
        "invoice_id,branch,city,product_line,unit_price,"
        "quantity,date,payment,rating\n"
    )

    mock_s3.get_object.return_value = {
        "Body": BytesIO(csv_content.encode())
    }

    with pytest.raises(ValueError, match="no data rows"):
        module.validate_csv("test-bucket", "empty.csv")


def test_non_csv_file(csv_reader):
    """Verify non-CSV files are skipped."""

    module, mock_s3 = csv_reader

    result = module.lambda_handler(
        {"bucket": "test-bucket", "key": "notes.txt"},
        None,
    )

    assert result["status"] == "skipped"
    mock_s3.get_object.assert_not_called()
