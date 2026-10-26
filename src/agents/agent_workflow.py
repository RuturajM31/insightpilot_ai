
"""
INSIGHTPILOT AI — MULTI-AGENT WORKFLOW
======================================

PURPOSE
-------
Coordinate three components:

1. Analyst Agent: Verify business facts.
2. Insights Agent: Generate an LLM explanation.
3. QA Agent: Review the explanation.

THEORY
------
A multi-agent workflow organizes specialized
components into a controlled sequence.

This workflow uses Python orchestration.
The Insights Agent uses a real local LLM.

It is not yet an autonomous LangGraph workflow.
Its strength is explicit control and traceability.

SAFETY
------
The verified Python finding is always preserved.
An AI interpretation is shown only after QA approval.
"""

from src.agents.analyst_agent import run_analyst_agent
from src.agents.insights_agent import run_insights_agent
from src.agents.qa_agent import review_agent_output


def run_agent_workflow(data, question, use_llm=True):
    """
    Execute the full analytical agent workflow.

    INPUT:
        data: Prepared retail DataFrame.
        question: User's business question.
        use_llm: Enable or disable local Ollama.

    OUTPUT:
        A dictionary containing:
        - answer
        - verified_answer
        - ai_explanation
        - category
        - evidence
        - engine
        - status
        - qa_status
        - qa_findings
        - agent_trace
    """

    # STEP 1 — Run the Analyst Agent.
    analyst = run_analyst_agent(data, question)

    trace = [{
        "agent": "analyst",
        "status": analyst["status"],
        "selected_tool": analyst["selected_tool"],
    }]

    # If no verified analysis is available, return
    # the rules-engine answer without calling Ollama.
    if analyst["status"] != "verified":
        return {
            "answer": analyst["answer"],
            "verified_answer": analyst["answer"],
            "ai_explanation": None,
            "category": analyst["category"],
            "evidence": analyst["evidence"],
            "engine": "verified_rules",
            "status": "fallback",
            "qa_status": "not_run",
            "qa_findings": [],
            "agent_trace": trace,
        }

    # STEP 2 — Run the Insights Agent.
    insights = run_insights_agent(
        data,
        question,
        analyst,
        use_llm=use_llm,
    )

    trace.append({
        "agent": "insights",
        "status": insights["status"],
        "llm_status": insights["llm_status"],
    })

    # STEP 3 — Run the QA Agent.
    qa = review_agent_output(analyst, insights)

    trace.append({
        "agent": "qa",
        "status": qa["status"],
        "approved": qa["approved"],
    })

    # STEP 4 — Only publish QA-approved explanations.
    approved = (
        qa["approved"]
        and isinstance(qa["ai_explanation"], str)
        and bool(qa["ai_explanation"].strip())
    )

    explanation = (
        qa["ai_explanation"] if approved else None
    )

    # STEP 5 — Build the final answer.
    # The original verified finding always comes first.
    answer = qa["verified_answer"]

    if explanation:
        answer += (
            "\n\nAI interpretation: "
            + explanation
        )

    return {
        "answer": answer,
        "verified_answer": qa["verified_answer"],
        "ai_explanation": explanation,
        "category": analyst["category"],
        "evidence": qa["evidence"],
        "engine": (
            "multi_agent_llm"
            if approved else "verified_rules"
        ),
        "status": (
            "approved"
            if approved else "fallback"
        ),
        "qa_status": qa["status"],
        "qa_findings": qa["findings"],
        "agent_trace": trace,
    }


if __name__ == "__main__":
    """
    Demonstrate the complete workflow with
    the prepared UCI Online Retail dataset.
    """

    from pathlib import Path
    import pandas as pd

    project = Path(__file__).resolve().parents[2]
    csv_path = (
        project / "data" / "online_retail_prepared.csv.gz"
    )

    df = pd.read_csv(csv_path, low_memory=False)

    questions = [
        "What was our best sales month?",
        "What was the largest decline?",
    ]

    print("\n=== INSIGHTPILOT AGENT WORKFLOW ===")

    for question in questions:
        result = run_agent_workflow(
            df,
            question,
            use_llm=True,
        )

        print("\nQUESTION:", question)
        print("\nVERIFIED:", result["verified_answer"])
        print(
            "\nAI INTERPRETATION:",
            result["ai_explanation"] or "Not approved",
        )
        print("\nENGINE:", result["engine"])
        print("STATUS:", result["status"])
        print("QA STATUS:", result["qa_status"])
        print("QA FINDINGS:", result["qa_findings"])
        print("AGENT TRACE:", result["agent_trace"])
