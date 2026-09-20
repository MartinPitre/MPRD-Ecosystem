# MPRD_V1 Phase 1 Validation Test 04

## Recursive Knowledge Evolution Validation

**Framework:** Martin Pitre Framework of Relational Distinction, Persistence, and Recursive Development  
**Algorithm:** MPRD_V1 Core Algorithm v1.0.1  
**Validation phase:** Phase 1  
**Execution date:** 29 July 2026  
**Environment:** Google Colab / Python standard library  
**Scientific outcome:** **PASS**  
**Execution completeness:** **COMPLETE**  
**Core scenarios:** **7 of 7 PASS**  
**Repeatability:** **30 runs, 1 unique SHA-256 digest**

## Overview

Validation Test 04 evaluates whether MPRD_V1 can evolve a claim through sequential supporting and contradicting evidence while preserving all previously accepted records, maintaining deterministic behaviour, and converging to a stable knowledge state.

The primary evidence sequence moves a claim from `CANDIDATE` through `INSUFFICIENT`, `SUPPORTED`, and `PERSISTENT`, then introduces a material contradiction that changes the claim to `CONTESTED`. Further independent support improves the measured scores but does not erase the contradiction. A separate contradiction-dominant control verifies that the system can also produce a `REJECTED` state when warranted.

## Scientific Objective

> Determine whether recursive evidence integration produces stable, traceable, and logically consistent knowledge-state evolution as support and contradiction accumulate over time.

## Validation Objectives

The test was designed to verify:

- recursive claim updates after sequential evidence additions;
- transitions among `CANDIDATE`, `INSUFFICIENT`, `SUPPORTED`, `PERSISTENT`, `CONTESTED`, and `REJECTED`;
- preservation of previously accepted evidence;
- contradiction handling without corruption of the evidence network;
- stable convergence when an unchanged final evidence state is re-evaluated;
- correct rejection in a contradiction-dominant control case;
- deterministic final states and identical run digests across repeated executions.

## Frozen Test Configuration

| Parameter | Value |
| --- | ---: |
| Support threshold | 0.60 |
| Persistence threshold | 0.75 |
| Rejection threshold | 0.25 |
| Contradiction contested threshold | 0.20 |
| Contradiction penalty | 0.65 |
| Evidence weight | 0.45 |
| Independence weight | 0.20 |
| Recurrence weight | 0.15 |
| Relational weight | 0.20 |
| Minimum independent groups for support | 2 |
| Minimum independent groups for persistence | 2 |
| Minimum supporting records for persistence | 2 |
| Maximum convergence evaluations | 20 |

The four scoring weights sum to `1.0`. The harness validates configuration ordering and evidence fields before any record can affect the claim state.

## Primary Evidence Packet

Five records were introduced sequentially:

| Cycle | Evidence | Relation | Source | Independence group | Quality | Reliability | Purpose |
| ---: | --- | --- | --- | --- | ---: | ---: | --- |
| 1 | `E1` | Support | `source_alpha` | `group_alpha` | 0.88 | 0.90 | First supporting observation |
| 2 | `E2` | Support | `source_beta` | `group_beta` | 0.92 | 0.91 | Independent confirmation |
| 3 | `E3` | Support | `source_gamma` | `group_gamma` | 0.98 | 0.98 | Additional strong independent support |
| 4 | `E4` | Contradiction | `source_delta` | `group_delta` | 0.62 | 0.66 | Moderate contradictory observation |
| 5 | `E5` | Support | `source_epsilon` | `group_epsilon` | 0.95 | 0.94 | Further independent support after contradiction |

Evidence strength is calculated as:

```text
evidence_strength = sqrt(quality × reliability)
```

Only supporting-source groups contribute to the independent-support count. Contradictory records remain preserved as explicit relationships in the accumulated evidence state.

## Rejection-Control Packet

The test includes a separate control case to verify that contradiction-dominant evidence can be rejected:

| Cycle | Evidence | Relation | Quality | Reliability | Purpose |
| ---: | --- | --- | ---: | ---: | --- |
| 1 | `R1` | Support | 0.20 | 0.25 | Weak supporting control observation |
| 2 | `R2` | Contradiction | 0.98 | 0.99 | Strong contradictory control observation |

This packet is evaluated independently from the primary knowledge-evolution sequence.

## Scoring Method

For the evidence visible at each cycle, the harness calculates:

