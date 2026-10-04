# Software Requirements Specification
## Retail Market Basket Analysis System

**Document Type:** Software Requirements Specification (SRS)
**Version:** 1.0
**Status:** Draft for review

### Table of Contents

1. Introduction (Purpose, Document Conventions, Intended Audience, Product Scope, References)
2. Overall Description (Product Perspective, Product Functions, User Classes, Operating Environment, Constraints, Assumptions)
3. Specific Requirements (Functional Requirements, Non-Functional Requirements)
4. System Models (Use Case Diagram, Activity Diagram, Data Flow Diagram)
5. Detailed Project Design (Dataset Description, Module Design, Algorithm Design, Data Model, Sample Output, Implementation Plan)
6. Testing Plan
7. Conclusion
8. Appendix

---

## 1. Introduction

### 1.1 Purpose

The purpose of this Software Requirements Specification (SRS) document is to define the functional and non-functional requirements for the Retail Market Basket Analysis System. It provides a complete conceptual and structural blueprint for development, evaluation, and understanding of the project scope.

### 1.2 Document Conventions

| Abbreviation | Expansion |
| --- | --- |
| FR | Functional Requirement |
| NFR | Non-Functional Requirement |
| SRS | Software Requirements Specification |
| KDD | Knowledge Discovery in Databases |
| ETL | Extract, Transform, Load |

### 1.3 Intended Audience

- Project Guides and Evaluators
- Development Team & Data Engineers
- Data Analysts and Business Managers

### 1.4 Product Scope

The system is a data mining application designed to analyze purchasing patterns in retail transaction data. Key capabilities include:

- Ingesting retail transaction datasets from standard file formats.
- Preprocessing raw transactional data (cleaning, handling missing entries, transforming to binary matrix).
- Applying the Apriori algorithm for frequent itemset generation.
- Deriving key association rules with metrics including Support, Confidence, and Lift.
- Visualizing pattern insights through charts, network graphs, and interactive query views.

#### Key Business Benefit

Enables retail managers to optimize product placement, construct high-margin promotional bundles, and significantly improve cross-selling performance.

### 1.5 References

- Han, J., Kamber, M. - Data Mining: Concepts and Techniques, 3rd Edition
- Tan, P.N., Steinbach, M., Kumar, V. - Introduction to Data Mining
- Lab Experiment 3: Association Rule Mining using WEKA
- Lab Experiment 9: Python program for frequent itemsets / association rules

---

## 2. Overall Description

### 2.1 Product Perspective

A standalone data mining application built using Python scientific libraries (pandas, mlxtend, matplotlib, networkx) with an optional interactive web dashboard interface powered by streamlit.

### 2.2 Product Functions

| Function | Description |
| --- | --- |
| Data Ingestion | Load retail transaction data directly from CSV files. |
| Data Preprocessing | Handle missing values, trim whitespace, remove exact duplicates. |
| Frequent Itemset Generation | Apply the Apriori algorithm based on a configurable minimum support threshold. |
| Rule Generation | Derive actionable association rules based on minimum confidence. |
| Rule Evaluation | Compute and evaluate rule quality using Support, Confidence, and Lift metrics. |
| Visualization | Generate item frequency bar charts, network interaction graphs, and scatter plots. |
| Interactive Query | Filter rules containing specific target antecedent or consequent products. |

### 2.3 User Classes and Characteristics

| User Class | Description | Technical Expertise |
| --- | --- | --- |
| Data Analyst | Runs deep analyses, tunes thresholds, interprets statistical outputs. | High |
| Retail Manager | Views visual dashboards, makes merchandising & placement decisions. | Low |
| System Admin | Maintains system dependencies and updates reference datasets. | Medium |
| Evaluator / Guide | Reviews project architecture, compliance, and final outputs. | Medium |

### 2.4 Operating Environment

#### Hardware Requirements

| Component | Minimum Specification |
| --- | --- |
| Processor | Dual-core CPU, 2.0 GHz or higher |
| RAM | 4 GB (8 GB recommended for datasets above 100,000 transactions) |
| Disk Space | 500 MB application footprint |
| Display | 1024 x 768 resolution for dashboard viewing |

#### Software Requirements

