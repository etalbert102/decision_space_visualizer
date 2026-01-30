# Decision Space Visualizer Audit (Python) — Judgment-Preserving Doctrine

## Doctrine Stress Test
Doctrine under test: Judgment-Preserving Doctrine (demo regime)

Regime: Demo / diagnostic (no commits-to-world, synthetic data, local operator)

Doctrine minimum set for this regime:
- Boundaries enumerated
- Invariants are loud at boundaries (not assert-only)
- Reproducibility record (inputs + version)
- Contract clarity sufficient for review without code spelunking

Out of scope in this regime: access control, durable audit logs, runtime approval gates

Pass condition: all minimum-set items are “Green,” with any “Yellow” tagged as “Operationalization-only.”

## 0) Audit metadata
- Project name: Decision Space Visualizer
- Repo / version / commit: decision_space @ 49a7d5d8889cef9a2436e3efcdff56839df33516
- Auditor: Codex (automated review)
- Date: January 30, 2026
- Intended users / operators: Researchers, ML practitioners, policy reviewers; local/demo usage
- Deployment context (local / server / pipeline / scheduled job / API): Local Streamlit app
- Data sensitivity (public / internal / restricted): Public / synthetic
- "Commits to the world"? (writes records, triggers actions, publishes outputs others rely on): No
- If **Yes**, list commitments:
  - [ ] Database writes
  - [ ] File/object store writes
  - [ ] External API side effects
  - [ ] Notifications / tickets
  - [ ] Model outputs that drive decisions
  - [ ] Other:

---

## 1) System summary (1 page max)
**What it does (plain language):**
A Streamlit app that generates synthetic candidates, scores them with a fixed logistic model, then applies threshold/top-K/budget constraints to show which candidates are visible to human review and which are removed before review.

**Primary inputs:**
- Source(s): UI parameters (seed, n_candidates, threshold, top_k, budget) and internal synthetic data generator
- Format(s): Scalars + in-memory pandas DataFrames
- Trust level (trusted / semi-trusted / untrusted): Trusted (local user input)

**Primary outputs:**
- Where outputs go: Streamlit UI tables, summary text, and charts
- Who relies on them: Local user in the session

**Failure cost (what goes wrong if it’s wrong):**
- Silent failure risk: Medium (could mislead about option loss if invariants break without a visible error)
- Irreversibility: Low (no side effects; can re-run with corrected logic)

---

## 2) Boundaries (where judgment belongs)
List the project’s boundaries (points where state changes, transitions occur, or others depend on outputs).

### Boundary inventory
For each boundary, fill:
- Boundary name:
- Type: Input / State transition / Irreversible action / Published output
- Location(s): file/module/function(s)
- What changes in the world:
- Who is impacted:
- Reversibility: Easy / Costly / Hard / Impossible
- Detection: Obvious / Delayed / Silent

**Boundaries identified:**
1. UI parameter entry (Input)
   - Location: `app.py` sidebar controls
   - Change: user-defined thresholds/budget/seed
   - Impact: changes results shown
   - Reversibility: Easy (adjust sliders)
   - Detection: Obvious
2. Candidate generation (State transition)
   - Location: `src/data.py:generate_candidates`
   - Change: synthetic dataset created
   - Impact: downstream scoring/constraints
   - Reversibility: Easy (re-run with same seed)
   - Detection: Obvious
3. Scoring (State transition)
   - Location: `src/model.py:score_candidates`
   - Change: adds logit/score
   - Impact: ranking and constraints
   - Reversibility: Easy (re-run)
   - Detection: Obvious
4. Constraint application (State transition)
   - Location: `src/constraints.py:apply_constraints`
   - Change: partitions candidates into shown/dropped
   - Impact: determines visibility and explanations
   - Reversibility: Easy
   - Detection: Obvious if assertions trip; otherwise can be silent
5. Published output (Published output)
   - Location: `app.py` render tables/summary/charts
   - Change: UI output visible to user
   - Impact: user interpretation
   - Reversibility: Easy (refresh/re-run)
   - Detection: Obvious

**Audit check**
- [x] All irreversible actions are explicitly listed as boundaries.
- [x] “Outputs others rely on” are treated as boundaries even if reversible.

---

## 3) Judgment anchors (explicit checkpoints at boundaries)
A judgment anchor must specify: **authority, evidence, alternatives, irreversibility, record**.

### Anchor checklist (repeat per boundary)
**Boundary:** Constraint application (`src/constraints.py:apply_constraints`)
- Anchor present? Partial (implicit via UI parameters + invariants)
- Where is the anchor implemented? `app.py` sliders; assertions in `src/constraints.py`

**Authority (who is allowed to decide here?)**
- Decision owner (role/team): Local user
- Mechanism of authorization:
  - [x] Config flag / policy (UI parameters)
  - [ ] Runtime approval step
  - [ ] Access control / permissions
  - [ ] Explicit “dry-run then promote”
  - [ ] Other:

