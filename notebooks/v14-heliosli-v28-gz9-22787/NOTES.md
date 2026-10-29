# v14 - heliosli "The dataset is now public now. Enjoy!" (release v28_gz9), hash-verified

Replaces the staged somejoint full-XOR v14 (proj. 22.630): heliosli's newest public release is ahead on every task.

| task | source | cost | ratio |
|---|---|---:|---:|
| invsqrt | busyaprime newest (mrmeows 63q build, two regions rebuilt) | 102,349 | 20.291 |
| dqi | somejoint 897q decoder | 4.1294e11 (default salt) / 4.1484e11 (salt notebook-verification, 1 phase error) | 59.18 / 58.91 |
| dfthcsos | somejoint R8/B143/C60 + heliosli angle circuits + Gluzdov W/H2_I | 3.40572e8 | 9.853 |

Commit run (CPU): all three official verifiers PASS, GM 22.752 at salt `notebook-verification` (heliosli: 22.787 at two salts).
Submitted 2026-10-29 06:15 UTC, ref 57761095 (10-29 quantum slot 1/5).

Chem diagnostics (local, `research/chem_metrics.py`): error_1 = error_2 = 19.9976 mHa (limit 20), E_gap = 3.914899 (floor 3.914898),
Lambda = 304.02, lambda_eff = 48.632. Every gate binds, so a W/H2_I-only refit has no slack left; lambda_eff ~ sqrt(2 Lambda E_gap)
means the remaining lever is Lambda (needs a new factorization U with lower one-norm, i.e. recompiling angle circuits).
