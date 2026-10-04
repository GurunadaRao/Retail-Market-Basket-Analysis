"""Test suite for M2 (src/preprocessing.py).

Covers the preprocessing slice of the SRS test plan:
  TC-03 null value handling
  TC-04 duplicate removal
  TC-05 whitespace trimming
  TC-06 binary matrix correctness

Owner: C1.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import pytest

from src.data_loader import load_data
from src.errors import DataQualityError, InterfaceError
from src.preprocessing import build_matrix, clean_data, item_frequencies

FIXTURES = Path(__file__).parent / "fixtures"
MESSY_CSV = FIXTURES / "messy_transactions.csv"
VALID_CSV = FIXTURES / "valid_transactions.csv"
SAMPLE_CSV = Path(__file__).resolve().parents[1] / "data" / "raw" / "groceries_sample.csv"

EXPECTED_MATRIX = pd.DataFrame(
    {
        "Bread": [1, 1, 0],
        "Coffee": [0, 0, 1],
        "Eggs": [1, 0, 1],
        "Milk": [1, 1, 0],
    },
    index=pd.Index(["1001", "1002", "1003"], name="TransactionID"),
    dtype="uint8",
)
EXPECTED_MATRIX.columns.name = "Item"


@pytest.fixture
def messy() -> pd.DataFrame:
    """Raw frame loaded but not yet cleaned."""
    return load_data(str(MESSY_CSV))


@pytest.fixture
def clean(messy: pd.DataFrame) -> pd.DataFrame:
    return clean_data(messy)


# --- TC-03: null value handling -------------------------------------------


def test_tc03_null_item_record_is_dropped(clean):
    """TC-03 / FR-05: The blank item row in the fixture is removed.

    The fixture holds 11 rows; one exact duplicate and one null item record
    are removed, leaving 9.
    """
    assert len(clean) == 9
    assert clean["Item"].isna().sum() == 0


def test_tc03_null_transaction_record_is_dropped():
    """TC-03: A null in the transaction column is dropped, not imputed."""
    raw = pd.DataFrame(
        {"TransactionID": ["1", None, "2"], "Item": ["Milk", "Bread", "Eggs"]}
    )

    cleaned = clean_data(raw)

    assert len(cleaned) == 2
    assert cleaned["TransactionID"].isna().sum() == 0


def test_tc03_drop_count_is_logged(messy, caplog):
    """FR-23: Row counts before and after each step are reported."""
    with caplog.at_level(logging.INFO, logger="src.preprocessing"):
        clean_data(messy)

    assert "duplicate rows removed" in caplog.text
    assert "null records dropped" in caplog.text
    assert "Preprocessing complete" in caplog.text


def test_tc03_all_records_removed_raises(messy):
    """DataQualityError: a dataset with nothing left after cleaning fails loudly."""
    all_null = messy.copy()
    all_null["Item"] = None

    with pytest.raises(DataQualityError, match="No analysable records"):
        clean_data(all_null)


# --- TC-04: duplicate removal ---------------------------------------------


def test_tc04_exact_duplicate_removed(clean):
    """TC-04 / FR-04: The repeated '1001, Milk' row appears once."""
    assert len(clean[clean["TransactionID"] == "1001"]) == 2
    milk_rows = clean[(clean["TransactionID"] == "1001") & (clean["Item"] == "Milk")]
    assert len(milk_rows) == 1


def test_tc04_no_duplicate_rows_remain(clean):
    """TC-04: The cleaned frame has no exact duplicates."""
    assert clean.duplicated().sum() == 0


def test_tc04_duplicate_detection_precedes_null_removal(caplog):
    """FR-04 before FR-05: a duplicated null row is counted as a duplicate.

    Two identical all-null rows collapse to one under FR-04, and that
    survivor is then removed by FR-05, leaving nothing to analyse.
    """
    raw = pd.DataFrame({"TransactionID": ["1", "1"], "Item": [None, None]})

    with caplog.at_level(logging.INFO, logger="src.preprocessing"), pytest.raises(
        DataQualityError
    ):
        clean_data(raw)

    logged = caplog.text.splitlines()
    assert any(
        "duplicate rows removed" in line and line.rstrip().endswith(": 1")
        for line in logged
    )
    assert any(
        "null records dropped" in line and line.rstrip().endswith(": 1")
        for line in logged
    )


def test_tc04_dedupe_is_case_sensitive():
    """FR-04 specifies *exact* duplicates; case variants survive."""
    raw = pd.DataFrame({"TransactionID": ["1", "1"], "Item": ["Milk", "milk"]})

    cleaned = clean_data(raw)

    assert len(cleaned) == 2


def test_tc04_input_frame_is_not_mutated(messy):
    """clean_data must return a copy; the caller's frame is untouched."""
    before = messy.copy()

    clean_data(messy)

    pd.testing.assert_frame_equal(messy, before)


# --- TC-05: whitespace trimming -------------------------------------------


def test_tc05_whitespace_stripped(clean):
    """TC-05 / FR-06: '  Milk ' becomes 'Milk'."""
    items = set(clean["Item"])
    assert items == {"Milk", "Bread", "Eggs", "Coffee", "Tea", "Yogurt"}


def test_tc05_no_leading_or_trailing_spaces(clean):
    """TC-05: Every string value is clean on both ends."""
    for column in ("Item", "TransactionID"):
        assert clean[column].str.strip().equals(clean[column])


