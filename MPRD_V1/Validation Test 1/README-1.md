# MPRD_V1 Validation Test 01

## Core State Classification Validation

**Framework:** Martin Pitre Framework of Relational Distinction, Persistence, and Recursive Development  
**Algorithm:** MPRD_V1 Core Algorithm  
**Validated version:** 1.0.1 corrective validation baseline  
**Execution date:** 28 July 2026  
**Environment:** Google Colab / Python standard library  
**Final result:** **PASS — 10 of 10 scenarios**  
**Validation status:** Complete

## Overview

Validation Test 01 evaluates whether the MPRD_V1 core classification engine assigns claim states according to its documented governance rules. The test focuses on the correctness, conservatism, determinism, and auditability of the decision logic rather than predictive performance.

The validation examined insufficient evidence, strong single observations, independent confirmation, weak recurrence, contradictory evidence, persistent support, invalid inputs, and deterministic repeat execution.

## Validation Objective

The test was designed to verify that MPRD_V1 can:

- validate evidence records and reject invalid inputs;
- classify claims deterministically;
- enforce evidence-independence requirements;
- enforce support and persistence requirements;
- identify materially contradictory evidence;
- produce identical classifications, scores, and state digests when the same valid scenario is rerun in a fresh instance.

## Required Classification Behaviour

The tested governance rules require that:

1. A single observation cannot become `SUPPORTED` without independent confirmation.
2. Repeated weak observations cannot become `PERSISTENT` solely through recurrence and independence bonuses.
3. Strong independent evidence can become `PERSISTENT` when both support and persistence criteria are satisfied.
4. Material unresolved contradiction produces a `CONTESTED` state.
5. Invalid evidence records raise explicit `ValidationError` exceptions.
6. Repeated executions of identical valid inputs produce identical substantive states and audit digests.

## Evidence-Preserving Correction History

The original MPRD_V1 Core Algorithm v1.0 execution passed 8 of 10 scenarios. Scenarios 02 and 04 exposed two defects in the classification decision logic. The original failed execution was preserved as evidence, the defects were documented, and the same ten scenarios and expected outcomes were retained for the corrected rerun.

| Measure | Original run | Corrected rerun |
| --- | ---: | ---: |
| Algorithm version | 1.0 | 1.0.1 |
| Scenarios passed | 8/10 | 10/10 |
| Scenarios failed | 2 | 0 |
| Deterministic repeat checks | PASS | PASS |
| Overall result | FAIL | PASS |

The failure was not removed or retroactively rewritten. Preserving both runs demonstrates that the validation process identified actual rule defects and that the corrected implementation was subsequently retested.

### Correction 1 — Single-source insufficiency

In v1.0, a single high-quality observation exceeded the support threshold and was classified as `SUPPORTED` before the single-source insufficiency rule was evaluated.

Version 1.0.1 evaluates the single-record, single-independence-group condition before general supported classification. A lone observation therefore remains `INSUFFICIENT`, regardless of its quality, until independent confirmation exists.

### Correction 2 — Support requirement for persistence

In v1.0, two weak observations accumulated enough recurrence and independence credit to become `PERSISTENT`, even though their adjusted support remained below the ordinary support threshold.

Version 1.0.1 requires adjusted support to meet the support threshold in addition to the persistence threshold, minimum independent-group requirement, and minimum recurrence requirement.

The underlying numerical scoring formulas were not changed. The corrective baseline changed the order and conditions used to determine the final status.

## Corrected Classification Order

Version 1.0.1 applies the following decision order:

1. `CONTESTED` — unresolved material contradiction exists.
2. `REJECTED` — support is below the rejection threshold.
3. `INSUFFICIENT` — only one record from one independence group is available.
4. `PERSISTENT` — support and persistence criteria are fully satisfied.
5. `SUPPORTED` — the support threshold is satisfied but persistence is incomplete.
6. `CANDIDATE` — evidence remains below the support threshold.

## Corrected Rerun Results

### Classification scenarios

| # | Scenario | Expected | Observed | Support | Persistence | Confidence | Result |
| ---: | --- | --- | --- | ---: | ---: | ---: | --- |
| 01 | One low-quality observation | `INSUFFICIENT` | `INSUFFICIENT` | 0.293000 | 0.396500 | 0.486150 | PASS |
| 02 | One high-quality observation | `INSUFFICIENT` | `INSUFFICIENT` | 0.681125 | 0.590562 | 0.699619 | PASS |
| 03 | Two independent strong observations | `PERSISTENT` | `PERSISTENT` | 0.956125 | 0.978063 | 0.975869 | PASS |
| 04 | Two weak observations | `CANDIDATE` | `CANDIDATE` | 0.522000 | 0.761000 | 0.737100 | PASS |
| 05 | Strong evidence with contradiction | `CONTESTED` | `CONTESTED` | 0.305155 | 0.652577 | 0.437835 | PASS |
| 06 | Multiple independent confirmations | `PERSISTENT` | `PERSISTENT` | 0.914500 | 0.957250 | 0.952975 | PASS |

