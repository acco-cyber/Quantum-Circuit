# v15 - best-of public portfolio, every member re-verified (public 23.00032)

Kaggle kernel `gwey1025/vqcc-v15-bestof` (private, CPU only), submitted 2026-10-30 11:57 UTC, ref 57804518, **public 23.00032** (best at the time).

| task | source | cost (local salt cw1030a) | ratio |
|---|---|---:|---:|
| invsqrt | Ahmed Berat Ozer, *DF-THC Group Compression* output, 62 qubits, sha 6dbb98b3 | 100,940 | 20.574 |
| dqi | 889-qubit decoder sha 7a378f47 (hengck23 / kirilltym / somejoint lineage), shipped in Ozer's output | 4.0840e11 | 59.84 |
| dfthcsos | heliosli *The dataset is public now* 10-30 release, npz 6503daab (lambda_eff 48.324, T 16266, Q 430) | 3.37994e8 | 9.928 |

Projected GM 23.035, scored 23.000 (DQI cost is salt dependent; the LB salt costs a little more than ours).
The notebook reads the two source kernels' outputs (`kernel_sources`), pins member SHA-256 prefixes, re-runs the three
official verifiers (quick invsqrt check in interactive mode, full in the commit run) and writes `submission.zip`.
Credits: Ahmed Berat Ozer, heliosli, yoyobar, busyaprime, mrmeows, somejoint, alexchilton, Dmitrii Gluzdov (Apache-2.0).
