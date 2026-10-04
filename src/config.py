"""Shared constants and default thresholds for the whole pipeline.

Per collaboration rule CP-2 this file is **append-only within a module
block**: contributors may add new named constants but must never rename or
delete an existing one, because every other module imports from here.

Per the action plan (Phase 0.2), no module may hard-code a threshold
internally. If you need a new tunable, add it below and announce it in the
weekly sync.

Owner: C1. See docs/INTERFACES.md section 2.
"""

# --- Dataset schema -------------------------------------------------------

DEFAULT_ITEM_COL = "Item"
DEFAULT_TXN_COL = "TransactionID"

# --- Mining thresholds ----------------------------------------------------

DEFAULT_MIN_SUPPORT = 0.01
DEFAULT_MIN_CONFIDENCE = 0.30
DEFAULT_MIN_LIFT = 1.00

# Warn the user when min_support drops below this, because Apriori
# candidate generation grows combinatorially (risk R-03).
MIN_SUPPORT_FLOOR = 0.001

# --- Presentation ---------------------------------------------------------

TOP_N_ITEMS = 15
TOP_N_RULES = 20

# --- Output artefacts -----------------------------------------------------

RULES_FILENAME = "rules.csv"
ITSETS_FILENAME = "itemsets.csv"