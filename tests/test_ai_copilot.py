
"""
INSIGHTPILOT AI — COPILOT TESTS
===============================

PURPOSE
-------
Check that the Copilot answers using correct data.

We test both:
- Answers it SHOULD provide.
- Questions it SHOULD NOT guess about.
"""

import pandas as pd

from src.ai_copilot import answer_business_question


def sample_data():
    """Create three months with known sales."""

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


def test_highest_sales_answer():
    result = answer_business_question(
        sample_data(),
        "What was our best sales month?"
    )

    assert result["category"] == "highest_month"
    assert "February 2026" in result["answer"]
    assert "£120.00" in result["answer"]


def test_growth_answer():
    result = answer_business_question(
        sample_data(),
        "Which month had the strongest growth?"
    )

    assert result["category"] == "growth"
    assert "+20.00%" in result["answer"]


def test_decline_answer():
    result = answer_business_question(
        sample_data(),
        "What was the largest decline?"
    )

    assert result["category"] == "decline"
    assert "March 2026" in result["answer"]
    assert "-25.00%" in result["answer"]


def test_total_sales_answer():
    result = answer_business_question(
        sample_data(),
        "What were our total sales?"
    )

    assert result["category"] == "total_sales"
    assert "£310.00" in result["answer"]
    assert "not audited net revenue" in result["answer"]


def test_unknown_question():
    result = answer_business_question(
        sample_data(),
        "What is the capital of France?"
    )

    assert result["category"] == "unsupported"
    assert "cannot answer" in result["answer"]


def test_no_invented_cause():
    result = answer_business_question(
        sample_data(),
        "Why did sales decline?"
    )

    assert result["category"] == "explanation_limit"
    assert "cannot establish the cause" in result["answer"]
    assert "hypotheses" in result["answer"]


def test_empty_question():
    result = answer_business_question(
        sample_data(),
        ""
    )

    assert result["category"] == "help"


def test_incomplete_period():
    df = sample_data()

    # Make the last month incomplete.
    df.loc[3, "InvoiceDate"] = "2026-03-10"

    result = answer_business_question(
        df,
        "Are any months incomplete?"
    )

    assert result["category"] == "data_coverage"
    assert "March 2026" in result["answer"]


def test_no_data():
    empty = sample_data().iloc[0:0]

    result = answer_business_question(
        empty,
        "What was our best sales month?"
    )

    assert result["category"] == "no_data"


def test_engine_is_not_mislabeled_as_llm():
    result = answer_business_question(
        sample_data(),
        "What was our best month?"
    )

    assert result["engine"] == "verified_rules"