```text
independence_component = clamp(independent_support_groups / 3)
recurrence_component   = clamp(supporting_records / 4)

relation_balance = clamp(
    (support_count − contradiction_count + total_evidence)
    / (2 × total_evidence)
)

support_score = clamp(
    0.45 × mean_support_strength
  + 0.20 × independence_component
  + 0.15 × recurrence_component
  + 0.20 × relation_balance
)

adjusted_support = clamp(
    support_score − 0.65 × contradiction_score
)

confidence = clamp(
    0.70 × adjusted_support
  + 0.20 × independence_component
  + 0.10 × recurrence_component
)

persistence = clamp(
    0.55 × adjusted_support
  + 0.25 × independence_component
  + 0.20 × recurrence_component
)
```

All scores are bounded to `[0, 1]`.

## Classification Governance

The v1.0.1 harness applies a conservative decision order:

1. `CANDIDATE` when no evidence has been integrated.
2. `INSUFFICIENT` for one unconfirmed supporting record.
3. `REJECTED` when very strong contradiction combines with low adjusted support.
4. `CONTESTED` when material contradiction remains present.
5. `PERSISTENT` when adjusted support, persistence, independence, and recurrence requirements are all met.
6. `SUPPORTED` when the ordinary support threshold and independent-confirmation requirement are met.
7. `REJECTED` when contradiction exists and adjusted support is below the rejection threshold.
8. `CANDIDATE` when evidence exists but none of the preceding states applies.

Contradiction is assessed before `SUPPORTED` and `PERSISTENT`. Later supporting evidence can therefore improve the numerical state without silently removing a preserved disagreement.

## Core Scenario Results

| Scenario | Validation event | Evidence | Support / contradiction | Independent support groups | Support score | Contradiction score | Adjusted support | Confidence | Persistence | Expected and observed state | Result |
| ---: | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1 | Initial candidate claim | 0 | 0 / 0 | 0 | 0.00000000 | 0.00000000 | 0.00000000 | 0.00000000 | 0.00000000 | `CANDIDATE` | PASS |
| 2 | First supporting evidence | 1 | 1 / 0 | 1 | 0.70464138 | 0.00000000 | 0.70464138 | 0.58491564 | 0.52088610 | `INSUFFICIENT` | PASS |
| 3 | Independent confirmation | 2 | 2 / 0 | 2 | 0.81444262 | 0.00000000 | 0.81444262 | 0.75344317 | 0.71461011 | `SUPPORTED` | PASS |
| 4 | Additional independent support | 3 | 3 / 0 | 3 | 0.93023952 | 0.00000000 | 0.93023952 | 0.92616767 | 0.91163174 | `PERSISTENT` | PASS |
| 5 | Contradictory evidence | 4 | 3 / 1 | 3 | 0.88023952 | 0.63968742 | 0.46444270 | 0.60010989 | 0.65544348 | `CONTESTED` | PASS |
| 6 | Additional supporting evidence | 5 | 4 / 1 | 4 | 0.92961565 | 0.63968742 | 0.51381883 | 0.65967318 | 0.73260036 | `CONTESTED` | PASS |
| 7 | Convergence and rejection control | 5 | 4 / 1 | 4 | 0.92961565 | 0.63968742 | 0.51381883 | 0.65967318 | 0.73260036 | Stable `CONTESTED`; control `REJECTED` | PASS |

Every scenario also required the current evidence state to contain all identifiers accepted in the preceding primary scenario.

## Knowledge-State Evolution

```text
CANDIDATE
    ↓ first support
INSUFFICIENT
    ↓ independent confirmation
SUPPORTED
    ↓ strong independent recurrence
PERSISTENT
    ↓ material contradiction
CONTESTED
    ↓ further support with contradiction preserved
CONTESTED
    ↓ unchanged recursive evaluation
STABLE CONTESTED
```

The transition from `PERSISTENT` to `CONTESTED` demonstrates revisability: a previously strong claim is not protected from later contradictory evidence. The final state remains contested even though additional support improves confidence and persistence.

## Final Primary Knowledge State

| Metric | Result |
| --- | ---: |
| Status | `CONTESTED` |
| Evidence integrated | 5 |
| Supporting records | 4 |
| Contradicting records | 1 |
| Independent supporting groups | 4 |
| Support score | 0.92961565 |
| Contradiction score | 0.63968742 |
| Adjusted support | 0.51381883 |
| Confidence | 0.65967318 |
| Persistence | 0.73260036 |
| Convergence | `STABLE` |

## Rejection-Control Result

| Metric | Result |
| --- | ---: |
| Status | `REJECTED` |
| Evidence integrated | 2 |
| Supporting / contradicting records | 1 / 1 |
| Support score | 0.30478973 |
| Contradiction score | 0.98498731 |
| Adjusted support | 0.00000000 |
| Confidence | 0.09166667 |
| Persistence | 0.13333333 |

The control demonstrates that the algorithm did not classify every contradictory case as merely contested. Strong contradiction combined with effectively zero adjusted support correctly triggered rejection.

