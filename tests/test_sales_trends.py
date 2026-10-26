
"""
INSIGHTPILOT AI — SALES TREND TESTS
===================================

PURPOSE:
Check that monthly sales calculations are correct.

We use small datasets with known answers.
This helps us catch mistakes before adding the
feature to our Streamlit dashboard.
"""

from pathlib import Path
import sys

import pandas as pd
import pytest


# Find our project's src folder.
PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "src"))

from sales_trends import calculate_monthly_trends


# -----------------------------------------------
# Create example data for our tests
# -----------------------------------------------

def example_data():
    return pd.DataFrame({
        "InvoiceDate": [
            "2026-01-01",
            "2026-01-15",
            "2026-02-10",
            "2026-03-31",
        ],
        "BusinessCategory": [
            "Product",
            "Product",
            "Product",
            "Product",
        ],
        "TransactionType": [
            "Sale",
            "Sale",
            "Sale",
            "Sale",
        ],
        "ProductSalesAmount": [
            40.0,
            60.0,
            120.0,
            90.0,
        ],
    })


# TEST 1: Monthly totals are correct.
def test_monthly_totals():

    result = calculate_monthly_trends(example_data())

    assert len(result) == 3
    assert result["ProductSales"].tolist() == [
        100.0, 120.0, 90.0
    ]


# TEST 2: Monthly growth is correct.
def test_monthly_growth():

    result = calculate_monthly_trends(example_data())

    # January has no previous month.
    assert pd.isna(result.loc[0, "MoMGrowthPct"])

    # February: 100 to 120 = +20%.
    assert result.loc[1, "MoMGrowthPct"] == pytest.approx(20.0)

    # March: 120 to 90 = -25%.
    assert result.loc[2, "MoMGrowthPct"] == pytest.approx(-25.0)


# TEST 3: An incomplete final month is excluded.
def test_incomplete_month():

    df = example_data()

    # The dataset now ends on March 10.
    df.loc[3, "InvoiceDate"] = "2026-03-10"

    result = calculate_monthly_trends(df)

    assert not bool(result.loc[2, "IsCompleteMonth"])
    assert pd.isna(result.loc[2, "MoMGrowthPct"])


# TEST 4: Missing sales months are included.
def test_month_without_sales():

    df = pd.DataFrame({
        "InvoiceDate": ["2026-01-01", "2026-03-31"],
        "BusinessCategory": ["Product", "Product"],
        "TransactionType": ["Sale", "Sale"],
        "ProductSalesAmount": [100.0, 150.0],
    })

    result = calculate_monthly_trends(df)

    assert len(result) == 3
    assert result.loc[1, "ProductSales"] == 0.0

    # We cannot calculate percentage growth from zero.
    assert pd.isna(result.loc[2, "MoMGrowthPct"])


# TEST 5: Other charges must not count as sales.
def test_exclude_shipping():

    df = example_data()

    shipping = pd.DataFrame({
        "InvoiceDate": ["2026-02-15"],
        "BusinessCategory": ["Shipping"],
        "TransactionType": ["Sale"],
        "ProductSalesAmount": [500.0],
    })

    df = pd.concat([df, shipping], ignore_index=True)

    result = calculate_monthly_trends(df)

    assert result.loc[1, "ProductSales"] == 120.0


# TEST 6: Missing required fields must fail.
def test_missing_columns():

    df = pd.DataFrame({"InvoiceDate": ["2026-01-01"]})

    with pytest.raises(ValueError):
        calculate_monthly_trends(df)
