
"""
INSIGHTPILOT AI — QA AGENT REGRESSION TESTS
===========================================

PURPOSE
-------
Verify that the QA Agent accepts useful explanations,
rejects unsupported statements, and never changes
the original verified evidence.

The additional tests reproduce errors we observed
in actual Llama 3.2 responses.
"""

import copy

import pandas as pd

from src.agents.analyst_agent import run_analyst_agent
from src.agents.qa_agent import review_agent_output


def sample_data():
    """Small dataset with known figures."""

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
            40.0, 60.0, 120.0, 90.0,
        ],
    })


def sample_results():
    """Build matching Analyst and Insights results."""

    analyst = run_analyst_agent(
        sample_data(),
        "What was our best sales month?",
    )

    insights = {
        "agent": "insights",
        "verified_answer": analyst["answer"],
        "evidence": list(analyst["evidence"]),
        "status": "generated",
        "llm_status": "accepted",
        "ai_explanation": (
            "Identifying the strongest sales period gives "
            "the business a useful benchmark for comparison. "
            "The next step could be to examine product mix "
            "and order volumes across comparable periods."
        ),
    }

    return analyst, insights


def test_approve_valid_interpretation():
    analyst, insights = sample_results()

    qa = review_agent_output(analyst, insights)

    assert qa["status"] == "approved"
    assert qa["approved"] is True
    assert qa["ai_explanation"] is not None


def test_reject_unsupported_demand_claim():
    analyst, insights = sample_results()

    insights["ai_explanation"] = (
        "A drop in customer demand explains the "
        "lower sales observed in the reporting period. "
        "The business should examine its product "
        "portfolio to decide what to change next."
    )

    qa = review_agent_output(analyst, insights)

    assert qa["status"] == "rejected"
    assert qa["approved"] is False
    assert qa["ai_explanation"] is None


def test_reject_evidence_mismatch():
    analyst, insights = sample_results()

    insights["verified_answer"] = (
        "Incorrect analytical finding."
    )

    qa = review_agent_output(analyst, insights)

    assert qa["status"] == "rejected"
    assert qa["ai_explanation"] is None
    assert "Evidence mismatch" in qa["findings"][0]


def test_reject_fabricated_number():
    analyst, insights = sample_results()

    insights["ai_explanation"] = (
        "This reporting period showed an additional "
        "increase of 99 percent. The business can "
        "use this number when planning future "
        "sales activities and commercial strategy."
    )

    qa = review_agent_output(analyst, insights)

    assert qa["status"] == "rejected"
    assert qa["approved"] is False


def test_unavailable_llm_fallback():
    analyst, insights = sample_results()

    insights["status"] = "fallback"
    insights["llm_status"] = "unavailable"
    insights["ai_explanation"] = None

    qa = review_agent_output(analyst, insights)

    assert qa["status"] == "fallback"
    assert qa["ai_explanation"] is None
    assert qa["verified_answer"] == analyst["answer"]


def test_verified_answer_never_changes():
    analyst, insights = sample_results()

    original = copy.deepcopy(analyst)

    qa = review_agent_output(analyst, insights)

    assert qa["verified_answer"] == original["answer"]
    assert qa["evidence"] == original["evidence"]
    assert analyst == original


def test_unverified_analyst_not_approved():
    analyst, insights = sample_results()

    analyst["status"] = "not_analyzed"

    qa = review_agent_output(analyst, insights)

    assert qa["approved"] is False
    assert qa["status"] == "fallback"
    assert qa["ai_explanation"] is None


# --------------------------------------------------
# NEW REGRESSION TESTS
# --------------------------------------------------

def test_reject_steady_downward_trend():
    """
    A single monthly decline does not establish
    a sustained downward trend.
    """

    analyst, insights = sample_results()

    insights["ai_explanation"] = (
        "A month-to-month decrease in product sales "
        "indicates a steady downward trend, suggesting "
        "potential problems in overall performance. "
        "Further research would be needed."
    )

    qa = review_agent_output(analyst, insights)

    assert qa["status"] == "rejected"
    assert any(
        "trend_claim" in finding
        for finding in qa["findings"]
    )


def test_reject_potential_demand_problem():
    """
    'Potential issues with customer demand'
    is not supported by sales alone.
    """

    analyst, insights = sample_results()

    insights["ai_explanation"] = (
        "The observed change suggests potential "
        "issues with customer demand or market "
        "conditions. The business should check "
        "whether those factors affected sales."
    )

    qa = review_agent_output(analyst, insights)

    assert qa["status"] == "rejected"
    assert any(
        "demand_problem_claim" in finding
        for finding in qa["findings"]
    )


def test_reject_sustained_decline_claim():
    """
    A claim of sustained decline requires
    evidence from multiple comparable periods.
    """

    analyst, insights = sample_results()

    insights["ai_explanation"] = (
        "This result reflects a sustained decline "
        "in sales performance across the business. "
        "Management should investigate the trend "
        "before changing its commercial plans."
    )

    qa = review_agent_output(analyst, insights)

    assert qa["status"] == "rejected"


def test_accept_cautious_investigation():
    """
    A recommendation to investigate is acceptable
    when it does not claim an unverified cause.
    """

    analyst, insights = sample_results()

    insights["ai_explanation"] = (
        "This sales change is worth investigating, "
        "but it does not establish a business cause. "
        "The business could compare product mix, "
        "order counts and market performance across "
        "comparable reporting periods."
    )

    qa = review_agent_output(analyst, insights)

    assert qa["status"] == "approved"
    assert qa["approved"] is True
    assert qa["ai_explanation"] is not None