| Component | Specification |
| --- | --- |
| Operating System | Windows 10/11, Ubuntu 20.04+, macOS 12+ |
| Language | Python 3.9 or higher |
| Libraries | pandas, numpy, mlxtend, matplotlib, networkx, seaborn, streamlit |
| IDE / Environment | Jupyter Notebook, VS Code, or PyCharm |
| Browser | Any modern browser (Chrome, Edge, Firefox) for the Streamlit dashboard |

### 2.5 Constraints

| ID | Constraint Description |
| --- | --- |
| C1 | Input data must be available in a delimited text format (CSV) with a header row. |
| C2 | Transactions must be identifiable by a single transaction ID column for basket reconstruction. |
| C3 | The Apriori algorithm's candidate generation is exponential in the number of distinct items; minimum support must be tuned to keep runtime tractable. |
| C4 | The system operates in an offline, single-user mode with no multi-user concurrency or authentication layer. |
| C5 | Association rules are descriptive, not predictive; no causal inference may be drawn from output. |
| C6 | No internet dependency at runtime; all libraries must be installed locally. |

### 2.6 Assumptions

| ID | Assumption |
| --- | --- |
| A1 | The source dataset contains a genuine transactional structure (each row represents an item purchased in a transaction). |
| A2 | Item names are consistent across records; spelling variants are treated as distinct items unless normalized. |
| A3 | The dataset is assumed to be sufficiently representative of the retail domain to make discovered patterns meaningful. |
| A4 | The user is technically competent enough to interpret statistical metrics such as support, confidence, and lift. |
| A5 | Sufficient disk space and memory are available to load the selected dataset into memory. |

---

## 3. Specific Requirements

### 3.1 Functional Requirements

| FR ID | Requirement Description | Priority |
| --- | --- | --- |
| FR-01 | The system shall accept a CSV file path as input and load it into a pandas DataFrame. | Must |
| FR-02 | The system shall validate the presence of the mandatory transaction ID and item columns and halt with a clear message if absent. | Must |
| FR-03 | The system shall report the total number of transactions, distinct items, and total records ingested. | Must |
| FR-04 | The system shall identify and remove exact duplicate rows from the dataset. | Must |
| FR-05 | The system shall drop records with missing or null values in mandatory columns. | Must |
| FR-06 | The system shall strip leading and trailing whitespace from item names and transaction IDs. | Must |
| FR-07 | The system shall convert all values to string type to ensure a consistent binary matrix build. | Must |
| FR-08 | The system shall pivot the long-format transaction data into a binary (0/1) matrix where rows are transactions and columns are items. | Must |
| FR-09 | The system shall accept a user-configurable minimum support threshold (default 0.01) via CLI argument, function parameter, or dashboard slider. | Must |
| FR-10 | The system shall generate all frequent itemsets whose support is greater than or equal to the specified minimum support using the Apriori algorithm. | Must |
| FR-11 | The system shall display the generated frequent itemsets along with their support values, sorted descending by support. | Must |
| FR-12 | The system shall accept a user-configurable minimum confidence threshold (default 0.3) for rule filtering. | Must |
| FR-13 | The system shall derive association rules in the form Antecedent → Consequent from all frequent itemsets. | Must |
| FR-14 | The system shall compute support, confidence, and lift for every generated rule. | Must |
| FR-15 | The system shall filter rules by minimum confidence and by a user-specified minimum lift to remove uninteresting rules. | Must |
| FR-16 | The system shall sort the final rule set by lift descending, then by confidence descending. | Must |
| FR-17 | The system shall export the final rule set to a CSV file for external analysis. | Should |
| FR-18 | The system shall generate a bar chart of the top N items by transaction frequency. | Must |
| FR-19 | The system shall generate a scatter plot of Support vs. Confidence with point size proportional to Lift. | Should |
| FR-20 | The system shall generate a network graph in which items are nodes and rules are directed weighted edges. | Must |
| FR-21 | The system shall provide an interactive query interface to filter rules by a chosen antecedent or consequent item. | Should |
| FR-22 | The system shall display all parameter values used for the current run so results remain reproducible. | Must |
| FR-23 | The system shall log execution progress, including row counts before and after each preprocessing step. | Should |
| FR-24 | The system shall support an optional Streamlit web dashboard as an alternative interface to the CLI. | Could |

### 3.2 Non-Functional Requirements

