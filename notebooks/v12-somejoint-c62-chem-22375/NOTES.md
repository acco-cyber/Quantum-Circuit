# v12 - 2026-10-28 ~06:00 UTC (quantum slot 4 of 10-28)

Upload of the public output of `somejoint/quantum-circuits-22-44-local-gm-our-chemistry` (run 2026-10-28 04:30 UTC,
zip sha256 5b2b5023af2dc126...). Credits: somejoint (Agniv Banerjee) team, busyaprime, mrmeows, Ozer.

Diff vs v11 (member hashes in `submission-members.sha256`): **only the dfthcsos chemistry** changed.

| task | component | cost | vs v11 |
|---|---|---:|---|
| invsqrt | busyaprime 63q v2 (sha 07314803) | 102,664 | identical |
| dqi | somejoint 897q decoder (sha b3354f60) | 4.2235e11 | identical |
| dfthcsos | somejoint team R8/B143 C62 factorization, phased five-word angle lookups; lambda_eff 48.271, T 16,752, Q 430 | 3.47715e8 | was 3.4934e8 (-0.47%) |

Local check in this session: official `dfthcsos/verify.py` + competition `kickmix.so`, own salt `local-check-1028b`
-> PASS, cost 347,715,360 (`dfthcsos-verifier-local.json`). Projection: 22.33981 x (3.4934/3.47715)^(1/3) = 22.375.
No GPU used.

Note: their chemistry has a *higher* lambda_eff (48.27 vs 47.49) but fewer Toffolis (16,752 vs 17,066) and one fewer
qubit - the ANGLES loader (phased five-word lookups) is where the saving is. Combining the C46 table's lower
lambda_eff with this loader would be the next own-work chemistry step.
