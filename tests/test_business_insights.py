
"""
INSIGHTPILOT AI — BUSINESS INSIGHTS TESTS
=========================================

PURPOSE:
Check that our automated findings are correct.

THEORY:
A test gives a program data with known results,
then checks whether it produces the right answer.
"""

import pandas as pd

from src.business_insights import generate_business_insights


# Create a simple dataset for testing.
def sample_data():

    return pd.DataFrame({
        "InvoiceDate": [
            "2026-01-01",
            "2026-01-31",
            "2026-02-15",
            "2026-03-31",
        ],
        "BusinessCategory": ["Product"] * 4,
        "TransactionType": ["Sale"] * 4,
        "ProductSalesAmount": [
            40.0, 60.0, 120.0, 90.0
        ],
    })


# TEST 1: Findings should be generated.
def test_insights_exist():

    insights = generate_business_insights(sample_data())

    assert len(insights) > 0


# TEST 2: Find the highest-sales month.
def test_highest_sales_month():

    insights = generate_business_insights(sample_data())

    best = next(
        item for item in insights
        if item["title"] == "Highest product sales"
    )

    assert "February 2026" in best["message"]
    assert "£120.00" in best["message"]


# TEST 3: Detect monthly growth.
def test_positive_growth():

    insights = generate_business_insights(sample_data())

    growth = next(
        item for item in insights
        if item["title"] == "Strongest monthly growth"
    )

    assert "+20.00%" in growth["message"]


# TEST 4: Detect monthly decline.
def test_negative_growth():

    insights = generate_business_insights(sample_data())

    decline = next(
        item for item in insights
        if item["title"] == "Largest monthly decline"
    )

    assert "-25.00%" in decline["message"]


# TEST 5: Detect incomplete months.
def test_incomplete_month():

    df = sample_data()
    df.loc[3, "InvoiceDate"] = "2026-03-10"

    insights = generate_business_insights(df)

    warnings = [
        item for item in insights
        if item["title"] == "Incomplete reporting period"
    ]

    assert len(warnings) == 1
    assert "March 2026" in warnings[0]["message"]


# TEST 6: Handle an empty dataset.
def test_empty_dataset():

    df = pd.DataFrame(columns=[
        "InvoiceDate",
        "BusinessCategory",
        "TransactionType",
        "ProductSalesAmount",
    ])

    insights = generate_business_insights(df)

    assert insights[0]["title"] == "No data available"