**Evidence (what evidence is required?)**
- Required validations / checks:
  - [ ] Schema validation
  - [x] Range / domain constraints (UI slider bounds; data generator bounds)
  - [ ] Referential integrity
  - [ ] “Minimum evidence” thresholds
  - [x] Sampling / spot checks (tests + validate_distribution.py)
  - [ ] Other:
- Where enforced: `app.py` slider bounds; `src/data.py` assertions; tests in `tests/`

**Alternatives (what alternatives still exist?)**
- Supported modes:
  - [x] Dry-run (no side effects)
  - [x] No-op (set constraints non-binding)
  - [ ] Human review queue
  - [ ] Quarantine / hold
  - [ ] Partial commit
- Are alternatives easy to select at runtime? Yes

**Irreversibility (what becomes hard to undo?)**
- Enumerate irreversible effects: None (local UI only)
- Rollback strategy exists? N/A
- Rollback tested? N/A
- Blast radius bounded? Yes (single session)

**Record (what is recorded for later reconstruction?)**
- Record requirement (Demo): must capture run parameters + code version in-copyable form
- Current state: none
- Evidence needed to pass: screenshot or text block showing parameters + commit hash

**Anchor verdict**
- Demo verdict: Needs work
- Operational verdict: Needs work
- Reason: Anchors are implicit and there is no record/approval path; acceptable for demo, insufficient for ops.

---

## 4) Contracts (matter more than internal code)
Contracts define: accepted inputs, produced outputs, error behavior, invariants, change handling.

### 4.1 Public interfaces (list)
- [x] CLI entrypoints (Streamlit: `streamlit run app.py`)
- [x] Library API (imported functions/classes)
- [ ] HTTP endpoints
- [ ] Scheduled jobs / workers
- [ ] Data interfaces (tables/files/topics)

**Interfaces identified:**
1. Streamlit app entrypoint: `app.py`
2. Data generation: `src/data.py:generate_candidates`
3. Scoring: `src/model.py:score_candidates`
4. Constraints: `src/constraints.py:apply_constraints`
5. Validation script: `scripts/validate_distribution.py`

### 4.2 Contract checklist (repeat per interface)
**Interface:** `src/constraints.py:apply_constraints`
- Contract documented? Partial (docstring + tests)

**Accepted**
- Input schema: DataFrame with `id`, `score`, features; scalar params threshold/top_k/budget
- Trust assumptions: trusted internal caller
- Backwards compatibility expectations: not stated

**Produced**
- Output schema: dict with `shown`, `dropped`, `counts`, `boundary_items` and intermediate frames
- Semantics: `dropped` includes only after-threshold capacity drops
- Downstream consumers: `app.py` UI and tests

**Errors**
- Failure modes enumerated? Partial (asserts for invariants)
- Error taxonomy: None
- Error surfaces are loud? Yes if asserts enabled; otherwise could be silent

**Change handling**
- Versioning strategy: None
- Deprecation policy: None
- “Breaking change” detection: Tests in `tests/`

**Contract verdict**
- Demo verdict: Needs work
- Operational verdict: Needs work
- Reason: Contracts exist via docstrings/tests but lack explicit schemas and error taxonomy.

---

## 5) Invariants (replace intuition)
An invariant must be: plainly stated, enforced at boundaries, tested/monitored, loud when violated.

### 5.1 Invariant inventory
List invariants as **plain sentences**.
1. Shown UNION dropped equals after-threshold; shown INTERSECT dropped is empty.
2. Scores are strictly within (0, 1) after scoring.
3. All feature values are within [0, 1] after generation.
4. Candidate IDs are stable and sequential (C0000...)
5. Dropped margins are non-negative and dropped list sorted by margin.

### 5.2 Invariant enforcement (repeat per invariant)
**Invariant:** Shown UNION dropped equals after-threshold; disjoint sets
- Where enforced: `src/constraints.py:apply_constraints` asserts
- How enforced:
  - [x] Validation (raise/stop)
  - [ ] Constraint
  - [ ] Guardrail
- Tests exist? Yes (`tests/test_constraints.py`)
- Monitoring exists? No
- Violation is loud? Yes in debug runs; not if Python asserts disabled

**Invariant verdict**
- Demo verdict: Needs work
- Operational verdict: Needs work
- Reason: Invariants are assert-only; loudness is not guaranteed in optimized runs.

---

## 6) Reviewability (review change, not code)
Review should focus on: behavioral change, guarantees at risk, failure visibility, rollback.

### 6.1 Change summary discipline
- Is there a CHANGELOG or release notes? No
- Do PRs/commits summarize **behavioral change** (not refactor notes)? Unknown
- Can an expert evaluate a change without reading most files? Partially (docs exist, but no formal change log)

### 6.2 “Change audit” checklist (for the latest significant change)
- Change described in one paragraph: Not available
- What behavior changed: Not available
- Which contracts changed: Not available
- Which invariants could break: Not available
- How failure would show up (logs/metrics/user-visible): Not available
- Rollback plan: Not applicable (local tool)
- Migration needed (data/schema)? No

