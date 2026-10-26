
"""
INSIGHTPILOT AI — MONTHLY SALES TRENDS
======================================

PURPOSE
-------
Calculate monthly product sales and sales growth.

WHAT WE LEARN
-------------
1. Group transactions by month.
2. Calculate total sales for each month.
3. Compare sales with the previous month.
4. Detect months without sales.
5. Avoid misleading comparisons for partial months.

THEORY: MONTH-OVER-MONTH GROWTH
------------------------------
MoM growth measures how sales change from one
month to the next.

Example:
January = £100
February = £120

Growth = (120 - 100) / 100 * 100 = 20%

IMPORTANT:
Only compare months with complete calendar-date
coverage. This does not guarantee that every
transaction is present in the dataset.
"""

import pandas as pd


# --------------------------------------------------
# STEP 1 — Define our main function
# --------------------------------------------------

def calculate_monthly_trends(data):
    """
    Calculate monthly product sales.

    INPUT:
        A prepared retail DataFrame.

    OUTPUT:
        A DataFrame containing:
        - Month
        - ProductSales
        - MoMGrowthPct
        - IsCompleteMonth
    """

    # Check that important columns exist.
    required = {
        "InvoiceDate",
        "BusinessCategory",
        "TransactionType",
        "ProductSalesAmount",
    }

    missing = required - set(data.columns)

    if missing:
        raise ValueError(
            f"Missing columns: {sorted(missing)}"
        )

    # --------------------------------------------------
    # STEP 2 — Prepare data safely
    # --------------------------------------------------

    # Work on a copy so the original is unchanged.
    df = data.copy()

    # Convert dates into proper datetime values.
    df["InvoiceDate"] = pd.to_datetime(
        df["InvoiceDate"],
        errors="raise",
    )

    # Missing dates could lead to incorrect trends.
    if df["InvoiceDate"].isna().any():
        raise ValueError(
            "InvoiceDate contains missing dates"
        )

    # Make sure amounts are numerical.
    df["ProductSalesAmount"] = pd.to_numeric(
        df["ProductSalesAmount"],
        errors="raise",
    )

    # Reject missing or negative product-sales amounts.
    if (
        df["ProductSalesAmount"].isna().any()
        or (df["ProductSalesAmount"] < 0).any()
    ):
        raise ValueError(
            "Invalid product sales amounts"
        )

    # Return an empty result for an empty dataset.
    if df.empty:
        return pd.DataFrame(
            columns=[
                "Month",
                "ProductSales",
                "MoMGrowthPct",
                "IsCompleteMonth",
            ]
        )

    # --------------------------------------------------
    # STEP 3 — Find the dataset date range
    # --------------------------------------------------

    first_date = df["InvoiceDate"].min().normalize()
    last_date = df["InvoiceDate"].max().normalize()

    # --------------------------------------------------
    # STEP 4 — Select normal product sales
    # --------------------------------------------------

    sales = df.loc[
        df["BusinessCategory"].eq("Product")
        & df["TransactionType"].eq("Sale")
    ].copy()

    # Convert each transaction date into its month.
    sales["Month"] = (
        sales["InvoiceDate"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    # Add product-sales amounts for each month.
    monthly_sales = sales.groupby("Month")[
        "ProductSalesAmount"
    ].sum()

    # Create a continuous list of calendar months.
    # This also includes months with no product sales.
    months = pd.date_range(
        first_date.to_period("M").to_timestamp(),
        last_date.to_period("M").to_timestamp(),
        freq="MS",
    )

    result = pd.DataFrame({"Month": months})

    result["ProductSales"] = (
        result["Month"]
        .map(monthly_sales)
        .fillna(0.0)
    )

    # --------------------------------------------------
    # STEP 5 — Identify partial calendar months
    # --------------------------------------------------

    # Initially mark months as complete.
    result["IsCompleteMonth"] = True

    first_month_start = result["Month"].iloc[0]

    last_month_end = (
        result["Month"].iloc[-1]
        + pd.offsets.MonthEnd(0)
    )

    # If data starts after the first calendar day,
    # the first month is incomplete.
    if first_date > first_month_start:
        result.loc[0, "IsCompleteMonth"] = False

    # If data ends before the final calendar day,
    # the last month is incomplete.
    if last_date < last_month_end:
        result.loc[
            result.index[-1],
            "IsCompleteMonth"
        ] = False

    # --------------------------------------------------
    # STEP 6 — Calculate month-over-month growth
    # --------------------------------------------------

    # Get each previous month's sales.
    previous_sales = result["ProductSales"].shift(1)

    # Percentage increase or decrease.
    result["MoMGrowthPct"] = (
        (result["ProductSales"] - previous_sales)
        / previous_sales
        * 100
    )

    # IMPORTANT FIX:
    # shift(fill_value=False) avoids the Pandas
    # FutureWarning caused by shift().fillna(False).
    previous_complete = result[
        "IsCompleteMonth"
    ].shift(1, fill_value=False)

    # Growth is valid only when:
    # 1. Current month has complete date coverage.
    # 2. Previous month has complete date coverage.
    # 3. Previous sales are greater than zero.
    valid = (
        result["IsCompleteMonth"]
        & previous_complete
        & (previous_sales > 0)
    )

    # Invalid comparisons become NaN.
    # NaN means no meaningful percentage is available.
    result.loc[
        ~valid, "MoMGrowthPct"
    ] = float("nan")

    return result
