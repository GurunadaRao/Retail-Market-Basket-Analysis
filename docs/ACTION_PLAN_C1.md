# Action Plan — Contributor 1 (Gurunada Rao)
**Role:** Data Infrastructure & Pipeline Lead
**Modules owned:** `src/data_loader.py`, `src/preprocessing.py`, `src/models.py`, `src/config.py`, `main.py`, `tests/fixtures/`
**Requirements owned:** FR-01–FR-08, FR-17
**Tests owned:** TC-01–TC-07, TC-14

---

## Phase 0 — Unblockers (Do first, before any code)

The two documents disagree on names. Every downstream module import depends on this being settled, so it must be closed in the first sync, not during integration.

| # | Action | Output | Blocks |
| --- | --- | --- | --- |
| 0.1 | Confirm mining module filename: `apriori_engine.py` (collab doc) vs `mining.py` (SRS 5.2). Publish the decision. | Decision in `docs/INTERFACES.md` | C2 entirely |
| 0.2 | Confirm FR numbering scheme. Collab doc uses FR1–FR12; SRS uses FR-01–FR-24. Recommend adopting FR-01–FR-24 as authoritative and using the mapping table (collab 9.3) for team traceability. | Updated SRS §3 + collab §9.3 | All traceability claims |
| 0.3 | Freeze the six interface contracts in collab §6.1–6.6 with C2 and C3. Sign off in the weekly sync **before** code is written (CP-3). | Signed contracts in `docs/INTERFACES.md` | C2, C3 |
| 0.4 | Agree the dataset schema and obtain the source CSV. Confirm the mandatory column names (`Item`, `TransactionID`). | `docs/DATASET_SCHEMA.md` | TC-01, TC-02 |
| 0.5 | `git init`, create `feature/c1/repo-scaffold`, first commit. | Repo with history | everything |

**Exit criteria:** a green-to-yellow build in which C2 can import `build_matrix` output without asking a question.

---

## Phase 1 — Repository Scaffold (Day 1–2)

| # | Action | SRS / TC |
| --- | --- | --- |
| 1.1 | Pin dependency versions in `requirements.txt`; record Python version in README | NFR-07, NFR-11 |
| 1.2 | Create `src/__init__.py`, `tests/__init__.py`, `tests/fixtures/`, `outputs/figures/` | — |
| 1.3 | Write `.gitignore` covering `.venv/`, `__pycache__/`, `.pytest_cache/`, `outputs/`, `data/processed/` | CP-6 |
| 1.4 | Decide whether `outputs/` and `data/processed/` are tracked; if tracked, add `.gitkeep` (they are currently gitignored, so they vanish in git) | CP-6 |
| 1.5 | Verify a clean virtual environment installs and `pytest` runs | NFR-07 |

**PR:** `chore(c1): scaffold repository structure, requirements, and gitignore`

---

## Phase 2 — M1 Data Loader (Day 3–5)

**File:** `src/data_loader.py` — function `load_data(path, item_col, txn_col)`

| # | Action | Requirement |
| --- | --- | --- |
| 2.1 | Read CSV into a DataFrame; never return a partially validated frame | FR-01 |
| 2.2 | Validate presence of `txn_col` and `item_col`; raise a custom `SchemaError` with the missing column named | FR-02, NFR-09 |
| 2.3 | Raise `FileNotFoundError` with the path for a missing file | FR-02, TC-02 |
| 4a | Report record count, transaction count, and distinct item count on load | FR-03 |
| 2.5 | Reject a headers-only CSV with a descriptive error, not an empty-frame crash | TC-07 |
| 2.6 | Docstring on every public function; PEP 8 naming | NFR-11 |

**Tests — `tests/test_data_loader.py`:**
- TC-01 valid CSV loads, row count matches file
- TC-02 missing mandatory column raises `SchemaError` naming the column
- TC-07a empty dataset (headers only) raises a descriptive error
- TC-07b all-null item column raises rather than returning an empty frame

**Exit criteria:** TC-01, TC-02, TC-07 pass; no unhandled exception path remains.

---

## Phase 3 — M2 Preprocessing (Day 6–10)

**File:** `src/preprocessing.py` — functions `clean_data(df, ...)`, `build_matrix(clean_df, ...)`

This is the highest-risk phase: `build_matrix` output is the contract boundary with C2 (risk R-01).

### 3a — `clean_data` (Day 6–7)

| # | Action | Requirement | Test |
| --- | --- | --- | --- |
| 3.1 | Remove exact duplicate rows | FR-04 | TC-04 |
| 3.2 | Drop records with null/missing values in mandatory columns | FR-05 | TC-03 |
| 3.3 | Strip leading/trailing whitespace from item and transaction IDs | FR-06 | TC-05 |
| 3.4 | Cast all values to string for a consistent matrix build | FR-07 | TC-05 |
| 3.5 | Log row counts before and after each step | FR-23 | — |

### 3b — `build_matrix` (Day 8–9)

| # | Action | Requirement | Test |
| --- | --- | --- | --- |
| 3.6 | Pivot long format to a binary 0/1 matrix: rows = transactions, columns = items | FR-08 | TC-06 |
| 3.7 | Ensure one row per transaction, deduplicated item columns, integer 0/1 dtype | FR-08 | TC-06 |
| 3.8 | Use a sparse representation where the item count justifies it | NFR-01, NFR-05 | TC-18 |
| 3.9 | Benchmark on 100,000 transactions — preprocessing must complete under 30 s | NFR-01 | TC-18 |

### 3c — Contract handoff (Day 10)

