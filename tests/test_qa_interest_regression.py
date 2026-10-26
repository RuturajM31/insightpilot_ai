
"""
INSIGHTPILOT AI — INTEREST AND DEMAND REGRESSION TESTS

PURPOSE
-------
Reproduce unsupported claims from the Germany Copilot test.

THEORY
------
A sales decline alone does not prove reduced
customer interest or reduced demand.
"""

from src.agents.qa_agent import review_agent_output


def make_agent_results(explanation):
    """Create matching Analyst and Insights Agent results."""

    verified = (
        "June 2011 had the largest month-over-month product sales "
        "decline: -48.46%. The available figures do not establish "
        "the reason for this decline."
    )

    evidence = [
        "June 2011",
        "Monthly growth: -48.46%",
    ]

    analyst = {
        "agent": "analyst",
        "answer": verified,
        "category": "decline",
        "status": "verified",
        "evidence": evidence,
    }

    insights = {
        "agent": "insights",
        "verified_answer": verified,
        "evidence": list(evidence),
        "status": "generated",
        "llm_status": "accepted",
        "ai_explanation": explanation,
    }

    return analyst, insights


def test_reject_exact_real_world_germany_output():
    """Reject the precise problematic Llama explanation."""

    explanation = (
        "A significant month-to-month decrease in product sales indicates "
        "a substantial drop-off in customer interest or market demand. "
        "A useful follow-up check would be to investigate the specific "
        "products or categories affected by this decline, as well as any "
        "changes in marketing strategies or external factors that may "
        "have contributed to the downturn."
    )

    analyst, insights = make_agent_results(explanation)

    result = review_agent_output(analyst, insights)

    assert result["status"] == "rejected"
    assert result["approved"] is False
    assert result["ai_explanation"] is None
    assert result["verified_answer"] == analyst["answer"]

    assert any(
        "interest_or_demand_change_claim" in finding
        for finding in result["findings"]
    )


def test_reject_claim_that_customer_interest_fell():
    """A decline in interest cannot be inferred from sales alone."""

    explanation = (
        "The recorded sales change indicates a drop in customer interest. "
        "The business could examine inventory availability and customer "
        "order counts before taking further action."
    )

    analyst, insights = make_agent_results(explanation)

    result = review_agent_output(analyst, insights)

    assert result["status"] == "rejected"


def test_reject_claim_of_market_demand_problem():
    """A potential demand problem is not a verified finding."""

    explanation = (
        "The decline suggests a potential issue with market demand. "
        "Further analysis should examine sales quantities, product mix "
        "and stock availability before drawing conclusions."
    )

    analyst, insights = make_agent_results(explanation)

    result = review_agent_output(analyst, insights)

    assert result["status"] == "rejected"


def test_accept_hypotheses_as_questions_for_investigation():
    """Allow cautious investigation without claiming a cause."""

    explanation = (
        "This decline alone does not establish its cause. The business "
        "could investigate whether customer interest, product demand, "
        "inventory availability or order volumes changed, using "
        "additional evidence before drawing conclusions."
    )

    analyst, insights = make_agent_results(explanation)

    result = review_agent_output(analyst, insights)

    assert result["status"] == "approved"
    assert result["ai_explanation"] == explanation
