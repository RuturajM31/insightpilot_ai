
"""
INSIGHTPILOT AI — QUALITY ASSURANCE AGENT
=========================================

PURPOSE
-------
Review AI-generated business interpretations before publication.
Preserve the Analyst Agent's verified findings and evidence.

THEORY
------
Evidence-grounded QA checks whether an AI interpretation
contains unsupported numerical, causal, demand or trend claims.

This is deterministic QA, not an independent LLM reviewer.
Passing it cannot guarantee that every statement is correct.
"""

import re

from src.llm_engine import validate_explanation


# Detect unsupported changes in customer interest or demand.
# Distinguish assertions from cautious investigation questions.
DEMAND_SUBJECT = r"(?:(?:customer|product|consumer|market)\s+)?demand"

INTEREST_OR_DEMAND = (
    r"(?:(?:customer|consumer|buyer|market|product)\s+)?"
    r"(?:interest|demand)"
)

UNSUPPORTED_CLAIMS = (
    (
        "interest_or_demand_change_claim",
        re.compile(
            r"\b(?:drop(?:[ -]?off)?|fall|decline|decrease|"
            r"increase|rise|growth|surge|reduction|loss)\s+in\s+"
            + INTEREST_OR_DEMAND + r"\b",
            re.IGNORECASE,
        ),
    ),
    (
        "interest_or_demand_problem_claim",
        re.compile(
            r"\b(?:issues?|problems?|weakness|weakening|shortfall|lack)\s+"
            r"(?:with|in|of)\s+" + INTEREST_OR_DEMAND + r"\b",
            re.IGNORECASE,
        ),
    ),
    (
        "inferred_interest_or_demand_claim",
        re.compile(
            r"\b(?:indicates?|shows?|demonstrates?|confirms?|"
            r"reflects?|suggests?|implies?)\s+"
            r"(?:a\s+)?(?:substantial\s+|significant\s+|potential\s+)?"
            r"(?:drop(?:[ -]?off)?|fall|decline|decrease|"
            r"increase|rise|loss|issue|problem)\s+"
            r"(?:in|with)\s+" + INTEREST_OR_DEMAND + r"\b",
            re.IGNORECASE,
        ),
    ),
    (
        "demand_change_claim",
        re.compile(
            r"\b(?:drop|drop[ -]?off|fall|decline|decrease|increase|"
            r"rise|growth|surge|reduction)\s+in\s+"
            + DEMAND_SUBJECT + r"\b",
            re.IGNORECASE,
        ),
    ),
    (
        "demand_problem_claim",
        re.compile(
            r"\b(?:issues?|problems?|weakness|weakening|shortfall|lack)\s+"
            r"(?:with|in|of)\s+" + DEMAND_SUBJECT + r"\b",
            re.IGNORECASE,
        ),
    ),
    (
        "unsupported_trend_claim",
        re.compile(
            r"\b(?:steady|sustained|continuous|continuing|persistent|"
            r"long[ -]?term|ongoing)\s+(?:downward\s+)?"
            r"(?:trend|decline|decrease|drop|fall)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "asserted_downward_trend",
        re.compile(
            r"\b(?:indicates?|shows?|demonstrates?|confirms?|reflects?)\s+"
            r"(?:a\s+)?(?:steady\s+|sustained\s+)?downward\s+trend\b",
            re.IGNORECASE,
        ),
    ),
    (
        "causal_claim",
        re.compile(
            r"\b(?:because of|caused by|due to|driven by|resulted from|"
            r"responsible for|proves? that)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "profit_claim",
        re.compile(
            r"\b(?:profitability|profits?|margins?)\s+"
            r"(?:increased|improved|grew|rose|decreased|fell|declined)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "guaranteed_outcome",
        re.compile(
            r"\b(?:will definitely|guarantees?|certainly will|will always)\b",
            re.IGNORECASE,
        ),
    ),
)


def _make_qa_result(analyst_result, status, findings, explanation=None):
    """Always return the original Analyst Agent's verified evidence."""
    return {
        "agent": "qa",
        "status": status,
        "approved": status == "approved",
        "verified_answer": analyst_result["answer"],
        "ai_explanation": explanation,
        "evidence": list(analyst_result["evidence"]),
        "findings": findings,
    }


def review_agent_output(analyst_result, insights_result):
    """Approve an interpretation only when all configured checks pass."""

    if not isinstance(analyst_result, dict):
        raise ValueError("Analyst result must be a dictionary.")

    if not isinstance(insights_result, dict):
        raise ValueError("Insights result must be a dictionary.")

    required_analyst = {
        "agent", "answer", "category", "status", "evidence"
    }

    required_insights = {
        "agent", "verified_answer", "ai_explanation", "evidence",
        "status", "llm_status",
    }

    if not required_analyst.issubset(analyst_result):
        raise ValueError("Analyst result has missing fields.")

    if not required_insights.issubset(insights_result):
        raise ValueError("Insights result has missing fields.")

    if analyst_result["agent"] != "analyst":
        raise ValueError("Expected an Analyst Agent result.")

    if insights_result["agent"] != "insights":
        raise ValueError("Expected an Insights Agent result.")

    # Never approve an unverified analytical result.
    if analyst_result["status"] != "verified":
        return _make_qa_result(
            analyst_result,
            "fallback",
            ["Analyst result is not verified."],
        )

    # Both agents must reference identical verified evidence.
    if (
        insights_result["verified_answer"] != analyst_result["answer"]
        or insights_result["evidence"] != analyst_result["evidence"]
    ):
        return _make_qa_result(
            analyst_result,
            "rejected",
            ["Evidence mismatch between agents."],
        )

    # The LLM must have generated an accepted interpretation.
    if (
        insights_result["status"] != "generated"
        or insights_result["llm_status"] != "accepted"
    ):
        return _make_qa_result(
            analyst_result,
            "fallback",
            ["No accepted AI interpretation available."],
        )

    explanation = insights_result["ai_explanation"]

    # First apply the existing numerical and format checks.
    valid, reason = validate_explanation(explanation)

    if not valid:
        return _make_qa_result(
            analyst_result,
            "rejected",
            [f"LLM validation failed: {reason}"],
        )

    # Then detect unsupported business interpretations.
    findings = [
        f"Unsupported claim: {name}"
        for name, pattern in UNSUPPORTED_CLAIMS
        if pattern.search(explanation)
    ]

    if findings:
        return _make_qa_result(
            analyst_result,
            "rejected",
            findings,
        )

    return _make_qa_result(
        analyst_result,
        "approved",
        ["Passed configured QA checks."],
        explanation=explanation,
    )


if __name__ == "__main__":
    """Run all three agents using the real retail dataset."""

    from pathlib import Path
    import pandas as pd

    from src.agents.analyst_agent import run_analyst_agent
    from src.agents.insights_agent import run_insights_agent

    project = Path(__file__).resolve().parents[2]

    df = pd.read_csv(
        project / "data" / "online_retail_prepared.csv.gz",
        low_memory=False,
    )

    question = "What was the largest decline?"

    analyst = run_analyst_agent(df, question)

    insights = run_insights_agent(
        df,
        question,
        analyst,
        use_llm=True,
    )

    qa = review_agent_output(analyst, insights)

    print("\n=== INSIGHTPILOT QA AGENT ===")
    print("QUESTION:", question)
    print("VERIFIED FINDING:", qa["verified_answer"])
    print("QA STATUS:", qa["status"])
    print("QA APPROVED:", qa["approved"])
    print("QA FINDINGS:", qa["findings"])
    print(
        "AI INTERPRETATION:",
        qa["ai_explanation"] or "Rejected or unavailable.",
    )