| # | Action |
| --- | --- |
| 3.10 | Hand C2 a committed fixture matrix so the mining engine can be integration-tested in parallel (mitigates R-01) |
| 3.11 | Agree with C2 the exact DataFrame shape, index name, and column dtype C2 will receive; record in `docs/INTERFACES.md` |
| 3.12 | Verify against C2's expectations on the same fixture before either side merges |

**Exit criteria:** TC-03, TC-04, TC-05, TC-06, TC-18 pass; C2 has confirmed the matrix contract in writing.

---

## Phase 4 — Config & Models (Day 11–12)

**Files:** `src/config.py`, `src/models.py`

| # | Action | Requirement |
| --- | --- | --- |
| 4.1 | Define and freeze the six shared constants (`DEFAULT_ITEM_COL`, `DEFAULT_TXN_COL`, `DEFAULT_MIN_SUPPORT`, `DEFAULT_MIN_CONFIDENCE`, `DEFAULT_MIN_LIFT`, `TOP_N_ITEMS`, `TOP_N_RULES`) | collab §6.6 |
| 4.2 | Announce the constants to C2 and C3; enforce that no module hard-codes a threshold | CP-2 |
| 4.3 | Implement export helpers writing itemsets and rules to CSV with correct headers | FR-17 |
| 4.4 | Make `config.py` append-only within a module block; document that rule in the file header | CP-2 |
| 4.5 | Confirm export format with C2 (who produces the rule rows) and C3 (who validates in TC-06) | R-04 |

**Tests:** TC-14 export writes a file with correct headers and row count.

---

## Phase 5 — CLI Entry Point (Day 13–14)

**File:** `main.py`

| # | Action | Requirement |
| --- | --- | --- |
| 5.1 | Wire the pipeline: load → clean → matrix → *(mining, owned by C2)* → export | FR-01–FR-08, FR-17 |
| 5.2 | Accept file path and thresholds as CLI arguments with sane defaults from `config.py` | FR-09, NFR-06 |
| 5.3 | Print the run summary: parameter values, row counts, distinct items, itemsets, rules | FR-22, FR-23 |
| 5.4 | Guard the mining import so the CLI still runs end-to-end if C2's module is not yet merged | R-04 |
| 5.5 | Document CLI usage in README | NFR-06 |

**Exit criteria:** the CLI runs end-to-end on the sample dataset and prints a summary identical in format to SRS §5.5.

---

## Phase 6 — Documentation & Handoff (Day 15)

| # | Action | Requirement |
| --- | --- | --- |
| 6.1 | Finalize `docs/SRS.md` (align FR numbering per Phase 0.2) | — |
| 6.2 | Write `docs/INTERFACES.md` with every frozen signature and its version | CP-8 |
| 6.3 | Write `docs/DATASET_SCHEMA.md` — column names, types, expected row counts | FR-02 |
| 6.4 | Write `README.md` — setup, environment, CLI usage, dataset placement | NFR-06 |
| 6.5 | Run the full test suite and the weekly smoke test | FR-23 |

---

## Phase 7 — Integration & Support (Week 3 onward)

Your build is done; the remaining work is keeping everyone else unblocked.

| # | Action | Cadence |
| --- | --- | --- |
| 7.1 | Review pull requests for interface conformance | Twice weekly (Tue, Fri) |
| 7.2 | Merge approved PRs to `main`; preserve contributor history per commit rules | After each approval |
| 7.3 | Run the integration smoke test on merged `main` | Weekly, Friday |
| 7.4 | Rebase own branches after every merge | Daily |
| 7.5 | Answer C2's and C3's interface questions within one working day | Continuous |
| 7.6 | No merges on Fridays after 16:00 | — |
| 7.7 | Tune thresholds against the 100,000-transaction benchmark to confirm NFR-01 and NFR-02 | Week 3 |

---

## Working Cadence

| Rhythm | When | Action |
| --- | --- | --- |
| Daily | Morning | `git pull --rebase`, pick up two interface questions |
| Twice weekly | Tue, Fri | Open PRs for review |
| Weekly | Friday | Integration smoke test with C2 and C3 |
| Milestone | End of Week 3 | Dataset pipeline validated end-to-end — **you own this** |

---

## Definition of Done (per contribution)

- [ ] Committed to `feature/c1/*`, never directly to `main`
- [ ] Conventional Commit message with `Refs: FR-xx, TC-xx`
- [ ] Docstrings on every public function; PEP 8 naming
- [ ] Own test file passes with `pytest`
- [ ] PR description references the satisfied SRS requirement IDs (CP-5)
- [ ] Integration lead approved the merge
- [ ] Weekly smoke test passes on merged `main`

---

## Risks You Own

| Risk | Mitigation | Status |
| --- | --- | --- |
| R-01 Matrix output does not match C2's mining input | Freeze contract in Phase 0; share fixture matrix in Phase 3c before either merge | Open |
| R-02 Conflicting edits to `config.py` | Single owner, append-only, announce additions | Open |
| R-05 Late merge conflicts erode the demo timeline | Twice-weekly merge windows, daily rebase, small commits | Open |
| R-06 Dataset schema mismatch | Schema validation with descriptive errors in M1 (TC-02) | Open |
| R-01a `outputs/` and `data/processed/` are gitignored and untracked | Decide in Phase 1.4; add `.gitkeep` if the team needs them in the repo | Open |

---

## Open Questions for the Team

1. Is the mining module `apriori_engine.py` or `mining.py`?
2. Which FR numbering scheme is authoritative in the final report?
3. Does C2 or C3 own TC-06 export validation? Collab doc assigns it to C3; the SRS traceability matrix maps export to M5 (C2).
4. Should `outputs/` be tracked in git despite CP-6?
5. Which dataset is the reference dataset, and who owns refreshing it?