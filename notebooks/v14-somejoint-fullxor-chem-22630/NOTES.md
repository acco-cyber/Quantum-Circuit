# v14 - STAGED 2026-10-28 11:50 UTC, not yet submitted (10-28 quantum budget 5/5 used) -> submit with the first 10-29 slot

Source: public output of `somejoint/quantum-circuits-22-63-local-gm-full-xor-chem` (run 2026-10-28 10:32 UTC),
`submission.zip` sha256 `e84aeea1fee8baa5486d3dd1f71b6af3d0b5cdf07d6b4115d61706db9a7737b6`. Credits: somejoint (Agniv Banerjee)
team, heliosli / alexchilton (889q DQI), busyaprime + mrmeows (63q invsqrt).

Diff vs v13 (member hashes in `submission-members.sha256`): **only the dfthcsos chemistry** changed.

| task | component | cost | vs v13 |
|---|---|---:|---|
| invsqrt | busyaprime 63q v2 (07314803) | 102,664 | identical |
| dqi | 889q decoder (4ee7a17b) | 4.1478e11 | identical |
| dfthcsos | somejoint R8/B143 **C60** factorization, full-XOR five-word angle lookups; lambda_eff 48.561, T 16,528, Q 430 | 3.45124e8 | was 3.47715e8 (-0.75%) |

Local check in this session: official `dfthcsos/verify.py` + competition `kickmix.so`, own salt `local-check-1028j`
-> PASS, cost 345,124,297 (`dfthcsos-verifier-local.json`). All 18 member hashes match the source manifest.
Projection: 22.57336 x (3.47715/3.45124)^(1/3) = **22.630**. No GPU used.

How to submit (next run, after 00:00 UTC 10-29, check `kaggle competitions submissions` first):
```
kaggle kernels output somejoint/quantum-circuits-22-63-local-gm-full-xor-chem -p q14
sha256sum q14/submission.zip   # must be e84aeea1...
kaggle competitions submit google-verifiable-quantum-circuit-compilation -f q14/submission.zip -m "v14: ..."
```
If somejoint has re-run the notebook and the sha differs, re-verify the members against `submission-members.sha256`.

Note: the full-XOR loader cuts angles Toffolis (4299 vs 4333 per pass) and the C60 table has lambda_eff 48.56. A lower
lambda_eff table (C46 at 47.49) compiled with this loader is still the open own-work chemistry step (~-2% chem cost).
