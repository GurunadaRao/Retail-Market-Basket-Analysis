"""CLI entry point for the Retail Market Basket Analysis pipeline.

Wires the owned modules together:

    load_data -> clean_data -> build_matrix -> [mine_itemsets -> generate_rules] -> export

The mining stage belongs to C2 (``src/apriori_engine.py``). Until that module
lands, the CLI still runs the full ingestion and preprocessing path and says
plainly that mining was skipped, rather than crashing on ImportError (risk
R-04). Pass ``--require-mining`` to turn that situation into a failure, which
is what the weekly smoke test should use once C2's module is merged.

Owner: C1. Satisfies FR-09, FR-17, FR-22, FR-23.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from src.config import (
    DEFAULT_ITEM_COL,
    DEFAULT_MIN_CONFIDENCE,
    DEFAULT_MIN_LIFT,
    DEFAULT_MIN_SUPPORT,
    DEFAULT_TXN_COL,
    ITSETS_FILENAME,
    MIN_SUPPORT_FLOOR,
    RULES_FILENAME,
)
from src.data_loader import load_data
from src.errors import MarketBasketError
from src.models import export_itemsets, export_rules
from src.preprocessing import build_matrix, clean_data, item_frequencies

logger = logging.getLogger("retail_mba")

LINE = "=" * 62
THIN = "-" * 62

#: Exit code used when --require-mining is set but the engine is missing.
EXIT_MINING_UNAVAILABLE = 3
#: Exit code used for a user-facing pipeline failure.
EXIT_FAILURE = 1


def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser (FR-09)."""
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Retail Market Basket Analysis -- Apriori association rule mining.",
    )
    parser.add_argument(
        "--data",
        default="data/raw/groceries_sample.csv",
        help="Path to the transaction CSV (default: %(default)s)",
    )
    parser.add_argument(
        "--min-support",
        type=float,
        default=DEFAULT_MIN_SUPPORT,
        help="Minimum itemset support, 0 < x <= 1 (default: %(default)s)",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=DEFAULT_MIN_CONFIDENCE,
        help="Minimum rule confidence, 0 <= x <= 1 (default: %(default)s)",
    )
    parser.add_argument(
        "--min-lift",
        type=float,
        default=DEFAULT_MIN_LIFT,
        help="Minimum rule lift, x >= 0 (default: %(default)s)",
    )
    parser.add_argument(
        "--item-col",
        default=DEFAULT_ITEM_COL,
        help="Name of the item column (default: %(default)s)",
    )
    parser.add_argument(
        "--txn-col",
        default=DEFAULT_TXN_COL,
        help="Name of the transaction column (default: %(default)s)",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Directory for exported artefacts (default: %(default)s)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="How many top items to list in the summary (default: %(default)s)",
    )
    parser.add_argument(
        "--require-mining",
        action="store_true",
        help="Exit non-zero if the Apriori engine (C2's module) is unavailable",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the per-step logging; print only the summary",
    )
    return parser


def validate_thresholds(args: argparse.Namespace) -> None:
    """Reject out-of-range thresholds before any work is done.

    Failing fast matters here: an invalid min_support would otherwise surface
    as a confusing empty rule set much later (risk R-03).
    """
    if not 0 < args.min_support <= 1:
        raise ValueError(f"--min-support must be in (0, 1], got {args.min_support}.")
    if not 0 <= args.min_confidence <= 1:
        raise ValueError(
            f"--min-confidence must be in [0, 1], got {args.min_confidence}."
        )
    if args.min_lift < 0:
        raise ValueError(f"--min-lift must be >= 0, got {args.min_lift}.")
    if args.top_n < 1:
        raise ValueError(f"--top-n must be >= 1, got {args.top_n}.")


def _load_mining_engine():
    """Import C2's engine, returning ``None`` if it is not present yet.

    Imported lazily so the ingestion and preprocessing path stays usable
    before ``src/apriori_engine.py`` is merged.
    """
    try:
        from src import apriori_engine
    except ImportError:
        return None
    return apriori_engine


