"""Test suite for M1 (src/data_loader.py).

Covers the loader's slice of the SRS test plan:
  TC-01 valid CSV load
  TC-02 invalid CSV / missing mandatory column
  TC-07 empty and all-null dataset handling

Owner: C1.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import pytest

from src.data_loader import load_data
from src.errors import DataQualityError, MarketBasketError, SchemaError

FIXTURES = Path(__file__).parent / "fixtures"
VALID_CSV = FIXTURES / "valid_transactions.csv"
MISSING_ITEM_CSV = FIXTURES / "missing_item_column.csv"
EMPTY_CSV = FIXTURES / "empty_headers_only.csv"
ALL_NULL_CSV = FIXTURES / "all_null_items.csv"
SAMPLE_CSV = Path(__file__).resolve().parents[1] / "data" / "raw" / "groceries_sample.csv"


# --- TC-01: valid CSV loads correctly --------------------------------------


def test_tc01_valid_csv_loads():
    """TC-01: A well-formed CSV loads and keeps every row."""
    frame = load_data(str(VALID_CSV))

    assert isinstance(frame, pd.DataFrame)
    assert len(frame) == 7
    assert list(frame.columns) == ["TransactionID", "Item"]


def test_tc01_mandatory_columns_present():
    """TC-01: Both mandatory columns are guaranteed on return."""
    frame = load_data(str(VALID_CSV))

    assert "TransactionID" in frame.columns
    assert "Item" in frame.columns


def test_tc01_reports_transaction_and_item_counts(caplog):
    """TC-01 / FR-03: record, transaction and item counts are reported."""
    with caplog.at_level(logging.INFO, logger="src.data_loader"):
        load_data(str(VALID_CSV))

    logged = caplog.text
    assert "records          : 7" in logged
    assert "transactions     : 3" in logged
    assert "distinct items   : 4" in logged


def test_tc01_reference_dataset_loads():
    """The shipped reference dataset in data/raw must remain loadable."""
    frame = load_data(str(SAMPLE_CSV))

    assert len(frame) > 0
    assert frame["Item"].nunique() >= 10


def test_tc01_column_names_are_overridable(tmp_path):
    """A dataset using non-default column names loads via explicit arguments."""
    csv = tmp_path / "alt.csv"
    csv.write_text("basket,product\n1,Milk\n1,Bread\n2,Coffee\n", encoding="utf-8")

    frame = load_data(str(csv), item_col="product", txn_col="basket")

    assert len(frame) == 3


# --- TC-02: invalid CSV handling ------------------------------------------


def test_tc02_missing_file_raises_filenotfound(tmp_path):
    """TC-02: A non-existent path fails loudly with the offending path."""
    missing = tmp_path / "nope.csv"

    with pytest.raises(FileNotFoundError, match="Dataset not found"):
        load_data(str(missing))


def test_tc02_directory_path_raises_filenotfound(tmp_path):
    """A directory is not a dataset."""
    with pytest.raises(FileNotFoundError):
        load_data(str(tmp_path))


def test_tc02_missing_item_column_raises_schemaerror():
    """TC-02: A CSV without the item column raises SchemaError naming it."""
    with pytest.raises(SchemaError) as excinfo:
        load_data(str(MISSING_ITEM_CSV))

    message = str(excinfo.value)
    assert "Item" in message
    assert "missing mandatory column" in message


def test_tc02_missing_transaction_column_raises_schemaerror():
    """TC-02: A CSV without the transaction column is also rejected."""
    csv = FIXTURES / "valid_transactions.csv"

    with pytest.raises(SchemaError, match="NotPresent"):
        load_data(str(csv), txn_col="NotPresent")


def test_tc02_schemaerror_is_a_marketbasketerror():
    """Decision D-3: callers may catch the whole family with one clause."""
    with pytest.raises(MarketBasketError):
        load_data(str(MISSING_ITEM_CSV))


def test_tc02_error_message_lists_columns_found():
    """The message must help the user fix the dataset, not just complain."""
    with pytest.raises(SchemaError) as excinfo:
        load_data(str(MISSING_ITEM_CSV))

    assert "Product" in str(excinfo.value)


# --- TC-07: empty and all-null datasets ------------------------------------


def test_tc07_headers_only_csv_raises_dataqualityerror():
    """TC-07: A headers-only CSV raises rather than returning an empty frame."""
    with pytest.raises(DataQualityError, match="no transaction records"):
        load_data(str(EMPTY_CSV))


def test_tc07_all_null_item_column_raises_dataqualityerror():
    """TC-07: An entirely null item column is rejected."""
    with pytest.raises(DataQualityError, match="entirely null"):
        load_data(str(ALL_NULL_CSV))


def test_tc07_dataqualityerror_is_a_marketbasketerror():
    """Decision D-3: DataQualityError shares the common base class."""
    with pytest.raises(MarketBasketError):
        load_data(str(EMPTY_CSV))


def test_tc07_partially_null_column_is_accepted(tmp_path):
    """Only an entirely null column is fatal; sparse nulls are cleaned later."""
    csv = tmp_path / "sparse.csv"
    csv.write_text("TransactionID,Item\n1,Milk\n2,\n3,Bread\n", encoding="utf-8")

    frame = load_data(str(csv))

    assert len(frame) == 3
    assert frame["Item"].isna().sum() == 1


def test_tc07_zero_byte_file_raises_schemaerror(tmp_path):
    """A zero-byte file has no header at all, so it is a schema failure."""
    csv = tmp_path / "zero.csv"
    csv.write_text("", encoding="utf-8")

    with pytest.raises(MarketBasketError):
        load_data(str(csv))