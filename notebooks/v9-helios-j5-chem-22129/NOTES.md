# v9 - 2026-10-28 00:45 UTC (slot 1 of 10-28)

Direct upload of the public output of `heliosli/happy-to-make-the-dataset-public-if-it-useful`
(run 2026-10-28 00:11 UTC; archive sha256 `e97548f8b2a37937...`). Source notebook copied here as
`source-heliosli.ipynb` (its release dataset is private, so the kernel itself cannot be forked).

| task | component | cost | ratio | vs v8 |
|---|---|---:|---:|---|
| invsqrt | mrmeows 63q (sha 0766a111) | 103,546 | 20.057 | byte-identical |
| dqi | somejoint 883q + 658-Toffoli jet (sha ef334fee) | ~4.36e11 | ~56.0 | byte-identical |
| dfthcsos | Ozer C46 table, J=5 loaders, W/H2_I refit, lambda_eff 47.494, T 17,066, Q 431 | 3.4934e8 | 9.6055 | was 3.551e8 / 9.451 |

Local check in this session: official `dfthcsos.verify` (salt `local-check-1028`) -> PASS,
cost 349,339,717, lambda_eff 47.494, 17,066 Toffolis, 431 qubits. invsqrt/dqi not re-run (same bytes as the scored v8).

Expected public: 22.009 x (3.551/3.4934)^(1/3) = ~22.13.

Credits: heliosli, Ahmed Berat Ozer, Michael Rustad, mrmeows, marculera, lightningv08, somejoint (Agniv Banerjee). No GPU used.

## Lesson / next
Chemistry is still the weakest term (9.6x). The DQI cost moves with the salt; invsqrt is frozen across all public
portfolios. Top LB 25.6 implies private work on at least two tasks.