**Reviewability verdict**
- Demo verdict: Needs work
- Operational verdict: Needs work
- Reason: No CHANGELOG or change-audit template to summarize behavioral impact.

---

## 7) Human readability (mandatory where judgment is required)
Mandatory readability areas: boundaries/anchors, contracts, invariants, failure behavior, change summaries.

### 7.1 Readability checklist
- [x] Boundary points are obvious in code structure (dedicated modules/functions)
- [ ] Anchors are explicit (named, discoverable, not “incidental”)
- [x] Contracts are adjacent to interfaces (docstrings)
- [x] Invariants are written as sentences near enforcement
- [x] Failure behavior is discoverable (asserts + UI warnings)

**Readability verdict**
- Demo verdict: Needs work
- Operational verdict: Needs work
- Reason: Anchors are not explicitly named; doctrine concepts are implicit.

---

## 8) Failure behavior (silent failure prevention)
- Top 5 failure modes (rank by likelihood × impact):
  1. Invariants violated but asserts disabled (`python -O`) leading to silent bad partitions.
  2. Constraint boundary calculations incorrect after refactor, mislabeling drops.
  3. Data generation drift (seed or edge_fraction changes) leading to misleading dynamics.
  4. Cache key errors producing stale results for changed data.
  5. Cross-platform float differences causing determinism tests to fail or confusing minor shifts.
- For each: detection method (log/metric/assert/test), and operator action.
  - 1: Tests in `tests/test_constraints.py`; action: replace asserts with explicit checks + UI errors.
  - 2: Tests in `tests/test_constraints.py`; action: run tests after changes.
  - 3: Tests + `scripts/validate_distribution.py`; action: re-run validation.
  - 4: Tests + manual UI comparison; action: invalidate cache or adjust hash inputs.
  - 5: Determinism tests; action: run on supported platforms or relax tolerances.

**Checks**
- [x] “Default success” is not returned when evidence is missing.
- [x] Missing context is recorded as missing (not fabricated).
- [x] Partial/uncertain states are represented explicitly.

---

## 9) Minimal evidence pack (attach artifacts)
Provide links or filenames.
- Architecture / flow diagram (optional): `docs/default_screenshot.png` (visual reference)
- Boundary list (required if commits-to-world): N/A
- Contract specs (schemas/docstrings): `src/data.py`, `src/model.py`, `src/constraints.py`
- Invariant list: `src/constraints.py`, `src/types.py`, `tests/test_constraints.py`
- Test report / CI status: `tests/` (run locally)
- Example audit log event: None (not implemented)
- Rollback runbook or notes: N/A (no side effects)
- Example run record (copy/paste):
  - commit:
  - seed:
  - n_candidates:
  - threshold:
  - top_k:
  - budget:
  - edge_fraction (if applicable):
  - timestamp:

---

## 10) Decision thresholds (final)
### Risk rating
- Commitment irreversibility: Low
- Silent failure risk: Medium
- Judgment anchor coverage: Weak
- Contract clarity: Adequate
- Invariant enforcement: Adequate
- Reviewability: Weak

**Doctrine verdict**
- Demo verdict: Needs work
- Operational verdict: Needs work
- Reason: Repro record is Red and invariants loud are Yellow; ops requires anchors and durable record.

### Doctrine Coverage Matrix
| Doctrine primitive | Required (Demo) | Evidence in this repo | Demo status | Operational status | Delta (to move to operational) |
|---|---|---|---|---|---|
| Boundaries explicit | Yes | Section 2 + module split | Green | Green | — |
| Anchors explicit | Partial | UI params + invariants | Yellow | Red | Name anchors + add record + approval path |
| Invariants loud | Yes | asserts + tests | Yellow | Red | replace asserts with runtime checks + UI surfacing |
| Repro record | Yes | none | Red | Red | add “run record” block |
| Contracts clear | Yes (light) | docstring/tests | Yellow | Yellow | add typed schema/dataclass + error taxonomy |
| Reviewability | Yes (light) | no changelog | Yellow | Red | add changelog + change-audit template |

### Doctrine pass thresholds
Demo doctrine pass threshold:
- Boundaries = Green AND
- Invariants loud = Green/Yellow (Yellow allowed only if tests always run in CI and UI shows failure) AND
- Repro record = Green

Operationalization threshold (if you ever claim it can be used beyond demo):
- Anchors explicit = Green AND
- Record = Green (durable) AND
- Reviewability = Green

To satisfy demo threshold:
- Repro record: add “run record” block with parameters + commit hash captured per run.
- Invariants loud: replace asserts with runtime checks and surface failures in UI (or guarantee CI + UI warnings).

To satisfy operationalization threshold:
- Anchors explicit: name anchors + add approval path + record.
- Record (durable): implement persisted log with retention.
- Reviewability: add CHANGELOG + change-audit template.

### One-sentence accountability statement
Who owns correctness of the commitments this software makes:
- Owner: Project maintainer
- On-call / escalation: N/A (local tool)
- Where that responsibility is recorded: README / project docs (implicit)
