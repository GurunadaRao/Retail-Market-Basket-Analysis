"""Test suite for the CLI entry point (main.py).

Covers FR-09 (configurable thresholds), FR-22 (parameter reporting),
FR-23 (progress logging), and the guarded mining import that keeps the CLI
usable before C2's module lands (risk R-04).

Owner: C1.
"""

from __future__ import annotations

import logging

import pandas as pd
import pytest

import main
from src.config import (
    DEFAULT_MIN_CONFIDENCE,
    DEFAULT_MIN_LIFT,
    DEFAULT_MIN_SUPPORT,
    MIN_SUPPORT_FLOOR,
)

SAMPLE_CSV = "data/raw/groceries_sample.csv"
FIXTURE_CSV = "tests/fixtures/valid_transactions.csv"


@pytest.fixture
def args():
    """A parsed argument namespace pointing at the small fixture."""
    return main.build_parser().parse_args(
        ["--data", FIXTURE_CSV, "--output-dir", "outputs"]
    )


class _StubEngine:
    """Stand-in for C2's apriori_engine, used to exercise the wired path."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def mine_itemsets(self, matrix, min_support):
        self.calls.append(("mine_itemsets", min_support))
        # Per contract section 6, itemsets live in the index and the frame
        # carries exactly one column, 'support'.
        return pd.DataFrame(
            {"support": [0.75, 0.5]},
            index=pd.Index(
                [frozenset({"Bread", "Milk"}), frozenset({"Milk"})],
                name="itemsets",
            ),
        )

    def generate_rules(self, itemsets, min_confidence):
        self.calls.append(("generate_rules", min_confidence))
        return pd.DataFrame(
            {
                "antecedents": [frozenset({"Milk"}), frozenset({"Bread"})],
                "consequents": [frozenset({"Eggs"}), frozenset({"Milk"})],
                "support": [0.4, 0.5],
                "confidence": [0.3, 0.9],
                "lift": [0.8, 2.0],
            }
        )


# --- FR-09: argument parsing ----------------------------------------------


def test_defaults_come_from_config():
    """FR-09: Defaults are not hard-coded in main.py."""
    args = main.build_parser().parse_args([])

    assert args.min_support == DEFAULT_MIN_SUPPORT
    assert args.min_confidence == DEFAULT_MIN_CONFIDENCE
    assert args.min_lift == DEFAULT_MIN_LIFT


def test_thresholds_are_overridable():
    """FR-09: All three thresholds are settable from the command line."""
    args = main.build_parser().parse_args(
        ["--min-support", "0.2", "--min-confidence", "0.7", "--min-lift", "1.5"]
    )

    assert (args.min_support, args.min_confidence, args.min_lift) == (0.2, 0.7, 1.5)


def test_column_names_are_overridable():
    """Non-default dataset schemas are reachable without code changes."""
    args = main.build_parser().parse_args(["--item-col", "Product", "--txn-col", "Basket"])

    assert args.item_col == "Product"
    assert args.txn_col == "Basket"


@pytest.mark.parametrize(
    "argv",
    [
        ["--min-support", "0"],
        ["--min-support", "-0.1"],
        ["--min-support", "1.5"],
        ["--min-confidence", "1.5"],
        ["--min-confidence", "-0.2"],
        ["--min-lift", "-1"],
        ["--top-n", "0"],
    ],
)
def test_out_of_range_thresholds_are_rejected(argv):
    """Bad thresholds fail fast instead of producing a confusing empty result."""
    args = main.build_parser().parse_args(argv)

    with pytest.raises(ValueError):
        main.validate_thresholds(args)


@pytest.mark.parametrize(
    "argv",
    [["--min-support", "1.0"], ["--min-confidence", "0"], ["--min-lift", "0"]],
)
def test_boundary_thresholds_are_accepted(argv):
    """The extremes of each valid range must not be rejected."""
    args = main.build_parser().parse_args(argv)

    main.validate_thresholds(args)


# --- R-03: low support warning --------------------------------------------


def test_low_min_support_emits_a_warning(args, caplog):
    """R-03: A support below the floor warns about combinatorial blow-up."""
    args.min_support = MIN_SUPPORT_FLOOR / 10

    with caplog.at_level(logging.WARNING, logger="retail_mba"):
        main.run(args)

    assert any("combinatorially" in record.message for record in caplog.records)


def test_default_min_support_emits_no_warning(args, caplog):
    """Normal operation stays quiet."""
    with caplog.at_level(logging.WARNING, logger="retail_mba"):
        main.run(args)

    assert not any("combinatorially" in record.message for record in caplog.records)


# --- R-04: guarded mining import ------------------------------------------


def test_pipeline_runs_without_the_mining_engine(args, monkeypatch, capsys):
    """R-04: A missing C2 module must not crash the ingestion path."""
    monkeypatch.setattr(main, "_load_mining_engine", lambda: None)

    exit_code = main.run(args)

    assert exit_code == 0
    assert "mining stage skipped" in capsys.readouterr().out


def test_require_mining_fails_when_engine_is_missing(args, monkeypatch, capsys):
    """The smoke test can insist on mining rather than accepting a skip."""
    monkeypatch.setattr(main, "_load_mining_engine", lambda: None)
    args.require_mining = True

    exit_code = main.run(args)

    assert exit_code == main.EXIT_MINING_UNAVAILABLE
    assert "ERROR" in capsys.readouterr().err


def test_loader_returns_none_when_engine_is_absent(monkeypatch):
    """The guard returns None rather than propagating ImportError."""
    import sys

    monkeypatch.setitem(sys.modules, "src.apriori_engine", None)

    assert main._load_mining_engine() is None


# --- The wired path, with a stubbed engine --------------------------------


def test_engine_receives_the_configured_thresholds(args, monkeypatch, tmp_path):
    """The engine is called with the user's thresholds, not the defaults."""
    engine = _StubEngine()
    monkeypatch.setattr(main, "_load_mining_engine", lambda: engine)
    args.min_support = 0.25
    args.min_confidence = 0.4
    args.output_dir = str(tmp_path)

    main.run(args)

    assert ("mine_itemsets", 0.25) in engine.calls
    assert ("generate_rules", 0.4) in engine.calls


