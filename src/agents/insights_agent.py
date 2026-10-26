
"""
INSIGHTPILOT AI — INSIGHTS AGENT
================================

PURPOSE
-------
Generate a business interpretation using our real
local Llama model and verified analytical evidence.

THEORY
------
An LLM can interpret data in natural language,
but it must not replace trusted calculations.

WORKFLOW
--------
1. Receive the Analyst Agent's verified finding.
2. Call our existing Ollama LLM engine.
3. Check that the underlying finding is unchanged.
4. Return the interpretation separately.
5. Fall back safely when AI is unavailable.

The QA Agent will provide additional checking later.
"""

from src.llm_engine import answer_with_llm


def run_insights_agent(
    data,
    question,
    analyst_result,
    use_llm=True,
):
    """
    Generate an optional AI interpretation.

    INPUT:
        data: Prepared retail DataFrame.
        question: User's business question.
        analyst_result: Output of the Analyst Agent.
        use_llm: Whether to call Ollama.

    OUTPUT:
        A dictionary with verified evidence,
        an optional interpretation, and status.
    """

    # STEP 1: Validate the Analyst Agent's result.
    if not isinstance(analyst_result, dict):
        raise ValueError(
            "Analyst result must be a dictionary."
        )

    required = {
        "agent",
        "answer",
        "category",
        "status",
        "evidence",
    }

    if not required.issubset(analyst_result):
        raise ValueError(
            "Analyst result is missing required fields."
        )

    if analyst_result["agent"] != "analyst":
        raise ValueError(
            "Expected a result from the Analyst Agent."
        )

    if analyst_result["status"] != "verified":
        return {
            "agent": "insights",
            "verified_answer": analyst_result["answer"],
            "ai_explanation": None,
            "evidence": analyst_result["evidence"],
            "status": "skipped",
            "llm_status": "analyst_not_verified",
        }

    # STEP 2: Ask our existing LLM engine.
    llm_result = answer_with_llm(
        data,
        question,
        use_llm=use_llm,
    )

    # STEP 3: Check that the LLM engine used
    # the same verified calculation as the analyst.
    # Never accept mismatched evidence.
    if (
        llm_result.get("verified_answer")
        != analyst_result["answer"]
        or llm_result.get("category")
        != analyst_result["category"]
    ):
        return {
            "agent": "insights",
            "verified_answer": analyst_result["answer"],
            "ai_explanation": None,
            "evidence": analyst_result["evidence"],
            "status": "rejected",
            "llm_status": "evidence_mismatch",
        }

    # STEP 4: Accept only interpretations
    # already accepted by the LLM engine.
    accepted = (
        llm_result.get("llm_status") == "accepted"
        and llm_result.get("engine") == "ollama_local"
        and isinstance(
            llm_result.get("ai_explanation"),
            str,
        )
        and bool(
            llm_result["ai_explanation"].strip()
        )
    )

    return {
        "agent": "insights",
        "verified_answer": analyst_result["answer"],
        "ai_explanation": (
            llm_result["ai_explanation"]
            if accepted else None
        ),
        "evidence": analyst_result["evidence"],
        "status": (
            "generated" if accepted else "fallback"
        ),
        "llm_status": llm_result.get(
            "llm_status",
            "unknown",
        ),
    }


if __name__ == "__main__":
    """
    Demonstrate the Analyst and Insights Agents
    together using the actual retail dataset.
    """

    from pathlib import Path

    import pandas as pd

    from src.agents.analyst_agent import (
        run_analyst_agent,
    )

    project = Path(__file__).resolve().parents[2]

    csv_path = (
        project
        / "data"
        / "online_retail_prepared.csv.gz"
    )

    df = pd.read_csv(
        csv_path,
        low_memory=False,
    )

    question = "What was our best sales month?"

    analyst = run_analyst_agent(
        df,
        question,
    )

    insights = run_insights_agent(
        df,
        question,
        analyst,
        use_llm=True,
    )

    print("\n=== INSIGHTPILOT INSIGHTS AGENT ===")
    print("\nQUESTION:", question)
    print("\nVERIFIED:", insights["verified_answer"])

    print(
        "\nAI EXPLANATION:",
        insights["ai_explanation"]
        or "No validated explanation available.",
    )

    print("\nSTATUS:", insights["status"])
    print("LLM STATUS:", insights["llm_status"])
