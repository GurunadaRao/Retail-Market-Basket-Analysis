"""Test suite for M5 data models and exporters (src/models.py).

Covers the export slice of the SRS test plan:
  TC-14 rule export writes correct headers and row count
  TC-19 reproducibility: two identical runs produce identical files

Also guards decisions D-5, D-8 and D-9.

Owner: C1.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.errors import InterfaceError
from src.models import (
    FrequentItemset,
    Rule,
    deserialize_itemset,
    export_itemsets,
    export_rules,
    itemsets_to_records,
    load_rules,
    rules_to_records,
    serialize_itemset,
)

RULE_COLUMNS = ["antecedents", "consequents", "support", "confidence", "lift"]


@pytest.fixture
def rules() -> pd.DataFrame:
    """A rules frame shaped exactly as C2's generate_rules must return."""
    return pd.DataFrame(
        {
            "antecedents": [
                frozenset({"Butter"}),
                frozenset({"Coffee"}),
                frozenset({"Milk", "Bread"}),
            ],
            "consequents": [
                frozenset({"Bread"}),
                frozenset({"Sugar"}),
                frozenset({"Eggs"}),
            ],
            "support": [0.0561, 0.0523, 0.0612],
            "confidence": [0.3120, 0.3010, 0.3290],
            "lift": [2.714, 2.586, 2.481],
        }
    )


@pytest.fixture
def itemsets() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "items": [
                frozenset({"Butter"}),
                frozenset({"Bread"}),
                frozenset({"Milk", "Bread"}),
            ],
            "support": [0.18, 0.24, 0.12],
        }
    )


# --- D-8: itemset serialisation ------------------------------------------


def test_d08_serializes_with_plus_separator():
    """D-8: Items are joined by ' + ' inside braces."""
    assert serialize_itemset({"Milk", "Bread"}) == "{Bread + Milk}"


def test_d08_serialisation_is_sorted_and_deterministic():
    """D-8 / NFR-10: frozenset ordering must never change the output."""
    forward = serialize_itemset(frozenset({"Butter", "Apple", "Cherry"}))
    reverse = serialize_itemset(frozenset({"Cherry", "Butter", "Apple"}))

    assert forward == reverse == "{Apple + Butter + Cherry}"


def test_d08_single_item_roundtrip():
    """A single-item itemset still gets braces."""
    assert serialize_itemset({"Milk"}) == "{Milk}"
    assert deserialize_itemset("{Milk}") == frozenset({"Milk"})


def test_d08_deserialize_tolerates_whitespace_and_missing_braces():
    """Hand-edited spreadsheets lose braces and padding; parsing must cope."""
    assert deserialize_itemset("  Bread + Milk  ") == frozenset({"Bread", "Milk"})
    assert deserialize_itemset("Milk") == frozenset({"Milk"})
    assert deserialize_itemset("{}") == frozenset()
    assert deserialize_itemset("") == frozenset()
    assert deserialize_itemset(None) == frozenset()


def test_d08_roundtrip_is_lossless():
    """Serialise then parse returns the original set."""
    original = frozenset({"Yogurt", "Milk", "Bread"})

    assert deserialize_itemset(serialize_itemset(original)) == original


def test_d08_bare_string_is_rejected():
    """Passing a string would iterate characters; that is a bug, not input."""
    with pytest.raises(InterfaceError, match="bare string"):
        serialize_itemset("Milk")


# --- D-9: typed records ---------------------------------------------------


def test_d09_rules_to_records_preserves_metrics(rules):
    """Typed conversion keeps all three metrics intact."""
    records = rules_to_records(rules)

    assert len(records) == 3
    assert all(isinstance(record, Rule) for record in records)
    assert records[0].lift == pytest.approx(2.714)
    assert records[2].antecedents == frozenset({"Milk", "Bread"})


def test_d09_records_are_immutable(rules):
    """Dataclasses are frozen, so a record cannot drift after handoff."""
    record = rules_to_records(rules)[0]

    with pytest.raises(Exception):
        record.lift = 99.0