| NFR ID | Category | Requirement Description |
| --- | --- | --- |
| NFR-01 | Performance | Preprocessing of 100,000 transactions must complete within 30 seconds on the minimum specified hardware. |
| NFR-02 | Performance | Apriori itemset generation at min support = 0.01 must complete within 60 seconds for a 100,000-transaction dataset. |
| NFR-03 | Performance | The Streamlit dashboard must render results within 5 seconds of a query submission. |
| NFR-04 | Scalability | The design must accommodate datasets up to 1 million transactions through threshold tuning, without code modification. |
| NFR-05 | Memory | Peak memory usage must not exceed 4 GB for a 100,000-transaction dataset. |
| NFR-06 | Usability | Any user shall be able to execute a complete analysis by supplying a file path and two thresholds, with no more than 5 additional interactions. |
| NFR-07 | Portability | The system must run on Windows, Linux, and macOS without platform-specific code changes. |
| NFR-08 | Modularity | Preprocessing, mining, evaluation, and visualization must be implemented as independently callable functions/modules. |
| NFR-09 | Reliability | Invalid input must produce a descriptive error message rather than an unhandled exception or silent failure. |
| NFR-10 | Reproducibility | Two runs with identical input and parameters must produce identical output. |
| NFR-11 | Maintainability | All modules must follow PEP 8 naming conventions with docstrings on every public function. |
| NFR-12 | Security | The system performs no credential handling, network calls, or code execution from user-supplied data. |
| NFR-13 | Visual Quality | All charts must include labelled axes, titles, legends, and a colour-blind-safe palette. |
| NFR-14 | Testability | Core preprocessing and rule-evaluation logic must be verifiable by automated unit tests. |

---

## 4. System Models

### 4.1 Use Case Diagram

```
 +-----------------------------------------------------+
 |     Retail Market Basket Analysis System            |
 +-----------------------------------------------------+
                         |
   +---------------------+---------------------+
   |                     |                     |
(Load CSV)        (Set Thresholds)       (View Results)
   |                     |                     |
   |                     |                     |
(Preprocess Data)  (Apply Apriori)     (View Charts)
   |                     |                     |
   |                     |                     |
(Clean Data)        (Generate Rules)   (Query Rules)
   |                     |                     |
   |                     |                     |
   |              (Compute Metrics)      (Export CSV)
   |                     |                     |
   +---------------------+---------------------+
                         |
          +--------------+---------------+
          |              |               |
   +-------------+ +------------+ +--------------+
   | Data Analyst| |Retail Mgr  | |System Admin  |
   +-------------+ +------------+ +--------------+
```

**Actor Responsibilities**

| Actor | Use Cases |
| --- | --- |
| Data Analyst | Load CSV, Clean Data, Set Thresholds, Apply Apriori, Generate Rules, Compute Metrics, Export CSV, View Charts, Query Rules |
| Retail Manager | View Charts, Query Rules |
| System Admin | Load CSV, View Results (reference dataset updates) |
| Evaluator / Guide | View Results (all use cases, read-only) |

### 4.2 Activity Diagram (Core Analysis Flow)

```
[Start]
   |
   v
[User provides CSV path] --><Mandatory columns present?> --No--> [Raise descriptive error] --> [End]
   |Yes
   v
[Load into DataFrame] --> [Report shape: rows, distinct items]
   |
   v
[Remove exact duplicate rows] --> [Drop null/mandatory records] --> [Strip whitespace] --> [Cast to string]
   |
   v
[Pivot to binary matrix (transaction x item)]
   |
   v
[Read min_support] --> [Apriori: generate frequent itemsets]
   |
   v
[Filter itemsets by min_confidence] --> [Compute support, confidence, lift]
   |
   v
[Filter by min_lift] --> [Sort by lift desc, confidence desc]
   |
   v
[Export rules to CSV] --> [Render bar chart / scatter plot / network graph]
   |
   v
[Interactive query filter] --> [Display matching rules]
   |
   v
[End]
```

### 4.3 Data Flow Diagram (Level 0)

