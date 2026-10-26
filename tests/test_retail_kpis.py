
"""
INSIGHTPILOT AI — KPI TESTS

We use small example datasets where we already
know the correct answers.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

# Find our project and its src folder.
PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "src"))

from retail_kpis import calculate_retail_kpis


def test_correct_kpis():

    # Invoice A has two products.
    # Invoice B has one product.
    # Invoice C is a cancellation.
    # Invoice D is a shipping charge.
    data = pd.DataFrame({
        "InvoiceNo": ["A", "A", "B", "C", "D"],
        "BusinessCategory": [
            "Product", "Product", "Product",
            "Product", "Shipping"
        ],
        "TransactionType": [
            "Sale", "Sale", "Sale",
            "Cancellation", "Sale"
        ],
        "ProductSalesAmount": [
            10.0, 20.0, 30.0, 0.0, 0.0
        ]
    })

    result = calculate_retail_kpis(data)

    assert result["gross_product_sales"] == 60.0
    assert result["sales_orders"] == 2
    assert result["average_order_value"] == 30.0


def test_no_sales():

    data = pd.DataFrame(columns=[
        "InvoiceNo",
        "BusinessCategory",
        "TransactionType",
        "ProductSalesAmount"
    ])

    result = calculate_retail_kpis(data)

    assert result["sales_orders"] == 0
    assert result["average_order_value"] == 0.0


def test_missing_column():

    data = pd.DataFrame({
        "InvoiceNo": ["A"]
    })

    with pytest.raises(ValueError):
        calculate_retail_kpis(data)


def test_negative_amount():

    data = pd.DataFrame({
        "InvoiceNo": ["A"],
        "BusinessCategory": ["Product"],
        "TransactionType": ["Sale"],
        "ProductSalesAmount": [-5.0]
    })

    with pytest.raises(ValueError):
        calculate_retail_kpis(data)
