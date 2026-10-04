# Dataset Schema

**Owner:** C1
**Applies to:** any CSV passed to `python main.py --data <path>`

---

## 1. Required Shape

Long (tidy) format — **one row per item purchased per transaction**.

```csv
TransactionID,Item
1001,Milk
1001,Bread
1002,Coffee
```

A wide format (one column per item, one row per basket) is **not** accepted.
`build_matrix` produces the wide form internally; the pipeline consumes only
the long form as input.

---

## 2. Columns

| Column | Required | Inferred type | Role |
| --- | --- | --- | --- |
| `TransactionID` | Yes | `int64` → cast to `str` | Basket key |
| `Item` | Yes | `object` → cast to `str` | Basket item |
| `Date` | No | any | Preserved by `clean_data`, ignored by `build_matrix` |
| `Price` | No | any | Preserved by `clean_data`, ignored by `build_matrix` |

Per decision **D-7**, optional columns survive cleaning so C3 can report date
ranges and price context without a second loader. Mining never reads them.

Column names are overridable:

```bash
python main.py --data orders.csv --item-col Product --txn-col Basket
```

---

## 3. Validation Rules

Enforced by `src/data_loader.load_data`, in this order:

| # | Rule | Failure |
| --- | --- | --- |
| 1 | Path must resolve to an existing file | `FileNotFoundError` |
| 2 | File must parse as delimited text with a header row | `SchemaError` |
| 3 | `TransactionID` must be present | `SchemaError` |
| 4 | `Item` must be present | `SchemaError` |
| 5 | At least one data row must exist | `DataQualityError` |
| 6 | `Item` must not be entirely null | `DataQualityError` |

A *sparse* null in `Item` is **not** fatal at load time — those rows are
dropped during cleaning and the count is logged (FR-23).

---

## 4. Cleaning Transformations

Applied by `src.preprocessing.clean_data`, in this order:

| Step | Rule | Effect |
| --- | --- | --- |
| 1 | `drop_duplicates()` | Removes **exact** duplicate rows (FR-04). `Milk` and `milk` are treated as different items. |
| 2 | `dropna(subset=[txn, item])` | Drops rows null in either mandatory column (FR-05) |
| 3 | `.str.strip()` | Removes leading/trailing whitespace (FR-06). Inner spaces are preserved. |
| 4 | `.astype(str)` | Both mandatory columns become `str` (FR-07) |

If nothing survives, `DataQualityError` is raised rather than returning an
empty frame.

---

## 5. Derived Matrix

`build_matrix` pivots the cleaned long frame into:

| Property | Value |
| --- | --- |
| Index | `TransactionID`, one row per transaction, **sorted ascending**, named `TransactionID` |
| Columns | One per distinct item, **sorted ascending**, named `Item` |
| dtype | `uint8` |
| Values | `0` or `1` only |

```
Item           Bread  Coffee  Eggs  Milk
TransactionID
1001               1       0     1     1
1002               1       0     0     1
1003               0       1     1     0
```

This is the exact input `src/apriori_engine.py` receives (contract §5).
`tests/fixtures/expected_matrix.csv` is the committed golden file; if
`test_tc06_golden_matrix_fixture_is_reproduced` fails, **the contract has
changed and C2 must be notified before merging** (risk R-01).

---

## 6. Reference Dataset

`data/raw/groceries_sample.csv` — committed, read-only.

| Property | Value |
| --- | --- |
| Transactions | 50 (IDs 1001–1050) |
| Distinct items | 14 |
| Records | 134 |
| Optional columns | None |

| Item | Frequency |
| --- | --- |
| Bread | 19 |
| Milk | 16 |
| Cereal | 13 |
| Coffee | 11 |
| Eggs | 11 |
| Yogurt | 10 |
| Butter | 9 |
| Sugar | 8 |
| Cheese | 8 |
| Tea | 7 |
| Juice | 6 |
| Pasta | 6 |
| Tomato | 6 |
| Biscuits | 4 |

> **Caveat.** This dataset is **synthetic and hand-built**, sized so the test
> suite runs in under three seconds. It is adequate for contract tests and the
> demo, but it **cannot** support the performance claims in NFR-01 (30 s for
> 100,000 transactions) or NFR-02 (60 s for Apriori). A real POS extract of
> at least 100,000 transactions is still required before those can be
> validated. Tracked as a known gap in `docs/INTERFACES.md` §10.

Test fixtures in `tests/fixtures/` deliberately exercise the failure modes:

| Fixture | Purpose |
| --- | --- |
| `valid_transactions.csv` | Clean 3-basket input for TC-06 |
| `messy_transactions.csv` | Nulls, duplicates, whitespace, optional columns |
| `missing_item_column.csv` | Schema failure (TC-02) |
| `empty_headers_only.csv` | Empty dataset (TC-07) |
| `all_null_items.csv` | Entirely null item column (TC-07) |
| `expected_matrix.csv` | Golden binary matrix (R-01 tripwire) |

---

## 7. Adding a New Dataset

1. Drop the CSV into `data/raw/`. Never commit processed derivatives — `data/processed/` is gitignored.
2. Confirm the mandatory columns, or pass `--item-col` / `--txn-col`.
3. Smoke-test ingestion and preprocessing only:

   ```bash
   python main.py --data data/raw/<new>.csv --min-support 0.05
   ```

4. Note the reported record / transaction / item counts in the final report, so FR-03 figures stay traceable.