```
 +----------+  CSV file   +--------------------------------+
 |  Retail  | ------------> |  Data Ingestion &             |
 |  Txn     |               |  Preprocessing Engine         |
 |  Dataset |               +--------------------------------+
 +----------+                        |
                                      | cleaned transactions
                                      | (long format)
                                      v
                         +-------------------------------+
                         |  Binary Matrix Builder        |
                         +-------------------------------+
                                      |
                                      | transaction-item matrix
                                      v
                         +-------------------------------+
                         |  Apriori Frequent Itemset     |
                         |  Generator                    |
                         +-------------------------------+
                                      |
                                      | frequent itemsets
                                      v
                         +-------------------------------+
                         |  Association Rule Generator   |
                         |  + Quality Evaluator          |
                         +-------------------------------+
                                      |
                                      | scored rules
                    +-----------------+-------------------+
                    |                                     |
                    v                                     v
   +-------------------------------+     +-------------------------------+
   |  Visualization Module         |     |  Rule Export / Interactive    |
   |  (bar, scatter, network)      |     |  Query Module                 |
   +-------------------------------+     +-------------------------------+
                    |                                     |
                    v                                     v
   +-------------------------------+     +-------------------------------+
   |  Retail Manager / Analyst     |     |  Analyst reports & exports    |
   +-------------------------------+     +-------------------------------+
```

**DFD Data Dictionary**

| Flow | Content |
| --- | --- |
| CSV file | Long-format retail transaction records |
| Cleaned transactions | Deduplicated, null-free, whitespace-trimmed records |
| Transaction-item matrix | Binary (0/1) pivot of transactions by item |
| Frequent itemsets | Itemsets with support ≥ min_support, with support values |
| Scored rules | Rules with support, confidence, and lift computed |

---

## 5. Detailed Project Design

### 5.1 Dataset Description

Retail transaction datasets are conventionally stored in long (tidy) format, where each row represents a single item purchased within a single transaction.

| Attribute | Type | Description | Role |
| --- | --- | --- | --- |
| TransactionID | String / Integer | Unique basket identifier | Basket key |
| Item | String | Product name purchased | Basket item |
| (Optional) Date | Date | Transaction date | Time dimension (unused by core Apriori) |
| (Optional) Price | Float | Unit or line price | Filter only, not used in core mining |

**Illustrative sample (long format):**

| TransactionID | Item |
| --- | --- |
| 1001 | Milk |
| 1001 | Bread |
| 1001 | Eggs |
| 1002 | Milk |
| 1002 | Bread |
| 1003 | Coffee |
| 1003 | Eggs |

The long-format dataset is pivoted into the binary matrix below, which is the true input to the Apriori algorithm:

| TID | Milk | Bread | Eggs | Coffee |
| --- | --- | --- | --- | --- |
| 1001 | 1 | 1 | 1 | 0 |
| 1002 | 1 | 1 | 0 | 0 |
| 1003 | 0 | 0 | 1 | 1 |

### 5.2 Module Design

| Module | Key Functions | Responsibility | Dependency |
| --- | --- | --- | --- |
| M1 Data Loader | `load_data(path)` | Read CSV, validate schema, report shape | pandas |
| M2 Preprocessor | `clean_data(df)`, `build_matrix(df)` | Deduplicate, null-handling, whitespace trim, string cast, pivot | pandas |
| M3 Itemset Miner | `mine_itemsets(matrix, min_support)` | Apriori frequent itemset generation | mlxtend.frequent_patterns |
| M4 Rule Generator | `generate_rules(itemsets, metric, min_confidence)` | Derive antecedent → consequent rules | mlxtend.frequent_patterns |
| M5 Rule Evaluator | `evaluate_rules(rules, min_lift)`, `export_rules(rules, path)` | Lift computation, filtering, sorting, CSV export | pandas |
| M6 Visualizer | `plot_item_frequency()`, `plot_support_confidence()`, `build_network_graph()` | Bar chart, scatter plot, network graph | matplotlib, seaborn, networkx |
| M7 Query Engine | `filter_rules(rules, item, direction)` | Interactive antecedent/consequent filtering | pandas |
| M8 Interface Layer | `main()`, `dashboard_app()` | CLI entry point; optional Streamlit UI | streamlit (optional) |

**Dependency flow:** M1 → M2 → M3 → M4 → M5 → {M6, M7} → M8. Modules M1–M5 are strictly sequential; M6 and M7 are parallel consumers of the rule set produced by M5.

### 5.3 Algorithm Design

#### Algorithm: Apriori Frequent Itemset Mining

