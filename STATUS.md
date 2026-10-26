# Status - Google Quantum AI: Verifiable Quantum Circuit Compilation

Competition: https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation (deadline 2027-01-20).
Score = geometric mean over invsqrt / dqi / dfthcsos of cost_reference / cost_submission (official kickmix verifiers).

| version | date (UTC) | public | what |
|---|---|---:|---|
| v1 | 10-26 04:06 | 12.131 | rebuilt public Round-13 pipeline (dmitriigluzdov) |
| v2 | 10-26 04:13 | 13.713 | + michaelrustad R10/B129/C60 chemistry |
| v3 | 10-26 04:49 | 13.725 | + lambda_eff refit on CPU |
| v4 | 10-26 06:37 | 13.920 | invsqrt 76q mrmeows + DQI 881q + dfthcsos mrmeows 8-bit R4/B333/C128 |
| v5 | 10-26 07:11 | **15.134** | v4 + chemistry 7.91x (R10/B129/C60 8-bit, Bro8 tensor-lookup compiler J=5) |
| v6 | 10-27 (next budget) | pending | public plateau portfolio, projection 19.51 - `notebooks/v6-public-plateau-19.5` |

Leaderboard 2026-10-26 23:00 UTC: 23.352 / 22.886 / 22.794 / 22.475 / 21.579. Best public notebooks: 19.5-19.6.

`notebooks/<version>/` holds the Kaggle notebook, kernel-metadata.json and NOTES.md for each submission from v6 on
(v1-v5 were built and uploaded by earlier sessions as zip files; their composition is in the table above).
`docs/` has the organisers' chemistry scoring README; `reference/` the public baseline notebook.
