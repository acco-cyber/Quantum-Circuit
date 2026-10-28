# v10 - 2026-10-28 ~02:05 UTC (quantum slot 2 of 10-28)

Direct upload of the public output of `somejoint/quantum-circuits-22-34-local-gm-897-qubit-dqi`
(run 2026-10-28 01:30 UTC). Every member hash-checked against its `submission-members.sha256` (all OK).

| task | component | cost | ratio | vs v9 |
|---|---|---:|---:|---|
| invsqrt | mrmeows 63q (sha 0766a111) | 103,546 | 20.057 | byte-identical |
| dqi | "Astra Pro" 897q decoder + 658-Toffoli jet (sha b3354f60), 440,633 mean Toffolis | 4.2235e11 | 57.87 | was 883q ~4.36e11 / ~56.0 |
| dfthcsos | heliosli J5 on Ozer C46 table (sha ab4d2288) | 3.4934e8 | 9.6055 | byte-identical |

Local check in this session: official `verify_submission_dqi.py` + competition `kickmix.so`, two salts
(`local-check-1028b`, `local-check-1028c`) -> PASS, 0 value / 0 phase errors, score 4.22346e11.

Lesson: 14 more qubits (883 -> 897) bought ~3% fewer Toffolis -> net -3.2% DQI cost. Cost ~ Q x T here, so the
qubit/Toffoli trade-off in the decoder is still open. Expected public ~22.34. No GPU used.
