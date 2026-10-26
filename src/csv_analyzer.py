
"""
INSIGHTPILOT AI — GENERAL CSV ANALYZER
======================================

PURPOSE
-------
This file helps our application understand CSV datasets.

It can:
1. Read a CSV file.
2. Count rows and columns.
3. Identify column names and data types.
4. Suggest what each column represents.
5. Find missing values.
6. Find duplicate rows.
7. Calculate basic numerical statistics.

THEORY: EXPLORATORY DATA ANALYSIS (EDA)
---------------------------------------
EDA means exploring data before analyzing it.

Example:
Imagine receiving a spreadsheet with 1,000 rows.

Before making charts, we need to know:
- What information does it contain?
- Which columns contain numbers?
- Are any values missing?
- Are any rows duplicated?

That is what our analyzer does.

IMPORTANT
---------
This analyzer does not change or delete original data.
Column roles are suggestions, not guaranteed facts.
"""


# ------------------------------------------------
# STEP 1 — Import Python libraries
# ------------------------------------------------

from pathlib import Path
import pandas as pd


# ------------------------------------------------
# STEP 2 — Identify column roles
# ------------------------------------------------

def identify_column_roles(df):
    """
    Guess what each column represents.

    THEORY:
    A data type tells us how Python stores a value.

    A column role tells us what the value means.

    Example:
    CustomerID = Identifier
    Age = Numeric
    Country = Category/Text
    OrderDate = Date

    These are initial guesses.
    """

    roles = {}

    # Examine every column separately.
    for column in df.columns:

        # Make column names easier to compare.
        name = (
            str(column)
            .lower()
            .replace("_", "")
            .replace(" ", "")
        )

        # Identify columns containing IDs or codes.
        if (
            name.endswith("id")
            or name.endswith("code")
            or name.endswith("number")
            or name.endswith("no")
        ):
            roles[column] = "Identifier"

        # Identify columns likely to contain dates.
        elif (
            "date" in name
            or "timestamp" in name
        ):
            roles[column] = "Date"

        # Identify numerical measurements.
        elif pd.api.types.is_numeric_dtype(df[column]):
            roles[column] = "Numeric"

        # Everything else is classified as text/category.
        else:
            roles[column] = "Category/Text"

    return roles


# ------------------------------------------------
# STEP 3 — Analyze a CSV file
# ------------------------------------------------

def analyze_csv(file_path):
    """
    Read a CSV file and return basic information.

    INPUT:
    file_path = location of the CSV file.

    OUTPUT:
    Dictionary containing the analysis results.

    THEORY: DICTIONARY
    A dictionary stores information as key-value pairs.

    Example:
    {"rows": 100, "columns": 5}
    """

    # Convert the file location into a Path object.
    path = Path(file_path)

    # Make sure the file exists.
    if not path.is_file():
        raise FileNotFoundError(
            f"CSV file not found: {path}"
        )

    # Read the CSV into a Pandas DataFrame.
    df = pd.read_csv(
        path,
        encoding="utf-8-sig",
        low_memory=False
    )

    # Stop if the dataset contains no rows.
    if df.empty:
        raise ValueError(
            "The CSV contains no data rows."
        )

    # Collect information about the dataset.
    results = {

        # Number of records.
        "rows": len(df),

        # Number of columns.
        "columns": len(df.columns),

        # Names of all columns.
        "column_names": df.columns.tolist(),

        # Suggested column meanings.
        "column_roles": identify_column_roles(df),

        # Data types detected by Pandas.
        "data_types": df.dtypes.astype(str).to_dict(),

        # Missing values in each column.
        "missing_values": df.isna().sum().to_dict(),

        # Number of duplicate rows.
        "duplicate_rows": int(df.duplicated().sum()),

        # Statistics for numerical columns.
        "numeric_summary": df.describe().to_dict()
    }

    return results


# ------------------------------------------------
# STEP 4 — Test with our retail dataset
# ------------------------------------------------

if __name__ == "__main__":

    # Find our main project folder.
    project_folder = (
        Path(__file__).resolve().parent.parent
    )

    # Locate our original CSV.
    csv_file = (
        project_folder
        / "data"
        / "online_retail_raw.csv"
    )

    print("Analyzing CSV...")

    # Run our analysis function.
    result = analyze_csv(csv_file)

    print("\n=== DATASET OVERVIEW ===")

    print("Rows:", result["rows"])
    print("Columns:", result["columns"])

    print("\n=== COLUMN NAMES ===")
    print(result["column_names"])

    print("\n=== DATA TYPES ===")
    for column, data_type in result["data_types"].items():
        print(f"{column}: {data_type}")

    print("\n=== SUGGESTED COLUMN ROLES ===")
    for column, role in result["column_roles"].items():
        print(f"{column}: {role}")

    print("\n=== MISSING VALUES ===")
    for column, count in result["missing_values"].items():
        print(f"{column}: {count}")

    print("\n=== DUPLICATE ROWS ===")
    print(result["duplicate_rows"])

    print("\nCSV ANALYSIS COMPLETED!")
