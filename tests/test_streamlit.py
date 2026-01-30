"""Tests for Streamlit-specific functionality (NEW)."""

from src.data import generate_candidates
from src.model import score_candidates
from src.constraints import apply_constraints

def test_cache_invalidation():
    """Cached functions must respect all parameters."""
    # Note: Can't actually test @st.cache_data decorator in pytest,
    # but we can test the underlying functions

    # Test 1: Different seeds produce different results
    df1 = generate_candidates(seed=42, n_candidates=120, edge_fraction=0.15)
    df1 = score_candidates(df1)

    df2 = generate_candidates(seed=99, n_candidates=120, edge_fraction=0.15)
    df2 = score_candidates(df2)

    assert not df1['score'].equals(df2['score']), \
        "Different seeds should produce different scores"

    # Test 2: Different thresholds produce different results
    df = generate_candidates(seed=42, n_candidates=120)
    df = score_candidates(df)

    result1 = apply_constraints(df, threshold=0.3, top_k=20, budget=10)
    result2 = apply_constraints(df, threshold=0.7, top_k=20, budget=10)

    assert result1['counts']['n_shown'] != result2['counts']['n_shown'], \
        "Different thresholds should produce different results"

    # Test 3: Different top_k produces different results
    result3 = apply_constraints(df, threshold=0.5, top_k=10, budget=10)
    result4 = apply_constraints(df, threshold=0.5, top_k=30, budget=10)

    # Unless top_k > n_after_threshold, results should differ
    if (len(result3['after_threshold']) > 10 and
        len(result4['after_threshold']) > 10):
        assert len(result3['after_topk']) != len(result4['after_topk']), \
            "Different top_k should produce different results"

def test_dataframe_hash_deterministic():
    """DataFrame hash is deterministic."""
    from src.utils import compute_dataframe_hash

    df1 = generate_candidates(seed=42, n_candidates=120)
    df1 = score_candidates(df1)

    df2 = generate_candidates(seed=42, n_candidates=120)
    df2 = score_candidates(df2)

    hash1 = compute_dataframe_hash(df1)
    hash2 = compute_dataframe_hash(df2)

    assert hash1 == hash2, "Same data should produce same hash"
