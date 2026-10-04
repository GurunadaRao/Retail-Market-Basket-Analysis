"""M1 -- Data ingestion and schema validation.

Loads a retail transaction CSV and guarantees, on return, that the frame
carries the mandatory columns required by every downstream module. The
loader never hands back a partially validated frame: if validation fails,
an exception is raised (FR-02, NFR-09).

Owner: C1. Satisfies FR-01, FR-02, FR-03.
See docs/INTERFACES.md section 4 for the frozen contract.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from .config import DEFAULT_ITEM_COL, DEFAULT_TXN_COL
from .errors import DataQualityError, SchemaError

logger = logging.getLogger(__name__)

#: Columns every downstream module relies on being present.
MANDATORY_COLUMNS = (DEFAULT_TXN_COL, DEFAULT_ITEM_COL)


def load_data(
    path: str,
    item_col: str = DEFAULT_ITEM_COL,
    txn_col: str = DEFAULT_TXN_COL,
) -> pd.DataFrame:
    """Load a retail transaction CSV and validate its schema.

    Parameters
    ----------
    path:
        Filesystem path to a delimited text file with a header row.
    item_col:
        Name of the column holding the purchased item. Default ``"Item"``.
    txn_col:
        Name of the column identifying the basket. Default
        ``"TransactionID"``.

    Returns
    -------
    pandas.DataFrame
        The raw frame, guaranteed to contain ``txn_col`` and ``item_col``.

    Raises
    ------
    FileNotFoundError
        If ``path`` does not point to an existing file.
    SchemaError
        If either mandatory column is absent, or the file cannot be parsed
        as delimited text.
    DataQualityError
        If the frame has zero rows, or ``item_col`` is entirely null.
    """
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Dataset not found: {source}")

    frame = _read_csv(source)
    _check_columns(frame, item_col, txn_col)
    _check_quality(frame, item_col)

    _report(source, frame, item_col, txn_col)
    return frame


def _read_csv(source: Path) -> pd.DataFrame:
    """Parse the file, converting any parser failure into a SchemaError."""
    try:
        return pd.read_csv(source)
    except pd.errors.EmptyDataError as exc:
        raise SchemaError(f"Dataset is empty: {source}") from exc
    except (pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise SchemaError(
            f"Dataset could not be parsed as delimited text: {source} ({exc})"
        ) from exc


def _check_columns(frame: pd.DataFrame, item_col: str, txn_col: str) -> None:
    """Raise SchemaError if any mandatory column is missing."""
    missing = [name for name in (txn_col, item_col) if name not in frame.columns]
    if missing:
        raise SchemaError(
            f"Dataset is missing mandatory column(s): {', '.join(missing)}. "
            f"Columns found: {list(frame.columns)}. "
            f"Pass item_col/txn_col to override the expected names."
        )


def _check_quality(frame: pd.DataFrame, item_col: str) -> None:
    """Raise DataQualityError when the frame holds nothing analysable."""
    if frame.empty:
        raise DataQualityError(
            "Dataset contains a header row but no transaction records."
        )
    if frame[item_col].isna().all():
        raise DataQualityError(
            f"Column '{item_col}' is entirely null; no analysable items present."
        )


def _report(
    source: Path,
    frame: pd.DataFrame,
    item_col: str,
    txn_col: str,
) -> None:
    """Log the ingestion summary required by FR-03 and FR-23."""
    logger.info("Loaded %s", source)
    logger.info("  records          : %d", len(frame))
    logger.info("  distinct items   : %d", frame[item_col].nunique())
    logger.info(
        "  transactions     : %d", frame[txn_col].nunique()
    )