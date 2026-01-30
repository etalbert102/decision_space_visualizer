"""Synthetic candidate data generation.

CRITICAL REQUIREMENTS:
1. Use np.random.default_rng(seed) - NO global state pollution
2. Fixed generation order (base, then edges A, B, C)
3. No shuffling after ID assignment
4. All features in [0, 1]

Determinism guarantee:
  Same seed + n_candidates -> identical output
  (within same numpy version and platform)
"""

import numpy as np
import pandas as pd

# Edge case configuration
DEFAULT_EDGE_FRACTION = 0.15  # 15% of candidates are edge cases
EDGE_CASE_TEMPLATES = 3  # Number of edge case templates (A, B, C)

def generate_candidates(
    seed: int = 42,
    n_candidates: int = 120,
    edge_fraction: float = DEFAULT_EDGE_FRACTION
) -> pd.DataFrame:
    """Generate synthetic candidates with base population + edge cases.

    Parameters:
      seed: Random seed (use default_rng, not global np.random.seed)
      n_candidates: Total number of candidates
      edge_fraction: Fraction of candidates that are edge cases (0.15 = 15%)

    Returns:
      DataFrame with columns: id, urgency, confidence, impact, cost, case_type

    Edge cases (evenly split across 3 templates):
      - Template A: High urgency, low confidence
      - Template B: High impact, high cost
      - Template C: Borderline (near threshold)
    """
    # CRITICAL: Local RNG, no global state
    rng = np.random.default_rng(seed)

    # Calculate split between base and edge cases
    n_base = int(n_candidates * (1 - edge_fraction))
    n_edge = n_candidates - n_base
    n_per_edge_template = n_edge // EDGE_CASE_TEMPLATES

    # BASE POPULATION (85%)
    # priority is internal variable, not in output schema
    priority = rng.beta(2, 5, size=n_base)

    base_df = pd.DataFrame({
        'urgency': np.clip(priority + rng.normal(0, 0.12, size=n_base), 0, 1),
        'confidence': np.clip(0.60 * priority + 0.20 + rng.normal(0, 0.14, size=n_base), 0, 1),
        'impact': np.clip(0.70 * priority + 0.10 + rng.normal(0, 0.13, size=n_base), 0, 1),
        'cost': np.clip(1.00 - priority + rng.normal(0, 0.12, size=n_base), 0, 1),
        'case_type': 'base'
    })

    # EDGE CASE A: High urgency, low confidence
    edge_a = pd.DataFrame({
        'urgency': rng.beta(6, 2, n_per_edge_template),
        'confidence': rng.beta(2, 6, n_per_edge_template),
        'impact': rng.beta(4, 3, n_per_edge_template),
        'cost': rng.beta(4, 3, n_per_edge_template),
        'case_type': 'high_urg_low_conf'
    })

    # EDGE CASE B: High impact, high cost
    edge_b = pd.DataFrame({
        'urgency': rng.beta(3, 4, n_per_edge_template),
        'confidence': rng.beta(4, 3, n_per_edge_template),
        'impact': rng.beta(7, 2, n_per_edge_template),
        'cost': rng.beta(7, 2, n_per_edge_template),
        'case_type': 'high_impact_high_cost'
    })

    # EDGE CASE C: Borderline cluster
    # Adjust n for remainder (handles cases where n_edge not divisible by 3)
    n_borderline = n_edge - (EDGE_CASE_TEMPLATES - 1) * n_per_edge_template

    edge_c = pd.DataFrame({
        'urgency': np.clip(rng.normal(0.55, 0.08, n_borderline), 0, 1),
        'confidence': np.clip(rng.normal(0.50, 0.10, n_borderline), 0, 1),
        'impact': np.clip(rng.normal(0.55, 0.09, n_borderline), 0, 1),
        'cost': np.clip(rng.normal(0.50, 0.10, n_borderline), 0, 1),
        'case_type': 'borderline'
    })

    # CONCATENATE in FIXED order (do not shuffle!)
    df = pd.concat([base_df, edge_a, edge_b, edge_c], ignore_index=True)

    # ASSIGN STABLE IDs in row order
    df.insert(0, 'id', [f'C{i:04d}' for i in range(len(df))])

    # Verify all features in [0, 1]
    feature_cols = ['urgency', 'confidence', 'impact', 'cost']
    for col in feature_cols:
        assert (df[col] >= 0).all() and (df[col] <= 1).all(), \
            f"Feature {col} out of bounds"

    return df