**Classification result: 6 of 6 PASS.**

### Invalid-input scenarios

| # | Invalid condition | Expected | Observed | Result |
| ---: | --- | --- | --- | --- |
| 07 | Duplicate evidence identifiers | `ValidationError` | Duplicate evidence IDs rejected | PASS |
| 08 | Quality value greater than 1 | `ValidationError` | Out-of-range quality rejected | PASS |
| 09 | Reliability value below 0 | `ValidationError` | Out-of-range reliability rejected | PASS |
| 10 | Missing evidence identifier | `ValidationError` | Empty identifier rejected | PASS |

**Invalid-input result: 4 of 4 PASS.**

## Determinism and Auditability

Each of the six valid classification scenarios was executed twice using fresh algorithm instances. A repeat check passed only when both executions produced identical:

- claim status;
- support score;
- persistence score;
- confidence score;
- complete state digest.

All six valid scenarios passed the deterministic repeat comparison.

### Recorded state digests

| Scenario | SHA-256 state digest |
| ---: | --- |
| 01 | `4431011c85ec5101f813a23ee59a8db69079676388d2f3e1446655f7aa686fc5` |
| 02 | `07b6a3c53e9b77a3ce6acf85cdfeef1120365cefebb17ffe31a5bbf1cef0d8cc` |
| 03 | `dbee8abf0d9a5b885c71441d0d4a11de0788e1c9d33893e3fd49029ff0d0f5ba` |
| 04 | `2d0e0f521e51bf41c830aab84f34197a7a5e388be7684cef01e01339d012d97b` |
| 05 | `625ac9984ad0af67121824dd0d828a84c3ce95a371d0aada6a53223fa9da575b` |
| 06 | `f14deb776b741e5000df63fbd53bab96989f342a40014b934cc92443d4c20b57` |

These digests identify the recorded substantive states produced by this implementation and configuration. They do not independently prove the scientific validity of the framework.

## Repository Contents

The Test 01 evidence package may include:

```text
MPRD_V1_Validation_Test_01/
├── README.md
├── MPRD_V1_Validation_Test_01_Description.docx
├── MPRD_V1_Validation_Test_01_Standalone.py
├── MPRD_V1_Validation_Test_01_Execution_Record_FAIL.docx
├── MPRD_V1_Validation_Test_01_Corrected_Standalone.py
├── MPRD_V1_Validation_Test_01_Corrected_Execution_Record_PASS.docx
├── MPRD_V1_Validation_Test_01_Results.json
├── MPRD_V1_Validation_Test_01_All_Figures.zip
└── supporting figures and audit records
```

File availability and figure names may vary by repository release. The failed execution, corrected code, successful rerun, results, and supporting visuals should be interpreted together as one evidence package.

## Reproduction

The corrected standalone script uses the Python standard library and was executed in Google Colab.

```bash
python MPRD_V1_Validation_Test_01_Corrected_Standalone.py
```

For a controlled reproduction:

1. Preserve the original evidence package unchanged.
2. Use MPRD_V1 Core Algorithm v1.0.1 and the included corrected Test 01 script.
3. Run all ten scenarios without changing their inputs or expected outcomes.
4. Confirm a 10/10 result.
5. Confirm that every valid scenario passes its deterministic repeat comparison.
6. Compare recorded scores and state digests with the values in this README and the corrected execution record.
7. Save new outputs separately and document any environmental or result differences.

## Interpretation Boundaries

Validation Test 01 provides evidence that MPRD_V1 Core Algorithm v1.0.1 met the predefined classification, input-validation, and deterministic-repeat requirements under these ten controlled scenarios.

It does not establish:

- correctness under every possible evidence configuration;
- predictive accuracy or real-world performance;
- generalization to other datasets or operational environments;
- superiority over other classification or reasoning approaches;
- independent scientific replication or peer review;
- production readiness;
- validation of later MPRD tests, MPRD_R integrations, or the complete MKCS system.

## Formal Conclusion

MPRD_V1 Core Algorithm v1.0.1 **PASSED Validation Test 01**:

- Classification scenarios: **6/6 PASS**
- Invalid-input scenarios: **4/4 PASS**
- Deterministic repeat checks: **PASS**
- Overall result: **10/10 PASS**
- Disposition: **Validated for progression to Validation Test 02**

## Author

**Martin Pitre**  
Veteran • Researcher • Explorer

## Research Principle

> **The incredible becomes credible through evidence.**
