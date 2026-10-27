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
| v6 | 10-27 00:01 | **19.579** | public plateau portfolio (kirilltym QROM+Tower42, byte-identical, credited) - `notebooks/v6-public-plateau-19.5` |

Leaderboard 2026-10-27 00:32 UTC: 23.352 / 22.886 / 22.805 / 22.698 / 21.755. Our team: **rank 92 / 1171** at 19.579
(up from ~129 at 15.134). About 25 teams share the public plateau 19.5790 exactly; rank 3 needs > 22.80.

## Next (own work needed - no public part is ahead of v6)
* chemistry (7.86x, the small ratio): a new factorization fit with lower lambda_eff under the acceptance gates
  (Lambda > 49, E_gap > 3.9149 Ha) and fewer addressed vectors, then re-compile with the J=5 loaders. The dfthc-sos
  training library and verifier are in the competition data; lambda_eff x T x Q is the full cost, so a 10% lambda_eff
  cut is +3.2% on the score.
* dqi (49.4x): 883 qubits, cost ~ Q^2 x Toffolis; each qubit is -0.23% dqi cost, each 1% Toffoli cut is -1%.
* invsqrt (19.1x): 63 qubits / 1,404 mean Toffolis; cheaper polynomial phasing or 1-2 fewer ancilla.
4 of 5 daily submissions remain for 2026-10-27.

`notebooks/<version>/` holds the Kaggle notebook, kernel-metadata.json and NOTES.md for each submission from v6 on
(v1-v5 were built and uploaded by earlier sessions as zip files; their composition is in the table above).
`docs/` has the organisers' chemistry scoring README; `reference/` the public baseline notebook.
