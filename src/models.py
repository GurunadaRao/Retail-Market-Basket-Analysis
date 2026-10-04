"""Data models and export helpers.

This module is the single writer for every artefact the pipeline emits. Per
decision **D-5**, C2 produces the rule rows and C3 validates them through
:func:`load_rules`, but neither may re-implement the writer -- that would
reintroduce exactly the serialisation drift the contract exists to prevent.

Two things live here:

* Frozen dataclasses (:class:`FrequentItemset`, :class:`Rule`) giving C3 a
  typed surface for the dashboard instead of positional column access (D-9).
* CSV serialisation of the artefacts themselves (FR-17), using the itemset
  format fixed in D-8: ``{Milk + Bread}``.

Owner: C1. See docs/INTERFACES.md sections 7 and 8.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

from .errors import InterfaceError

logger = logging.getLogger(__name__)

#: Delimiter between items inside a serialised itemset (D-8).
ITEM_SEPARATOR = " + "

#: Header written by :func:`export_rules`, in order.
RULE_COLUMNS = ["antecedents", "consequents", "support", "confidence", "lift"]

#: Header written by :func:`export_itemsets`, in order.
ITEMSET_COLUMNS = ["items", "support"]


@dataclass(frozen=True)
class FrequentItemset:
    """A set of items appearing together at least ``support`` of the time."""

    items: frozenset[str]
    support: float

    def __str__(self) -> str:
        return f"{serialize_itemset(self.items)} (support={self.support:.4f})"


@dataclass(frozen=True)
class Rule:
    """A directional association rule with its three quality metrics."""

    antecedents: frozenset[str]
    consequents: frozenset[str]
    support: float
    confidence: float
    lift: float

    def __str__(self) -> str:
        return (
            f"{serialize_itemset(self.antecedents)} -> "
            f"{serialize_itemset(self.consequents)} "
            f"(sup={self.support:.4f} conf={self.confidence:.4f} lift={self.lift:.4f})"
        )


# --- Itemset serialisation -------------------------------------------------


def serialize_itemset(itemset: Iterable[str]) -> str:
    """Render an itemset as ``{Milk + Bread}`` per decision D-8.

    Items are sorted ascending so the output is deterministic regardless of
    ``frozenset`` iteration order -- without this, re-exporting the same rule
    could produce a different cell and break TC-19 reproducibility.
    """
    if isinstance(itemset, str):
        raise InterfaceError(
            "serialize_itemset expects a collection of item names, not a "
            f"bare string: {itemset!r}. Wrap it in a set first."
        )
    return "{" + ITEM_SEPARATOR.join(sorted(str(item) for item in itemset)) + "}"


def deserialize_itemset(text: str) -> frozenset[str]:
    """Parse ``{Milk + Bread}`` back into a frozenset.

    Tolerates surrounding whitespace, a missing pair of braces, and an empty
    cell, which all occur in hand-edited spreadsheets.
    """
    if text is None:
        return frozenset()
    cleaned = str(text).strip()
    if cleaned.startswith("{"):
        cleaned = cleaned[1:]
    if cleaned.endswith("}"):
        cleaned = cleaned[:-1]
    cleaned = cleaned.strip()
    if not cleaned:
        return frozenset()
    return frozenset(part.strip() for part in cleaned.split("+") if part.strip())


# --- Typed views -----------------------------------------------------------


def _as_frozenset(value, context: str) -> frozenset[str]:
    """Coerce a cell or index entry into a frozenset of item names.

    Accepts a real collection, or a serialised string such as
    ``{Milk + Bread}``. Anything else is a contract violation from the
    calling module and is reported as such rather than surfacing as an
    obscure ``TypeError`` deeper in the pipeline.
    """
    if isinstance(value, str):
        return deserialize_itemset(value)
    if isinstance(value, (frozenset, set, list, tuple)):
        return frozenset(str(item) for item in value)
    raise InterfaceError(
        f"{context} must hold item names as a collection or a '{ITEM_SEPARATOR.strip()}'-separated "
        f"string, but found {type(value).__name__}: {value!r}. "
        "Per contract section 6, frequent itemsets belong in the frame's "
        "index (or an 'items' column), alongside a 'support' column."
    )


def itemsets_to_records(itemsets: pd.DataFrame) -> list[FrequentItemset]:
    """Convert a C2 itemsets frame into typed records.

    Accepts either an ``items`` column or an index of itemsets.
    """
    if "support" not in itemsets.columns:
        raise InterfaceError("itemsets frame is missing the 'support' column.")

    if "items" in itemsets.columns:
        raw = itemsets["items"]
    else:
        raw = itemsets.index.to_series()

    return [
        FrequentItemset(
            items=_as_frozenset(value, "Each itemset"),
            support=float(support),
        )
        for value, support in zip(raw, itemsets["support"])
    ]


def rules_to_records(rules: pd.DataFrame) -> list[Rule]:
    """Convert a C2 rules frame into typed records for the dashboard."""
    missing = [name for name in RULE_COLUMNS if name not in rules.columns]
    if missing:
        raise InterfaceError(
            f"rules frame is missing column(s): {', '.join(missing)}. "
            f"Columns found: {list(rules.columns)}."
        )

    records: list[Rule] = []
    for row in rules.itertuples(index=False):
        records.append(
            Rule(
                antecedents=_as_frozenset(row.antecedents, "The 'antecedents' column"),
                consequents=_as_frozenset(row.consequents, "The 'consequents' column"),
                support=float(row.support),
                confidence=float(row.confidence),
                lift=float(row.lift),
            )
        )
    return records


# --- Export ----------------------------------------------------------------


def _ensure_parent(path: str) -> Path:
    """Create the parent directory if it does not already exist."""
    target = Path(path)
    if target.parent and not target.parent.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
    return target


def export_itemsets(itemsets: pd.DataFrame, path: str) -> str:
    """Write frequent itemsets to a UTF-8 CSV and return the path.

    Parameters
    ----------
    itemsets:
        Frame with a ``support`` column and either an ``items`` column or an
        index of itemsets.
    path:
        Destination CSV path. Parent directories are created as needed.

    Returns
    -------
    str
        The path written.
    """
    if itemsets.empty:
        raise InterfaceError("Refusing to export an empty itemsets frame.")

    target = _ensure_parent(path)
    payload = pd.DataFrame(
        {
            "items": [serialize_itemset(record.items) for record in itemsets_to_records(itemsets)],
            "support": itemsets["support"].astype(float),
        }
    )
    payload.to_csv(target, index=False, encoding="utf-8")
    logger.info("Exported %d itemsets to %s", len(payload), target)
    return str(target)


def export_rules(rules: pd.DataFrame, path: str) -> str:
    """Write association rules to a UTF-8 CSV and return the path.

    The written header is exactly ``antecedents, consequents, support,
    confidence, lift`` (contract section 7). Itemsets are serialised per D-8.

    Parameters
    ----------
    rules:
        Frame produced by C2's ``generate_rules``.
    path:
        Destination CSV path. Parent directories are created as needed.

    Returns
    -------
    str
        The path written.
    """
    missing = [name for name in RULE_COLUMNS if name not in rules.columns]
    if missing:
        raise InterfaceError(
            f"Cannot export rules: missing column(s) {', '.join(missing)}. "
            f"Columns found: {list(rules.columns)}."
        )

    target = _ensure_parent(path)
    records = rules_to_records(rules)
    payload = pd.DataFrame(
        {
            "antecedents": [serialize_itemset(record.antecedents) for record in records],
            "consequents": [serialize_itemset(record.consequents) for record in records],
            "support": [record.support for record in records],
            "confidence": [record.confidence for record in records],
            "lift": [record.lift for record in records],
        }
    )
    payload.to_csv(target, index=False, encoding="utf-8")
    logger.info("Exported %d rules to %s", len(payload), target)
    return str(target)


def load_rules(path: str) -> pd.DataFrame:
    """Read a rules CSV written by :func:`export_rules`.

    This is the entry point C3 uses to validate an exported artefact in
    TC-06. Itemset cells are left as strings; use :func:`rules_to_records` to
    obtain frozensets.

    Raises
    ------
    InterfaceError
        If the file is missing or lacks the five contract columns.
    """
    source = Path(path)
    if not source.is_file():
        raise InterfaceError(f"Rules file not found: {source}")

    frame = pd.read_csv(source)
    missing = [name for name in RULE_COLUMNS if name not in frame.columns]
    if missing:
        raise InterfaceError(
            f"Rules file {source} is missing column(s): {', '.join(missing)}. "
            f"Columns found: {list(frame.columns)}."
        )

    logger.info("Loaded %d rules from %s", len(frame), source)
    return frame


__all__ = [
    "ITEM_SEPARATOR",
    "RULE_COLUMNS",
    "ITEMSET_COLUMNS",
    "FrequentItemset",
    "Rule",
    "serialize_itemset",
    "deserialize_itemset",
    "itemsets_to_records",
    "rules_to_records",
    "export_itemsets",
    "export_rules",
    "load_rules",
]