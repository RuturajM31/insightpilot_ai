
"""
INSIGHTPILOT AI — ANALYST AGENT TESTS
=====================================

PURPOSE
-------
Verify that the Analyst Agent selects the
correct analytical operation and preserves
the results from trusted Python calculations.
"""

import pandas as pd

from src.agents.analyst_agent import run_analyst_agent


def sample_data():
    """Small dataset with known answers."""

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
            40.0,
            60.0,
            120.0,
            90.0,
        ],
    })


def test_highest_month_tool():
    result = run_analyst_agent(
        sample_data(),
        "What was our best sales month?",
    )

    assert result["agent"] == "analyst"
    assert result["status"] == "verified"
    assert result["category"] == "highest_month"
    assert result["selected_tool"] == (
        "Highest monthly product sales"
    )
    assert "February 2026" in result["answer"]
    assert "£120.00" in result["answer"]


def test_growth_tool():
    result = run_analyst_agent(
        sample_data(),
        "Which month had the strongest growth?",
    )

    assert result["status"] == "verified"
    assert result["category"] == "growth"
    assert "+20.00%" in result["answer"]


def test_decline_tool():
    result = run_analyst_agent(
        sample_data(),
        "What was the largest decline?",
    )

    assert result["status"] == "verified"
    assert result["category"] == "decline"
    assert "-25.00%" in result["answer"]


def test_total_sales_tool():
    result = run_analyst_agent(
        sample_data(),
        "What were our total sales?",
    )

    assert result["status"] == "verified"
    assert result["category"] == "total_sales"
    assert "£310.00" in result["answer"]


def test_unsupported_question():
    result = run_analyst_agent(
        sample_data(),
        "Who won the football match?",
    )

    assert result["status"] == "not_analyzed"
    assert result["selected_tool"] is None
    assert result["category"] == "unsupported"


def test_no_invented_causes():
    result = run_analyst_agent(
        sample_data(),
        "Why did sales decline?",
    )

    assert result["category"] == "explanation_limit"
    assert "cannot establish the cause" in result["answer"]


def test_evidence_is_preserved():
    result = run_analyst_agent(
        sample_data(),
        "What was our best sales month?",
    )

    assert isinstance(result["evidence"], list)
    assert "Month: February 2026" in result["evidence"]
    assert "Gross product sales: £120.00" in result["evidence"]
