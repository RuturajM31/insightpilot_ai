
"""
INSIGHTPILOT AI — AUTOMATED BUSINESS INSIGHTS
=============================================

PURPOSE
-------
Turn verified sales calculations into useful
business findings written in simple English.

WHAT WE WILL LEARN
------------------
1. How to find the best-performing month.
2. How to identify increases and decreases.
3. How to explain results using simple rules.
4. Why we must avoid unsupported conclusions.

THEORY: RULE-BASED ANALYTICS
----------------------------
A rule-based system follows clear instructions.

For example:
IF monthly growth is positive:
    Say that sales increased.

This file does not use an LLM yet.
It uses our tested sales-trends engine.
"""

import pandas as pd

from src.sales_trends import calculate_monthly_trends


def generate_business_insights(data):
    """
    Analyze prepared retail data and return findings.

    INPUT:
        A prepared retail Pandas DataFrame.

    OUTPUT:
        A list of dictionaries.

    Each finding contains:
        - title
        - message
        - type
    """

    # STEP 1: Reuse our tested monthly calculations.
    trends = calculate_monthly_trends(data)

    # Store our findings here.
    insights = []

    # No dates means there is nothing to summarize.
    if trends.empty:
        return [{
            "title": "No data available",
            "message": "There are no transactions to analyze.",
            "type": "info",
        }]

    # STEP 2: Use complete calendar months for comparisons.
    # Date coverage does not guarantee that every
    # transaction has been recorded.
    complete = trends.loc[
        trends["IsCompleteMonth"]
    ].copy()

    if complete.empty:
        return [{
            "title": "Incomplete reporting period",
            "message": (
                "There are no complete calendar months "
                "available for comparison."
            ),
            "type": "warning",
        }]

    # STEP 3: Find the highest-sales complete month.
    best = complete.loc[
        complete["ProductSales"].idxmax()
    ]

    best_month = best["Month"].strftime("%B %Y")
    best_sales = float(best["ProductSales"])

    insights.append({
        "title": "Highest product sales",
        "message": (
            f"{best_month} recorded the highest "
            f"product sales among complete months, "
            f"at £{best_sales:,.2f}."
        ),
        "type": "success",
    })

    # STEP 4: Find valid monthly growth comparisons.
    valid_growth = complete.dropna(
        subset=["MoMGrowthPct"]
    )

    if not valid_growth.empty:

        # Biggest positive change.
        increases = valid_growth.loc[
            valid_growth["MoMGrowthPct"] > 0
        ]

        if not increases.empty:
            strongest = increases.loc[
                increases["MoMGrowthPct"].idxmax()
            ]

            insights.append({
                "title": "Strongest monthly growth",
                "message": (
                    f"{strongest['Month']:%B %Y} had "
                    f"the strongest month-over-month "
                    f"increase: "
                    f"{strongest['MoMGrowthPct']:+.2f}%."
                ),
                "type": "success",
            })

        # Biggest negative change.
        declines = valid_growth.loc[
            valid_growth["MoMGrowthPct"] < 0
        ]

        if not declines.empty:
            weakest = declines.loc[
                declines["MoMGrowthPct"].idxmin()
            ]

            insights.append({
                "title": "Largest monthly decline",
                "message": (
                    f"{weakest['Month']:%B %Y} had "
                    f"the largest month-over-month "
                    f"decrease: "
                    f"{weakest['MoMGrowthPct']:.2f}%."
                ),
                "type": "warning",
            })

    # STEP 5: Warn about incomplete calendar months.
    incomplete = trends.loc[
        ~trends["IsCompleteMonth"]
    ]

    if not incomplete.empty:
        months = ", ".join(
            incomplete["Month"].dt.strftime("%B %Y")
        )

        insights.append({
            "title": "Incomplete reporting period",
            "message": (
                f"{months} does not have full calendar-date "
                f"coverage and is excluded from monthly "
                f"growth comparisons."
            ),
            "type": "warning",
        })

    # STEP 6: Explain the limitations.
    insights.append({
        "title": "How to interpret these findings",
        "message": (
            "These findings describe changes in "
            "identified gross product sales. "
            "They do not establish why sales changed "
            "or prove that every transaction is present."
        ),
        "type": "info",
    })

    return insights


# STEP 7: Test with our retail dataset.
if __name__ == "__main__":

    from pathlib import Path

    project = Path(__file__).resolve().parent.parent
    csv_path = project / "data" / "online_retail_prepared.csv.gz"

    df = pd.read_csv(csv_path, low_memory=False)

    findings = generate_business_insights(df)

    print("\n=== INSIGHTPILOT AI — BUSINESS INSIGHTS ===")

    for finding in findings:
        print(f"\n{finding['title']}")
        print(finding["message"])
