# v6 - public plateau portfolio (kirilltym "QROM + Tower42", development projection 19.506)

| task | circuit | qubits | cost | ratio |
|---|---|---:|---:|---:|
| invsqrt | mrmeows 63-qubit structural build | 63 | 108,560.36 | 19.13 |
| dqi | Özer v8 Bézout-Schur (jday96314 decoder lineage, Chilton 883q synthesis) | 883 | 4.9505e11 | 49.37 |
| dfthcsos | lightningv08 J=5 five-word loaders on Özer R4/B255/C128 8-bit factors + kirilltym exact gauge | 429 | 4.2697e8 | 7.86 |

Archive SHA-256 `84c55bf3a432e123a14289f420fb863f6d4147191f7fcd48781e3cfce08ac124` (50,108,684 bytes, 18 members), downloaded
2026-10-26 23:03 UTC from the notebook output (run of 21:35 UTC). Submitted as-is (byte-identical) - see the submission
description for the credit line. Note from the source NOTICE: the jday96314 GitHub decoder has no declared code licence;
the compiled binary is reused from Chilton's public Kaggle output.

Why this and not our own v5 line: v5 = 15.13 was itself an assembly of public parts (invsqrt 76q, DQI 881q, chemistry 7.9x).
Every component is now dominated by a newer public one (63q invsqrt, 883q Schur DQI at 49x, J=5 chemistry at 7.86x).

## Where the top (23.35 / 22.89 / 22.79 on 2026-10-26) is ahead
Geometric mean 23.35 vs 19.5 = +20% on each task on average. The chemistry ratio (7.86x) is the smallest and the most
movable: lower lambda_eff (better factorization fit under the E_gap > 3.9149 Ha and Lambda > 49 gates), fewer addressed
vectors (B), and cheaper loaders. DQI pays qubits squared: each qubit saved at 883 is -0.23% cost.