```
INPUT : binary matrix B (transactions x items), minimum support s
OUTPUT: set F of all frequent itemsets

F1  <- { {i} : support({i}) >= s }        // frequent 1-itemsets
Ck  <- F1                                 // candidate k-itemsets
k   <- 1
WHILE Ck is not empty:
    // Candidate generation: join Fk with itself, prune by (k-1)-subsets in Fk
    C(k+1) <- Join(Ck, Ck) minus Supersets(Ck, Fk)

    // Database scan and count
    FOR each candidate c in C(k+1):
        count(c) <- number of transactions in B containing all items of c
        support(c) <- count(c) / |B|

    F(k+1) <- { c in C(k+1) : support(c) >= s }
    k     <- k + 1
RETURN union of all Fk
```

#### Rule Derivation and Evaluation

```
FOR each frequent itemset I in F:
    FOR each non-empty proper subset L of I:              // antecedent / LHS
        R  <- I \ L                                     // consequent / RHS
        conf(L -> R) = support(L union R) / support(L) = support(I) / support(L)
        lift(L -> R) = conf(L -> R) / support(R)
        IF conf >= min_confidence AND lift >= min_lift:
            RETAIN rule (L -> R, support, confidence, lift)
```

#### Metric Interpretation

| Metric | Formula | Meaning |
| --- | --- | --- |
| Support | support(A ∪ B) = transactions containing A and B / total transactions | How frequent the item combination is |
| Confidence | confidence(A → B) = support(A ∪ B) / support(A) | Reliability of the rule |
| Lift | lift(A → B) = confidence(A → B) / support(B) | Gain over random co-occurrence; > 1 positive association, = 1 independence, < 1 negative association |

**Apriori correctness basis:** the Apriori property states that a k-itemset can be frequent only if all of its (k-1)-subsets are frequent. This downward-closure property is what permits the pruning step, guaranteeing that no frequent itemset is ever discarded.

**Complexity:** candidate generation is combinatorial; generation of k-itemsets is O(C(n, k) · |B|) in the worst case. Practical tractability is achieved by threshold tuning — raising min support sharply reduces the candidate space.

### 5.4 Data Model

#### In-Memory Structures

| Structure | Type | Fields | Notes |
| --- | --- | --- | --- |
| `DataFrame` (raw) | pandas | all source columns | Long format, pre-clean |
| `DataFrame` (clean) | pandas | TransactionID, Item (+ optional) | Deduplicated, trimmed |
| `DataFrame` (matrix) | pandas | TransactionID index + one 0/1 column per item | Sparse-friendly |
| `DataFrame` (itemsets) | pandas | `support` | One row per frequent itemset |
| `DataFrame` (rules) | pandas | `antecedents`, `consequents`, `support`, `confidence`, `lift` | Final scored rule set |

#### Rule Output Schema

| Column | Type | Example | Description |
| --- | --- | --- | --- |
| antecedents | frozenset | {Milk, Bread} | LHS itemset |
| consequents | frozenset | {Eggs} | RHS itemset |
| support | float | 0.045 | Joint occurrence ratio |
| confidence | float | 0.310 | Conditional probability |
| lift | float | 1.420 | Association strength vs. baseline |

#### Persistent Artefacts

| Artefact | Format | Purpose |
| --- | --- | --- |
| Cleaned dataset | CSV | Auditable preprocessing output |
| Frequent itemsets | CSV | Intermediate result for re-analysis |
| Association rules | CSV | Final deliverable / report appendix |
| Charts | PNG | Report figures |

### 5.5 Sample Output

**Console summary:**

```
==========================================================
 RETAIL MARKET BASKET ANALYSIS
==========================================================
 Loaded dataset        : groceries.csv
 Raw records           : 9835
 Exact duplicates      : 687 removed
 Null records          : 12 removed
 Clean transactions    : 9136
 Distinct items        : 34
 Minimum support       : 0.05
 Minimum confidence    : 0.30
 Minimum lift          : 1.00
----------------------------------------------------------
 Frequent itemsets     : 27
 Association rules     : 14
----------------------------------------------------------
 Top items by frequency:
   Milk                : 2513 (0.2751)
   Bread               : 2201  (0.2409)
   Eggs                : 1724  (0.1887)
   Coffee              : 1490  (0.1631)
----------------------------------------------------------
 Top 5 rules by lift:
   {Butter} -> {Bread}      sup=0.0561 conf=0.3120 lift=2.714
   {Coffee} -> {Sugar}      sup=0.0523 conf=0.3010 lift=2.586
   {Yogurt} -> {Milk}       sup=0.0612 conf=0.3290 lift=2.481
   {Cheese} -> {Bread}      sup=0.0588 conf=0.3060 lift=2.412
   {Cereal} -> {Milk}       sup=0.0644 conf=0.3180 lift=2.307
==========================================================
```