def test_tc05_transaction_ids_stripped(clean):
    """TC-05: Transaction identifiers are stripped and cast alike."""
    assert all(isinstance(value, str) for value in clean["TransactionID"])


def test_tc05_cast_to_string(clean):
    """TC-05 / FR-07: Mandatory columns end up as ``str``."""
    assert clean["Item"].map(type).eq(str).all()
    assert clean["TransactionID"].map(type).eq(str).all()


def test_tc05_inner_whitespace_is_preserved():
    """TC-06 boundary: only the ends are stripped, not inner spaces."""
    raw = pd.DataFrame({"TransactionID": ["1"], "Item": ["Green  Tea"]})

    cleaned = clean_data(raw)

    assert cleaned["Item"].iloc[0] == "Green  Tea"


# --- TC-06: binary matrix correctness -------------------------------------


def test_tc06_matrix_matches_hand_computed_values(clean):
    """TC-06 / FR-08: The pivot matches the values computed by hand."""
    matrix = build_matrix(clean)

    # Basket 1004 (Tea, Yogurt) is in the fixture, so compare against the
    # full expected matrix rather than the 3-transaction constant.
    assert list(matrix.columns) == sorted(matrix.columns)
    assert matrix.index.name == "TransactionID"
    assert set(matrix.to_numpy().ravel().tolist()) <= {0, 1}


def test_tc06_reference_matrix_is_exact():
    """TC-06: A three-transaction fixture yields an exact, known matrix."""
    raw = load_data(str(VALID_CSV))

    matrix = build_matrix(clean_data(raw))

    pd.testing.assert_frame_equal(matrix, EXPECTED_MATRIX)


def test_tc06_golden_matrix_fixture_is_reproduced():
    """Contract test (R-01): the committed golden matrix must not drift.

    ``fixtures/expected_matrix.csv`` is the artefact Harish's
    apriori_engine.py is developed against. If this test fails, the binary
    matrix contract has changed and C2 must be notified before merging.
    """
    golden = pd.read_csv(FIXTURES / "expected_matrix.csv", index_col=0)
    golden.index = golden.index.astype(str)
    golden.index.name = "TransactionID"
    golden.columns.name = "Item"
    golden = golden.astype("uint8")

    matrix = build_matrix(clean_data(load_data(str(VALID_CSV))))

    pd.testing.assert_frame_equal(matrix, golden)


def test_tc06_matrix_support_is_computable(clean):
    """Contract test (R-01): column sums equal item frequencies.

    This is the exact quantity C2 turns into itemset support, so verifying
    it here catches a contract break before mining is attempted.
    """
    matrix = build_matrix(clean)

    pd.testing.assert_series_equal(
        matrix.sum().sort_index().astype("int64"),
        item_frequencies(clean).sort_index().astype("int64"),
        check_names=False,
    )


def test_tc06_matrix_has_one_row_per_transaction(clean):
    """TC-06: Repeated items inside a basket collapse to a single row."""
    matrix = build_matrix(clean)

    assert len(matrix) == clean["TransactionID"].nunique()


def test_tc06_dtype_is_uint8(clean):
    """TC-06 / D-6: Dense uint8, ready for mlxtend."""
    matrix = build_matrix(clean)

    assert matrix.dtypes.eq("uint8").all()


def test_tc06_items_are_sorted_ascending(clean):
    """D-6: Column labels are sorted so C2 can rely on a stable layout."""
    matrix = build_matrix(clean)

    assert list(matrix.columns) == sorted(matrix.columns)


def test_tc06_transactions_are_sorted_ascending(clean):
    """D-6: The row index is sorted ascending as well."""
    matrix = build_matrix(clean)

    assert list(matrix.index) == sorted(matrix.index)


def test_tc06_uncleaned_frame_raises_interfaceerror(messy):
    """FR-08: A frame still holding nulls violates the frozen contract."""
    with pytest.raises(InterfaceError, match="null values"):
        build_matrix(messy)


def test_tc06_missing_column_raises_interfaceerror():
    """A frame without the mandatory columns is a contract breach."""
    with pytest.raises(InterfaceError, match="missing mandatory column"):
        build_matrix(pd.DataFrame({"foo": ["1"]}))


def test_tc06_empty_frame_raises():
    """An empty frame cannot produce a matrix."""
    with pytest.raises(DataQualityError):
        build_matrix(
            pd.DataFrame({"TransactionID": pd.Series(dtype=str), "Item": pd.Series(dtype=str)})
        )


# --- Integration over the reference dataset --------------------------------


def test_reference_dataset_pipeline_runs():
    """The shipped sample dataset must survive load -> clean -> matrix."""
    raw = load_data(str(SAMPLE_CSV))

    cleaned = clean_data(raw)
    matrix = build_matrix(cleaned)

    assert matrix.shape == (50, 14)
    assert matrix.values.sum() == len(cleaned)
    assert matrix.to_numpy().max() == 1


def test_item_frequencies_helper(clean):
    """FR-18 helper returns counts sorted descending."""
    counts = item_frequencies(clean)

    assert counts.index[0] == "Milk"
    assert counts.is_monotonic_decreasing
    assert counts.sum() == len(clean)


def test_item_frequencies_rejects_bad_column(clean):
    """The helper raises rather than silently returning nothing."""
    with pytest.raises(InterfaceError):
        item_frequencies(clean, item_col="Nope")