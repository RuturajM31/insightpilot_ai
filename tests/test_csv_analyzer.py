
"""
INSIGHTPILOT AI — CSV ANALYZER TESTS
====================================

PURPOSE:
Check that our CSV analyzer works correctly.

THEORY:
Automated tests compare actual results with
answers we already know are correct.
"""

from pathlib import Path
import sys

import pandas as pd
import pytest


# Allow Python to find our analyzer.
PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "src"))

from csv_analyzer import analyze_csv, identify_column_roles


# Test 1: Recognize different column types.
def test_column_roles():

    df = pd.DataFrame({
        "CustomerID": [101, 102],
        "Age": [25, 30],
        "OrderDate": ["2026-01-01", "2026-01-02"],
        "Country": ["Germany", "France"]
    })

    roles = identify_column_roles(df)

    assert roles["CustomerID"] == "Identifier"
    assert roles["Age"] == "Numeric"
    assert roles["OrderDate"] == "Date"
    assert roles["Country"] == "Category/Text"


# Test 2: Count rows and columns.
def test_csv_shape(tmp_path):

    file = tmp_path / "sample.csv"

    file.write_text(
        "Product,Quantity\nPen,2\nBook,3\n",
        encoding="utf-8"
    )

    result = analyze_csv(file)

    assert result["rows"] == 2
    assert result["columns"] == 2


# Test 3: Detect missing values.
def test_missing_values(tmp_path):

    file = tmp_path / "missing.csv"

    file.write_text(
        "Name,Age\nAlice,25\nBob,\n",
        encoding="utf-8"
    )

    result = analyze_csv(file)

    assert result["missing_values"]["Age"] == 1


# Test 4: Detect duplicate rows.
def test_duplicates(tmp_path):

    file = tmp_path / "duplicates.csv"

    file.write_text(
        "Product,Quantity\nPen,2\nPen,2\n",
        encoding="utf-8"
    )

    result = analyze_csv(file)

    assert result["duplicate_rows"] == 1


# Test 5: Reject a missing file.
def test_missing_file(tmp_path):

    file = tmp_path / "does_not_exist.csv"

    with pytest.raises(FileNotFoundError):
        analyze_csv(file)


# Test 6: Reject a CSV with headers but no data.
def test_empty_csv(tmp_path):

    file = tmp_path / "empty.csv"

    file.write_text(
        "Product,Quantity\n",
        encoding="utf-8"
    )

    with pytest.raises(ValueError):
        analyze_csv(file)
