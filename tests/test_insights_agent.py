
"""
INSIGHTPILOT AI — INSIGHTS AGENT TESTS
======================================

PURPOSE
-------
Ensure the Insights Agent:
- Uses verified analytical evidence.
- Accepts valid LLM interpretations.
- Rejects mismatched evidence.
- Handles unavailable models safely.
- Skips unsupported analyst findings.

We mock the LLM so tests run without Ollama.
"""

from unittest.mock import patch

import pandas as pd
import pytest

from src.agents.analyst_agent import (
    run_analyst_agent,
)

from src.agents.insights_agent import (
    run_insights_agent,
)


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
            40.0, 60.0, 120.0, 90.0,
        ],
    })


def analyst_finding():
    return run_analyst_agent(
        sample_data(),
        "What was our best sales month?",
    )


def fake_llm_result(
    verified_answer,
    llm_status="accepted",
    category="highest_month",
):
    return {
        "verified_answer": verified_answer,
        "category": category,
        "engine": (
            "ollama_local"
            if llm_status == "accepted"
            else "verified_rules"
        ),
        "ai_explanation": (
            "The peak provides a useful benchmark "
            "for examining product mix and ordering "
            "patterns across reporting periods."
        ),
        "llm_status": llm_status,
    }


def test_valid_explanation():
    analyst = analyst_finding()

    with patch(
        "src.agents.insights_agent.answer_with_llm",
        return_value=fake_llm_result(
            analyst["answer"],
        ),
    ):
        result = run_insights_agent(
            sample_data(),
            "What was our best sales month?",
            analyst,
        )

    assert result["status"] == "generated"
    assert result["llm_status"] == "accepted"
    assert "benchmark" in result["ai_explanation"]


def test_verified_answer_is_unchanged():
    analyst = analyst_finding()

    with patch(
        "src.agents.insights_agent.answer_with_llm",
        return_value=fake_llm_result(
            analyst["answer"],
        ),
    ):
        result = run_insights_agent(
            sample_data(),
            "What was our best sales month?",
            analyst,
        )

    assert result["verified_answer"] == analyst["answer"]
    assert result["evidence"] == analyst["evidence"]


def test_evidence_mismatch_is_rejected():
    analyst = analyst_finding()

    with patch(
        "src.agents.insights_agent.answer_with_llm",
        return_value=fake_llm_result(
            "An incorrect verified answer.",
        ),
    ):
        result = run_insights_agent(
            sample_data(),
            "What was our best sales month?",
            analyst,
        )

    assert result["status"] == "rejected"
    assert result["ai_explanation"] is None
    assert result["llm_status"] == "evidence_mismatch"


def test_unavailable_llm_uses_fallback():
    analyst = analyst_finding()

    with patch(
        "src.agents.insights_agent.answer_with_llm",
        return_value=fake_llm_result(
            analyst["answer"],
            llm_status="unavailable",
        ),
    ):
        result = run_insights_agent(
            sample_data(),
            "What was our best sales month?",
            analyst,
        )

    assert result["status"] == "fallback"
    assert result["ai_explanation"] is None
    assert result["verified_answer"] == analyst["answer"]


def test_unsupported_question_skips_llm():
    analyst = run_analyst_agent(
        sample_data(),
        "Who won the football match?",
    )

    with patch(
        "src.agents.insights_agent.answer_with_llm"
    ) as mock_llm:
        result = run_insights_agent(
            sample_data(),
            "Who won the football match?",
            analyst,
        )

    mock_llm.assert_not_called()
    assert result["status"] == "skipped"
    assert result["ai_explanation"] is None


def test_invalid_analyst_result():
    with pytest.raises(ValueError):
        run_insights_agent(
            sample_data(),
            "What was our best month?",
            {},
        )


def test_category_mismatch_is_rejected():
    analyst = analyst_finding()

    with patch(
        "src.agents.insights_agent.answer_with_llm",
        return_value=fake_llm_result(
            analyst["answer"],
            category="decline",
        ),
    ):
        result = run_insights_agent(
            sample_data(),
            "What was our best sales month?",
            analyst,
        )

    assert result["status"] == "rejected"
    assert result["llm_status"] == "evidence_mismatch"