def test_engine_receives_the_binary_matrix(args, monkeypatch, tmp_path):
    """C2 gets a uint8 transaction-by-item frame, per contract section 5."""
    captured = {}

    class _CapturingEngine(_StubEngine):
        def mine_itemsets(self, matrix, min_support):
            captured["matrix"] = matrix
            return super().mine_itemsets(matrix, min_support)

    monkeypatch.setattr(main, "_load_mining_engine", lambda: _CapturingEngine())
    args.output_dir = str(tmp_path)

    main.run(args)

    matrix = captured["matrix"]
    assert matrix.dtypes.eq("uint8").all()
    assert matrix.index.name == "TransactionID"
    assert matrix.shape == (3, 4)


def test_lift_filter_is_applied_by_the_cli(args, monkeypatch, tmp_path):
    """FR-15: Rules below min_lift are dropped even if the engine kept them."""
    monkeypatch.setattr(main, "_load_mining_engine", lambda: _StubEngine())
    args.min_lift = 1.0
    args.output_dir = str(tmp_path)

    main.run(args)

    exported = pd.read_csv(tmp_path / "rules.csv")
    assert len(exported) == 1
    assert exported.loc[0, "lift"] == pytest.approx(2.0)


def test_rules_are_sorted_by_lift_descending(args, monkeypatch, tmp_path):
    """FR-16: The exported file is ordered regardless of engine output order."""
    monkeypatch.setattr(main, "_load_mining_engine", lambda: _StubEngine())
    args.output_dir = str(tmp_path)

    main.run(args)

    exported = pd.read_csv(tmp_path / "rules.csv")
    assert exported["lift"].is_monotonic_decreasing


