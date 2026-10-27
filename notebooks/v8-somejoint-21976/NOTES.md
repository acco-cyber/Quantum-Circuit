# v8 - 2026-10-27 22:50 UTC (slot 3 of 10-27)

Direct upload of the public output of `somejoint/quantum-circuits-21-98-local-gm-883-qubit-dqi`
(run 2026-10-27 21:54 UTC). Archive sha256 `be8301da5551ab72...`; all 18 member hashes re-checked
locally against `summary.json` before submitting.

| task | component | cost | ratio vs reference |
|---|---|---:|---:|
| invsqrt | mrmeows 63q hybrid (same as v7) | 103,546 | 20.057 |
| dqi | 883q decoder + 658-Toffoli jet (new vs v7's R18 877q 4.421e11) | 4.365e11 | 55.99 |
| dfthcsos | Ozer V9 circuits + busyaprime refit (same as v7) | 3.551e8 | 9.451 |

GM 21.976 by the official verifiers in the source run (v7: 21.882). Only the DQI block changed.
Credits: somejoint (Agniv Banerjee), mrmeows, Ahmed Berat Ozer, busyaprime. No GPU used.

## Lesson
Every public >21.8 portfolio shares the same invsqrt and chemistry blocks; they differ only in DQI.
Per-task "best of" composition across public outputs gives nothing extra right now. Rank 3 (>22.80)
needs own work: chemistry ratio 9.45 is the weakest term (GM elasticity 1/3 per task).
