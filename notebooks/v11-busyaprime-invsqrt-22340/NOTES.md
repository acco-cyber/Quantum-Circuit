# v11 - 2026-10-28 ~04:05 UTC (quantum slot 3 of 10-28)

Upload of the public output of `busyaprime/lb-22-33981-22x-cheaper-than-google-s-circuits` (run 2026-10-28 02:55 UTC,
zip sha256 aa1f4689...). `dungluongtuan/22-34-lb-reproducible-best-of-public-portfolio` contains the same members.

Diff vs v10 (member hashes in `submission-members.sha256`): **only invsqrt.kmb** changed.

| task | component | cost | vs v10 |
|---|---|---:|---|
| invsqrt | busyaprime 63q v2 (sha 07314803), 1334.5 mean / 1402 max Toffolis | 102,664 | was 103,546 (-0.85%) |
| dqi | somejoint 897q decoder (sha b3354f60) | 4.2235e11 | identical |
| dfthcsos | heliosli J5 on C46 table | 3.4934e8 | identical |

Local check in this session: official `verify_submission_invsqrt.py` + competition `kickmix.so` -> PASS, score
102,664.24 (`invsqrt-verifier-local.json`). Projection from v10 public: 22.2762 x (103546/102664)^(1/3) = 22.340.
No GPU used.

Lesson / next own-work lever: same 63 qubits, 14 fewer Toffolis per shot is worth +0.29% on the total score.
The gap to rank 3 (~24.2) is ~8% - needs a genuinely new DQI decoder or chemistry factorisation, not member swaps.
