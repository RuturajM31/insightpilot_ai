
"""
INSIGHTPILOT AI — RETAIL KPI ENGINE
===================================

PURPOSE:
Calculate important business measurements.

THEORY:
A KPI (Key Performance Indicator) measures
how well a business is performing.

THIS FILE CALCULATES:
1. Gross product sales
2. Number of sales orders
3. Average order value

IMPORTANT:
We exclude shipping, cancellations and other
adjustments from these product-sales KPIs.
"""

import pandas as pd


# Columns needed for our calculations.
REQUIRED_COLUMNS = {
    "InvoiceNo",
    "BusinessCategory",
    "TransactionType",
    "ProductSalesAmount",
}


def calculate_retail_kpis(data: pd.DataFrame) -> dict:
    """
    Calculate retail business KPIs.

    Input:
        A prepared retail DataFrame.

    Output:
        A dictionary containing three KPIs.
    """

    # STEP 1: Check required columns.
    missing = REQUIRED_COLUMNS - set(data.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    # STEP 2: Check sales amounts.
    amounts = pd.to_numeric(
        data["ProductSalesAmount"],
        errors="raise"
    )

    if amounts.isna().any() or (amounts < 0).any():
        raise ValueError(
            "ProductSalesAmount must contain non-negative numbers"
        )

    # STEP 3: Select normal product sales only.
    sale_mask = (
        data["BusinessCategory"].eq("Product")
        & data["TransactionType"].eq("Sale")
    )

    sales = data.loc[sale_mask]

    # Every sales order needs an invoice number.
    if sales["InvoiceNo"].isna().any():
        raise ValueError(
            "Sale rows must have invoice numbers"
        )

    # STEP 4: Calculate gross product sales.
    gross_sales = float(
        amounts.loc[sale_mask].sum()
    )

    # STEP 5: Count unique sales invoices.
    # One invoice can contain several products.
    order_count = int(
        sales["InvoiceNo"].astype("string").nunique()
    )

    # STEP 6: Calculate average order value.
    # Avoid dividing by zero when no sales exist.
    average_order_value = (
        gross_sales / order_count
        if order_count
        else 0.0
    )

    # STEP 7: Return our results.
    return {
        "gross_product_sales": gross_sales,
        "sales_orders": order_count,
        "average_order_value": average_order_value,
    }
