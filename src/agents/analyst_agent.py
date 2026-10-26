
"""
INSIGHTPILOT AI — ANALYST AGENT
===============================

PURPOSE
-------
Select an analytical operation based on a user's
question and retrieve verified business results.

THEORY
------
An AI agent can select and use tools to complete
a task.

This first component uses deterministic tool
selection. It does not independently use an LLM.
The LLM-powered Insights Agent comes next.

We reuse our tested analytics functions instead
of asking a language model to calculate figures.
"""

from src.ai_copilot import answer_business_question


# These are the analytical operations supported
# by our existing verified Copilot.
ANALYTICAL_TOOLS = {
    "highest_month": "Highest monthly product sales",
    "growth": "Strongest monthly growth",
    "decline": "Largest monthly decline",
    "total_sales": "Total gross product sales",
    "data_coverage": "Reporting-period coverage",
    "recommendation": "Business investigation guidance",
    "explanation_limit": "Causal evidence limitations",
}

# Categories that do not require or permit
# further factual analysis.
NON_ANALYTICAL_CATEGORIES = {
    "help",
    "unsupported",
    "no_data",
    "insufficient_coverage",
    "clarification",
}


def run_analyst_agent(data, question):
    """
    Choose an analysis and return verified findings.

    INPUT:
        data: Prepared retail DataFrame.
        question: User's natural-language question.

    OUTPUT:
        A dictionary containing:
        - agent
        - selected_tool
        - answer
        - category
        - evidence
        - status
    """

    # STEP 1: Reuse trusted question classification
    # and analytical calculations.
    result = answer_business_question(
        data,
        question,
    )

    category = result["category"]

    # STEP 2: Identify the selected operation.
    selected_tool = ANALYTICAL_TOOLS.get(category)

    # STEP 3: Mark unsupported questions honestly.
    if category in NON_ANALYTICAL_CATEGORIES:
        status = "not_analyzed"
    elif selected_tool is None:
        status = "unsupported"
    else:
        status = "verified"

    # STEP 4: Return a structured agent result.
    return {
        "agent": "analyst",
        "selected_tool": selected_tool,
        "answer": result["answer"],
        "category": category,
        "evidence": list(result["evidence"]),
        "status": status,
    }


if __name__ == "__main__":
    """
    Demonstrate the Analyst Agent on real data.
    """

    from pathlib import Path

    import pandas as pd

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

    questions = [
        "What was our best sales month?",
        "Which month had the strongest growth?",
        "What was the largest decline?",
    ]

    print("\n=== INSIGHTPILOT ANALYST AGENT ===")

    for question in questions:
        result = run_analyst_agent(df, question)

        print("\nQUESTION:", question)
        print("TOOL:", result["selected_tool"])
        print("ANSWER:", result["answer"])
        print("STATUS:", result["status"])
