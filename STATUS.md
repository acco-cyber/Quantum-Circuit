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
| v7 | 10-27 19:49 | **21.882** | busyaprime 'LB 21.88210' output, hash-pinned (invsqrt 63q, DQI R18 877q, chem V9 refit) - `notebooks/v7-busyaprime-21882` |
| v8 | 10-27 22:50 | **22.009** | somejoint 21.98 output: same as v7 but DQI 883q + 658-Toffoli jet (55.99x) - `notebooks/v8-somejoint-21976` |
| v9 | 10-28 00:45 | **22.129** | v8 + heliosli J5 chemistry refit (9.6055x, verified locally) - `notebooks/v9-helios-j5-chem-22129` |
| v10 | 10-28 02:05 | **22.276** | v9 + somejoint 897q DQI (57.87x, DQI verifier PASS locally) - `notebooks/v10-somejoint-897q-dqi-22339` |
| v11 | 10-28 04:05 | **22.340** | v10 + busyaprime 63q invsqrt v2 (102,664, verifier PASS locally) - `notebooks/v11-busyaprime-invsqrt-22340` |
| v12 | 10-28 05:58 | **22.375** | v11 + somejoint R8/B143 C62 chemistry 3.47715e8 (chem verifier PASS locally) - `notebooks/v12-somejoint-c62-chem-22375` |
| v13 | 10-28 08:52 | **22.573** | v12 + alexchilton 889q DQI 4.1478e11 (DQI verifier PASS locally x2 salts) - `notebooks/v13-alexchilton-889q-dqi-22510` |

Leaderboard 2026-10-27 00:32 UTC: 23.352 / 22.886 / 22.805 / 22.698 / 21.755. Our team: **rank 92 / 1171** at 19.579
(up from ~129 at 15.134). About 25 teams share the public plateau 19.5790 exactly; rank 3 needs > 22.80.

## Next (own work needed - no public part is ahead of v6)
* chemistry (7.86x, the small ratio): a new factorization fit with lower lambda_eff under the acceptance gates
  (Lambda > 49, E_gap > 3.9149 Ha) and fewer addressed vectors, then re-compile with the J=5 loaders. The dfthc-sos
  training library and verifier are in the competition data; lambda_eff x T x Q is the full cost, so a 10% lambda_eff
  cut is +3.2% on the score.
* dqi (49.4x): 883 qubits, cost ~ Q^2 x Toffolis; each qubit is -0.23% dqi cost, each 1% Toffoli cut is -1%.
* invsqrt (19.1x): 63 qubits / 1,404 mean Toffolis; cheaper polynomial phasing or 1-2 fewer ancilla.
2 of 5 daily submissions remain for 2026-10-27 (v6, v7, v8 used). Leaderboard 10-27 22:45: top 23.352.

`notebooks/<version>/` holds the Kaggle notebook, kernel-metadata.json and NOTES.md for each submission from v6 on
(v1-v5 were built and uploaded by earlier sessions as zip files; their composition is in the table above).
`docs/` has the organisers' chemistry scoring README; `reference/` the public baseline notebook.
| v14 | staged 10-28 11:50 | (proj. 22.630) | v13 + somejoint R8/B143 C60 full-XOR chemistry 3.45124e8 (verifier PASS locally) - **submit with first 10-29 slot** - `notebooks/v14-somejoint-fullxor-chem-22630` |
| v14 | 10-29 06:15 | pending (proj. 22.75-22.79) | heliosli 'dataset now public' release v28_gz9 (busyaprime 63q invsqrt 102,349; somejoint 897q DQI; somejoint R8/B143/C60 chem + heliosli angles + Gluzdov weights 3.4057e8) - supersedes the staged full-XOR v14 - `notebooks/v14-heliosli-v28-gz9-22787` |
| v15 | 10-30 11:57 | **23.000** | best-of: Ozer 62q invsqrt 100,940 + 889q DQI 7a378f47 4.084e11 + heliosli 10-30 chem 3.37994e8 (all PASS locally) - `notebooks/v15-bestof-23000` |

### 10-29 notes
* Quantum: every public portfolio now sits at ~22.78 (heliosli, kirilltym V22 22.78244 official - but kirilltym's loaders
  need bit7 = bit6 on the target, a narrower contract than general XOR; avoid), alexchilton v53 ~22.78. LB top 26.14 / 25.53 / 25.34.
  Chem gates all bind (error_1 = error_2 = 19.998 mHa, E_gap at floor, Lambda 304) -> W-only refits are exhausted; lambda_eff ~
  sqrt(2 Lambda E_gap), so the next real step is a lower-one-norm factorization U (new angle circuits). Remaining 10-29 quantum
  slots: hold for newer public releases or own circuits (resubmitting identical bytes gives the identical score).
* Smart Buildings: sb10 (gate 08:00) submitted 06:17 (slot 1/5). Next SB slots: wait for sb10 read-out, then gate 9.0/10.0 or back to 6.5.
