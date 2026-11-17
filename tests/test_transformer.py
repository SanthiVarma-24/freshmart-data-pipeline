
"""
FreshMart Analytics - Transformer Unit Tests
--------------------------------------------

Purpose:
    Verify data cleaning, calculations, rating classification,
    and date formatting performed by the transformer Lambda.

Testing Framework:
    pytest

AWS Access:
    Not required. The S3 client is mocked during module import.
"""

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import boto3
import pandas as pd
import pytest

TRANSFORMER_PATH = (
    Path(__file__).resolve().parents[1]
    / "lambdas"
    / "transformer"
    / "lambda_function.py"
)


@pytest.fixture
def transformer(monkeypatch):
    """Load the transformer module with a mocked S3 client."""

    mock_s3 = MagicMock()

    monkeypatch.setattr(
        boto3,
        "client",
        lambda service: mock_s3,
    )

    spec = importlib.util.spec_from_file_location(
        "transformer_lambda",
        TRANSFORMER_PATH,
    )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


@pytest.fixture
def sample_sales():
    """Create representative sales records for testing."""

    return pd.DataFrame(
        {
            "invoice_id": [
                "INV001",
                "INV002",
                "INV003",
                "INV004",
                "INV005",
            ],
            "branch": ["A", "B", "C", "A", "B"],
            "city": [
                "Kanpur",
                "Lucknow",
                "Agra",
                "Kanpur",
                "Lucknow",
            ],
            "product_line": [
                "Grocery",
                "Fashion",
                "Health",
                "Electronics",
                "Grocery",
            ],
            "unit_price": [100, 50, 20, 0, 40],
            "quantity": [2, 3, 1, 4, 0],
            "date": ["2025-11-01"] * 5,
            "payment": ["UPI"] * 5,
            "rating": [4.5, 6.0, 8.5, 7.0, 5.0],
        }
    )


def test_filter_invalid_rows(transformer, sample_sales):
    """Rows with zero quantity or price must be removed."""

    result = transformer.transform_sales(sample_sales)

    assert len(result) == 3
    assert "INV004" not in result["invoice_id"].values
    assert "INV005" not in result["invoice_id"].values


def test_total_amount(transformer, sample_sales):
    """Verify unit_price multiplied by quantity."""

    result = transformer.transform_sales(sample_sales)

    assert result["total_amount"].tolist() == [
        200.0,
        150.0,
        20.0,
    ]


def test_rating_categories(transformer, sample_sales):
    """Verify Low, Medium, and High rating thresholds."""

    result = transformer.transform_sales(sample_sales)

    assert result["rating_category"].tolist() == [
        "Low",
        "Medium",
        "High",
    ]


def test_date_format(transformer, sample_sales):
    """Verify dates are formatted as YYYY-MM-DD."""

    result = transformer.transform_sales(sample_sales)

    assert result["date"].tolist() == [
        "2025-11-01",
        "2025-11-01",
        "2025-11-01",
    ]


def test_missing_columns(transformer, sample_sales):
    """Verify missing required columns raise ValueError."""

    invalid_df = sample_sales.drop(columns=["rating"])

    with pytest.raises(ValueError, match="Missing required columns"):
        transformer.transform_sales(invalid_df)


@pytest.mark.parametrize(
    ("rating", "expected_category"),
    [
        (4.9, "Low"),
        (5.0, "Medium"),
        (7.0, "Medium"),
        (7.1, "High"),
    ],
)
def test_rating_category_boundaries(
    transformer, sample_sales, rating, expected_category
):
    """Verify rating classification at category boundaries."""

    test_data = sample_sales.iloc[[0]].copy()
    test_data["rating"] = rating

    result = transformer.transform_sales(test_data)

    assert result["rating_category"].iloc[0] == expected_category