def test_both_artefacts_are_written(args, monkeypatch, tmp_path):
    """A complete run produces the itemsets file as well as the rules file."""
    monkeypatch.setattr(main, "_load_mining_engine", lambda: _StubEngine())
    args.output_dir = str(tmp_path)

    main.run(args)

    assert (tmp_path / "rules.csv").is_file()
    assert (tmp_path / "itemsets.csv").is_file()


# --- FR-22 / FR-23: reporting ---------------------------------------------


def test_summary_reports_every_parameter(args, monkeypatch, tmp_path, capsys):
    """FR-22: All parameter values appear in the output for reproducibility."""
    monkeypatch.setattr(main, "_load_mining_engine", lambda: None)
    args.min_support = 0.15
    args.min_confidence = 0.45
    args.min_lift = 1.25
    args.output_dir = str(tmp_path)

    main.run(args)
    out = capsys.readouterr().out

    assert "0.15" in out
    assert "0.45" in out
    assert "1.25" in out
    assert "Item" in out
    assert "TransactionID" in out


def test_summary_reports_counts(args, monkeypatch, tmp_path, capsys):
    """FR-23: The summary carries the shape figures a reviewer needs."""
    monkeypatch.setattr(main, "_load_mining_engine", lambda: None)
    args.output_dir = str(tmp_path)

    main.run(args)
    out = capsys.readouterr().out

    assert "Raw records          : 7" in out
    assert "Clean transactions   : 3" in out
    assert "Distinct items       : 4" in out
    assert "Binary matrix        : 3 x 4" in out


def test_summary_lists_top_items(args, monkeypatch, tmp_path, capsys):
    """FR-18 input: The frequency ordering is visible without opening pandas."""
    monkeypatch.setattr(main, "_load_mining_engine", lambda: None)
    args.output_dir = str(tmp_path)
    args.top_n = 2

    main.run(args)
    out = capsys.readouterr().out

    assert "Top 2 items by frequency" in out
    assert "Milk" in out


def test_step_logging_emitted_by_default(capsys):
    """FR-23: Progress is logged unless --quiet is passed.

    Asserted against captured stderr rather than caplog: main() calls
    basicConfig(force=True), which intentionally replaces pytest's own log
    handler so that --quiet stays authoritative.
    """
    main.main(["--data", FIXTURE_CSV, "--output-dir", "outputs", "--min-support", "0.3"])

    captured = capsys.readouterr()
    assert "Preprocessing complete" in captured.err
    assert "null records dropped" in captured.err


def test_quiet_suppresses_step_logging(capsys):
    """--quiet keeps the log clean while the summary still prints."""
    main.main(["--data", FIXTURE_CSV, "--output-dir", "outputs", "--quiet"])

    captured = capsys.readouterr()
    assert "Preprocessing complete" not in captured.err
    assert "Preprocessing complete" not in captured.out
    assert "RETAIL MARKET BASKET ANALYSIS" in captured.out


# --- Failure paths ---------------------------------------------------------


def test_missing_dataset_returns_failure_code(capsys):
    """A bad path produces exit code 1 and a readable message."""
    exit_code = main.main(["--data", "does/not/exist.csv"])

    assert exit_code == main.EXIT_FAILURE
    assert "ERROR" in capsys.readouterr().err


def test_invalid_thresholds_return_failure_code(capsys):
    """Validation errors surface as exit code 1, not a traceback."""
    exit_code = main.main(["--data", FIXTURE_CSV, "--min-support", "2"])

    assert exit_code == main.EXIT_FAILURE
    assert "min-support" in capsys.readouterr().err


def test_bad_schema_returns_failure_code(capsys):
    """A dataset missing the item column fails cleanly through the CLI."""
    exit_code = main.main(["--data", "tests/fixtures/missing_item_column.csv"])

    assert exit_code == main.EXIT_FAILURE
    assert "missing mandatory column" in capsys.readouterr().err


def test_successful_run_returns_zero():
    """The happy path exits cleanly."""
    assert main.main(["--data", FIXTURE_CSV, "--quiet", "--output-dir", "outputs"]) == 0