# Polymorphic CPT Adjustments

The original Polymorphic network (Garc&iacute;a Alc&aacute;zar et al.) models
bearing degradation in electrical machines. All 22 variables are ternary
(Normal / Degradation / Failed). The 17 root nodes have extremely skewed
priors — P(Normal) > 0.997 for every root — meaning the non-Normal
states have expected counts well below 1 in a 1K sample. At 1K rows,
all root nodes (and consequently most child nodes) collapse to a single
value ("Normal"), making structure learning impossible.

Root node priors were adjusted so every state has P &ge; 0.005, giving
&ge; 99% probability of appearing at least once in 1K samples. The
original Degradation:Failed ratios are preserved within each tier.

## Adjusted Priors

| Tier | Nodes | Original | Adjusted |
|------|-------|----------|----------|
| 1 | ChemicalCorrosion, ImproperAssembly, InappropriateClearance, SurfaceCorrosion | 0.99965 / 0.00025 / 0.00010 | 0.985 / 0.010 / 0.005 |
| 2 | ExcessiveInterShaftCurrent, ExcessiveSpeed, PoorCooling, ScratchVibration | 0.99952 / 0.00030 / 0.00018 | 0.984 / 0.010 / 0.006 |
| 3 | HighFrequencyPulseVoltage, ImproperLubrification, PoorLubrification, SeverePartialDischarges | 0.99960 / 0.00020 / 0.00020 | 0.986 / 0.007 / 0.007 |
| 4 | HighTemperatureGluing, LocalizedHighTemperatures, Moisture, PresenceAbrasiveParticles | 0.99730 / 0.00100 / 0.00170 | 0.975 / 0.010 / 0.015 |
| 5 | Indentation | 0.99970 / 0.00020 / 0.00010 | 0.985 / 0.010 / 0.005 |

## Unchanged

- DAG structure: 22 nodes, 22 directed edges — no edges added or removed.
- Child node CPTs: all 5 child nodes (CorrosionFailure,
  InsulationDeterioration, PlasticDeformation, WearFault,
  SystemDegradation) retain their original deterministic max-severity
  logic.
- State labels: Normal / Degradation / Failed unchanged for all nodes.
- Original priors preserved in `polymorphic_bnrep.dsc`.
