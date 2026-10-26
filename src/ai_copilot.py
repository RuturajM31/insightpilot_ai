
"""
INSIGHTPILOT AI — EVIDENCE-GROUNDED COPILOT
==========================================

PURPOSE
-------
Answer common business questions in simple English
using verified calculations from our retail dataset.

WHAT WE LEARN
-------------
1. Natural-language question classification.
2. Reusing trusted analytical functions.
3. Answer grounding: calculations support the answer.
4. Handling unknown questions safely.
5. Separating evidence from business hypotheses.

IMPORTANT
---------
Version 1 is a deterministic, rule-based assistant.
It does NOT call a large language model yet.

A genuine LLM integration will be added separately.
"""

import re

import pandas as pd

from src.sales_trends import calculate_monthly_trends


def _has_any(text, words):
    """Check whether a question contains a word or phrase."""
    return any(word in text for word in words)


def _make_response(answer, category, evidence=None):
    """Give every answer the same easy-to-use structure."""
    return {
        "answer": answer,
        "category": category,
        "evidence": evidence or [],
        "engine": "verified_rules",
    }


def answer_business_question(data, question):
    """
    Answer a business question using verified retail data.

    Parameters
    ----------
    data : pandas.DataFrame
        Prepared retail transactions, including columns
        expected by calculate_monthly_trends().

    question : str
        A natural-language question typed by a user.

    Returns
    -------
    dict
        answer   : Text shown to the user.
        category : The type of question.
        evidence : Important calculated facts.
        engine   : Which answering engine was used.
    """

    # STEP 1 — Validate the user's question.
    if not isinstance(question, str) or not question.strip():
        return _make_response(
            "Please enter a question about your retail sales.",
            "help",
        )

    # Simple normalization makes matching easier.
    text = question.lower().strip()
    text = re.sub(r"\s+", " ", text)

    # STEP 2 — Recognize which type of answer is needed.
    # Check precise questions BEFORE broader categories.

    asks_why = _has_any(
        text,
        ["why", "reason", "cause", "caused", "because"],
    )

    asks_recommendation = _has_any(
        text,
        ["recommend", "suggest", "next step", "action",
         "improve", "investigate", "should we do"],
    )

    asks_coverage = _has_any(
        text,
        ["incomplete", "partial", "coverage",
         "missing month", "december 2011", "reliable"],
    )

    asks_highest = _has_any(
        text,
        ["highest", "best", "top month", "peak",
         "most sales", "biggest sales"],
    )

    asks_growth = _has_any(
        text,
        ["growth", "increase", "increased",
         "grew", "strongest rise"],
    )

    asks_decline = _has_any(
        text,
        ["decline", "drop", "decrease", "decreased",
         "fell", "fall", "worst month"],
    )

    asks_total = _has_any(
        text,
        ["total sales", "overall sales", "gross sales",
         "how much did we sell"],
    )

    recognized = any([
        asks_why,
        asks_recommendation,
        asks_coverage,
        asks_highest,
        asks_growth,
        asks_decline,
        asks_total,
    ])

    # Don't run expensive calculations for questions
    # that are outside this version's capabilities.
    if not recognized:
        return _make_response(
            "I can answer questions about total product sales, "
            "the highest-sales month, monthly growth, declines, "
            "incomplete periods, and possible investigations. "
            "I cannot answer that question reliably yet.",
            "unsupported",
        )

    # STEP 3 — Reuse our tested monthly analytics.
    trends = calculate_monthly_trends(data)

    if trends.empty:
        return _make_response(
            "This dataset has no transactions to analyze.",
            "no_data",
        )

    complete = trends.loc[
        trends["IsCompleteMonth"]
    ].copy()

    # STEP 4 — Questions asking WHY require caution.
    # A sales dataset can show WHAT changed, but it
    # cannot prove WHY the change happened.
    if asks_why:
        return _make_response(
            "The sales data can show when sales changed, "
            "but it cannot establish the cause. "
            "Possible explanations would need additional "
            "evidence, such as promotions, stock levels, "
            "pricing, or customer behavior. "
            "These are hypotheses, not verified findings.",
            "explanation_limit",
            [
                "The current dataset records sales activity.",
                "No causal analysis has been performed.",
            ],
        )

    # STEP 5 — Provide safe business recommendations.
    if asks_recommendation:
        return _make_response(
            "A useful next step is to investigate the months "
            "with the largest sales changes. Compare product "
            "mix, countries, order volumes, promotions, and "
            "stock availability where those records exist. "
            "Treat these as investigation ideas, not proven "
            "causes or guaranteed improvements.",
            "recommendation",
            [
                "Monthly changes are calculated from "
                "identified gross product sales.",
            ],
        )

    # STEP 6 — Explain incomplete reporting periods.
    if asks_coverage:
        incomplete = trends.loc[
            ~trends["IsCompleteMonth"]
        ]

        if incomplete.empty:
            return _make_response(
                "The selected records reach the calendar "
                "boundaries of every month in this selection. "
                "This does not prove every transaction exists.",
                "data_coverage",
            )

        month_names = ", ".join(
            incomplete["Month"].dt.strftime("%B %Y")
        )

        return _make_response(
            f"{month_names} has incomplete calendar-date "
            "coverage. It is excluded from monthly growth "
            "comparisons that require full months. "
            "Calendar coverage alone cannot prove that "
            "the underlying records are complete.",
            "data_coverage",
            [f"Incomplete months: {month_names}"],
        )

    # STEP 7 — Answer total product sales questions.
    if asks_total:
        total = float(trends["ProductSales"].sum())

        return _make_response(
            f"The selected records contain £{total:,.2f} "
            "in identified gross product sales. "
            "This is before cancellations and is not "
            "audited net revenue.",
            "total_sales",
            [f"Gross identified product sales: £{total:,.2f}"],
        )

    # The next questions need complete calendar months.
    if complete.empty:
        return _make_response(
            "There are no months with full calendar-date "
            "coverage in the selected records. "
            "I cannot make this monthly comparison reliably.",
            "insufficient_coverage",
        )

    # STEP 8 — Find the month with the highest sales.
    if asks_highest and not (
        asks_growth or asks_decline
    ):
        best = complete.loc[
            complete["ProductSales"].idxmax()
        ]

        month = best["Month"].strftime("%B %Y")
        amount = float(best["ProductSales"])

        return _make_response(
            f"{month} had the highest identified gross "
            f"product sales among complete months: "
            f"£{amount:,.2f}. "
            "This does not establish why sales were highest.",
            "highest_month",
            [
                f"Month: {month}",
                f"Gross product sales: £{amount:,.2f}",
            ],
        )

    # Only valid comparisons have a growth percentage.
    valid_growth = complete.dropna(
        subset=["MoMGrowthPct"]
    )

    if valid_growth.empty:
        return _make_response(
            "There are not enough comparable complete "
            "months to calculate month-over-month growth.",
            "insufficient_coverage",
        )

    # STEP 9 — Find the strongest positive growth.
    if asks_growth and not asks_decline:
        increases = valid_growth.loc[
            valid_growth["MoMGrowthPct"] > 0
        ]

        if increases.empty:
            return _make_response(
                "No positive month-over-month growth "
                "was found in the comparable months.",
                "growth",
            )

        best = increases.loc[
            increases["MoMGrowthPct"].idxmax()
        ]

        month = best["Month"].strftime("%B %Y")
        growth = float(best["MoMGrowthPct"])

        return _make_response(
            f"{month} had the strongest month-over-month "
            f"product sales growth: +{growth:.2f}%. "
            "This is an observed change, not a proven cause.",
            "growth",
            [
                f"Month: {month}",
                f"Monthly growth: +{growth:.2f}%",
            ],
        )

    # STEP 10 — Find the largest negative growth.
    if asks_decline:
        declines = valid_growth.loc[
            valid_growth["MoMGrowthPct"] < 0
        ]

        if declines.empty:
            return _make_response(
                "No month-over-month decline was found "
                "in the comparable months.",
                "decline",
            )

        worst = declines.loc[
            declines["MoMGrowthPct"].idxmin()
        ]

        month = worst["Month"].strftime("%B %Y")
        growth = float(worst["MoMGrowthPct"])

        return _make_response(
            f"{month} had the largest month-over-month "
            f"product sales decline: {growth:.2f}%. "
            "The available figures do not establish "
            "the reason for this decline.",
            "decline",
            [
                f"Month: {month}",
                f"Monthly growth: {growth:.2f}%",
            ],
        )

    # Avoid guessing when several categories overlap.
    return _make_response(
        "Please ask about one topic at a time, such as "
        "highest sales, monthly growth, or a decline.",
        "clarification",
    )


# STEP 11 — Allow a quick real-data demonstration.
if __name__ == "__main__":

    from pathlib import Path

    project = Path(__file__).resolve().parent.parent
    csv_path = project / "data" / "online_retail_prepared.csv.gz"

    df = pd.read_csv(csv_path, low_memory=False)

    questions = [
        "What was our best sales month?",
        "Which month had the strongest growth?",
        "What was the largest decline?",
        "Why did sales decline?",
        "Is December 2011 incomplete?",
        "What should we investigate next?",
    ]

    print("\n=== INSIGHTPILOT AI COPILOT ===")

    for question in questions:
        result = answer_business_question(df, question)

        print(f"\nQUESTION: {question}")
        print(f"ANSWER: {result['answer']}")
        print(f"ENGINE: {result['engine']}")
