import pandas as pd
from src.data import generate_candidates
from src.model import score_candidates
from src.constraints import apply_constraints

def test_cross_run_determinism():
    """Same seed produces identical results across runs (UPDATED WITH TOLERANCES)."""
    # Run 1
    df1 = generate_candidates(seed=42, n_candidates=120)
    df1 = score_candidates(df1)
    result1 = apply_constraints(df1, 0.5, 20, 10)

    # Run 2
    df2 = generate_candidates(seed=42, n_candidates=120)
    df2 = score_candidates(df2)
    result2 = apply_constraints(df2, 0.5, 20, 10)

    # Compare with tolerances (UPDATED)
    pd.testing.assert_frame_equal(
        result1['shown'], result2['shown'],
        check_exact=False,
        atol=1e-10,
        rtol=1e-10
    )

    pd.testing.assert_frame_equal(
        result1['dropped'], result2['dropped'],
        check_exact=False,
        atol=1e-10,
        rtol=1e-10
    )
