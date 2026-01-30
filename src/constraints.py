"""Constraint application engine.

Three-stage cascade:
  1. Score threshold (quality gate)
  2. Top-K filtering (capacity/triage gate)
  3. Review budget (attention/time gate)

INVARIANT (Critical):
  shown UNION dropped = after_threshold
  shown INTERSECT dropped = empty set

Outcome taxonomy (locked terms):
  - below threshold
  - eligible but dropped by capacity
  - shown to human

UI Semantics (UPDATED):
  - "Dropped (After Threshold)" = candidates eliminated post-threshold
  - "Below Threshold" = separate display/count
"""

import pandas as pd
from typing import Dict, Any, Optional


def compute_boundary_items(
    after_threshold: pd.DataFrame,
    after_topk: pd.DataFrame,
    shown: pd.DataFrame,
    threshold: float,
    top_k: int,
    budget: int,
    budget_actual: int
) -> Dict[str, Any]:
    """Compute boundary items and scores for visualization.

    Args:
        after_threshold: Candidates after threshold filter
        after_topk: Candidates after top-K filter
        shown: Final shown candidates
        threshold: Score threshold value
        top_k: Top-K parameter
        budget: Review budget parameter
        budget_actual: Actual budget used (min of budget and available)

    Returns:
        Dictionary with boundary scores and items:
            - threshold, top_k, budget: Input parameters
            - kth_score, kth_item: K-th boundary (if top-K binding)
            - budget_score, budget_item: Budget boundary (if budget binding)
    """
    boundary_items: Dict[str, Any] = {
        'threshold': threshold,
        'top_k': top_k,
        'budget': budget,
        'kth_score': None,
        'kth_item': None,
        'budget_score': None,
        'budget_item': None
    }

    # Kth boundary (only if top-K constraint is binding)
    is_topk_binding = top_k < len(after_threshold)
    if len(after_topk) > 0 and is_topk_binding:
        boundary_items['kth_score'] = after_topk.iloc[-1]['score']
        boundary_items['kth_item'] = after_topk.iloc[-1].to_dict()

    # Budget boundary (if budget constraint was binding)
    is_budget_binding = len(shown) == budget_actual and budget_actual < len(after_topk)
    if len(shown) > 0 and is_budget_binding:
        boundary_items['budget_score'] = shown.iloc[-1]['score']
        boundary_items['budget_item'] = shown.iloc[-1].to_dict()

    return boundary_items


def apply_constraints(
    df: pd.DataFrame,
    threshold: float,
    top_k: int,
    budget: int
) -> Dict[str, Any]:
    """Apply three-stage constraint cascade.

    Parameters:
      df: Scored candidates (must have 'score' column)
      threshold: Minimum score to pass quality gate
      top_k: Maximum candidates after threshold
      budget: Maximum candidates for human review

    Returns:
      Dictionary with:
        - all_candidates: All candidates sorted by score
        - after_threshold: Candidates passing threshold
        - after_topk: Top-K candidates
        - shown: Final shown set (within budget)
        - dropped: Dropped candidates with reasons & margins
        - boundary_items: Cutoff scores and items
        - counts: Summary counts

    Invariants enforced:
      - shown UNION dropped = after_threshold (partition)
      - shown INTERSECT dropped = empty set (disjoint)
      - Sorting: score DESC, id ASC (stable tie-breaking)
      - Margins: all non-negative
    """
    # Sort once with stable tie-breaking (UPDATED: use mergesort)
    all_candidates = df.sort_values(
        ['score', 'id'],
        ascending=[False, True],
        kind='mergesort'  # Explicitly stable, widely supported
    ).reset_index(drop=True)

    # Stage 1: Threshold filter
    after_threshold = all_candidates[
        all_candidates['score'] >= threshold
    ].copy().reset_index(drop=True)

    # Stage 2: Top-K filter
    k_actual = min(top_k, len(after_threshold))
    after_topk = after_threshold.iloc[:k_actual].copy().reset_index(drop=True)

    # Stage 3: Budget cap
    budget_actual = min(budget, len(after_topk))
    shown = after_topk.iloc[:budget_actual].copy().reset_index(drop=True)

    # Compute dropped set (only from after_threshold)
    shown_ids = set(shown['id'])
    dropped_candidates = []

    # Dropped reason: eligible but dropped by capacity (top-K)
    if len(after_topk) < len(after_threshold):
        outside_topk = after_threshold[
            ~after_threshold['id'].isin(after_topk['id'])
        ].copy()

        kth_score = after_topk.iloc[-1]['score']
        outside_topk['dropped_reason'] = 'eligible but dropped by capacity'
        outside_topk['capacity_stage'] = 'top_k'
        outside_topk['inclusion_margin'] = kth_score - outside_topk['score']

        dropped_candidates.append(outside_topk)

    # Dropped reason: eligible but dropped by capacity (budget)
    if len(shown) < len(after_topk):
        over_budget = after_topk[
            ~after_topk['id'].isin(shown_ids)
        ].copy()

        budget_score = shown.iloc[-1]['score']
        over_budget['dropped_reason'] = 'eligible but dropped by capacity'
        over_budget['capacity_stage'] = 'budget'
        over_budget['inclusion_margin'] = budget_score - over_budget['score']

        dropped_candidates.append(over_budget)

    # Combine and sort dropped by margin (closest first)
    if dropped_candidates:
        dropped = pd.concat(dropped_candidates, ignore_index=True)
        dropped = dropped.sort_values(
            ['inclusion_margin', 'score', 'id'],
            ascending=[True, False, True],
            kind='mergesort'  # Stable sort
        ).reset_index(drop=True)
    else:
        # No drops - empty DataFrame with correct schema
        dropped = pd.DataFrame(columns=list(df.columns) +
                                        ['dropped_reason', 'capacity_stage', 'inclusion_margin'])

    # Compute boundary items for visualization
    boundary_items = compute_boundary_items(
        after_threshold, after_topk, shown,
        threshold, top_k, budget, budget_actual
    )

    # Counts
    counts = {
        'n_total': len(all_candidates),
        'n_after_threshold': len(after_threshold),
        'n_after_topk': len(after_topk),
        'n_shown': len(shown),
        'n_dropped': len(dropped)
    }

    # INVARIANT CHECKS
    assert set(shown['id']) | set(dropped['id']) == set(after_threshold['id']), \
        "Partition invariant violated: shown UNION dropped != after_threshold"
    assert set(shown['id']) & set(dropped['id']) == set(), \
        "Disjoint invariant violated: shown INTERSECT dropped != empty"
    assert counts['n_shown'] + counts['n_dropped'] == counts['n_after_threshold'], \
        "Count invariant violated"

    # Margin checks
    if len(dropped) > 0:
        assert (dropped['inclusion_margin'] >= 0).all(), \
            "Negative margins detected"

    return {
        'all_candidates': all_candidates,
        'after_threshold': after_threshold,
        'after_topk': after_topk,
        'shown': shown,
        'dropped': dropped,
        'boundary_items': boundary_items,
        'counts': counts
    }
