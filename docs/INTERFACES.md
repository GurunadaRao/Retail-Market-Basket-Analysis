# Cross-Module Interface Contracts

**Owner:** C1 (integration lead)
**Status:** Frozen for the current release
**Last updated:** Phase 0 sync

This file is the authoritative record of every interface other modules depend on. Per rule **CP-8**, a signature listed here is frozen: changing it requires incrementing the version and notifying all contributors in the weekly sync.

---

## 0. Resolved Ambiguities

The SRS and the collaboration document disagreed on three points. These were settled in the Phase 0 sync and are now binding.

| # | Question | Decision | Rationale |
| --- | --- | --- | --- |
| D-1 | Is the mining module `apriori_engine.py` or `mining.py`? | **`src/apriori_engine.py`** | Matches the collaboration document. Also corrects the `apiroi_engine.py` typo present in the source PDF. |
| D-2 | Are `outputs/` and `data/processed/` tracked in git? | **Ignored, but `.gitkeep` committed** | Honours CP-6 for generated files while keeping the folder structure alive across clones. |
| D-3 | How do validation failures surface? | **Custom exceptions in `src/errors.py`** | Allows C2 and C3 to catch a precise failure category rather than parsing `ValueError` messages. |
| D-4 | Which FR numbering is authoritative? | **FR-01 to FR-24 (SRS)** | The condensed FR1–FR12 scheme in the collaboration document is retained only as a traceability shorthand (collab §9.3). |
| D-5 | Who validates exports (TC-06)? | **C2 produces, C3 validates, C1 provides the writer** | Split resolved: `models.py` owns `export_rules`, TC-14 covers it; C3's TC-06 checks the artefact. |
| D-6 | Dense or sparse binary matrix? | **Dense `uint8` DataFrame** | Stays directly consumable by `mlxtend.frequent_patterns.apriori`. Sparse would force C2 to hand-roll Apriori. |
| D-7 | Are optional columns preserved through cleaning? | **Yes — `clean_data` keeps them, `build_matrix` ignores them** | Lets C3 report date ranges and price context without a second loader. |
| D-8 | How are frozensets written into exported CSV cells? | **`{Milk + Bread}`** — items sorted ascending, joined by `" + "`, wrapped in braces** | Deterministic regardless of frozenset iteration order, readable in Excel, and trivial to split on `" + "`. Avoids the quoting hazard of a comma separator. |
| D-9 | How far does `src/models.py` go? | **Export/load helpers plus frozen `Rule` and `FrequentItemset` dataclasses** | Gives C3 a stable typed shape to code the dashboard against, rather than positional column access. |

---

## 1. Exceptions (`src/errors.py`, owned by C1)

```python
class MarketBasketError(Exception): ...
class SchemaError(MarketBasketError): ...
class DataQualityError(MarketBasketError): ...
class InterfaceError(MarketBasketError): ...
```

| Exception | Raised when | Typical caller handling |
| --- | --- | --- |
| `SchemaError` | Mandatory column absent, or file unreadable as delimited text | Abort; prompt the user to fix the dataset |
| `DataQualityError` | Dataset is empty, or a mandatory column is entirely null | Abort; no amount of threshold tuning will help |
| `InterfaceError` | An upstream module returns a frame violating the frozen contract | Bug — must be fixed, never caught and ignored |

Catching `MarketBasketError` catches all four.

---

## 2. Shared Configuration (`src/config.py`, owned by C1)

```python
DEFAULT_ITEM_COL = "Item"
DEFAULT_TXN_COL = "TransactionID"
DEFAULT_MIN_SUPPORT = 0.01
DEFAULT_MIN_CONFIDENCE = 0.30
DEFAULT_MIN_LIFT = 1.00
TOP_N_ITEMS = 15
TOP_N_RULES = 20
```

Per **CP-2** this file is append-only within a module block: contributors may add new named constants but never rename or delete an existing one. No module may hard-code a threshold internally (Phase 0.2 of the action plan).

---

## 3. Dataset Schema

Mandatory columns in the source CSV:

| Column | Type | Role |
| --- | --- | --- |
| `TransactionID` | string or integer | Basket key |
| `Item` | string | Basket item |

Optional columns (`Date`, `Price`) are retained if present but are not used by the core mining pipeline.

Column names are overridable per call via the `item_col` and `txn_col` parameters, defaulting to the constants above.

---

## 4. M1 → M2 : Ingestion to Preprocessing

**Owner:** C1 · **Version:** 1.0

```python
def load_data(
    path: str,
    item_col: str = DEFAULT_ITEM_COL,
    txn_col: str = DEFAULT_TXN_COL,
) -> pd.DataFrame:
```

**Contract**

- Returns a DataFrame guaranteed to contain `txn_col` and `item_col`.
- Raises `FileNotFoundError` if `path` does not exist.
- Raises `SchemaError` if either mandatory column is absent, or the file cannot be parsed as CSV.
- Raises `DataQualityError` if the frame has zero rows, or the `item_col` column is entirely null.
- Never returns a partially validated frame.

---

## 5. M2 → M3 : Preprocessing to Mining

**Owner:** C1 produces, C2 consumes · **Version:** 1.0

```python
def clean_data(df, item_col=DEFAULT_ITEM_COL, txn_col=DEFAULT_TXN_COL) -> pd.DataFrame
def build_matrix(clean_df, item_col=DEFAULT_ITEM_COL, txn_col=DEFAULT_TXN_COL) -> pd.DataFrame
```

**Contract**

