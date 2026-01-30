"""Fixed-coefficient logistic regression for candidate scoring.

Model specification (PLAIN TEXT):
  z = b0 + b1*urgency + b2*confidence + b3*impact + b4*cost
  score = sigmoid(z) = 1 / (1 + exp(-z))

Where:
  b0 = -1.2  (intercept, calibrated for ~50% pass rate at threshold=0.5)
  b1 = 1.5   (urgency: dominant factor for time-sensitive decisions)
  b2 = 1.0   (confidence: baseline signal quality)
  b3 = 0.8   (impact: potential value, slightly less than confidence)
  b4 = -0.6  (cost: penalty for resource consumption)

Rationale:
  - Coefficients chosen to create realistic score distribution with std > 0.15
  - urgency > confidence > impact reflects common prioritization logic
  - cost is negative (higher cost -> lower score)
  - NOT optimized to any metric; fixed for determinism and interpretability

Uses scipy.special.expit for numerically stable sigmoid computation.
"""

import pandas as pd
import numpy as np
from typing import Dict
from scipy.special import expit

# Fixed coefficients (do NOT train/fit)
MODEL_COEFS = {
    'intercept': -1.2,
    'urgency': 1.5,      # Dominant: time-sensitive decisions
    'confidence': 1.0,   # Baseline: signal quality
    'impact': 0.8,       # Potential value
    'cost': -0.6,        # Penalty for resource consumption
}

# Detailed coefficient justification (for interviews):
"""
Intercept: -1.2
  Chosen to achieve ~50% pass rate at threshold=0.5
  Given expected feature means ~0.5:
    z = -1.2 + 1.5*0.5 + 1.0*0.5 + 0.8*0.5 - 0.6*0.5
      = -1.2 + 0.75 + 0.5 + 0.4 - 0.3 = 0.15
    score = sigmoid(0.15) ~= 0.537
  Half of candidates have priority < 0.5, so ~50% pass threshold

Urgency: 1.5
  1.5x weight vs confidence (1.0) reflects time-sensitive nature
  Score change ~0.10 when urgency goes 0->1
    Delta_z = 1.5, Delta_score ~= 0.35 at score=0.5

Confidence: 1.0
  Baseline unit weight (reference point for other coefficients)

Impact: 0.8
  Slightly less than confidence (0.8 vs 1.0) because
  uncertain potential value < certain signal quality

Cost: -0.6
  Negative (penalty), but smaller magnitude than positive factors
  Chosen so high-priority items still pass despite cost

Sensitivity analysis (from Phase 2.5 validation):
  - Changing urgency to 1.0-2.0: score std varies 0.14-0.18 (acceptable)
  - Changing intercept +/-0.2: pass rate varies 40%-60% (acceptable)
  - These specific values chosen for interpretability, not optimization
"""

def score_candidates(
    df: pd.DataFrame,
    coefs: Dict[str, float] = MODEL_COEFS
) -> pd.DataFrame:
    """Score candidates using fixed-coefficient logistic regression.

    Adds columns:
      - logit: Linear score z
      - score: Probability score sigmoid(z) in (0, 1)

    Parameters:
      df: DataFrame with columns [urgency, confidence, impact, cost]
      coefs: Coefficient dict (default: MODEL_COEFS)

    Returns:
      DataFrame with added 'logit' and 'score' columns

    Raises:
      AssertionError if scores contain NaN or Inf
    """
    # Linear combination (logit)
    z = (coefs['intercept'] +
         coefs['urgency'] * df['urgency'] +
         coefs['confidence'] * df['confidence'] +
         coefs['impact'] * df['impact'] +
         coefs['cost'] * df['cost'])

    # Add to dataframe
    df = df.copy()
    df['logit'] = z
    df['score'] = expit(z)  # Numerically stable sigmoid

    # Validation
    assert not df['score'].isna().any(), "NaN scores detected"
    assert not np.isinf(df['score']).any(), "Inf scores detected"
    assert (df['score'] > 0).all() and (df['score'] < 1).all(), \
        "Scores outside (0, 1)"

    return df
