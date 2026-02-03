"""Decision Space Visualizer - Streamlit UI.

Caching strategy (UPDATED - NO JSON ROUND-TRIP):
  - Data generation & scoring: cached by seed, n_candidates
  - Constraint application: cached by DataFrame hash + parameters
  - Never access st.session_state in cached functions

Performance target: < 2s for UI updates after caching
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from src.data import generate_candidates
from src.model import score_candidates
from src.constraints import apply_constraints
from src.utils import compute_dataframe_hash, format_dataframe_for_display

# Page config
st.set_page_config(
    page_title="Decision Space Visualizer",
    layout="wide"
)


# UI HELPER FUNCTIONS
def render_candidate_table(
    results: Dict[str, Any],
    table_type: str,
    display_cols: List[str],
    float_cols: List[str],
    rows_per_table: int
) -> None:
    """Render a candidate table based on type.

    Args:
        results: Results dictionary from apply_constraints
        table_type: One of 'all', 'shown', 'dropped'
        display_cols: Columns to display
        float_cols: Columns to format as floats
        rows_per_table: Maximum rows to show
    """
    if table_type == 'all':
        df = results['all_candidates'][display_cols].head(rows_per_table)
        st.dataframe(
            format_dataframe_for_display(df, float_cols),
            hide_index=True,
            use_container_width=True
        )
    elif table_type == 'shown':
        if len(results['shown']) > 0:
            df = results['shown'][display_cols].head(rows_per_table)
            st.dataframe(
                format_dataframe_for_display(df, float_cols),
                hide_index=True,
                use_container_width=True
            )
        else:
            st.write("No candidates shown (none passed constraints)")
    elif table_type == 'dropped':
        if len(results['dropped']) > 0:
            dropped_display_cols = display_cols + ['dropped_reason', 'capacity_stage', 'inclusion_margin']
            df = results['dropped'][dropped_display_cols].head(rows_per_table)
            st.dataframe(
                format_dataframe_for_display(
                    df,
                    float_cols + ['inclusion_margin'],
                    {'inclusion_margin': 'Score Gap', 'dropped_reason': 'Reason', 'capacity_stage': 'Stage'}
                ),
                hide_index=True,
                use_container_width=True
            )
        else:
            st.write("No candidates dropped (all passed constraints)")


def get_boundary_for_stage(
    closest: pd.Series,
    boundary: Dict[str, Any],
    top_k: int,
    budget: int
) -> Tuple[Optional[Dict[str, Any]], str]:
    """Get boundary item and label based on capacity stage.

    Args:
        closest: Closest dropped candidate
        boundary: Boundary items dictionary
        top_k: Top-K parameter
        budget: Budget parameter

    Returns:
        Tuple of (boundary_item dict or None, boundary_label string)
    """
    boundary_item = None
    boundary_label = ""

    if closest['capacity_stage'] == 'top_k' and boundary['kth_item'] is not None:
        boundary_item = boundary['kth_item']
        boundary_label = f"Kth item (K={top_k})"
    elif closest['capacity_stage'] == 'budget' and boundary['budget_item'] is not None:
        boundary_item = boundary['budget_item']
        boundary_label = f"Budget boundary (budget={budget})"

    return boundary_item, boundary_label


def render_feature_comparison(
    closest: pd.Series,
    boundary_item: Dict[str, Any],
    boundary_label: str
) -> None:
    """Render feature comparison table between dropped and boundary items.

    Args:
        closest: Closest dropped candidate
        boundary_item: Boundary item for comparison
        boundary_label: Label describing the boundary
    """
    st.write(f"**Feature comparison** (dropped vs. {boundary_label}):")

    feature_cols_comp = ['urgency', 'confidence', 'impact', 'cost']
    comparison = pd.DataFrame({
        'Feature': feature_cols_comp,
        'Dropped': [closest[f] for f in feature_cols_comp],
        'Boundary': [boundary_item[f] for f in feature_cols_comp],
        'Delta': [closest[f] - boundary_item[f] for f in feature_cols_comp]
    })

    st.dataframe(
        comparison.style.format({
            'Dropped': '{:.3f}',
            'Boundary': '{:.3f}',
            'Delta': '{:+.3f}'
        }),
        hide_index=True,
        use_container_width=True
    )


def render_score_histogram(
    df_scored: pd.DataFrame,
    threshold: float,
    boundary: Dict[str, Any]
) -> None:
    """Render score distribution histogram with boundary lines.

    Args:
        df_scored: DataFrame with scored candidates
        threshold: Score threshold value
        boundary: Boundary items with kth_score and budget_score
    """
    import matplotlib.pyplot as plt

    # Dynamic bin count
    MIN_HISTOGRAM_BINS = 10
    MAX_HISTOGRAM_BINS = 30
    BIN_SIZE_DIVISOR = 5
    n_bins = max(MIN_HISTOGRAM_BINS, min(MAX_HISTOGRAM_BINS, len(df_scored) // BIN_SIZE_DIVISOR))

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.hist(df_scored['score'], bins=n_bins, alpha=0.7, edgecolor='black')
    ax.axvline(threshold, color='red', linestyle='--', label=f'Threshold ({threshold:.2f})')

    # Use explicit None checks
    if boundary['kth_score'] is not None:
        ax.axvline(boundary['kth_score'], color='orange', linestyle='--',
                  label=f'K boundary ({boundary["kth_score"]:.2f})')

    if boundary['budget_score'] is not None:
        ax.axvline(boundary['budget_score'], color='green', linestyle='--',
                  label=f'Budget boundary ({boundary["budget_score"]:.2f})')

    ax.set_xlabel('Score')
    ax.set_ylabel('Count')
    ax.set_title('Score Distribution')
    ax.legend()
    ax.grid(alpha=0.3)

    st.pyplot(fig)


# CACHING LAYER (UPDATED - NO JSON)
@st.cache_data
def generate_and_score_data(seed: int,
                            n_candidates: int,
                            edge_fraction: float = 0.15):
    """Generate and score candidates. Cached by parameters.

    CRITICAL: All parameters in signature for cache invalidation.
    """
    df = generate_candidates(seed, n_candidates, edge_fraction)
    df = score_candidates(df)
    return df

@st.cache_data
def compute_constraints_cached(_df: pd.DataFrame,  # Prefix with _ to hide from cache key
                               df_hash: str,  # Used for cache key
                               threshold: float,
                               top_k: int,
                               budget: int):
    """Apply constraints. Cached by hash + parameters (UPDATED).

    Note: DataFrame passed directly (no JSON round-trip).
    df_hash used only for cache key generation.
    """
    return apply_constraints(_df, threshold, top_k, budget)

# HEADER
st.title("Decision Space Visualizer")
st.caption("See which options disappear before human review as constraints tighten")

# SIDEBAR CONTROLS
with st.sidebar:
    st.header("Parameters")

    st.subheader("Data Generation")
    seed = st.number_input("Random seed", value=42, step=1, min_value=0)
    n_candidates = st.number_input("Number of candidates",
                                    value=120,
                                    min_value=10,
                                    max_value=500,
                                    help="Max 500 for performance")

    st.subheader("Constraints")
    threshold = st.slider("Score threshold",
                         min_value=0.0,
                         max_value=1.0,
                         value=0.50,
                         step=0.01,
                         help="Minimum score to pass quality gate")

    top_k = st.slider("Top-K after threshold",
                     min_value=1,
                     max_value=50,
                     value=20,
                     step=1,
                     help="Maximum candidates for top-K filter")

    budget = st.slider("Human review budget",
                      min_value=1,
                      max_value=top_k,
                      value=min(10, top_k),
                      step=1,
                      help="Maximum candidates for human review")

    st.subheader("Display")
    rows_per_table = st.slider("Rows per table", 5, 50, 15)

# COMPUTE RESULTS
with st.spinner('Generating candidates and computing scores...'):
    df_scored = generate_and_score_data(seed, n_candidates, 0.15)

df_hash = compute_dataframe_hash(df_scored)

with st.spinner('Applying constraints...'):
    results = compute_constraints_cached(
        df_scored,  # Pass DataFrame directly (no JSON)
        df_hash,    # Hash for cache key
        threshold,
        top_k,
        budget
    )

counts = results['counts']
boundary = results['boundary_items']

# RUN SUMMARY (UPDATED)
invariant_check = (counts['n_shown'] + counts['n_dropped'] ==
                   counts['n_after_threshold'])

st.info(f"""
**Parameters**: threshold={threshold:.2f}, K={top_k}, budget={budget}, seed={seed}

