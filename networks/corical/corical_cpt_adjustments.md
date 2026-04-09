# CORICAL CPT Adjustments

The original CORICAL network (Lau et al., 2021) is a COVID-19 vaccine
risk-benefit calculator where adverse outcomes have probabilities on the
order of 10⁻⁶ to 10⁻⁷. When forward-sampled, 9 of 20 variables collapse
to a single constant value ("No"), making structure learning impossible —
bnlearn correctly refuses since no conditional independence test can be
computed on zero-variance columns.

CPTs were adjusted to ensure all variables exhibit variation at the 1K
sample size used for structure learning benchmarking. All adjustments
preserve the DAG structure (20 nodes, 26 edges), qualitative causal
semantics, and relative gradients (e.g. age, dose, sex effects).

## Adjusted CPTs

| CPT | Original P(Yes) | Adjusted P(Yes) | Notes |
|---|---|---|---|
| BackgroundCSVTOver6Weeks | 3.8–7.5 × 10⁻⁷ | 0.03–0.05 | Age gradient preserved |
| BackgroundPVTOver6Weeks | 0–2.0 × 10⁻⁶ | 0.01–0.08 | Age gradient preserved |
| VaccineAssociatedTTS | 0–2.7 × 10⁻⁵ | 0–0.045 | P=0 when dose=None retained |
| Covid19AssociatedCSVT | 2.9–5.4 × 10⁻⁵ | 0.20–0.25 | P=0 when not infected retained |
| Covid19AssociatedPVT | 3.2–4.8 × 10⁻⁴ | 0.25–0.30 | P=0 when not infected retained |
| RiskOfSymptomaticInfection | 0.04–0.16 | 0.12–0.35 | ~2× boost to infection pool |
| RiskOfSymptInfUnderCurrent… | 0.005–0.576 | 0.05–0.576 | Low transmission entries raised |
| DieFromBackgroundCSVT | 0.07 | 0.15 | |
| DieFromBackgroundPVT | 0.27 | 0.27 | Unchanged |
| DieFromVaccineAssociatedTTS | 0.05 | 0.15 | |
| DieFromCovid19AssociatedCSVT | 0.174 | 0.40 | |
| DieFromCovid19AssociatedPVT | 0.198 | 0.40 | |
| DieFromCovid19 | 0–0.217 | 0.04–0.45 | Age/sex/vaccine gradient preserved |

## Verification

After adjustment, all 20 variables show variation in the first 1K rows of
a 100K forward sample. Across 20 random 1K windows, 18/20 had zero
degenerate variables; the remaining 2 had a single borderline variable
(DieFromCovid19 or DieFromCovid19AssociatedCSVT), acceptable for structure
learning with standard significance thresholds.

## Unchanged

- DAG structure: 20 nodes, 26 directed edges — no edges added or removed.
- Structural zeros: all P=0 entries (e.g. no TTS without vaccination, no
  Covid-associated thrombosis without infection) remain at zero.
- Exogenous priors: SARSCoV2Variant, Sex, AZVaccineDoses, Age, and
  IntensityOfCommunityTransmission are unchanged.
