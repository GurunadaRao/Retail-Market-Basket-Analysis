# Retail Market Basket Analysis System

A data mining application that applies the **Apriori algorithm** to retail
transaction data to discover frequently co-purchased products, then derives
association rules scored by **support**, **confidence**, and **lift**.

Built for the DWDM project. See `docs/SRS.md` (or
`SRS_Retail_Market_Basket_Analysis.md`) for the full specification and
`docs/ACTION_PLAN_C1.md` for the implementation plan.

---

## Quick Start

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux / macOS

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the pipeline against the bundled sample dataset
python main.py --data data/raw/groceries_sample.csv --min-support 0.05

# 4. Run the test suite
pytest -q
```

### CLI Options

| Flag | Default | Description |
| --- | --- | --- |
| `--data` | `data/raw/groceries_sample.csv` | Path to the transaction CSV |
| `--min-support` | `0.01` | Minimum itemset support, `0 < x <= 1` |
| `--min-confidence` | `0.30` | Minimum rule confidence, `0 <= x <= 1` |
| `--min-lift` | `1.00` | Minimum rule lift, `x >= 0` |
| `--item-col` | `Item` | Override the item column name |
| `--txn-col` | `TransactionID` | Override the transaction ID column name |
| `--output-dir` | `outputs` | Directory for `rules.csv` and `itemsets.csv` |
| `--top-n` | `10` | How many top items / rules to list in the summary |
| `--require-mining` | off | Exit non-zero if the Apriori engine is unavailable |
| `--quiet` | off | Suppress per-step logging; print only the summary |

### Exit Codes

| Code | Meaning |
| --- | --- |
| `0` | Pipeline completed |
| `1` | Pipeline failed (bad dataset, bad schema, invalid threshold) |
| `3` | `--require-mining` was set but `src/apriori_engine.py` is missing |

### Current Status

The ingestion and preprocessing stages are complete and tested. The mining
stage belongs to C2 (`src/apriori_engine.py`) and has not landed yet, so the
CLI runs the full data path and reports that mining was skipped. Add
`--require-mining` to make that situation a hard failure — which is what the
weekly smoke test should use once C2's module is merged.

---

## Dataset Format

Long (tidy) format — **one row per item purchased per transaction**.

```csv
TransactionID,Item
1001,Milk
1001,Bread
1002,Coffee
```

| Column | Required | Description |
| --- | --- | --- |
| `TransactionID` | Yes | Basket identifier |
| `Item` | Yes | Product name |
| `Date`, `Price` | No | Retained if present; unused by core mining |

Column names are overridable via `--item-col` / `--txn-col`.

---

## Repository Structure

```
.
├── app.py                  # Streamlit dashboard          [C3]
├── main.py                 # CLI entry point              [C1]
├── config.py → src/config.py
├── data/
│   ├── raw/                # Source datasets (read-only)
│   └── processed/          # Generated matrices           [git-ignored]
├── docs/
│   ├── INTERFACES.md       # Frozen cross-module contracts
│   ├── ACTION_PLAN_C1.md   # C1 implementation plan
│   └── DATASET_SCHEMA.md   # (Phase 6)
├── src/
│   ├── config.py           # Shared thresholds            [C1]
│   ├── errors.py           # Exception hierarchy          [C1]
│   ├── data_loader.py      # M1 ingestion                 [C1]
│   ├── preprocessing.py    # M2 cleaning + matrix         [C1]
│   ├── models.py           # Data models + export helpers [C1]
│   ├── apriori_engine.py   # M3 mining + rules            [C2]
│   ├── evaluation.py       # M4 metrics + filtering       [C2]
│   ├── queries.py          # M5 rule querying             [C2]
│   └── visualizer.py       # M6 charts + network graph    [C3]
├── tests/
│   ├── fixtures/           # Deterministic test datasets  [C1]
│   ├── test_data_loader.py # TC-01, TC-02, TC-07          [C1]
│   ├── test_apriori_engine.py                             [C2]
│   └── test_exports.py                                    [C3]
└── outputs/                # Generated artefacts          [git-ignored]
    └── figures/
```

Bracket markers show file ownership per collaboration rule CP-1. **Do not
edit a file you do not own** — raise an interface request instead.

---

## Architecture

```
CSV ──▶ M1 load_data ──▶ M2 clean_data ──▶ M2 build_matrix ──▶ M3 mine_itemsets
                                                                   │
                          M6 visualizer ◀── M5 export ◀── M4 generate_rules
                                                                   │
                                                        M5 filter_rules ──▶ M7 queries
```

`docs/INTERFACES.md` holds the frozen signature of every arrow above.

---

## Error Handling

All deliberate failures raise a subclass of `MarketBasketError`
(`src/errors.py`), so callers can catch the family in one clause:

| Exception | Meaning | Typical response |
| --- | --- | --- |
| `SchemaError` | Mandatory column absent, or unparseable file | Abort; fix the dataset |
| `DataQualityError` | No rows, or an entirely null item column | Abort; threshold tuning will not help |
| `InterfaceError` | Upstream module broke a frozen contract | Bug — propagate, do not suppress |

---

## Environment

Verified against **Python 3.13.1**. Exact pinned versions are in
`requirements.txt`.

> **Known gap:** `mlxtend` is not yet installed locally. It is required only
> by `src/apriori_engine.py` (C2's module). Pin a Python 3.13-compatible
> release before the mining engine is merged.

---

## References

1. Han, J., Kamber, M. — *Data Mining: Concepts and Techniques*, 3rd ed.
2. Tan, P.N., Steinbach, M., Kumar, V. — *Introduction to Data Mining*
3. Agrawal, R., Imieliński, T., Swami, A. — *Mining Association Rules Between Sets of Items in Large Databases*, SIGMOD 1993
4. Brin, S., Motwani, R. — *Fast Algorithms for Mining Association Rules*, VLDB 1995