**Counts**: Total={counts['n_total']}, After threshold={counts['n_after_threshold']}, \
Shown to human={counts['n_shown']}, Eligible but dropped by capacity={counts['n_dropped']}

**Data integrity**: {'✅ Verified' if invariant_check else '❌ Failed'} \
(All candidates after threshold are either shown or dropped, with no overlap or missing items)
""")

if not invariant_check:
    st.error("[ERROR] INVARIANT VIOLATION - Please report this bug")

# EDGE CASE WARNINGS (NEW)
n_below_threshold = counts['n_total'] - counts['n_after_threshold']

if n_below_threshold > 0 and counts['n_after_threshold'] == 0:
    st.warning(f"[WARNING] No candidates passed threshold ({threshold:.2f}). "
               f"All {counts['n_total']} candidates were filtered out. "
               f"Try lowering the threshold.")

if counts['n_shown'] == counts['n_after_threshold'] and counts['n_after_threshold'] > 0:
    st.info("[INFO] All candidates that passed threshold are shown. "
            "Constraints (top-K, budget) are not limiting.")

if counts['n_after_threshold'] > 0 and top_k >= counts['n_after_threshold']:
    st.info("[INFO] Top-K is not binding. All threshold-passing candidates are within K.")

# THREE-COLUMN LAYOUT
col1, col2, col3 = st.columns(3)

display_cols = ['id', 'score', 'urgency', 'confidence', 'impact', 'cost', 'case_type']
float_cols = ['score', 'urgency', 'confidence', 'impact', 'cost']

with col1:
    st.subheader("All Candidates")
    st.caption(f"Total: {counts['n_total']}")
    render_candidate_table(results, 'all', display_cols, float_cols, rows_per_table)

with col2:
    st.subheader("Shown to Human")
    st.caption(f"Shown to human: {counts['n_shown']} (budget cap)")
    render_candidate_table(results, 'shown', display_cols, float_cols, rows_per_table)

with col3:
    st.subheader("Eligible but Dropped by Capacity")
    st.caption(f"Eligible but dropped by capacity: {counts['n_dropped']}")
    render_candidate_table(results, 'dropped', display_cols, float_cols, rows_per_table)

# BELOW THRESHOLD INFO (NEW)
if n_below_threshold > 0:
    st.info(f"[INFO] {n_below_threshold} additional candidates did not meet the minimum score "
            f"threshold ({threshold:.2f}) and are not shown in the tables above.")

# CASE TYPE EXPLANATION (NEW)
with st.expander("[INFO] What is 'Case Type'?"):
    st.markdown("""
    Candidates are generated with different patterns to create interesting dynamics:

    - **base**: Normal candidates (85% of total)
    - **high_urg_low_conf**: High urgency but low confidence (edge case)
    - **high_impact_high_cost**: High potential but expensive (edge case)
    - **borderline**: Scores near the threshold (edge case)

    Edge cases help demonstrate how constraints affect different types of candidates.
    """)

# CLOSEST DROPPED EXPLAINER (UPDATED)
st.markdown("---")
st.subheader("Closest Dropped Option")

if len(results['dropped']) > 0:
    closest = results['dropped'].iloc[0]

    col_a, col_b, col_c = st.columns([1, 1, 2])

    with col_a:
        st.metric("Candidate ID", closest['id'])
        st.metric("Score", f"{closest['score']:.3f}")

    with col_b:
        st.write("**Dropped because**")
        st.write(f"{closest['dropped_reason']} ({closest['capacity_stage']})")
        st.metric("Score margin",  # UPDATED LABEL
                 f"{closest['inclusion_margin']:.3f}",
                 help="Difference in model score, not feature distance")

    with col_c:
        st.info("[INFO] **Score margin** = how much the model score was below the cutoff. "
                "This is a difference in predicted scores, not a distance in feature space. "
                "Feature differences below show what actually differed.")

    # Feature comparison
    boundary_item, boundary_label = get_boundary_for_stage(closest, boundary, top_k, budget)

    if boundary_item is not None:
        render_feature_comparison(closest, boundary_item, boundary_label)
else:
    st.write("No candidates dropped (all passed constraints)")

# OPTIONAL: Score distribution histogram
with st.expander("[CHART] Score Distribution"):
    render_score_histogram(df_scored, threshold, boundary)
