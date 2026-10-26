
"""
INSIGHTPILOT AI — AGENT WORKFLOW TESTS
======================================

PURPOSE
-------
Test the complete Analyst → Insights → QA workflow.

WHAT WE CHECK
-------------
1. Approved AI explanations are displayed.
2. Rejected explanations are hidden.
3. Verified facts remain unchanged.
4. Unsupported questions skip the LLM.
5. The workflow works without Ollama.
6. Agent execution is recorded.
7. Evidence mismatches are rejected.

We simulate the Insights Agent so automated
tests do not depend on a running LLM.
"""

from unittest.mock import patch

import pandas as pd

from src.agents.agent_workflow import (
    run_agent_workflow,
)


def sample_data():
    """Small dataset with known sales figures."""

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


def fake_insights(
    data,
    question,
    analyst_result,
    use_llm=True,
):
    """Simulate a valid Insights Agent response."""

    return {
        "agent": "insights",
        "verified_answer": analyst_result["answer"],
        "evidence": list(analyst_result["evidence"]),
        "status": "generated",
        "llm_status": "accepted",
        "ai_explanation": (
            "This peak provides a useful benchmark "
            "for comparisons across reporting periods. "
            "The business could investigate product "
            "mix and order volumes to understand "
            "the observed pattern more clearly."
        ),
    }


def test_approved_ai_explanation():
    """Approved AI text should appear in the answer."""

    with patch(
        "src.agents.agent_workflow.run_insights_agent",
        side_effect=fake_insights,
    ):
        result = run_agent_workflow(
            sample_data(),
            "What was our best sales month?",
        )

    assert result["status"] == "approved"
    assert result["qa_status"] == "approved"
    assert result["engine"] == "multi_agent_llm"
    assert "AI interpretation:" in result["answer"]


def test_verified_facts_preserved():
    """LLM output must not change calculated numbers."""

    with patch(
        "src.agents.agent_workflow.run_insights_agent",
        side_effect=fake_insights,
    ):
        result = run_agent_workflow(
            sample_data(),
            "What was our best sales month?",
        )

    assert "February 2026" in result["verified_answer"]
    assert "£120.00" in result["verified_answer"]
    assert result["answer"].startswith(
        result["verified_answer"]
    )


def test_reject_unsupported_demand_claim():
    """The QA Agent must block unsupported demand claims."""

    def unsafe_insights(data, question, analyst_result, use_llm=True):
        result = fake_insights(
            data,
            question,
            analyst_result,
            use_llm,
        )

        result["ai_explanation"] = (
            "A drop in customer demand explains "
            "the lower sales in this period. "
            "The business should immediately "
            "change its commercial strategy."
        )

        return result

    with patch(
        "src.agents.agent_workflow.run_insights_agent",
        side_effect=unsafe_insights,
    ):
        result = run_agent_workflow(
            sample_data(),
            "What was our best sales month?",
        )

    assert result["status"] == "fallback"
    assert result["qa_status"] == "rejected"
    assert result["ai_explanation"] is None
    assert result["engine"] == "verified_rules"
    assert "£120.00" in result["answer"]


def test_unsupported_question_skips_agents():
    """Questions outside scope must not call the LLM."""

    with patch(
        "src.agents.agent_workflow.run_insights_agent"
    ) as mock_insights:
        result = run_agent_workflow(
            sample_data(),
            "Who won the football match?",
        )

    mock_insights.assert_not_called()

    assert result["status"] == "fallback"
    assert result["qa_status"] == "not_run"
    assert result["engine"] == "verified_rules"
    assert len(result["agent_trace"]) == 1


def test_llm_unavailable():
    """The application must work without Ollama."""

    def unavailable_insights(data, question, analyst_result, use_llm=True):
        return {
            "agent": "insights",
            "verified_answer": analyst_result["answer"],
            "evidence": list(analyst_result["evidence"]),
            "status": "fallback",
            "llm_status": "unavailable",
            "ai_explanation": None,
        }

    with patch(
        "src.agents.agent_workflow.run_insights_agent",
        side_effect=unavailable_insights,
    ):
        result = run_agent_workflow(
            sample_data(),
            "What was our best sales month?",
        )

    assert result["status"] == "fallback"
    assert result["qa_status"] == "fallback"
    assert result["ai_explanation"] is None
    assert "£120.00" in result["verified_answer"]


def test_agent_execution_trace():
    """All three components should appear in the trace."""

    with patch(
        "src.agents.agent_workflow.run_insights_agent",
        side_effect=fake_insights,
    ):
        result = run_agent_workflow(
            sample_data(),
            "What was our best sales month?",
        )

    names = [
        step["agent"]
        for step in result["agent_trace"]
    ]

    assert names == [
        "analyst",
        "insights",
        "qa",
    ]


def test_evidence_mismatch():
    """The QA Agent must reject mismatched evidence."""

    def mismatch_insights(data, question, analyst_result, use_llm=True):
        result = fake_insights(
            data,
            question,
            analyst_result,
            use_llm,
        )

        result["verified_answer"] = (
            "Incorrect analytical result."
        )

        return result

    with patch(
        "src.agents.agent_workflow.run_insights_agent",
        side_effect=mismatch_insights,
    ):
        result = run_agent_workflow(
            sample_data(),
            "What was our best sales month?",
        )

    assert result["status"] == "fallback"
    assert result["qa_status"] == "rejected"
    assert result["ai_explanation"] is None
    assert "£120.00" in result["verified_answer"]
