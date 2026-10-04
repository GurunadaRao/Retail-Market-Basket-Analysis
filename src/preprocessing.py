"""M2 -- Preprocessing and binary matrix construction.

Two responsibilities, in strict order:

``clean_data``
    Turn a raw long-format transaction frame into a trustworthy long-format
    frame: no nulls in the mandatory columns, no whitespace, no duplicates,
    everything cast to ``str``. Optional columns are preserved (D-7).

``build_matrix``
    Pivot the cleaned long frame into the dense ``uint8`` transaction-by-item
    binary matrix that the Apriori engine consumes (D-6).

Owner: C1. Satisfies FR-04, FR-05, FR-06, FR-07, FR-08.
See docs/INTERFACES.md section 5 for the frozen contract.
"""

from __future__ import annotations

import logging
import time

import pandas as pd

from .config import DEFAULT_ITEM_COL, DEFAULT_TXN_COL
from .errors import DataQualityError, InterfaceError

logger = logging.getLogger(__name__)


def clean_data(
    df: pd.DataFrame,
    item_col: str = DEFAULT_ITEM_COL,
    txn_col: str = DEFAULT_TXN_COL,
) -> pd.DataFrame:
    """Clean a raw long-format transaction frame.

    Steps, in the order mandated by FR-04 through FR-07:

    1. Remove exact duplicate rows (FR-04).
    2. Drop records whose mandatory columns are null (FR-05).
    3. Strip leading and trailing whitespace from the mandatory columns (FR-06).
    4. Cast the mandatory columns to ``str`` (FR-07).

    Parameters
    ----------
    df:
        Raw frame as returned by :func:`src.data_loader.load_data`.
    item_col:
        Name of the item column. Default ``"Item"``.
    txn_col:
        Name of the transaction identifier column. Default
        ``"TransactionID"``.

    Returns
    -------
    pandas.DataFrame
        Cleaned long-format frame. Optional columns from the source are
        preserved; a copy is returned, so the input is never mutated.

    Raises
    ------
    InterfaceError
        If a mandatory column is absent from ``df``.
    DataQualityError
        If nothing analysable remains after cleaning.
    """
    _require_columns(df, item_col, txn_col)

    started = time.perf_counter()
    cleaned = df.copy()

    before = len(cleaned)
    cleaned = cleaned.drop_duplicates()
    _log_step("duplicate rows removed", before - len(cleaned))

    before = len(cleaned)
    cleaned = cleaned.dropna(subset=[txn_col, item_col])
    _log_step("null records dropped", before - len(cleaned))

    for name in (txn_col, item_col):
        if pd.api.types.is_object_dtype(cleaned[name]) or pd.api.types.is_string_dtype(
            cleaned[name]
        ):
            cleaned[name] = cleaned[name].str.strip()
    _log_step("whitespace trimmed", 0)

    cleaned[txn_col] = cleaned[txn_col].astype(str)
    cleaned[item_col] = cleaned[item_col].astype(str)
    _log_step("mandatory columns cast to str", 0)

    if cleaned.empty:
        raise DataQualityError(
            "No analysable records remain after preprocessing. "
            "Check for null or malformed values in the mandatory columns."
        )

    cleaned = cleaned.reset_index(drop=True)
    logger.info(
        "Preprocessing complete in %.3fs: %d records, %d transactions, %d distinct items",
        time.perf_counter() - started,
        len(cleaned),
        cleaned[txn_col].nunique(),
        cleaned[item_col].nunique(),
    )
    return cleaned


def build_matrix(
    clean_df: pd.DataFrame,
    item_col: str = DEFAULT_ITEM_COL,
    txn_col: str = DEFAULT_TXN_COL,
) -> pd.DataFrame:
    """Pivot cleaned long-format data into a binary transaction-item matrix.

    Parameters
    ----------
    clean_df:
        Output of :func:`clean_data`.
    item_col:
        Name of the item column. Default ``"Item"``.
    txn_col:
        Name of the transaction identifier column. Default
        ``"TransactionID"``.

    Returns
    -------
    pandas.DataFrame
        Dense ``uint8`` frame indexed by transaction (one row per
        transaction, ascending), one column per distinct item (labels sorted
        ascending), containing only 0 and 1. The index is named ``txn_col``.

    Raises
    ------
    InterfaceError
        If ``clean_df`` is missing a mandatory column or still contains nulls
        in either, indicating ``clean_data`` was skipped or mis-called.
    DataQualityError
        If no matrix can be produced.
    """
    _require_columns(clean_df, item_col, txn_col)

    nulls = clean_df[[txn_col, item_col]].isna().any(axis=None)
    if nulls:
        raise InterfaceError(
            f"build_matrix received null values in '{txn_col}' or '{item_col}'. "
            "Call clean_data first; the binary matrix contract requires a "
            "fully populated frame."
        )

    if clean_df.empty:
        raise DataQualityError("Cannot build a binary matrix from an empty frame.")

    started = time.perf_counter()
    matrix = (
        pd.crosstab(clean_df[txn_col], clean_df[item_col])
        .astype("uint8")
        .sort_index(axis=0)
        .sort_index(axis=1)
    )
    matrix.index.name = txn_col
    matrix.columns.name = item_col

    logger.info(
        "Binary matrix built in %.3fs: %d transactions x %d items (%s)",
        time.perf_counter() - started,
        matrix.shape[0],
        matrix.shape[1],
        matrix.dtypes.unique().tolist(),
    )
    return matrix


def item_frequencies(clean_df: pd.DataFrame, item_col: str = DEFAULT_ITEM_COL) -> pd.Series:
    """Return the transaction count per item, sorted descending.

    Convenience helper for the FR-18 frequency chart. C3 owns the plotting;
    this only supplies the numbers.
    """
    if item_col not in clean_df.columns:
        raise InterfaceError(f"Column '{item_col}' is absent from the given frame.")

    counts = clean_df[item_col].value_counts()
    return counts


def _require_columns(df: pd.DataFrame, item_col: str, txn_col: str) -> None:
    """Raise InterfaceError if a mandatory column is missing."""
    missing = [name for name in (txn_col, item_col) if name not in df.columns]
    if missing:
        raise InterfaceError(
            f"Frame is missing mandatory column(s): {', '.join(missing)}. "
            f"Columns found: {list(df.columns)}."
        )


def _log_step(label: str, removed: int) -> None:
    """Log one preprocessing step for FR-23 traceability."""
    logger.info("  %-34s: %d", label, removed)