def test_d09_itemsets_to_records(itemsets):
    """Typed itemsets carry their support value."""
    records = itemsets_to_records(itemsets)

    assert len(records) == 3
    assert all(isinstance(record, FrequentItemset) for record in records)
    assert records[1].items == frozenset({"Bread"})


def test_d09_itemsets_accept_index_instead_of_column(itemsets):
    """C2 may return itemsets indexed by itemset; both shapes are accepted."""
    indexed = itemsets.set_index("items")

    records = itemsets_to_records(indexed)

    assert len(records) == 3
    assert records[2].items == frozenset({"Milk", "Bread"})


def test_d09_missing_columns_raise(rules):
    """A frame that violates the contract fails loudly."""
    with pytest.raises(InterfaceError, match="missing column"):
        rules_to_records(rules.drop(columns=["lift"]))


def test_d09_malformed_itemsets_index_raises_clearly():
    """Regression: a scalar index used to surface as an obscure TypeError.

    If C2 returns itemsets without putting them in the index or an 'items'
    column, the failure must name the problem instead of exploding inside
    frozenset().
    """
    malformed = pd.DataFrame({"support": [0.5, 0.75]})

    with pytest.raises(InterfaceError) as excinfo:
        itemsets_to_records(malformed)

    message = str(excinfo.value)
    assert "must hold item names as a collection" in message
    assert "contract section 6" in message


def test_d09_malformed_rules_cells_raise_clearly(rules):
    """A scalar where an itemset belongs must be reported, not crashed on."""
    broken = rules.copy()
    broken.loc[0, "antecedents"] = 42

    with pytest.raises(InterfaceError, match="antecedents"):
        rules_to_records(broken)


def test_d09_records_accept_serialised_strings(rules):
    """Records can be rebuilt from an exported CSV without extra parsing."""
    from_frame = rules_to_records(rules)
    csv_like = rules.copy()
    csv_like["antecedents"] = [serialize_itemset(a) for a in rules["antecedents"]]
    csv_like["consequents"] = [serialize_itemset(c) for c in rules["consequents"]]

    from_strings = rules_to_records(csv_like)

    assert [r.antecedents for r in from_strings] == [r.antecedents for r in from_frame]


def test_d09_record_str_is_readable(rules):
    """The dashboard prints these directly, so __str__ must be legible."""
    text = str(rules_to_records(rules)[0])

    assert "->" in text
    assert "lift=" in text


# --- TC-14: rule export ---------------------------------------------------


def test_tc14_export_writes_expected_header(rules, tmp_path):
    """TC-14 / FR-17: The header is exactly the five contract columns."""
    target = tmp_path / "rules.csv"

    export_rules(rules, str(target))

    header = target.read_text(encoding="utf-8").splitlines()[0]
    assert header == "antecedents,consequents,support,confidence,lift"


def test_tc14_export_writes_correct_row_count(rules, tmp_path):
    """TC-14: One output row per input rule, no header counted."""
    target = tmp_path / "rules.csv"

    export_rules(rules, str(target))

    assert len(load_rules(str(target))) == len(rules)


def test_tc14_export_uses_d08_format(rules, tmp_path):
    """TC-14 / D-8: Cells carry the agreed serialisation."""
    target = tmp_path / "rules.csv"

    export_rules(rules, str(target))

    frame = load_rules(str(target))
    assert frame.loc[2, "antecedents"] == "{Bread + Milk}"
    assert frame.loc[0, "consequents"] == "{Bread}"


def test_tc14_export_returns_the_path(rules, tmp_path):
    """FR-17: The writer returns where it wrote."""
    target = tmp_path / "rules.csv"

    written = export_rules(rules, str(target))

    assert Path(written) == target
    assert target.is_file()


def test_tc14_export_creates_missing_parent_directory(rules, tmp_path):
    """A nested destination path must not fail on a missing directory."""
    target = tmp_path / "outputs" / "reports" / "rules.csv"

    export_rules(rules, str(target))

    assert target.is_file()