**Rule table (excerpt):**

| Antecedent | Consequent | Support | Confidence | Lift |
| --- | --- | --- | --- | --- |
| {Butter} | {Bread} | 0.0561 | 0.3120 | 2.714 |
| {Coffee} | {Sugar} | 0.0523 | 0.3010 | 2.586 |
| {Yogurt} | {Milk} | 0.0612 | 0.3290 | 2.481 |
| {Cheese} | {Bread} | 0.0588 | 0.3060 | 2.412 |
| {Cereal} | {Milk} | 0.0644 | 0.3180 | 2.307 |

### 5.6 Implementation Plan

| Phase | Activities | Deliverables | Timeline |
| --- | --- | --- | --- |
| Phase 1 | Requirement finalization, dataset acquisition, environment setup | Approved SRS, `requirements.txt` | Week 1 |
| Phase 2 | M1 + M2 implementation: loader, cleaner, matrix builder | `data_loader.py`, `preprocessing.py` | Week 2 |
| Phase 3 | M3 + M4 + M5: Apriori mining, rule derivation, metric evaluation, export | `mining.py`, `evaluation.py` | Week 3 |
| Phase 4 | M6 + M7: bar chart, scatter plot, network graph, query filter | `visualization.py`, `queries.py` | Week 4 |
| Phase 5 | M8: CLI entry point and Streamlit dashboard | `main.py`, `app.py` | Week 5 |
| Phase 6 | Unit and integration testing, threshold tuning, performance validation | `tests/`, test report | Week 6 |
| Phase 7 | Documentation, final report, demonstration | SRS, report, demo | Week 7 |

**Milestones:** dataset pipeline validated end-to-end (end of Week 3); first complete rule set generated (end of Week 4); presentation-ready build (end of Week 6).

---

## 6. Testing Plan

### 6.1 Testing Strategy

| Level | Scope | Technique |
| --- | --- | --- |
| Unit Testing | Preprocessing, metric, filtering functions | Assertions on known small fixtures |
| Integration Testing | M1 → M2 → M3 → M4 → M5 end-to-end pipeline | Run full pipeline on a labelled sample dataset |
| Validation Testing | Statistical correctness of output | Hand-verify support/confidence/lift against manual counts |
| Performance Testing | Runtime and memory at target scale | Time-stamped runs on the 100,000-transaction dataset |
| Usability Testing | Threshold tuning and dashboard navigation | Guided walkthrough with a non-technical Retail Manager |
| Regression Testing | Stability after refactoring | Re-run the full test suite after every module change |

### 6.2 Test Cases

| TC ID | Test Description | Input | Expected Result |
| --- | --- | --- | --- |
| TC-01 | Load a valid CSV | `groceries.csv` | DataFrame loaded; row count matches file |
| TC-02 | Missing mandatory column | CSV without `Item` | Descriptive error raised, no crash |
| TC-03 | Null value handling | CSV with 5 null items | 5 rows dropped; count reported |
| TC-04 | Duplicate removal | CSV with repeated identical rows | Duplicates removed; unique count correct |
| TC-05 | Whitespace trimming | Item `" Milk "` | Normalized to `"Milk"` |
| TC-06 | Binary matrix correctness | 3-transaction fixture | Matrix matches hand-computed values |
| TC-07 | Frequent itemset generation | Fixture, min_support = 0.5 | Exactly the expected itemsets returned |
| TC-08 | Minimum support strictness | min_support = 1.0 | No spurious itemsets returned |
| TC-09 | Rule derivation direction | Itemset {Milk, Bread} | Both Milk→Bread and Bread→Milk produced |
| TC-10 | Confidence calculation | Known fixture | Value matches manual division to 4 decimals |
| TC-11 | Lift calculation | Known fixture | Value matches confidence / support(consequent) |
| TC-12 | Lift filtering | min_lift = 3.0 | Only rules with lift ≥ 3.0 retained |
| TC-13 | Sorting order | Full rule set | Descending lift, then descending confidence |
| TC-14 | Rule export | Export to CSV | File written with correct headers and row count |
| TC-15 | Interactive filter | Query antecedent `Milk` | Only rules with Milk in LHS returned |
| TC-16 | Empty result handling | Query for a non-existent item | Graceful empty result, no exception |
| TC-17 | Parameter sensitivity | min_support 0.01 vs 0.10 | Higher support yields fewer itemsets and rules |
| TC-18 | Performance benchmark | 100,000 transactions | Preprocessing < 30 s; Apriori < 60 s |
| TC-19 | Reproducibility | Two identical runs | Byte-identical exported rule files |
| TC-20 | Empty dataset | CSV with headers only | Descriptive error, no crash |

