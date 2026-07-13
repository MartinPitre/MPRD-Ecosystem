# UTA Code

## Overview

This folder contains the reference implementation of **Uncertainty Transformation Analysis (UTA) v1**.

The code provided here serves as a computational representation of the UTA framework described in the Theory section of this repository. It allows researchers, students, and interested readers to explore, reproduce, and extend the uncertainty transformation calculations used within the UTA project.

---

## Purpose

The UTA algorithm models how uncertainty may change over time as information is gained, interpreted, remembered, or challenged.

UTA v1 is based on the transformation equation:

**U_new = U_old − R + C + S − M**

Where:

| Variable | Description |
|----------|-------------|
| U_old | Initial uncertainty |
| U_new | Updated uncertainty |
| R | Resolution through evidence or confirmation |
| C | Complexity introduced by new information |
| S | Surprise or unexpected developments |
| M | Memory, familiarity, or historical stabilization |

The implementation is intended as a research and educational tool rather than a production decision-making system.

---

## Contents

### UTA_Algorithm_v1_0.py

Reference implementation of the UTA v1 framework.

This file demonstrates how uncertainty transformations can be calculated using the UTA model.

---

## Relationship to Theory

The code in this folder is derived directly from the documents contained within the Theory directory.

Researchers are encouraged to review the theoretical documentation before interpreting algorithm outputs.

Theory provides the conceptual foundation; code provides the computational implementation.

---

## Relationship to the Pilot Study

The pilot study contained in the Pilot directory represents the first empirical evaluation of the UTA framework.

The code in this folder represents the underlying model, while the pilot study provides evidence regarding repeatability, stability, and event-type signature behavior.

---

## Version Information

**Current Algorithm Version:** UTA_Algorithm_v1_0

**Status:** Baseline Reference Implementation

This implementation is preserved as the original reference version associated with UTA Theory v1.2 and the initial pilot study.

Future improvements or alternative implementations should be versioned separately to preserve reproducibility.

---

## Usage

Researchers may use, inspect, modify, and extend the code in accordance with the repository license.

Any published work derived from this implementation should provide appropriate attribution.

---

## Author

Martin Pitre

Independent Researcher

---

## Research Principle

*"The incredible becomes credible through evidence."*
