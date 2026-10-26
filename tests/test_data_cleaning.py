
"""
INSIGHTPILOT AI — DATA CLEANING TESTS
=====================================

PURPOSE:
Check that our retail cleaning rules work correctly.

THEORY:
A unit test checks one small part of a program.

We use small example datasets where we already
know what the correct answers should be.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest


# Allow Python to find our src folder.
PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "src"))

from data_cleaning import classify_transactions


# TEST 1: Normal product sale
def test_normal_sale():

    data = pd.DataFrame({
        "InvoiceNo": ["1001"],
        "StockCode": ["ABC123"],
        "Quantity": [3],
        "UnitPrice": [5.0]
    })

    result = classify_transactions(data)

    assert result.iloc[0]["TransactionType"] == "Sale"
    assert result.iloc[0]["BusinessCategory"] == "Product"
    assert result.iloc[0]["ProductSalesAmount"] == 15.0


# TEST 2: Cancelled product
def test_cancellation():

    data = pd.DataFrame({
        "InvoiceNo": ["C1002"],
        "StockCode": ["ABC123"],
        "Quantity": [-2],
        "UnitPrice": [5.0]
    })

    result = classify_transactions(data)

    assert result.iloc[0]["TransactionType"] == "Cancellation"
    assert result.iloc[0]["ProductSalesAmount"] == 0.0


# TEST 3: Shipping fee is not product revenue
def test_shipping():

    data = pd.DataFrame({
        "InvoiceNo": ["1003"],
        "StockCode": ["POST"],
        "Quantity": [1],
        "UnitPrice": [10.0]
    })

    result = classify_transactions(data)

    assert result.iloc[0]["BusinessCategory"] == "Shipping"
    assert result.iloc[0]["ProductSalesAmount"] == 0.0


# TEST 4: Zero-price record
def test_zero_price():

    data = pd.DataFrame({
        "InvoiceNo": ["1004"],
        "StockCode": ["ABC123"],
        "Quantity": [2],
        "UnitPrice": [0.0]
    })

    result = classify_transactions(data)

    assert result.iloc[0]["TransactionType"] == "Zero Price"
    assert result.iloc[0]["ProductSalesAmount"] == 0.0


# TEST 5: Missing required column
def test_missing_column():

    data = pd.DataFrame({
        "InvoiceNo": ["1005"],
        "Quantity": [2],
        "UnitPrice": [5.0]
    })

    with pytest.raises(ValueError):
        classify_transactions(data)


# TEST 6: Original data must remain unchanged
def test_original_data_unchanged():

    data = pd.DataFrame({
        "InvoiceNo": ["1006"],
        "StockCode": ["ABC123"],
        "Quantity": [2],
        "UnitPrice": [5.0]
    })

    original = data.copy(deep=True)

    classify_transactions(data)

    pd.testing.assert_frame_equal(data, original)


# TEST 7: Bad debt must not count as sales
def test_bad_debt():

    data = pd.DataFrame({
        "InvoiceNo": ["A1007"],
        "StockCode": ["B"],
        "Quantity": [1],
        "UnitPrice": [-100.0]
    })

    result = classify_transactions(data)

    assert result.iloc[0]["TransactionType"] == "Accounting Adjustment"
    assert result.iloc[0]["BusinessCategory"] == "Other Charge"
    assert result.iloc[0]["ProductSalesAmount"] == 0.0


# TEST 8: Manual transactions must remain separate
def test_manual_transaction():

    data = pd.DataFrame({
        "InvoiceNo": ["1008"],
        "StockCode": ["M"],
        "Quantity": [1],
        "UnitPrice": [20.0]
    })

    result = classify_transactions(data)

    assert result.iloc[0]["BusinessCategory"] == "Manual"
    assert result.iloc[0]["ProductSalesAmount"] == 0.0
