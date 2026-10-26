# Google Quantum AI - Verifiable Quantum Circuit Compilation

Working repo for the Kaggle competition
[google-verifiable-quantum-circuit-compilation](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation)
(deadline 2027-01-20, 982 teams). Paper: arXiv:2610.23832.

## Status (2026-10-26)

| Submission | Public score | Composition |
|---|---:|---|
| v1 (2026-10-26 04:06) | 12.131 | rebuilt public Round-13 pipeline (dmitriigluzdov sources, Apache-2.0): invsqrt 78q / 1,696 Teq, DQI 881q, dfthcsos R1/B496 |
| v2 (2026-10-26 04:13) | **13.713** | same invsqrt + DQI; dfthcsos replaced by michaelrustad R10 / B129 / C60 group-compressed factorisation (5.99x local) |

Leaderboard top (same day): 21.10 / 20.18 / 19.55. Our rank: ~129 / 982.

## How the score works

Score = geometric mean over the three benchmarks of `cost_reference / cost_submission`, with

* invsqrt: `Q x (Toffoli + T/4)` (reference Q 260, 7,735 Toffoli -> 2.08e6)
* DQI decoder: `Q^2 x Toffoli x repetition factor` (reference 2.44e13)
* dfthcsos (FeMoCo block encoding): modelled walk-step cost x lambda_eff (reference 3.36e9)

Each `.kmb` is checked by the organisers' kickmix fuzz-test verifier (Fiat-Shamir seeded inputs).

## Where the headroom is

* The chemistry benchmark (dfthcsos) is the weakest component (~6x vs ~16x for the other two). It is
  dominated by the DF-THC factorisation: fewer addressed vectors (R, B, C), tighter angle quantisation
  and lower lambda_eff all cut the modelled cost. This is an optimisation / training problem, not a
  circuit problem, and is where the top teams are pulling away.
* invsqrt: public best is 78 qubits / ~1,700 Toffoli-equivalents (signed-digit Horner, shared lookup).
  Gains now come from cheaper polynomial phasing and fewer ancilla.
* DQI: 881-qubit in-place continued-fraction decoder; remaining gains are in the GF(2^12) inversion count.

## Layout

* `reference/public_notebooks/` - public notebooks used as a baseline (credited, Apache-2.0).
* `docs/` - organisers' scoring README for the chemistry benchmark.
* `notebooks/` - our own notebooks, one folder per submission (added as they are made).
