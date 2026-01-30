import pandas as pd
import numpy as np
from src.data import generate_candidates

def test_determinism():
    """Same seed produces identical results."""
    df1 = generate_candidates(seed=42, n_candidates=120)
    df2 = generate_candidates(seed=42, n_candidates=120)

    # Use tolerances for float comparisons
    pd.testing.assert_frame_equal(
        df1, df2,
        check_exact=False,
        atol=1e-10,
        rtol=1e-10
    )

def test_size_invariant():
    """Correct number of base + edge cases."""
    n = 120
    edge_frac = 0.15
    df = generate_candidates(seed=42, n_candidates=n, edge_fraction=edge_frac)

    assert len(df) == n
    n_edge = int(n * edge_frac)
    assert (df['case_type'] != 'base').sum() == n_edge

def test_feature_bounds():
    """All features in [0, 1]."""
    df = generate_candidates(seed=42, n_candidates=120)
    feature_cols = ['urgency', 'confidence', 'impact', 'cost']

    for col in feature_cols:
        assert (df[col] >= 0).all(), f"{col} has values < 0"
        assert (df[col] <= 1).all(), f"{col} has values > 1"

def test_id_stability():
    """IDs are stable and sequential."""
    df = generate_candidates(seed=42, n_candidates=120)

    expected_ids = [f'C{i:04d}' for i in range(120)]
    assert list(df['id']) == expected_ids

def test_no_global_state_pollution():
    """Using generate_candidates doesn't affect global np.random."""
    np.random.seed(999)
    before = np.random.randint(0, 1000)

    np.random.seed(999)
    _ = generate_candidates(seed=42, n_candidates=120)
    after = np.random.randint(0, 1000)

    assert before == after, "Global random state was polluted"
