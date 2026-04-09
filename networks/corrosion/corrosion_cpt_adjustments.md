# Corrosion CPT Adjustments

The original corrosion network (Dao et al., 2023) models under-deposit
corrosion in oil and gas pipelines. Three CPTs contain degenerate or
near-degenerate marginals that cause single-valued variables at the 1K
sample sizes used for structure learning benchmarking.

The original network is preserved as `corrosion_bnrep.dsc`. The adjusted
CPTs are in `corrosion.dsc`, `corrosion.xdsl`, and the regenerated
dataset in `datasets/corrosion_100k.csv.gz`.

All adjustments preserve the DAG structure (22 nodes, 24 edges),
qualitative causal semantics, and relative gradients.

## Adjusted CPTs

| CPT | Original | Adjusted | Notes |
|---|---|---|---|
| FlowVelocity | (1.0, 0.0, 0.0) | (0.60, 0.25, 0.15) | Fully degenerate — 100% High. Spread to give all three states meaningful mass while keeping High dominant. |
| OperatingPressure | (0.99, 0.01, 0.00) | (0.70, 0.18, 0.12) | Near-degenerate — Low never sampled, Moderate ~1%. Spread to ensure all states appear reliably in 1K samples. |
| DefectDepth \| WallThicknessLoss | (0)→(1.0, 0.0); (1)→(0.0, 1.0) | (0)→(0.90, 0.10); (1)→(0.10, 0.90) | Deterministic 1:1 mapping made DefectDepth perfectly redundant with WallThicknessLoss. Softened to 90/10 to allow structure learning to distinguish the two variables. |

## Additional Clean-up

| CPT | Original | Adjusted | Notes |
|---|---|---|---|
| ShearingForce \| (FlowVelocity=Low, OperatingPressure=High) | (1.11e-16, 0.20, 0.80) | (0.0, 0.20, 0.80) | Replaced floating-point artefact with clean zero. No behavioural change. |

## Verification

After adjustment, all 22 variables show variation in 50 random 1K draws
from a 100K forward sample. No trial had any degenerate (single-valued)
variable.

## Unchanged

- DAG structure: 22 nodes, 24 directed edges — no edges added or removed.
- All other CPTs: the 18 remaining CPTs are identical to the original.
- Structural zeros: no new zero entries were introduced.
- Exogenous priors: Chloride, MEG, InorganicDeposits, OrganicDeposits,
  MixedDeposits, OperatingTemperature, PartialPressureCO2, OD, and
  SteelGrade are unchanged.
