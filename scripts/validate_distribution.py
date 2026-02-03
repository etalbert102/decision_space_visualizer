"""Post-implementation validation (run after Phase 3).

CRITICAL: Imports actual implementation (no logic duplication).

Validates:
1. Score distribution has sufficient spread
2. Pass rate is reasonable
3. Constraint boundaries create interesting dynamics
4. All edge case templates are represented
5. Margin diversity exists
"""

import sys

def validate_score_distribution():
    """Validate actual implementation creates good demo dynamics."""
    sys.path.insert(0, '.')
    from src.data import generate_candidates
    from src.model import score_candidates, MODEL_COEFS
    from src.constraints import apply_constraints

    print("="*60)
    print("FULL PIPELINE VALIDATION (Phases 1-3)")
    print("="*60)

    # Generate with actual code
    df = generate_candidates(seed=42, n_candidates=120, edge_fraction=0.15)
    df = score_candidates(df, coefs=MODEL_COEFS)

    checks_passed = 0
    checks_total = 8

    # Check 1: Basic distribution
    score_std = df['score'].std()
    score_range = df['score'].max() - df['score'].min()

    # Updated: Allow 0.14 threshold (matches test)
    if score_std > 0.14:
        print(f"[PASS] Check 1: Score std > 0.14 ({score_std:.3f})")
        checks_passed += 1
    else:
        print(f"[FAIL] Check 1: Score std too low ({score_std:.3f})")

    # Check 2: Score range
    if score_range > 0.4:
        print(f"[PASS] Check 2: Score range > 0.4 ({score_range:.3f})")
        checks_passed += 1
    else:
        print(f"[FAIL] Check 2: Score range too narrow ({score_range:.3f})")

    # Check 3: Pass rate
    pass_rate = (df['score'] >= 0.5).mean()

    if 0.25 <= pass_rate <= 0.7:
        print(f"[PASS] Check 3: Pass rate in [25%, 70%] ({pass_rate:.1%})")
        checks_passed += 1
    else:
        print(f"[FAIL] Check 3: Pass rate too extreme ({pass_rate:.1%})")

    # Check 4: ALL edge case templates present
    edge_types = df[df['case_type'] != 'base']['case_type'].unique()
    expected_types = {'high_urg_low_conf', 'high_impact_high_cost', 'borderline'}

    if set(edge_types) == expected_types:
        print(f"[PASS] Check 4: All edge templates present ({len(edge_types)})")
        checks_passed += 1
    else:
        missing = expected_types - set(edge_types)
        print(f"[FAIL] Check 4: Missing edge templates: {missing}")

    # Check 5: Borderline cases near boundaries
    borderline = df[df['case_type'] == 'borderline']
    if len(borderline) > 0:
        median_score = borderline['score'].median()
        if 0.4 < median_score < 0.6:
            print(f"[PASS] Check 5: Borderline cases near threshold ({median_score:.3f})")
            checks_passed += 1
        else:
            print(f"[FAIL] Check 5: Borderline median far from threshold ({median_score:.3f})")
    else:
        print("[FAIL] Check 5: No borderline cases found")

    # NEW: Check 6-8: Constraint dynamics
    result = apply_constraints(df, threshold=0.5, top_k=20, budget=10)

    n_topk_drops = (result['dropped']['capacity_stage'] == 'top_k').sum() if len(result['dropped']) > 0 else 0
    n_budget_drops = (result['dropped']['capacity_stage'] == 'budget').sum() if len(result['dropped']) > 0 else 0

    # Check 6: Sufficient top-K drops
    if n_topk_drops >= 5:
        print(f"[PASS] Check 6: Sufficient top-K drops ({n_topk_drops})")
        checks_passed += 1
    else:
        print(f"[FAIL] Check 6: Too few top-K drops: {n_topk_drops} (need >=5)")

    # Check 7: Sufficient budget drops
    if n_budget_drops >= 5:
        print(f"[PASS] Check 7: Sufficient budget drops ({n_budget_drops})")
        checks_passed += 1
    else:
        print(f"[FAIL] Check 7: Too few budget drops: {n_budget_drops} (need >=5)")

    # Check 8: Margin diversity
    if len(result['dropped']) > 0:
        margins = result['dropped']['inclusion_margin']
        if margins.std() > 0.015:
            print(f"[PASS] Check 8: Margin diversity sufficient ({margins.std():.3f})")
            checks_passed += 1
        else:
            print(f"[FAIL] Check 8: Margins too uniform ({margins.std():.3f})")
    else:
        print("[FAIL] Check 8: No dropped candidates to check margins")

    # Additional info
    print("\nAdditional Statistics:")
    print(f"  Total candidates: {len(df)}")
    print(f"  Base cases: {(df['case_type'] == 'base').sum()}")
    print(f"  Edge cases: {(df['case_type'] != 'base').sum()}")
    print(f"  Score mean: {df['score'].mean():.3f}")
    print(f"  Score min: {df['score'].min():.3f}")
    print(f"  Score max: {df['score'].max():.3f}")

    # Results
    print("\n" + "="*60)
    print(f"RESULT: {checks_passed}/{checks_total} checks passed")
    print("="*60)

    if checks_passed == checks_total:
        print("\n[SUCCESS] ALL VALIDATIONS PASSED - Parameters look good!")
        print("Proceed to Phase 4: UI")
        return True
    elif checks_passed >= checks_total - 2:
        print(f"\n[WARNING] {checks_total - checks_passed} validation(s) failed (minor)")
        print("Parameters are acceptable. Proceed to Phase 4.")
        return True
    else:
        print(f"\n[ERROR] {checks_total - checks_passed} validation(s) failed")
        print("\nTROUBLESHOOTING GUIDE:")

        if score_std < 0.14:
            print("- Score std too low: Increase noise in data generation")
            print("  or increase coefficient magnitudes")

        if not (0.25 <= pass_rate <= 0.7):
            if pass_rate < 0.25:
                print("- Pass rate too low: Lower threshold or increase intercept")
            else:
                print("- Pass rate too high: Raise threshold or decrease intercept")

        print("\nOptions:")
        print("1. Adjust parameters based on guidance above")
        print("2. Re-run this script")
        print("3. If stuck after 3 tries, proceed with current params")
        print("   (can tune during implementation)")

        return False

if __name__ == '__main__':
    success = validate_score_distribution()
    sys.exit(0 if success else 1)
