
"""
INSIGHTPILOT AI — RETAIL DATA PREPARATION
=========================================

WHAT DOES THIS FILE DO?

1. Reads our Online Retail CSV.
2. Checks that important columns exist.
3. Identifies sales, cancellations and adjustments.
4. Separates products from shipping and other charges.
5. Calculates the value of each transaction.
6. Saves a new CSV without deleting original rows.

THEORY: DATA PREPROCESSING
Raw data can contain missing values, unusual transactions
and different types of information.

Data preprocessing helps us understand and organize it
before calculating business results.

IMPORTANT:
These rules are specific to our Online Retail dataset.
The general CSV analyzer will be built separately.
"""

from pathlib import Path

import pandas as pd


# ---------------------------------------------
# STEP 1 — Define file locations
# ---------------------------------------------

PROJECT_FOLDER = Path(__file__).resolve().parent.parent

INPUT_FILE = PROJECT_FOLDER / "data" / "online_retail_raw.csv"
OUTPUT_FILE = PROJECT_FOLDER / "data" / "online_retail_prepared.csv"


# ---------------------------------------------
# STEP 2 — Define special business codes
# ---------------------------------------------

# These codes identify transactions that are
# not ordinary product purchases.

SHIPPING_CODES = {"POST", "DOT", "C2"}

DISCOUNT_CODES = {"D"}

MANUAL_CODES = {"M"}

OTHER_CHARGE_CODES = {
    "BANK CHARGES",
    "B",
    "CRUK"
}

SPECIAL_ITEM_CODES = {"S", "PADS"}


# ---------------------------------------------
# STEP 3 — Classify the data
# ---------------------------------------------

def classify_transactions(df):
    """
    Add business labels and calculated amounts.

    Input: A Pandas DataFrame
    Output: A new DataFrame with additional columns

    The original DataFrame is not changed.
    """

    df = df.copy()

    # Check that the required columns are present.
    required = {
        "InvoiceNo",
        "StockCode",
        "Quantity",
        "UnitPrice"
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    # Make sure numeric fields contain numbers.
    df["Quantity"] = pd.to_numeric(
        df["Quantity"], errors="raise"
    )

    df["UnitPrice"] = pd.to_numeric(
        df["UnitPrice"], errors="raise"
    )

    # Missing numbers must not be treated as valid sales.
    if df[["Quantity", "UnitPrice"]].isna().any().any():
        raise ValueError("Quantity or UnitPrice contains missing values")

    # Identify cancelled invoices.
    cancelled = (
        df["InvoiceNo"]
        .astype("string")
        .str.startswith("C", na=False)
    )

    # -----------------------------------------
    # A. Identify transaction types
    # -----------------------------------------

    df["TransactionType"] = "Other"

    df.loc[
        (df["Quantity"] > 0)
        & (df["UnitPrice"] > 0)
        & ~cancelled,
        "TransactionType"
    ] = "Sale"

    df.loc[
        cancelled & (df["Quantity"] < 0),
        "TransactionType"
    ] = "Cancellation"

    df.loc[
        (df["Quantity"] < 0) & ~cancelled,
        "TransactionType"
    ] = "Adjustment"

    df.loc[
        df["UnitPrice"] == 0,
        "TransactionType"
    ] = "Zero Price"

    df.loc[
        df["UnitPrice"] < 0,
        "TransactionType"
    ] = "Accounting Adjustment"

    # -----------------------------------------
    # B. Identify business categories
    # -----------------------------------------

    df["BusinessCategory"] = "Product"

    codes = df["StockCode"].astype("string").str.strip()

    df.loc[
        codes.isin(SHIPPING_CODES),
        "BusinessCategory"
    ] = "Shipping"

    df.loc[
        codes.isin(DISCOUNT_CODES),
        "BusinessCategory"
    ] = "Discount"

    df.loc[
        codes.isin(MANUAL_CODES),
        "BusinessCategory"
    ] = "Manual"

    df.loc[
        codes.isin(OTHER_CHARGE_CODES),
        "BusinessCategory"
    ] = "Other Charge"

    df.loc[
        codes.isin(SPECIAL_ITEM_CODES),
        "BusinessCategory"
    ] = "Special Item"

    # -----------------------------------------
    # C. Calculate transaction amounts
    # -----------------------------------------

    # Example: 3 products x £5 = £15.
    df["LineAmount"] = (
        df["Quantity"] * df["UnitPrice"]
    )

    # Preliminary product sales:
    # Count only identified products with positive
    # quantity and price, excluding cancellations.
    product_sale = (
        (df["BusinessCategory"] == "Product")
        & (df["TransactionType"] == "Sale")
    )

    df["ProductSalesAmount"] = df["LineAmount"].where(
        product_sale, 0.0
    )

    # We will calculate returns and net revenue
    # separately after verifying the business rules.

    return df


# ---------------------------------------------
# STEP 4 — Read, prepare and save our CSV
# ---------------------------------------------

def prepare_data():

    print("Reading original retail dataset...")

    df = pd.read_csv(
        INPUT_FILE,
        encoding="utf-8-sig",
        dtype={
            "InvoiceNo": "string",
            "StockCode": "string",
            "CustomerID": "string"
        },
        parse_dates=["InvoiceDate"]
    )

    original_rows = len(df)

    prepared = classify_transactions(df)

    # Verify that no rows disappeared.
    assert len(prepared) == original_rows

    print("\nTransaction types:")
    print(prepared["TransactionType"].value_counts())

    print("\nBusiness categories:")
    print(prepared["BusinessCategory"].value_counts())

    print("\nTotal rows:", len(prepared))

    # Save the prepared dataset.
    prepared.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    print("\nSUCCESS: Prepared dataset saved!")
    print("File:", OUTPUT_FILE)


# ---------------------------------------------
# STEP 5 — Start the program
# ---------------------------------------------

if __name__ == "__main__":
    prepare_data()
