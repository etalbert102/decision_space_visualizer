import os
import time
from src.data import generate_candidates
from src.model import score_candidates
from src.constraints import apply_constraints

def test_performance_benchmark():
    """Full pipeline completes in reasonable time (CI-aware)."""
    start = time.time()

    df = generate_candidates(seed=42, n_candidates=120)
    df = score_candidates(df)
    result = apply_constraints(df, 0.5, 20, 10)

    elapsed = time.time() - start

    # Sanity checks that pipeline actually ran
    assert len(df) == 120, "Pipeline didn't generate data"
    assert 'score' in df.columns, "Pipeline didn't score"
    assert len(result['shown']) > 0, "Pipeline didn't apply constraints"

    # Timing threshold (plan requirement)
    # CI: 3s, Local: 1s
    ci_mode = os.environ.get("CI", "").lower() == "true"
    max_seconds = 3.0 if ci_mode else 1.0
    assert elapsed < max_seconds, (
        f"Pipeline too slow: {elapsed:.2f}s > {max_seconds:.1f}s"
    )

    print(f"Performance: {elapsed:.3f}s (target: <{max_seconds:.1f}s)")