### 6.3 Acceptance Criteria

The system is accepted when: all Must-priority FRs (FR-01 to FR-16, FR-18, FR-20, FR-22) are implemented and demonstrated; all Must and Should NFRs are met or formally justified as exceptions; TC-01 to TC-17, TC-19, and TC-20 pass; and TC-18 meets its stated time bounds.

---

## 7. Conclusion

This SRS document specifies a complete, achievable, and academically defensible design for a Retail Market Basket Analysis System. The design satisfies its stated business objective: transforming raw retail transaction data into actionable merchandising intelligence through Apriori-based association rule mining.

The system fulfills its four core functional pillars — reliable data ingestion and preprocessing, frequent itemset generation, rule derivation with quantitative evaluation, and multi-format visualization — while satisfying its non-functional obligations for performance, portability, modularity, and usability. The requirement set is internally consistent: each functional requirement traces to a module in the design, and each module maps back to a test case in the testing plan, ensuring complete traceability from specification to verification.

By converting statistically significant co-occurrence patterns into product pairings that retail managers can act upon directly — end-cap placement, bundle construction, and targeted promotion — the system delivers measurable commercial value beyond its academic purpose. Future enhancements may include support for sequential and time-based pattern mining, integration with live POS streams, and deployment of recommendation engines built on the discovered rules.

---

## 8. Appendix

### 8.1 Glossary

| Term | Definition |
| --- | --- |
| Support | Proportion of transactions in which an itemset appears. |
| Confidence | Conditional probability that the consequent appears given the antecedent. |
| Lift | Ratio of observed to expected co-occurrence; measures association strength. |
| Frequent itemset | An itemset whose support meets the minimum support threshold. |
| Association rule | A directional implication of the form Antecedent → Consequent. |
| Apriori | A bottom-up algorithm that generates frequent itemsets by iteratively extending and pruning candidates. |
| Antecedent (LHS) | The itemset on the left-hand side of a rule. |
| Consequent (RHS) | The itemset on the right-hand side of a rule. |
| Binary matrix | Transaction-by-item grid of 0/1 values used as Apriori input. |
| Market basket analysis | Study of which products are frequently purchased together. |
| KDD | Knowledge Discovery in Databases — the broader process this system instantiates. |
| ETL | Extract, Transform, Load — the data preparation pipeline represented by Module M2. |

### 8.2 Requirement Traceability Matrix

| Requirement | Module | Test Cases |
| --- | --- | --- |
| FR-01, FR-02, FR-03 | M1 | TC-01, TC-02 |
| FR-04, FR-05, FR-06, FR-07 | M2 | TC-03, TC-04, TC-05 |
| FR-08 | M2 | TC-06 |
| FR-09, FR-10, FR-11 | M3 | TC-07, TC-08, TC-17 |
| FR-12, FR-13 | M4 | TC-09 |
| FR-14, FR-15, FR-16, FR-17 | M5 | TC-10, TC-11, TC-12, TC-13, TC-14 |
| FR-18, FR-19, FR-20 | M6 | — (visual inspection) |
| FR-21 | M7 | TC-15, TC-16 |
| FR-22, FR-23 | M8 | TC-19 |
| FR-24 | M8 | — (optional interface) |

### 8.3 References

1. Han, J., Kamber, M. - *Data Mining: Concepts and Techniques*, 3rd Edition, Morgan Kaufmann, 2006.
2. Tan, P.N., Steinbach, M., Kumar, V. - *Introduction to Data Mining*, Pearson, 2018.
3. Agrawal, R., Imieliński, T., Swami, A. - *Mining Association Rules Between Sets of Items in Large Databases*, SIGMOD, 1993.
4. Brin, S., Motwani, R. - *Fast Algorithms for Mining Association Rules*, VLDB, 1995.
5. Lab Experiment 3 - Association Rule Mining using WEKA.
6. Lab Experiment 9 - Python program for frequent itemsets and association rules.