- `clean_data` returns **long format** (one row per item per transaction), free of nulls in the mandatory columns, whitespace-trimmed, de-duplicated, and cast to `str`.
- `clean_data` **preserves optional columns** (`Date`, `Price`, …) if they were present in the source, so C3 can report time ranges. `build_matrix` ignores them.
- `build_matrix` returns a **dense `uint8` pandas DataFrame**: index = `txn_col` values (one row per transaction), one column per distinct item, values 0 or 1, column labels sorted ascending.
- Dense `uint8` was chosen over `scipy.sparse` in decision **D-6** so the matrix stays directly consumable by `mlxtend.frequent_patterns.apriori`. Memory is comfortable below roughly 500,000 transactions x 5,000 items; beyond that, NFR-04 requires re-tuning rather than a representation change.
- `build_matrix` must raise `InterfaceError` if handed a frame that still contains nulls in either mandatory column.

**This is risk R-01.** C2 confirms the shape, index name, and dtype of what it receives before either side merges.

---

## 6. M3 → M4 : Mining to Evaluation

**Owner:** C2 · **Version:** 1.0 (declared here so C1 can wire `main.py` and `models.py`)

```python
def mine_itemsets(matrix, min_support=DEFAULT_MIN_SUPPORT) -> pd.DataFrame
# columns: support

def generate_rules(itemsets, min_confidence=DEFAULT_MIN_CONFIDENCE) -> pd.DataFrame
# columns: antecedents, consequents, support, confidence, lift
```

**Contract**

- `itemsets` has exactly one column, `support`.
- `rules` has exactly the five columns listed, in that order.
- `antecedents` and `consequents` are `frozenset`.
- `rules` is sorted by `lift` descending, then `confidence` descending.

---

## 7. M4 → M5 / M6 : Evaluation to Query and Visualization

**Owner:** C2 produces, C3 consumes · **Version:** 1.0

```python
def filter_rules(rules, item, direction="antecedent") -> pd.DataFrame
def export_rules(rules, path) -> str   # C1 provides, in models.py
```

**Contract**

- `direction` accepts `"antecedent"` or `"consequent"`; any other value raises `ValueError`.
- `filter_rules` returns an empty DataFrame **with the same columns** when nothing matches — never `None`.
- `export_rules` writes a UTF-8 CSV with a header row and returns the written path.
- Itemsets are serialised as **`{Milk + Bread}`** per decision **D-8**: items sorted ascending, joined by a literal `" + "`, wrapped in braces. Exported column order is `antecedents, consequents, support, confidence, lift`.

---

## 8. Data Models (`src/models.py`, owned by C1)

Frozen dataclasses give C3 a typed surface to code against (decision **D-9**).

```python
@dataclass(frozen=True)
class FrequentItemset:
    items: frozenset[str]
    support: float

@dataclass(frozen=True)
class Rule:
    antecedents: frozenset[str]
    consequents: frozenset[str]
    support: float
    confidence: float
    lift: float
```

| Helper | Signature | Purpose |
| --- | --- | --- |
| `serialize_itemset` | `(itemset: frozenset[str]) -> str` | `{Milk + Bread}` per D-8 |
| `deserialize_itemset` | `(text: str) -> frozenset[str]` | Inverse of the above; tolerates whitespace and empty braces |
| `export_itemsets` | `(itemsets: pd.DataFrame, path: str) -> str` | Writes `itemsets` with an `items,support` header |
| `export_rules` | `(rules: pd.DataFrame, path: str) -> str` | Writes `rules` with the five-column header |
| `load_rules` | `(path: str) -> pd.DataFrame` | Round-trips `export_rules`; **used by C3 to validate TC-06** |
| `rules_to_records` | `(rules: pd.DataFrame) -> list[Rule]` | Typed view for the dashboard |
| `itemsets_to_records` | `(itemsets: pd.DataFrame) -> list[FrequentItemset]` | Typed view for the dashboard |

**Dependency note (D-5):** C2 produces the rule rows, C3 validates the artefact via `load_rules`, and C1 owns this writer. Neither C2 nor C3 may re-implement `export_rules`.

---

## 9. CLI Contract (`main.py`, owned by C1)

`main.py` owns the pipeline wiring and the exit codes. C2 and C3 must not add
their own entry points or change these codes.

| Exit code | Meaning |
| --- | --- |
| `0` | Pipeline completed |
| `1` | Pipeline failed — bad dataset, bad schema, or invalid threshold |
| `3` | `--require-mining` was set but `src/apriori_engine.py` is unavailable |

Guarantees `main.py` makes regardless of what C2 returns:

- **FR-15** — rules below `--min-lift` are filtered out by the CLI.
- **FR-16** — exported rules are sorted by lift descending, then confidence descending.
- **FR-17** — both `rules.csv` and `itemsets.csv` are written to `--output-dir`.
- **FR-22** — every threshold and column name used is printed in the summary.

The mining import is guarded (risk **R-04**): while `src/apriori_engine.py`
is absent the CLI completes the ingestion and preprocessing path, prints that
mining was skipped, and exits `0`. Pass `--require-mining` to convert that
into exit code `3` instead.

---

## 10. Known Gaps

| Gap | Detail | Owner |
| --- | --- | --- |
| `mlxtend` not installed | Confirmed absent in the local Python 3.13.1 environment. Required only by C2's `apriori_engine.py`. | C2 |
| `mlxtend` version unpinned | Left commented out in `requirements.txt` pending a Python 3.13-compatible release. | C2 |
| Column ordering of the binary matrix | Contract says sorted ascending; C2 must not assume positional access, only label access. | C1 + C2 |
| Streamlit mock rules frame | C3 develops the dashboard against a mock until `apriori_engine` lands (risk R-04). Schema must match §6. | C3 |
| Reference dataset is synthetic | `data/raw/groceries_sample.csv` is 50 hand-built transactions. A real POS extract is still needed for the performance claims in NFR-01 and NFR-02. | C1 + team |