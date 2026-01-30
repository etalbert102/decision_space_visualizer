"""Type definitions and data classes.

INVARIANT DEFINITION (Critical - aligns code/tests/UI):
  shown UNION dropped = after_threshold
  shown INTERSECT dropped = empty set

Meaning:
  - "dropped" includes only candidates that passed threshold
  - below_threshold items are NOT in "dropped" table
  - Focus on "near misses" rather than clear rejects

UI Semantics:
  - "Dropped (After Threshold)" = eliminated by top-K or budget
  - "Below Threshold" = separate display, not in "dropped"
"""

from dataclasses import dataclass
from typing import Literal

@dataclass
class Candidate:
    """Individual candidate with features and scores.

    Note: 'priority' is internal to data generation, not in schema.
    """
    id: str
    urgency: float      # [0, 1]
    confidence: float   # [0, 1]
    impact: float       # [0, 1]
    cost: float         # [0, 1]
    case_type: str      # 'base' | 'high_urg_low_conf' | 'high_impact_high_cost' | 'borderline'

    # Added by model.score_candidates()
    logit: float = 0.0
    score: float = 0.0

    # Added by constraints.apply_constraints()
    rank: int = 0
    dropped_reason: str = ""
    inclusion_margin: float = 0.0

# Outcome taxonomy (locked terms)
OutcomeCategory = Literal[
    "below threshold",
    "eligible but dropped by capacity",
    "shown to human",
]
