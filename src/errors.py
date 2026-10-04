"""Custom exception hierarchy for the Retail Market Basket Analysis System.

Every error raised deliberately by this codebase derives from
:class:`MarketBasketError`, so downstream modules (C2's mining engine,
C3's dashboard) can catch the whole family with a single ``except`` clause
instead of parsing message strings.

Owner: C1. See docs/INTERFACES.md section 1.
"""


class MarketBasketError(Exception):
    """Base class for every error raised deliberately by this system."""


class SchemaError(MarketBasketError):
    """The input file is structurally unusable.

    Raised when a mandatory column is absent, when the file cannot be
    parsed as delimited text, or when the path does not resolve to a file.
    """


class DataQualityError(MarketBasketError):
    """The input parsed correctly but contains no analysable data.

    Raised when the frame has zero rows, or when a mandatory column is
    entirely null. Threshold tuning cannot rescue such a dataset.
    """


class InterfaceError(MarketBasketError):
    """An upstream module returned a frame that violates a frozen contract.

    This indicates a bug rather than bad input. It must not be caught and
    ignored; it should propagate so the contract violation is visible.
    """


__all__ = [
    "MarketBasketError",
    "SchemaError",
    "DataQualityError",
    "InterfaceError",
]