def run(args: argparse.Namespace) -> int:
    """Execute the pipeline described by ``args``.

    Returns
    -------
    int
        ``0`` on success, ``1`` on a pipeline failure, ``3`` when
        ``--require-mining`` was set but the engine is unavailable.
    """
    validate_thresholds(args)

    if args.min_support < MIN_SUPPORT_FLOOR:
        logger.warning(
            "min_support %.5f is below the floor %.5f. Apriori candidate "
            "generation grows combinatorially and may not terminate in "
            "reasonable time (risk R-03).",
            args.min_support,
            MIN_SUPPORT_FLOOR,
        )

    started = time.perf_counter()

    raw = load_data(args.data, item_col=args.item_col, txn_col=args.txn_col)
    cleaned = clean_data(raw, item_col=args.item_col, txn_col=args.txn_col)
    matrix = build_matrix(cleaned, item_col=args.item_col, txn_col=args.txn_col)

    engine = _load_mining_engine()
    itemsets = None
    rules = None

    if engine is None:
        message = (
            "src/apriori_engine.py is not available yet (owned by C2). "
            "Ingestion and preprocessing completed; mining was skipped."
        )
        if args.require_mining:
            print(f"{LINE}\nERROR: {message}\n{LINE}", file=sys.stderr)
            return EXIT_MINING_UNAVAILABLE
        logger.warning(message)
    else:
        itemsets = engine.mine_itemsets(matrix, min_support=args.min_support)
        rules = engine.generate_rules(itemsets, min_confidence=args.min_confidence)
        rules = _apply_lift_filter(rules, args.min_lift)

    output_dir = Path(args.output_dir)
    if itemsets is not None:
        export_itemsets(itemsets, str(output_dir / ITSETS_FILENAME))
    if rules is not None:
        export_rules(rules, str(output_dir / RULES_FILENAME))

    elapsed = time.perf_counter() - started
    print_summary(args, raw, cleaned, matrix, itemsets, rules, elapsed, engine is None)
    return 0


def _apply_lift_filter(rules, min_lift: float):
    """Filter rules by lift and sort them, if the engine did not already.

    Kept here so the CLI's guarantees hold even if C2 returns an unsorted
    frame. FR-15 and FR-16.
    """
    if rules is None or rules.empty:
        return rules
    filtered = rules[rules["lift"] >= min_lift]
    return filtered.sort_values(
        by=["lift", "confidence"], ascending=[False, False]
    ).reset_index(drop=True)


def print_summary(
    args: argparse.Namespace,
    raw,
    cleaned,
    matrix,
    itemsets,
    rules,
    elapsed: float,
    mining_skipped: bool,
) -> None:
    """Print the run summary required by FR-22 and FR-23."""
    print()
    print(LINE)
    print(" RETAIL MARKET BASKET ANALYSIS")
    print(LINE)
    print(f" Dataset              : {args.data}")
    print(f" Raw records          : {len(raw)}")
    print(f" Clean records        : {len(cleaned)}")
    print(f" Clean transactions   : {cleaned[args.txn_col].nunique()}")
    print(f" Distinct items       : {cleaned[args.item_col].nunique()}")
    print(f" Binary matrix        : {matrix.shape[0]} x {matrix.shape[1]} ({matrix.dtypes.unique()[0]})")
    print(THIN)
    print(" Parameters (FR-22)")
    print(f"   min support        : {args.min_support}")
    print(f"   min confidence     : {args.min_confidence}")
    print(f"   min lift           : {args.min_lift}")
    print(f"   item column        : {args.item_col}")
    print(f"   txn column         : {args.txn_col}")
    print(THIN)
    print(" Results")
    print(f"   frequent itemsets  : {0 if itemsets is None else len(itemsets)}")
    print(f"   association rules  : {0 if rules is None else len(rules)}")
    print(f"   wall clock         : {elapsed:.3f}s")
    print(THIN)
    print(f" Top {args.top_n} items by frequency (FR-18 input):")
    frequencies = item_frequencies(cleaned, item_col=args.item_col)
    for item, count in frequencies.head(args.top_n).items():
        print(f"   {item:<20}: {count:>6}  ({count / len(cleaned):.4f})")

    if mining_skipped:
        print(THIN)
        print(" NOTE: mining stage skipped -- src/apriori_engine.py not yet merged.")
    elif rules is not None and not rules.empty:
        print(THIN)
        print(f" Top {min(args.top_n, len(rules))} rules by lift:")
        for record in rules.head(args.top_n).itertuples(index=False):
            print(
                f"   {str(record.antecedents):<26} -> {str(record.consequents):<18} "
                f"sup={record.support:.4f} conf={record.confidence:.4f} lift={record.lift:.4f}"
            )
    print(LINE)


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and run the pipeline."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # force=True makes the level authoritative on every invocation. Without it
    # basicConfig is a no-op after the first call, so --quiet would silently
    # stop working on any subsequent run in the same process. The cost is
    # that any pre-existing handler (including pytest's caplog) is closed,
    # so the tests assert against captured stderr instead.
    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(levelname)-8s %(message)s",
        force=True,
    )

    try:
        return run(args)
    except FileNotFoundError as exc:
        # load_data raises a plain FileNotFoundError per contract section 4.
        print(f"{LINE}\nERROR: {exc}\n{LINE}", file=sys.stderr)
        return EXIT_FAILURE
    except MarketBasketError as exc:
        print(f"{LINE}\nERROR: {exc}\n{LINE}", file=sys.stderr)
        return EXIT_FAILURE
    except ValueError as exc:
        print(f"{LINE}\nERROR: {exc}\n{LINE}", file=sys.stderr)
        return EXIT_FAILURE


if __name__ == "__main__":
    raise SystemExit(main())