## Recursive Convergence

The convergence procedure re-evaluates the unchanged final primary evidence packet until two consecutive substantive claim states are identical. Because no new evidence is introduced, the cycle metadata remains fixed at Cycle 5.

The test recorded:

- convergence after 2 evaluations;
- 1 unique convergence digest;
- final converged state identical to the Cycle 5 state;
- all five primary evidence identifiers preserved;
- convergence status `STABLE`.

This is evidence of stable re-evaluation for the fixed test state. It does not establish universal mathematical convergence for arbitrary evidence streams.

## Determinism and Repeatability

The complete experiment—including all seven core scenarios, the rejection control, and the convergence record—was executed 30 times. Each run digest covers:

- algorithm and schema identity;
- frozen configuration;
- primary and control evidence packets;
- all scenario results;
- final primary and control states;
- convergence history.

All 30 runs produced one identical SHA-256 digest. The repeatability verification therefore passed and the recorded execution was deterministic under the documented conditions.

## Evidence Preservation and Traceability

Every primary state records:

- cycle and evidence count;
- supporting and contradicting counts;
- independent supporting-group count;
- support, contradiction, and adjusted-support scores;
- confidence and persistence;
- status and rationale;
- ordered evidence identifiers;
- SHA-256 state digest.

Each scenario checks that all evidence identifiers from the preceding state remain present. The Cycle 4 contradiction is preserved in the final and converged states.

## Repository Contents

The Test 04 evidence package may include:

```text
MPRD_V1_Phase_1_Validation_Test_04/
├── README.md
├── MPRD_V1_Phase_1_Validation_Test_04_Description.docx
├── MPRD_V1_Phase_1_Validation_Test_04_Standalone_Colab.py
├── MPRD_V1_Phase_1_Validation_Test_04_Summary_and_Results.docx
├── MPRD_V1_Phase_1_Validation_Test_04_Figures.zip
├── MPRD_V1_Validation_Test_04_Results.json
└── supporting figures and audit records
```

File availability may vary by repository release. The planning document, source code, raw JSON, written results, digests, and figures should be interpreted together as one evidence package.

## Reproduction

### Requirements

- Python 3
- Python standard library only
- Google Colab or another compatible Python environment

### Run in Google Colab

1. Open a new Google Colab notebook.
2. Copy `MPRD_V1_Phase_1_Validation_Test_04_Standalone_Colab.py` into one code cell.
3. Run the cell.
4. Confirm `PASS`, `COMPLETE`, `7/7`, stable convergence, rejection-control `REJECTED`, and `30 runs / 1 unique digest`.
5. Download `MPRD_V1_Validation_Test_04_Results.json` when prompted.

### Run locally

```bash
python MPRD_V1_Phase_1_Validation_Test_04_Standalone_Colab.py
```

For a controlled reproduction, do not change the configuration, primary or control packets, expected states, convergence limit, scoring rules, classification order, or repeat count. Preserve newly generated outputs separately and document any difference from the archived evidence.

## Interpretation Boundaries

Validation Test 04 provides evidence that MPRD_V1 Core Algorithm v1.0.1 met its predefined recursive knowledge-evolution, evidence-preservation, convergence, rejection-control, and repeatability criteria for the documented synthetic experiment.

It does not establish:

- correct behaviour for every possible evidence stream;
- empirical validity of the assigned quality and reliability values;
- real-world independence of simulated sources;
- factual truth or falsity of an external claim;
- predictive accuracy or causal inference;
- universal convergence under changing inputs;
- superiority over other evidence-integration systems;
- independent replication or peer review;
- production readiness;
- validation of Test 05, MPRD_R integrations, or the complete MKCS system.

The states `PERSISTENT`, `CONTESTED`, and `REJECTED` are outputs of the documented computational rules. They are not universal declarations of truth.

## Formal Conclusion

MPRD_V1 Phase 1 Validation Test 04 **PASSED** under the defined experimental conditions:

- Seven core scenarios executed and passed.
- The primary claim progressed from `CANDIDATE` to `PERSISTENT` before new contradiction changed it to `CONTESTED`.
- All previously accepted evidence remained preserved.
- Further support improved the numerical state without erasing the contradiction.
- The unchanged final state converged after two identical evaluations.
- The contradiction-dominant control correctly produced `REJECTED`.
- Thirty complete executions produced one unique SHA-256 digest.
- Execution completeness was reported as `COMPLETE`.

The result supported progression to the final planned MPRD_V1 Phase 1 validation test.

## Author

**Martin Pitre**  
Veteran • Researcher • Explorer

## Research Principle

> **The incredible becomes credible through evidence.**