def test_tc14_export_is_utf8_encoded(rules, tmp_path):
    """NFR-10: Encoding is pinned so re-reads are deterministic."""
    target = tmp_path / "rules.csv"

    export_rules(rules, str(target))

    assert target.read_bytes().decode("utf-8")


def test_tc14_export_roundtrips_through_load(rules, tmp_path):
    """C3's TC-06 path: export, reload, and rebuild typed records."""
    target = tmp_path / "rules.csv"

    export_rules(rules, str(target))
    reloaded = load_rules(str(target))
    records = rules_to_records(reloaded)

    assert len(records) == 3
    assert records[2].antecedents == frozenset({"Milk", "Bread"})
    assert records[2].lift == pytest.approx(2.481)


def test_tc14_export_rejects_incomplete_frame(rules, tmp_path):
    """Exporting a frame missing a contract column must not silently succeed."""
    with pytest.raises(InterfaceError, match="missing column"):
        export_rules(rules.drop(columns=["confidence"]), str(tmp_path / "rules.csv"))


def test_tc14_export_accepts_an_empty_rule_set(tmp_path):
    """Zero rules is a legitimate result, not an error."""
    empty = pd.DataFrame(columns=RULE_COLUMNS)

    written = export_rules(empty, str(tmp_path / "rules.csv"))

    assert len(load_rules(written)) == 0


def test_tc14_export_itemsets_writes_expected_header(itemsets, tmp_path):
    """The itemsets artefact carries its own two-column header."""
    target = tmp_path / "itemsets.csv"

    export_itemsets(itemsets, str(target))

    assert target.read_text(encoding="utf-8").splitlines()[0] == "items,support"


def test_tc14_export_itemsets_uses_d08_format(itemsets, tmp_path):
    """Itemsets use the same serialisation as rules."""
    target = tmp_path / "itemsets.csv"

    export_itemsets(itemsets, str(target))

    frame = pd.read_csv(target)
    assert frame.loc[2, "items"] == "{Bread + Milk}"
    assert len(frame) == 3


def test_tc14_export_itemsets_rejects_empty_frame(tmp_path):
    """An empty itemset frame is a failure upstream, not a valid artefact."""
    with pytest.raises(InterfaceError, match="empty itemsets"):
        export_itemsets(pd.DataFrame(columns=["items", "support"]), str(tmp_path / "i.csv"))


def test_tc14_load_rules_reports_missing_file(tmp_path):
    """C3 gets a clear error rather than a pandas stack trace."""
    with pytest.raises(InterfaceError, match="not found"):
        load_rules(str(tmp_path / "absent.csv"))


def test_tc14_load_rules_rejects_wrong_header(tmp_path):
    """A file missing contract columns is rejected, not partially read."""
    bad = tmp_path / "bad.csv"
    bad.write_text("a,b,c\n1,2,3\n", encoding="utf-8")

    with pytest.raises(InterfaceError, match="missing column"):
        load_rules(str(bad))


# --- TC-19: reproducibility ------------------------------------------------


def test_tc19_two_identical_exports_are_byte_identical(rules, tmp_path):
    """NFR-10: Re-exporting the same rules reproduces the file exactly."""
    first = tmp_path / "a.csv"
    second = tmp_path / "b.csv"

    export_rules(rules, str(first))
    export_rules(rules, str(second))

    assert first.read_bytes() == second.read_bytes()


def test_tc19_frozenset_order_does_not_affect_output(rules, tmp_path):
    """Reordering a frozenset internally must not change the exported cell."""
    shuffled = rules.copy()
    shuffled["antecedents"] = [
        frozenset(reversed(tuple(sorted(a)))) for a in rules["antecedents"]
    ]

    original_path = tmp_path / "a.csv"
    shuffled_path = tmp_path / "b.csv"
    export_rules(rules, str(original_path))
    export_rules(shuffled, str(shuffled_path))

    assert original_path.read_bytes() == shuffled_path.read_bytes()