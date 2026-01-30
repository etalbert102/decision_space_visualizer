import pandas as pd
from src.data import generate_candidates
from src.model import score_candidates
from src.constraints import apply_constraints

def make_test_data(n=20):
    """Helper: generate and score test data."""
    df = generate_candidates(seed=42, n_candidates=n)
    df = score_candidates(df)
    return df

def test_comprehensive_invariants():
    """All invariants must hold (ENHANCED)."""
    df = make_test_data(50)
    result = apply_constraints(df, threshold=0.5, top_k=20, budget=10)

    shown = set(result['shown']['id'])
    dropped = set(result['dropped']['id'])
    after_thresh = set(result['after_threshold']['id'])

    # Partition: shown UNION dropped = after_threshold
    assert shown | dropped == after_thresh, "Partition violated"

    # Disjoint: shown INTERSECT dropped = empty
    assert shown & dropped == set(), "Sets not disjoint"

    # Counts
    assert len(shown) + len(dropped) == len(after_thresh), "Count mismatch"

    # Uniqueness (no duplicates)
    assert len(shown) == result['shown'].shape[0]
    assert len(dropped) == result['dropped'].shape[0]

    # Sorting
    if len(result['shown']) > 1:
        assert result['shown']['score'].is_monotonic_decreasing or \
               result['shown']['score'].nunique() == 1, "Shown not sorted"

    if len(result['dropped']) > 1:
        assert result['dropped']['inclusion_margin'].is_monotonic_increasing or \
               result['dropped']['inclusion_margin'].nunique() == 1, \
               "Dropped not sorted by margin"

    # Margins non-negative
    if len(result['dropped']) > 0:
        assert (result['dropped']['inclusion_margin'] >= 0).all(), \
            "Negative margins"

    # Reasons present
    if len(result['dropped']) > 0:
        assert result['dropped']['dropped_reason'].notna().all(), \
            "Missing drop reasons"
        assert (result['dropped']['dropped_reason'] ==
                'eligible but dropped by capacity').all(), \
            "Dropped reason not standardized"

    # NEW: Boundary item consistency
    if result['boundary_items']['kth_item'] is not None:
        kth_id = result['boundary_items']['kth_item']['id']
        assert kth_id in result['after_topk']['id'].values, \
            "Kth item not in after_topk set"
        assert kth_id == result['after_topk'].iloc[-1]['id'], \
            "Kth item is not last item in after_topk"

    if result['boundary_items']['budget_item'] is not None:
        budget_id = result['boundary_items']['budget_item']['id']
        assert budget_id in result['shown']['id'].values, \
            "Budget item not in shown set"
        assert budget_id == result['shown'].iloc[-1]['id'], \
            "Budget item is not last item in shown"

    # NEW: Margin calculation correctness
    for idx, row in result['dropped'].iterrows():
        if row['capacity_stage'] == 'top_k':
            expected_margin = (result['boundary_items']['kth_score'] -
                             row['score'])
            assert abs(row['inclusion_margin'] - expected_margin) < 1e-6, \
                f"Margin mismatch for {row['id']}"

        elif row['capacity_stage'] == 'budget':
            expected_margin = (result['boundary_items']['budget_score'] -
                             row['score'])
            assert abs(row['inclusion_margin'] - expected_margin) < 1e-6, \
                f"Margin mismatch for {row['id']}"

    # NEW: ID format validation
    all_ids = pd.concat([result['shown']['id'], result['dropped']['id']])
    for id_val in all_ids:
        assert id_val.startswith('C'), f"Invalid ID prefix: {id_val}"
        assert len(id_val) == 5, f"Invalid ID length: {id_val}"
        assert id_val[1:].isdigit(), f"Invalid ID format: {id_val}"

    # NEW: No duplicate IDs
    assert len(all_ids) == len(set(all_ids)), "Duplicate IDs detected"

def test_boundary_edge_cases():
    """Boundary items correct when K > n or budget > K."""
    df = make_test_data(10)

    # K > n
    result = apply_constraints(df, threshold=0, top_k=100, budget=5)
    assert len(result['after_topk']) <= 10
    assert len(result['shown']) == 5

    # budget > K
    result = apply_constraints(df, threshold=0, top_k=5, budget=20)
    assert len(result['shown']) == 5

    # K = 1
    result = apply_constraints(df, threshold=0, top_k=1, budget=1)
    assert len(result['shown']) == 1
    if result['boundary_items']['kth_item'] is not None:
        assert result['boundary_items']['kth_item']['id'] == result['shown'].iloc[0]['id']

def test_tie_breaking_stability():
    """Tied scores broken by ID ascending."""
    df = pd.DataFrame({
        'id': ['C0003', 'C0001', 'C0002', 'C0004'],
        'score': [0.6, 0.5, 0.5, 0.4],
        'urgency': [0.5] * 4,
        'confidence': [0.5] * 4,
        'impact': [0.5] * 4,
        'cost': [0.5] * 4,
        'logit': [0.0] * 4,
        'case_type': ['test'] * 4
    })

    result = apply_constraints(df, threshold=0.4, top_k=3, budget=2)

    # After sorting: C0003 (0.6), C0001 (0.5), C0002 (0.5), C0004 (0.4)
    # After threshold (>=0.4): all 4 pass
    # Top-3: C0003, C0001, C0002
    # Shown (budget=2): C0003, C0001
    # Dropped: C0002 (budget), C0004 (top_k)

    assert len(result['shown']) == 2
    assert list(result['shown']['id']) == ['C0003', 'C0001']
    assert len(result['dropped']) == 2
    # C0002 should be first in dropped (over_budget, margin=0)
    # Then C0004 (outside_topK, margin=0.1)
    assert result['dropped'].iloc[0]['id'] == 'C0002'
    assert result['dropped'].iloc[0]['dropped_reason'] == 'eligible but dropped by capacity'
    assert result['dropped'].iloc[0]['capacity_stage'] == 'budget'
    assert result['dropped'].iloc[1]['id'] == 'C0004'
    assert result['dropped'].iloc[1]['dropped_reason'] == 'eligible but dropped by capacity'
    assert result['dropped'].iloc[1]['capacity_stage'] == 'top_k'

def test_no_drops_when_all_pass():
    """Empty dropped set when all pass constraints."""
    df = make_test_data(10)
    result = apply_constraints(df, threshold=0.0, top_k=50, budget=50)

    assert len(result['dropped']) == 0
    assert len(result['shown']) == len(df)

def test_margin_calculations():
    """Margins calculated correctly."""
    df = make_test_data(20)
    result = apply_constraints(df, threshold=0.5, top_k=10, budget=5)

    if len(result['dropped']) > 0:
        # All margins should be positive
        assert (result['dropped']['inclusion_margin'] > 0).all()

        # Closest dropped has smallest margin
        closest = result['dropped'].iloc[0]
        assert closest['inclusion_margin'] == result['dropped']['inclusion_margin'].min()
